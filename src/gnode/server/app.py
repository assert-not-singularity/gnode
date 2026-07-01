"""FastAPI application factory for the gnode service (plan §6).

Read endpoints land here first: the node catalog and graph validation. Image,
evaluate, and graph-workspace endpoints are added in later work items.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gnode.core import registry
from gnode.core.graph import Graph  # noqa: TC001 — FastAPI resolves this annotation at runtime
from gnode.core.validation import validate_graph
from gnode.server.schemas import ValidationResponse

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# Vite dev server origins (frontend, M3). The built SPA is served same-origin.
_DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Discover nodes once and cache the catalog at startup."""
    registry.discover()
    app.state.catalog = registry.catalog()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="gnode", version="0.1.0", lifespan=_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_DEV_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/nodes")
    def list_nodes() -> list[dict[str, Any]]:
        """The node catalog: typed ports + params JSON Schema per node."""
        return app.state.catalog

    @app.post("/api/validate", response_model=ValidationResponse)
    def validate(graph: Graph) -> ValidationResponse:
        """Validate a graph — ports, types, cycles, required inputs, params."""
        result = validate_graph(graph)
        return ValidationResponse(
            valid=result.valid, errors=result.errors, warnings=result.warnings
        )

    return app


app = create_app()
