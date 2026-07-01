"""Server workspace — on-disk ``images/`` and ``graphs/`` directories (plan §6).

Uploaded images and saved ``.gnode`` graphs live here so the server is a real
local tool. The workspace image store is *confined to the images directory* and
only accepts bare, validated ids — so Load/Save nodes driven by untrusted graph
input can't read or write outside the workspace (unlike the path-resolving
``FilesystemImageStore`` the CLI uses on trusted local paths).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from PIL import Image

from gnode.core.image import from_pil, to_uint8

if TYPE_CHECKING:
    from pathlib import Path

    import numpy as np


class WorkspaceImageStore:
    """An ``ImageStore`` confined to ``images_dir``. ``image_id`` must be a bare
    filename (no separators / traversal); ids that escape the directory raise."""

    _ID_RE = re.compile(r"[A-Za-z0-9._-]+")

    def __init__(self, images_dir: Path) -> None:
        self._dir = images_dir

    def _resolve(self, image_id: str) -> Path:
        if not self._ID_RE.fullmatch(image_id):
            raise ValueError(f"invalid image id: {image_id!r}")
        path = (self._dir / image_id).resolve()
        if path.parent != self._dir.resolve():
            raise ValueError(f"image id escapes the workspace: {image_id!r}")
        return path

    def load(self, image_id: str) -> np.ndarray:
        return from_pil(Image.open(self._resolve(image_id)))

    def save(self, image_id: str, image: np.ndarray) -> None:
        Image.fromarray(to_uint8(image), "RGB").save(self._resolve(image_id))


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.images_dir = root / "images"
        self.graphs_dir = root / "graphs"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.graphs_dir.mkdir(parents=True, exist_ok=True)
        self.image_store = WorkspaceImageStore(self.images_dir)
