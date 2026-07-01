"""Shared fixtures + helpers for the engine/catalog test suite.

Kept deliberately small and deterministic (fixed seeds, tiny arrays) so the
whole suite stays fast and its assertions can be exact (the engine is pure).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from gnode.core.context import NodeContext
from gnode.core.registry import discover

if TYPE_CHECKING:
    from collections.abc import Callable

# Populate the node registry once for the whole suite (idempotent).
discover()

# Small fixed fixture size shared across the suite.
H, W = 24, 32


def make_image(seed: int = 0, *, h: int = H, w: int = W) -> np.ndarray:
    """A deterministic IMAGE fixture: float32, [h, w, 3], 0..255."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(h, w, 3)).astype(np.float32)


def make_map(seed: int = 1, *, h: int = H, w: int = W) -> np.ndarray:
    """A deterministic MAP/MASK-shaped fixture: float32, [h, w], 0..255."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(h, w)).astype(np.float32)


def make_mask(seed: int = 2, *, h: int = H, w: int = W) -> np.ndarray:
    """A deterministic MASK fixture: float32, [h, w], 0..1."""
    rng = np.random.default_rng(seed)
    return rng.random(size=(h, w)).astype(np.float32)


class MemoryStore:
    """A tiny in-memory ``ImageStore`` for tests (satisfies the protocol)."""

    def __init__(self, images: dict[str, np.ndarray] | None = None) -> None:
        self.images: dict[str, np.ndarray] = dict(images or {})

    def load(self, image_id: str) -> np.ndarray:
        return self.images[image_id]

    def save(self, image_id: str, image: np.ndarray) -> None:
        self.images[image_id] = image


def node_ctx(
    *,
    node_id: str = "n",
    seed: int = 0,
    resolution: tuple[int, int] = (H, W),
    store: MemoryStore | None = None,
) -> NodeContext:
    """Build a ``NodeContext`` mirroring what the engine hands to ``evaluate``:
    an rng pre-seeded from ``seed`` (matching the engine in ``engine.py``)."""
    return NodeContext(
        node_id=node_id,
        seed=seed,
        resolution=resolution,
        rng=np.random.default_rng(np.random.SeedSequence(seed)),
        store=store,
    )


@pytest.fixture
def image() -> np.ndarray:
    return make_image()


@pytest.fixture
def image_factory() -> Callable[..., np.ndarray]:
    return make_image
