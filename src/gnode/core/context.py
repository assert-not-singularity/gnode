"""Evaluation context (plan §3.2, §3.5).

Two thin dataclasses:

* ``Context`` — graph-level, passed to ``Engine.evaluate`` (global seed, target
  resolution, injected image store, progress + cancellation).
* ``NodeContext`` — per-node, built by the engine and handed to ``evaluate``. It
  carries a *pre-seeded* rng and the resolved seed so nodes never re-implement
  seed precedence and never touch global ``np.random``.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from gnode.core import rng
from gnode.core.errors import EvaluationCancelledError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import Any

    import numpy as np

    from gnode.core.ports import ImageStore


@dataclass
class CancellationToken:
    """Cooperative cancellation for superseded live-preview evaluations."""

    _event: threading.Event = field(default_factory=threading.Event)

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise EvaluationCancelledError


@dataclass
class Context:
    """Graph-level evaluation context passed to ``Engine.evaluate``."""

    seed: int = 0
    resolution: tuple[int, int] = (768, 768)
    store: ImageStore | None = None
    progress: Callable[[str, float], None] | None = None
    cancel: CancellationToken = field(default_factory=CancellationToken)

    def resolve_seed(
        self, node_id: str, inputs: Mapping[str, Any] | None = None, param_seed: int | None = None
    ) -> int:
        """Seed precedence (plan §5): wired ``SEED`` input > param seed > derived
        from the global seed and node id."""
        wired = inputs.get("seed") if inputs else None
        if wired is not None:
            return int(wired)
        if param_seed is not None:
            return int(param_seed)
        return rng.derive_seed(self.seed, node_id)


@dataclass
class NodeContext:
    """Per-node context handed to ``evaluate``."""

    node_id: str
    seed: int
    resolution: tuple[int, int]
    rng: np.random.Generator
    store: ImageStore | None = None
    progress: Callable[[str, float], None] | None = None
    cancel: CancellationToken = field(default_factory=CancellationToken)
