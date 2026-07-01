"""Driven adapters (filesystem). Kept out of the pure ``core`` — the engine and
nodes depend only on the ``ImageStore`` protocol (``gnode.core.ports``)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

from gnode.core.image import from_pil, to_uint8

if TYPE_CHECKING:
    import numpy as np


class FilesystemImageStore:
    """An ``ImageStore`` backed by files. ``image_id`` is a path; relative ids are
    resolved against ``root`` (e.g. the directory of the ``.gnode`` file)."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else None

    def _resolve(self, image_id: str) -> Path:
        path = Path(image_id)
        if path.is_absolute() or self.root is None:
            return path
        return self.root / path

    def load(self, image_id: str) -> np.ndarray:
        return from_pil(Image.open(self._resolve(image_id)))

    def save(self, image_id: str, image: np.ndarray) -> None:
        path = self._resolve(image_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(to_uint8(image), "RGB").save(path)
