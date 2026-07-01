"""Server workspace — on-disk ``images/`` and ``graphs/`` directories (plan §6).

Uploaded images and saved ``.gnode`` graphs live here so the server is a real
local tool. The image store implements the engine's ``ImageStore`` protocol, so
Load/Save nodes resolve ids against the same directory the upload endpoint writes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gnode.adapters import FilesystemImageStore

if TYPE_CHECKING:
    from pathlib import Path


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.images_dir = root / "images"
        self.graphs_dir = root / "graphs"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.graphs_dir.mkdir(parents=True, exist_ok=True)
        self.image_store = FilesystemImageStore(self.images_dir)
