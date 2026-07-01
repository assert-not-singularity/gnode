"""IMAGE/MASK helpers, convention guards, and PNG encoding (plan §3.1, §6).

Pure — no filesystem access. File read/write lives in a driven adapter
(``gnode.adapters``); this module only converts between arrays, PIL images, and
PNG bytes, and enforces the array conventions at node boundaries.
"""

from __future__ import annotations

import base64
from io import BytesIO

import numpy as np
from PIL import Image

from gnode.core.errors import NodeContractError


def ensure_image(x: object, *, where: str = "image") -> np.ndarray:
    """Assert an IMAGE convention: float32, [H, W, 3]. Returns the array."""
    if not isinstance(x, np.ndarray):
        raise NodeContractError(f"{where}: expected numpy array, got {type(x).__name__}")
    if x.dtype != np.float32:
        raise NodeContractError(f"{where}: expected float32, got {x.dtype}")
    if x.ndim != 3 or x.shape[2] != 3:
        raise NodeContractError(f"{where}: expected [H, W, 3], got shape {x.shape}")
    return x


def ensure_mask(x: object, *, where: str = "mask") -> np.ndarray:
    """Assert a MASK/MAP convention: float32, [H, W]. Returns the array."""
    if not isinstance(x, np.ndarray):
        raise NodeContractError(f"{where}: expected numpy array, got {type(x).__name__}")
    if x.dtype != np.float32:
        raise NodeContractError(f"{where}: expected float32, got {x.dtype}")
    if x.ndim != 2:
        raise NodeContractError(f"{where}: expected [H, W], got shape {x.shape}")
    return x


def to_uint8(img: np.ndarray) -> np.ndarray:
    """Clip to 0..255 and cast to uint8 (the only place we clip — for output)."""
    return np.clip(img, 0, 255).astype(np.uint8)


def from_pil(im: Image.Image) -> np.ndarray:
    """PIL image → IMAGE array (RGB, float32, 0..255)."""
    return np.asarray(im.convert("RGB")).astype(np.float32)


def decode_image_bytes(data: bytes) -> np.ndarray:
    """Encoded image bytes (PNG/JPEG/…) → IMAGE array."""
    return from_pil(Image.open(BytesIO(data)))


def fit(img: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Resize an IMAGE to ``(H, W)`` with Lanczos (used by Load and previews)."""
    h, w = size
    im = Image.fromarray(to_uint8(ensure_image(img)), "RGB").resize(
        (w, h), Image.Resampling.LANCZOS
    )
    return from_pil(im)


def to_png_bytes(img: np.ndarray, max_edge: int | None = None) -> bytes:
    """Encode an IMAGE as PNG bytes, optionally downscaled to ``max_edge`` px."""
    im = Image.fromarray(to_uint8(ensure_image(img)), "RGB")
    if max_edge is not None:
        im.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    buf = BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def to_png_dataurl(img: np.ndarray, max_edge: int | None = None) -> str:
    """Encode an IMAGE as a ``data:image/png;base64,…`` URL for previews."""
    return "data:image/png;base64," + base64.b64encode(to_png_bytes(img, max_edge)).decode("ascii")
