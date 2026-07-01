"""Property-based engine invariants (plan §5, Hypothesis).

Random *valid* DAGs built from throwaway ``_test.*`` nodes must satisfy:

* evaluation of any target succeeds;
* the scheduler's topological order is valid — every dependency precedes the
  node that consumes it;
* evaluating the same graph twice yields byte-identical arrays (determinism).

Examples are kept small and fast (few nodes, 8x8 images, fixed strategies).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from gnode.core import scheduler
from gnode.core.engine import Engine
from gnode.core.graph import Graph
from gnode.core.node import In, Node, NodeParams
from gnode.core.registry import register_node
from gnode.core.types import PortType

RES = (8, 8)


@register_node
class _PropSource(Node):
    type = "_prop.source"
    category = "Test"
    title = "Prop Source"
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        value: float = 1.0

    def evaluate(self, inputs, params, ctx):
        h, w = ctx.resolution
        return {"image": np.full((h, w, 3), params.value, dtype=np.float32)}


@register_node
class _PropUnary(Node):
    type = "_prop.unary"
    category = "Test"
    title = "Prop Unary"
    inputs = {"image": In(PortType.IMAGE)}
    outputs = {"image": PortType.IMAGE}
    uses_seed = True

    class Params(NodeParams):
        amount: float = 1.0
        seed: int | None = None

    def evaluate(self, inputs, params, ctx):
        # A little rng use so determinism is a real (not trivial) property.
        jitter = ctx.rng.normal(0.0, 1.0, inputs["image"].shape).astype(np.float32)
        return {"image": inputs["image"] + params.amount + jitter}


@register_node
class _PropBinary(Node):
    type = "_prop.binary"
    category = "Test"
    title = "Prop Binary"
    inputs = {"a": In(PortType.IMAGE), "b": In(PortType.IMAGE)}
    outputs = {"image": PortType.IMAGE}

    def evaluate(self, inputs, params, ctx):
        return {"image": (inputs["a"] + inputs["b"]) * 0.5}


# A DAG description: for each node beyond the sources, pick its kind and wire its
# input(s) to strictly-earlier nodes (guaranteeing acyclicity by construction).
@st.composite
def _dags(draw: st.DrawFn) -> tuple[Graph, list[str]]:
    n_sources = draw(st.integers(min_value=1, max_value=3))
    n_ops = draw(st.integers(min_value=0, max_value=6))

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    ids: list[str] = []

    for i in range(n_sources):
        nid = f"s{i}"
        ids.append(nid)
        nodes.append({"id": nid, "type": "_prop.source", "params": {"value": draw(_floats())}})

    for j in range(n_ops):
        nid = f"o{j}"
        earlier = list(ids)  # every existing node (sources + prior ops)
        kind = draw(st.sampled_from(["unary", "binary"]))
        if kind == "unary":
            src = draw(st.sampled_from(earlier))
            nodes.append(
                {
                    "id": nid,
                    "type": "_prop.unary",
                    "params": {"amount": draw(_floats()), "seed": draw(_seeds())},
                }
            )
            edges.append({"from": [src, "image"], "to": [nid, "image"]})
        else:
            sa = draw(st.sampled_from(earlier))
            sb = draw(st.sampled_from(earlier))
            nodes.append({"id": nid, "type": "_prop.binary", "params": {}})
            edges.append({"from": [sa, "image"], "to": [nid, "a"]})
            edges.append({"from": [sb, "image"], "to": [nid, "b"]})
        ids.append(nid)

    graph = Graph.model_validate(
        {
            "meta": {"seed": draw(st.integers(0, 1000)), "resolution": list(RES)},
            "nodes": nodes,
            "edges": edges,
        }
    )
    return graph, ids


def _floats() -> st.SearchStrategy[float]:
    return st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False)


def _seeds() -> st.SearchStrategy[int | None]:
    return st.one_of(st.none(), st.integers(min_value=0, max_value=10_000))


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(_dags(), st.data())
def test_random_dag_evaluates_with_valid_topo_order(
    dag: tuple[Graph, list[str]], data: st.DataObject
) -> None:
    graph, ids = dag
    target = data.draw(st.sampled_from(ids))

    order, _node_map, incoming = scheduler.reachable_order(graph, [target])

    # Topo order validity: each dependency comes strictly before its consumer.
    pos = {nid: i for i, nid in enumerate(order)}
    for node_id in order:
        for _in_port, (src_node, _src_port) in incoming.get(node_id, {}).items():
            assert pos[src_node] < pos[node_id]

    out = Engine().evaluate(graph, [target])
    assert out[target]["image"].shape == (RES[0], RES[1], 3)


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(_dags(), st.data())
def test_random_dag_is_deterministic(dag: tuple[Graph, list[str]], data: st.DataObject) -> None:
    graph, ids = dag
    target = data.draw(st.sampled_from(ids))
    first = Engine().evaluate(graph, [target])[target]["image"]
    second = Engine().evaluate(graph, [target])[target]["image"]
    assert np.array_equal(first, second)


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(_dags())
def test_cache_reuse_does_not_change_result(dag: tuple[Graph, list[str]]) -> None:
    # A shared-cache engine evaluated twice must return the SAME array as a
    # cold engine — the cache never alters a result.
    graph, ids = dag
    target = ids[-1]
    warm = Engine()
    warm.evaluate(graph, [target])
    cached = warm.evaluate(graph, [target])[target]["image"]
    cold = Engine().evaluate(graph, [target])[target]["image"]
    assert np.array_equal(cached, cold)
