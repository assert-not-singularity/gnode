"""Preview encoding for the evaluate endpoint (plan §6).

Turns a node's output dict into a downscaled PNG data-URL: IMAGE outputs render
directly; 2-D MAP/MASK outputs are min-max normalized to a grayscale preview.
"""

from __future__ import annotations

import numpy as np

from gnode.core.image import to_png_dataurl
from gnode.server.schemas import NodePreview

_MAX_EDGE = 768


def _map_to_rgb(m: np.ndarray) -> np.ndarray:
    lo, hi = float(m.min()), float(m.max())
    norm = (m - lo) / (hi - lo) * 255.0 if hi > lo else np.zeros_like(m, dtype=np.float32)
    gray = norm.astype(np.float32)
    return np.stack([gray, gray, gray], axis=2)


def preview_of(outputs: dict[str, object]) -> NodePreview | None:
    """Pick a previewable output (prefer an IMAGE, else a MAP/MASK) and encode it."""
    for port, value in outputs.items():
        if isinstance(value, np.ndarray) and value.ndim == 3 and value.shape[2] == 3:
            height, width = value.shape[:2]
            return NodePreview(
                port=port,
                kind="image",
                data_url=to_png_dataurl(value, max_edge=_MAX_EDGE),
                width=width,
                height=height,
            )
    for port, value in outputs.items():
        if isinstance(value, np.ndarray) and value.ndim == 2:
            height, width = value.shape
            return NodePreview(
                port=port,
                kind="map",
                data_url=to_png_dataurl(_map_to_rgb(value), max_edge=_MAX_EDGE),
                width=width,
                height=height,
            )
    return None
