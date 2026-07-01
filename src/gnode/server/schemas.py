"""Request/response models for the gnode API (plan §6)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from gnode.core.graph import Graph


class ValidationResponse(BaseModel):
    """Result of ``POST /api/validate``."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ImageUploadResponse(BaseModel):
    """Result of ``POST /api/images``."""

    image_id: str
    width: int
    height: int


class NodePreview(BaseModel):
    """A rendered preview of one node's output."""

    port: str
    kind: str  # "image" | "map"
    data_url: str
    width: int
    height: int


class EvaluateRequest(BaseModel):
    """Body of ``POST /api/evaluate``."""

    graph: Graph
    targets: list[str]


class EvaluateResponse(BaseModel):
    """Previews per requested target, plus any per-node evaluation error."""

    previews: dict[str, NodePreview] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)


class GraphFileInfo(BaseModel):
    """A saved ``.gnode`` file in the workspace."""

    name: str
    filename: str


class SaveGraphRequest(BaseModel):
    """Body of ``POST /api/graphs``."""

    filename: str
    graph: Graph


class SaveGraphResult(BaseModel):
    filename: str
