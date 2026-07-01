"""Cache-key hardening (plan §5, top priority — a false hit returns the WRONG
image).

Two layers:

* ``structural_key`` canonicalization — param key ordering is irrelevant, but
  float-vs-int, nested ordering, seed, resolution, inputs, code_hash and the
  engine version salt must all be *distinguishing*. A collision here is the
  system's worst failure.
* an invalidation matrix on a small 3-node chain — changing a node's param
  invalidates that node and its descendants (measured via instrumented eval
  counts) while unrelated branches keep hitting the cache.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from gnode.core import cache as cache_mod
from gnode.core.cache import LRUCache, structural_key
from gnode.core.engine import Engine
from gnode.core.graph import Graph
from gnode.core.node import In, Node, NodeParams
from gnode.core.params import Slider
from gnode.core.registry import register_node
from gnode.core.types import PortType

if TYPE_CHECKING:
    import pytest

# ── structural_key canonicalization ───────────────────────────────────────────

RES = (8, 8)


def test_param_key_ordering_irrelevant() -> None:
    a = structural_key("t", {"a": 1, "b": 2, "c": 3}, {}, RES)
    b = structural_key("t", {"c": 3, "b": 2, "a": 1}, {}, RES)
    assert a == b


def test_float_vs_int_distinct() -> None:
    assert structural_key("t", {"x": 1}, {}, RES) != structural_key("t", {"x": 1.0}, {}, RES)


def test_float_repr_stable_but_value_sensitive() -> None:
    # Same float value → same key; a nearby distinct value → different key.
    assert structural_key("t", {"x": 0.1}, {}, RES) == structural_key("t", {"x": 0.1}, {}, RES)
    assert structural_key("t", {"x": 0.1}, {}, RES) != structural_key(
        "t", {"x": 0.10000000001}, {}, RES
    )


def test_nested_dict_ordering_irrelevant() -> None:
    a = structural_key("t", {"d": {"p": 1, "q": 2}}, {}, RES)
    b = structural_key("t", {"d": {"q": 2, "p": 1}}, {}, RES)
    assert a == b


def test_list_ordering_is_significant() -> None:
    # Lists are ordered data (e.g. gradient stops) — reordering must change the key.
    assert structural_key("t", {"stops": [1, 2, 3]}, {}, RES) != structural_key(
        "t", {"stops": [3, 2, 1]}, {}, RES
    )


def test_node_type_distinct() -> None:
    assert structural_key("a", {}, {}, RES) != structural_key("b", {}, {}, RES)


def test_resolution_distinct() -> None:
    assert structural_key("t", {}, {}, (8, 8)) != structural_key("t", {}, {}, (8, 16))


def test_seed_distinct_and_none_is_baseline() -> None:
    base = structural_key("t", {}, {}, RES)
    assert base == structural_key("t", {}, {}, RES, seed=None)
    assert base != structural_key("t", {}, {}, RES, seed=0)
    assert structural_key("t", {}, {}, RES, seed=0) != structural_key("t", {}, {}, RES, seed=1)


def test_code_hash_distinct() -> None:
    base = structural_key("t", {}, {}, RES)
    assert base != structural_key("t", {}, {}, RES, code_hash="abc")
    assert structural_key("t", {}, {}, RES, code_hash="abc") != structural_key(
        "t", {}, {}, RES, code_hash="def"
    )


def test_input_keys_distinct() -> None:
    assert structural_key("t", {}, {"image": "k1#image"}, RES) != structural_key(
        "t", {}, {"image": "k2#image"}, RES
    )
    # Same upstream key but a different source port must differ too.
    assert structural_key("t", {}, {"image": "k#a"}, RES) != structural_key(
        "t", {}, {"image": "k#b"}, RES
    )


def test_input_port_binding_distinct() -> None:
    # The same upstream key wired into a different input port is a different node.
    assert structural_key("t", {}, {"a": "k#o"}, RES) != structural_key("t", {}, {"b": "k#o"}, RES)


def test_version_salt_invalidates(monkeypatch: pytest.MonkeyPatch) -> None:
    before = structural_key("t", {"x": 1}, {}, RES)
    monkeypatch.setattr(cache_mod, "ENGINE_CACHE_VERSION", "999")
    after = structural_key("t", {"x": 1}, {}, RES)
    assert before != after


def test_bool_vs_int_distinct() -> None:
    # JSON renders True as "true", not "1" — the danger is a canonicalizer that
    # coerces. Guard that bool and its int form stay distinct.
    assert structural_key("t", {"x": True}, {}, RES) != structural_key("t", {"x": 1}, {}, RES)


def test_no_accidental_collisions_over_a_grid() -> None:
    # Distinct param/seed/resolution combinations must all map to distinct keys.
    keys = set()
    for typ in ("a", "b"):
        for val in (0, 1, 1.0, 2):
            for seed in (None, 0, 1):
                for res in ((8, 8), (8, 16)):
                    keys.add(structural_key(typ, {"v": val}, {}, res, seed=seed))
    assert len(keys) == 2 * 4 * 3 * 2


# ── LRUCache behaviour ─────────────────────────────────────────────────────────


def test_lru_evicts_oldest() -> None:
    lru = LRUCache(maxsize=2)
    lru.put("a", {"v": 1})
    lru.put("b", {"v": 2})
    lru.get("a")  # touch a → b is now oldest
    lru.put("c", {"v": 3})  # evicts b
    assert lru.get("a") is not None
    assert lru.get("b") is None
    assert lru.get("c") is not None


def test_compute_if_absent_computes_once() -> None:
    lru = LRUCache()
    calls = {"n": 0}

    def factory() -> dict:
        calls["n"] += 1
        return {"v": 1}

    first = lru.compute_if_absent("k", factory)
    second = lru.compute_if_absent("k", factory)
    assert first is second
    assert calls["n"] == 1


# ── invalidation matrix on a 3-node chain ─────────────────────────────────────

_CACHE_CALLS = {"src_a": 0, "src_b": 0, "add": 0, "combine": 0}


@register_node
class _CacheSource(Node):
    type = "_test.cache_source"
    category = "Test"
    title = "Cache Source"
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        value: float = 10.0
        tag: str = "a"

    def evaluate(self, inputs, params, ctx):
        _CACHE_CALLS[f"src_{params.tag}"] += 1
        h, w = ctx.resolution
        return {"image": np.full((h, w, 3), params.value, dtype=np.float32)}


@register_node
class _CacheAdd(Node):
    type = "_test.cache_add"
    category = "Test"
    title = "Cache Add"
    inputs = {"image": In(PortType.IMAGE)}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        amount: float = Slider(5.0, min=0, max=255, step=1)

    def evaluate(self, inputs, params, ctx):
        _CACHE_CALLS["add"] += 1
        return {"image": inputs["image"] + params.amount}


@register_node
class _CacheCombine(Node):
    type = "_test.cache_combine"
    category = "Test"
    title = "Cache Combine"
    inputs = {"a": In(PortType.IMAGE), "b": In(PortType.IMAGE)}
    outputs = {"image": PortType.IMAGE}

    def evaluate(self, inputs, params, ctx):
        _CACHE_CALLS["combine"] += 1
        return {"image": inputs["a"] + inputs["b"]}


def _diamond(*, a_val: float = 10.0, b_val: float = 20.0, add_amount: float = 5.0) -> Graph:
    """src_a → add ─┐
    src_b ──────────┴→ combine   (two independent branches feeding a join)."""
    return Graph.model_validate(
        {
            "meta": {"seed": 1, "resolution": [8, 8]},
            "nodes": [
                {"id": "sa", "type": "_test.cache_source", "params": {"value": a_val, "tag": "a"}},
                {"id": "sb", "type": "_test.cache_source", "params": {"value": b_val, "tag": "b"}},
                {"id": "add", "type": "_test.cache_add", "params": {"amount": add_amount}},
                {"id": "combine", "type": "_test.cache_combine", "params": {}},
            ],
            "edges": [
                {"from": ["sa", "image"], "to": ["add", "image"]},
                {"from": ["add", "image"], "to": ["combine", "a"]},
                {"from": ["sb", "image"], "to": ["combine", "b"]},
            ],
        }
    )


def _reset() -> None:
    for k in _CACHE_CALLS:
        _CACHE_CALLS[k] = 0


def test_changing_a_param_invalidates_node_and_descendants() -> None:
    _reset()
    engine = Engine()
    engine.evaluate(_diamond(add_amount=5.0), ["combine"])
    # Change only the 'add' node's param.
    engine.evaluate(_diamond(add_amount=9.0), ["combine"])

    assert _CACHE_CALLS["src_a"] == 1  # unchanged source → still cached
    assert _CACHE_CALLS["src_b"] == 1  # unrelated branch → still cached
    assert _CACHE_CALLS["add"] == 2  # its param changed → recomputed
    assert _CACHE_CALLS["combine"] == 2  # descendant of add → recomputed


def test_changing_one_branch_leaves_the_other_cached() -> None:
    _reset()
    engine = Engine()
    engine.evaluate(_diamond(b_val=20.0), ["combine"])
    engine.evaluate(_diamond(b_val=99.0), ["combine"])  # only branch B changes

    assert _CACHE_CALLS["src_a"] == 1  # branch A untouched
    assert _CACHE_CALLS["add"] == 1  # branch A untouched
    assert _CACHE_CALLS["src_b"] == 2  # branch B source changed
    assert _CACHE_CALLS["combine"] == 2  # join depends on B → recomputed


def test_full_cache_hit_recomputes_nothing() -> None:
    _reset()
    engine = Engine()
    graph = _diamond()
    engine.evaluate(graph, ["combine"])
    engine.evaluate(graph, ["combine"])  # identical → every node hits cache
    assert _CACHE_CALLS == {"src_a": 1, "src_b": 1, "add": 1, "combine": 1}


def test_result_is_correct_after_invalidation() -> None:
    # The point of the guard: after a param change the returned image is the NEW
    # one, never a stale cached array.
    _reset()
    engine = Engine()
    first = engine.evaluate(_diamond(add_amount=5.0), ["combine"])["combine"]["image"]
    second = engine.evaluate(_diamond(add_amount=9.0), ["combine"])["combine"]["image"]
    # combine = (a_val + add_amount) + b_val = (10+5)+20=35 ; then (10+9)+20=39
    assert np.allclose(first, 35.0)
    assert np.allclose(second, 39.0)
