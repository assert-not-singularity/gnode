"""Evaluation context (plan §3.2, §3.5).

A thin data holder + rng factory passed to every ``evaluate``. Deliberately
small: it carries the global seed, target resolution, an optional progress
callback, and a cancellation token — nothing node-specific.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from gnode.core import rng
from gnode.core.errors import EvaluationCancelledError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    import numpy as np


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
    seed: int = 0
    resolution: tuple[int, int] = (768, 768)
    progress: Callable[[str, float], None] | None = None
    cancel: CancellationToken = field(default_factory=CancellationToken)

    def rng_for(self, node_id: str, node_seed: int | None = None) -> np.random.Generator:
        return rng.rng_for(self.seed, node_id, node_seed)

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
