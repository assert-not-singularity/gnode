"""FastAPI application factory for the gnode service (plan §6).

Endpoints so far: the node catalog, graph validation, and image upload/serve.
Evaluate/preview and the graph workspace land in later work items.
"""

from __future__ import annotations

import asyncio
import os
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import ValidationError

from gnode.core import registry
from gnode.core.context import Context
from gnode.core.engine import Engine
from gnode.core.errors import NodeContractError, NodeEvalError
from gnode.core.graph import Graph, dump_graph, load_graph_file
from gnode.core.image import decode_image_bytes
from gnode.core.validation import validate_graph
from gnode.server.preview import preview_of
from gnode.server.schemas import (
    EvaluateRequest,
    EvaluateResponse,
    GraphFileInfo,
    ImageUploadResponse,
    SaveGraphRequest,
    SaveGraphResult,
    ValidationResponse,
)
from gnode.server.workspace import Workspace

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# Vite dev server origins (frontend, M3). The built SPA is served same-origin.
_DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
_DEFAULT_WORKSPACE = ".gnode-workspace"
_ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
# Serve only ids with a known image extension (mirrors _ALLOWED_EXT).
_IMAGE_ID_RE = re.compile(r"[A-Za-z0-9]+\.(?:png|jpg|jpeg|webp|bmp)")
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
_GRAPH_FILE_RE = re.compile(r"[A-Za-z0-9._-]+\.gnode")


def _safe_path(directory: Path, filename: str, pattern: re.Pattern[str]) -> Path:
    """Resolve ``filename`` inside ``directory``, rejecting bad names or traversal."""
    if not pattern.fullmatch(filename):
        raise HTTPException(status_code=400, detail="invalid filename")
    path = (directory / filename).resolve()
    if path.parent != directory.resolve():
        raise HTTPException(status_code=400, detail="invalid filename")
    return path


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Cache the node catalog and open the workspace at startup."""
    registry.discover()
    app.state.catalog = registry.catalog()
    app.state.workspace = Workspace(app.state.workspace_root)
    app.state.engine = Engine()  # persistent cache reused across requests
    yield


def create_app(workspace: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="gnode", version="0.1.0", lifespan=_lifespan)
    app.state.workspace_root = Path(
        workspace or os.environ.get("GNODE_WORKSPACE", _DEFAULT_WORKSPACE)
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_DEV_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/nodes")
    def list_nodes(request: Request) -> list[dict[str, Any]]:
        """The node catalog: typed ports + params JSON Schema per node."""
        return request.app.state.catalog

    @app.post("/api/validate", response_model=ValidationResponse)
    def validate(graph: Graph) -> ValidationResponse:
        """Validate a graph — ports, types, cycles, required inputs, params."""
        result = validate_graph(graph)
        return ValidationResponse(
            valid=result.valid, errors=result.errors, warnings=result.warnings
        )

    @app.post("/api/images", response_model=ImageUploadResponse)
    async def upload_image(request: Request, file: UploadFile) -> ImageUploadResponse:
        """Store an uploaded image and return a generated id + dimensions."""
        data = await file.read(_MAX_UPLOAD_BYTES + 1)
        if len(data) > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="image too large")
        try:
            image = decode_image_bytes(data)
        except Exception as exc:  # PIL raises assorted types on bad input
            raise HTTPException(status_code=400, detail="not a decodable image") from exc
        ext = Path(file.filename or "").suffix.lower()
        if ext not in _ALLOWED_EXT:
            ext = ".png"
        image_id = f"{uuid.uuid4().hex}{ext}"
        (request.app.state.workspace.images_dir / image_id).write_bytes(data)
        height, width = image.shape[:2]
        return ImageUploadResponse(image_id=image_id, width=width, height=height)

    @app.get("/api/images/{image_id}")
    def get_image(image_id: str, request: Request) -> FileResponse:
        """Serve a previously uploaded image by id (ids are validated, not paths)."""
        if not _IMAGE_ID_RE.fullmatch(image_id):
            raise HTTPException(status_code=400, detail="invalid image id")
        path = request.app.state.workspace.images_dir / image_id
        if not path.is_file():
            raise HTTPException(status_code=404, detail="image not found")
        return FileResponse(path)

    @app.post("/api/evaluate", response_model=EvaluateResponse)
    async def evaluate(req: EvaluateRequest, request: Request) -> EvaluateResponse:
        """Evaluate the graph for the requested targets, returning preview PNGs.

        The CPU-bound engine runs in a threadpool so the event loop stays free;
        the persistent engine cache is reused across requests (fast slider drags).
        """
        result = validate_graph(req.graph)
        if not result.valid:
            raise HTTPException(status_code=400, detail={"errors": result.errors})
        node_ids = {n.id for n in req.graph.nodes}
        missing = [t for t in req.targets if t not in node_ids]
        if missing:
            raise HTTPException(
                status_code=400, detail={"errors": [f"unknown target '{t}'" for t in missing]}
            )

        engine: Engine = request.app.state.engine
        ctx = Context(
            seed=req.graph.meta.seed,
            resolution=tuple(req.graph.meta.resolution),
            store=request.app.state.workspace.image_store,
        )
        loop = asyncio.get_running_loop()
        try:
            outputs = await loop.run_in_executor(None, engine.evaluate, req.graph, req.targets, ctx)
        except NodeEvalError as exc:
            return EvaluateResponse(errors={exc.node_id: str(exc)})
        except NodeContractError as exc:
            return EvaluateResponse(errors={exc.node_id or "graph": str(exc)})

        previews = {
            node_id: preview
            for node_id, node_out in outputs.items()
            if (preview := preview_of(node_out)) is not None
        }
        return EvaluateResponse(previews=previews)

    @app.get("/api/graphs", response_model=list[GraphFileInfo])
    def list_graphs(request: Request) -> list[GraphFileInfo]:
        """List the saved ``.gnode`` files in the workspace (regular files only)."""
        graphs_dir: Path = request.app.state.workspace.graphs_dir
        resolved = graphs_dir.resolve()
        return [
            GraphFileInfo(name=p.stem, filename=p.name)
            for p in sorted(graphs_dir.glob("*.gnode"))
            if p.is_file() and p.resolve().parent == resolved
        ]

    @app.post("/api/graphs", response_model=SaveGraphResult, status_code=201)
    def save_graph(req: SaveGraphRequest, request: Request) -> SaveGraphResult:
        """Save a graph to ``workspace/graphs/<filename>`` (validated filename)."""
        path = _safe_path(
            request.app.state.workspace.graphs_dir, req.filename.strip(), _GRAPH_FILE_RE
        )
        if path.exists() and not path.is_file():
            raise HTTPException(status_code=400, detail="target exists and is not a file")
        path.write_text(dump_graph(req.graph), encoding="utf-8")
        return SaveGraphResult(filename=path.name)

    @app.get("/api/graphs/{filename}", response_model=Graph)
    def get_graph(filename: str, request: Request) -> Graph:
        """Load a saved ``.gnode`` file and return the graph."""
        path = _safe_path(request.app.state.workspace.graphs_dir, filename, _GRAPH_FILE_RE)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="graph not found")
        try:
            return load_graph_file(path)
        except (ValueError, ValidationError) as exc:
            raise HTTPException(status_code=400, detail="invalid .gnode file") from exc

    return app


app = create_app()
