"""Graph validation + the single type-compat policy (plan §5).

Covers each error class ``validate_graph`` reports (duplicate id, unknown type,
missing required input, unknown port, type mismatch, >1 edge per input, cycle),
a fully valid graph, and a unit test of ``can_connect`` (exact match + ANY
wildcard).
"""

from __future__ import annotations

from typing import Any

import pytest

from gnode.core.graph import Graph
from gnode.core.types import PortType
from gnode.core.validation import can_connect, validate_graph


def _graph(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> Graph:
    return Graph.model_validate({"nodes": nodes, "edges": edges})


# ── can_connect ───────────────────────────────────────────────────────────────


def test_can_connect_exact_match() -> None:
    assert can_connect(PortType.IMAGE, PortType.IMAGE)
    assert not can_connect(PortType.IMAGE, PortType.MASK)
    assert not can_connect(PortType.MAP, PortType.IMAGE)


def test_can_connect_any_wildcard() -> None:
    for t in PortType:
        assert can_connect(PortType.ANY, t)
        assert can_connect(t, PortType.ANY)


# ── validate_graph: happy path ────────────────────────────────────────────────


def test_valid_graph() -> None:
    graph = _graph(
        nodes=[
            {"id": "seed", "type": "util.seed", "params": {"value": 3}},
            {"id": "load", "type": "io.load_image", "params": {"image_id": "x"}},
            {"id": "band", "type": "displace.band", "params": {}},
            {"id": "view", "type": "io.viewer", "params": {}},
        ],
        edges=[
            {"from": ["load", "image"], "to": ["band", "image"]},
            {"from": ["seed", "seed"], "to": ["band", "seed"]},
            {"from": ["band", "image"], "to": ["view", "image"]},
        ],
    )
    result = validate_graph(graph)
    assert result.valid, result.errors
    assert result.errors == []


# ── validate_graph: each error class ──────────────────────────────────────────


def test_duplicate_id() -> None:
    graph = _graph(
        nodes=[
            {"id": "dup", "type": "io.viewer"},
            {"id": "dup", "type": "io.viewer"},
        ],
        edges=[],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("duplicate node id" in e for e in result.errors)


def test_unknown_node_type() -> None:
    graph = _graph(nodes=[{"id": "n", "type": "does.not_exist"}], edges=[])
    result = validate_graph(graph)
    assert not result.valid
    assert any("unknown type" in e for e in result.errors)


def test_missing_required_input() -> None:
    # io.viewer requires an 'image' input; leave it unconnected.
    graph = _graph(nodes=[{"id": "v", "type": "io.viewer"}], edges=[])
    result = validate_graph(graph)
    assert not result.valid
    assert any("required input 'image' is not connected" in e for e in result.errors)


def test_unknown_output_port() -> None:
    graph = _graph(
        nodes=[
            {"id": "load", "type": "io.load_image", "params": {"image_id": "x"}},
            {"id": "view", "type": "io.viewer"},
        ],
        edges=[{"from": ["load", "nope"], "to": ["view", "image"]}],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("has no output port 'nope'" in e for e in result.errors)


def test_unknown_input_port() -> None:
    graph = _graph(
        nodes=[
            {"id": "load", "type": "io.load_image", "params": {"image_id": "x"}},
            {"id": "view", "type": "io.viewer"},
        ],
        edges=[{"from": ["load", "image"], "to": ["view", "nope"]}],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("has no input port 'nope'" in e for e in result.errors)


def test_type_mismatch_map_into_image() -> None:
    # util.split_channels emits MAP; wiring it into an IMAGE input is a mismatch.
    graph = _graph(
        nodes=[
            {"id": "load", "type": "io.load_image", "params": {"image_id": "x"}},
            {"id": "split", "type": "util.split_channels"},
            {"id": "view", "type": "io.viewer"},
        ],
        edges=[
            {"from": ["load", "image"], "to": ["split", "image"]},
            {"from": ["split", "r"], "to": ["view", "image"]},
        ],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("type mismatch" in e for e in result.errors)


def test_one_edge_per_input() -> None:
    graph = _graph(
        nodes=[
            {"id": "l1", "type": "io.load_image", "params": {"image_id": "x"}},
            {"id": "l2", "type": "io.load_image", "params": {"image_id": "y"}},
            {"id": "view", "type": "io.viewer"},
        ],
        edges=[
            {"from": ["l1", "image"], "to": ["view", "image"]},
            {"from": ["l2", "image"], "to": ["view", "image"]},  # 2nd edge to same input
        ],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("incoming edges (max 1)" in e for e in result.errors)


def test_cycle_detected() -> None:
    graph = _graph(
        nodes=[
            {"id": "x", "type": "io.viewer"},
            {"id": "y", "type": "io.viewer"},
        ],
        edges=[
            {"from": ["x", "image"], "to": ["y", "image"]},
            {"from": ["y", "image"], "to": ["x", "image"]},
        ],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("cycle" in e for e in result.errors)


def test_invalid_params_reported() -> None:
    # displace.band n_bands has ge=1; -5 is out of range.
    graph = _graph(
        nodes=[
            {"id": "load", "type": "io.load_image", "params": {"image_id": "x"}},
            {"id": "band", "type": "displace.band", "params": {"n_bands": -5}},
            {"id": "view", "type": "io.viewer"},
        ],
        edges=[
            {"from": ["load", "image"], "to": ["band", "image"]},
            {"from": ["band", "image"], "to": ["view", "image"]},
        ],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("params invalid" in e for e in result.errors)


@pytest.mark.parametrize("bad_endpoint", ["src", "dst"])
def test_edge_to_unknown_node(bad_endpoint: str) -> None:
    src = "ghost" if bad_endpoint == "src" else "load"
    dst = "ghost" if bad_endpoint == "dst" else "view"
    graph = _graph(
        nodes=[
            {"id": "load", "type": "io.load_image", "params": {"image_id": "x"}},
            {"id": "view", "type": "io.viewer"},
        ],
        edges=[{"from": [src, "image"], "to": [dst, "image"]}],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("unknown node" in e for e in result.errors)
