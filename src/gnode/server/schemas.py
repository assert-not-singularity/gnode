"""Request/response models for the gnode API (plan §6)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ValidationResponse(BaseModel):
    """Result of ``POST /api/validate``."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
