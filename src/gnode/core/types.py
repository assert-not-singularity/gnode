"""Port types and image conventions (plan §3.1).

Conventions pinned here and enforced in ``image.py``: an ``IMAGE`` is float32,
RGB, 0..255, origin top-left, axis 0 = rows (y), axis 1 = cols (x). Clip only at
the output/save node.
"""

from __future__ import annotations

from enum import StrEnum


class PortType(StrEnum):
    """The typed-port vocabulary. ``StrEnum`` so values serialize as plain
    strings in the catalog and ``.gnode`` JSON."""

    IMAGE = "IMAGE"
    MASK = "MASK"
    MAP = "MAP"
    FIELD = "FIELD"
    INT = "INT"
    FLOAT = "FLOAT"
    BOOL = "BOOL"
    VEC2 = "VEC2"
    COLOR = "COLOR"
    ENUM = "ENUM"
    SEED = "SEED"
    STRING = "STRING"
    ANY = "ANY"


# Per-type wire/handle colour hints for the frontend (plan §3.1). The backend
# ships these in the catalog; the UI reads them so wire compatibility is legible.
TYPE_COLORS: dict[PortType, str] = {
    PortType.IMAGE: "#e2e8f0",
    PortType.MASK: "#a3a3a3",
    PortType.MAP: "#38bdf8",
    PortType.FIELD: "#f472b6",
    PortType.INT: "#4ade80",
    PortType.FLOAT: "#22c55e",
    PortType.BOOL: "#eab308",
    PortType.VEC2: "#c084fc",
    PortType.COLOR: "#fb7185",
    PortType.ENUM: "#f59e0b",
    PortType.SEED: "#f97316",
    PortType.STRING: "#94a3b8",
    PortType.ANY: "#64748b",
}

# Image array conventions.
IMAGE_MAX: float = 255.0
