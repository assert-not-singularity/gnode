"""Driven-adapter protocols (plan §2, §3).

The pure core depends on these interfaces, never on concrete disk/web
implementations. Load/Save nodes reach the outside world through an injected
``ImageStore``; the engine reaches the cache through ``Cache``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import numpy as np


@runtime_checkable
class ImageStore(Protocol):
    """Where Load/Save nodes read/write image arrays, keeping disk I/O out of the
    pure core. Implementations: an in-memory store (tests) or a filesystem store
    (CLI/server)."""

    def load(self, image_id: str) -> np.ndarray: ...

    def save(self, image_id: str, image: np.ndarray) -> None: ...


@runtime_checkable
class Cache(Protocol):
    """Structural-key → node output-dict cache (plan §3.4)."""

    def get(self, key: str) -> dict | None: ...

    def put(self, key: str, value: dict) -> None: ...
