"""FastAPI application factory for the gnode service (plan §6).

Endpoints so far: the node catalog, graph validation, and image upload/serve.
Evaluate/preview and the graph workspace land in later work items.
"""

from __future__ import annotations

import os
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from gnode.core import registry
from gnode.core.graph import Graph  # noqa: TC001 — FastAPI resolves this annotation at runtime
from gnode.core.image import decode_image_bytes
from gnode.core.validation import validate_graph
from gnode.server.schemas import ImageUploadResponse, ValidationResponse
from gnode.server.workspace import Workspace

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# Vite dev server origins (frontend, M3). The built SPA is served same-origin.
_DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
_DEFAULT_WORKSPACE = ".gnode-workspace"
_IMAGE_ID_RE = re.compile(r"[A-Za-z0-9]+\.[A-Za-z0-9]+")
_ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Cache the node catalog and open the workspace at startup."""
    registry.discover()
    app.state.catalog = registry.catalog()
    app.state.workspace = Workspace(app.state.workspace_root)
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
        data = await file.read()
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

    return app


app = create_app()
