"""Node robustness regressions."""

from __future__ import annotations

import numpy as np

from gnode.core.context import Context
from gnode.core.engine import Engine
from gnode.core.graph import Graph


class _Mem:
    def __init__(self, image: np.ndarray) -> None:
        self.image = image

    def load(self, image_id: str) -> np.ndarray:
        return self.image

    def save(self, image_id: str, image: np.ndarray) -> None:
        pass


def test_block_mosh_small_image_does_not_crash() -> None:
    """A 200px-wide image with the default max_w=260 must not broadcast-crash."""
    image = (np.random.default_rng(0).random((128, 200, 3)) * 255).astype(np.float32)
    graph = Graph.model_validate(
        {
            "meta": {"seed": 1, "resolution": [128, 200]},
            "nodes": [
                {"id": "load", "type": "io.load_image", "params": {"image_id": "x"}},
                {"id": "mosh", "type": "displace.block_mosh", "params": {}},
                {"id": "view", "type": "io.viewer", "params": {}},
            ],
            "edges": [
                {"from": ["load", "image"], "to": ["mosh", "image"]},
                {"from": ["mosh", "image"], "to": ["view", "image"]},
            ],
        }
    )
    ctx = Context(seed=1, resolution=(128, 200), store=_Mem(image))
    out = Engine().evaluate(graph, ["view"], ctx)
    assert out["view"]["image"].shape == (128, 200, 3)
