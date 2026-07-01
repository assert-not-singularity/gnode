"""Core engine integration tests: evaluation, caching, determinism, seed
precedence, cycle detection, and structural-key canonicalization. Uses throwaway
``_test.*`` nodes registered here (the real catalog lands separately)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from gnode.core.cache import structural_key
from gnode.core.engine import Engine
from gnode.core.errors import GraphError
from gnode.core.graph import Graph
from gnode.core.node import In, Node, NodeParams
from gnode.core.params import Slider
from gnode.core.registry import register_node
from gnode.core.types import PortType

CALLS = {"const": 0, "add": 0, "noise": 0}


@register_node
class _Const(Node):
    type = "_test.const"
    category = "Test"
    title = "Const"
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        value: float = 10.0

    def evaluate(self, inputs, params, ctx):
        CALLS["const"] += 1
        h, w = ctx.resolution
        return {"image": np.full((h, w, 3), params.value, dtype=np.float32)}


@register_node
class _Add(Node):
    type = "_test.add"
    category = "Test"
    title = "Add"
    inputs = {"image": In(PortType.IMAGE)}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        amount: float = Slider(5.0, min=0, max=255, step=1)

    def evaluate(self, inputs, params, ctx):
        CALLS["add"] += 1
        return {"image": inputs["image"] + params.amount}


@register_node
class _Noise(Node):
    type = "_test.noise"
    category = "Test"
    title = "Noise"
    inputs = {"image": In(PortType.IMAGE)}
    outputs = {"image": PortType.IMAGE}
    uses_seed = True

    class Params(NodeParams):
        seed: int | None = None
        amount: float = 10.0

    def evaluate(self, inputs, params, ctx):
        CALLS["noise"] += 1
        noise = ctx.rng.normal(0.0, params.amount, inputs["image"].shape).astype(np.float32)
        return {"image": inputs["image"] + noise}


def _graph(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], *, seed: int = 1) -> Graph:
    return Graph.model_validate(
        {"meta": {"seed": seed, "resolution": [8, 8]}, "nodes": nodes, "edges": edges}
    )


def _chain(seed: int = 1, amount: float = 3.0) -> Graph:
    return _graph(
        nodes=[
            {"id": "a", "type": "_test.const", "params": {"value": 10.0}},
            {"id": "b", "type": "_test.add", "params": {"amount": amount}},
        ],
        edges=[{"from": ["a", "image"], "to": ["b", "image"]}],
        seed=seed,
    )


def test_evaluate_chain() -> None:
    out = Engine().evaluate(_chain(), ["b"])
    assert out["b"]["image"].shape == (8, 8, 3)
    assert np.allclose(out["b"]["image"], 13.0)


def test_cache_avoids_recompute() -> None:
    CALLS["const"] = CALLS["add"] = 0
    engine = Engine()
    graph = _chain()
    engine.evaluate(graph, ["b"])
    engine.evaluate(graph, ["b"])  # identical key -> cache hit, no recompute
    assert CALLS["add"] == 1
    assert CALLS["const"] == 1


def test_param_change_invalidates_only_downstream() -> None:
    CALLS["const"] = CALLS["add"] = 0
    engine = Engine()
    engine.evaluate(_chain(amount=3.0), ["b"])
    engine.evaluate(_chain(amount=9.0), ["b"])  # change downstream node only
    assert CALLS["const"] == 1  # source unchanged -> still cached
    assert CALLS["add"] == 2  # downstream recomputed


def test_determinism_across_engines() -> None:
    graph = _graph(
        nodes=[
            {"id": "a", "type": "_test.const"},
            {"id": "n", "type": "_test.noise", "params": {"amount": 12.0}},
        ],
        edges=[{"from": ["a", "image"], "to": ["n", "image"]}],
        seed=5,
    )
    first = Engine().evaluate(graph, ["n"])["n"]["image"]
    second = Engine().evaluate(graph, ["n"])["n"]["image"]
    assert np.array_equal(first, second)


def test_seed_reroll_changes_output() -> None:
    def run(seed: int) -> np.ndarray:
        graph = _graph(
            nodes=[
                {"id": "a", "type": "_test.const"},
                {"id": "n", "type": "_test.noise"},
            ],
            edges=[{"from": ["a", "image"], "to": ["n", "image"]}],
            seed=seed,
        )
        return Engine().evaluate(graph, ["n"])["n"]["image"]

    assert not np.array_equal(run(1), run(2))


def test_cycle_detection() -> None:
    graph = _graph(
        nodes=[
            {"id": "x", "type": "_test.add"},
            {"id": "y", "type": "_test.add"},
        ],
        edges=[
            {"from": ["x", "image"], "to": ["y", "image"]},
            {"from": ["y", "image"], "to": ["x", "image"]},
        ],
    )
    with pytest.raises(GraphError):
        Engine().evaluate(graph, ["x"])


def test_structural_key_canonicalization() -> None:
    base = structural_key("t", {"a": 1, "b": 2.0}, {}, (8, 8))
    # key ordering is irrelevant
    assert base == structural_key("t", {"b": 2.0, "a": 1}, {}, (8, 8))
    # seed and float-vs-int are distinguishing
    assert base != structural_key("t", {"a": 1, "b": 2.0}, {}, (8, 8), seed=1)
    assert structural_key("t", {"a": 1.0}, {}, (8, 8)) != structural_key("t", {"a": 1}, {}, (8, 8))
