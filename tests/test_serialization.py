""".gnode serialization round-trip + version migration (plan §3.6, §5).

The on-disk schema (``from``/``to`` edge aliases, ``meta``, ``nodes``, ``edges``)
is a stable public contract, so load→dump→load must be an identity and the edge
aliases must survive a round-trip. ``migrate`` is the identity for schema 1.0.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from gnode.core.graph import (
    SCHEMA_VERSION,
    Graph,
    dump_graph,
    load_graph,
    load_graph_file,
    migrate,
    save_graph_file,
)

if TYPE_CHECKING:
    from pathlib import Path

_SAMPLE = {
    "version": "1.0",
    "meta": {"seed": 7, "resolution": [512, 512]},
    "nodes": [
        {"id": "load", "type": "io.load_image", "pos": [40, 200], "params": {"image_id": "s.png"}},
        {"id": "band", "type": "displace.band", "pos": [300, 200], "params": {"n_bands": 12}},
        {"id": "view", "type": "io.viewer", "pos": [560, 200], "params": {}},
    ],
    "edges": [
        {"from": ["load", "image"], "to": ["band", "image"]},
        {"from": ["band", "image"], "to": ["view", "image"]},
    ],
}


def test_round_trip_identity() -> None:
    graph = Graph.model_validate(_SAMPLE)
    reloaded = load_graph(dump_graph(graph))
    assert reloaded.model_dump() == graph.model_dump()


def test_edge_aliases_survive_round_trip() -> None:
    graph = load_graph(json.dumps(_SAMPLE))
    dumped = json.loads(dump_graph(graph))
    # The serialized form uses the 'from'/'to' aliases, not the internal names.
    for edge in dumped["edges"]:
        assert set(edge) == {"from", "to"}
        assert "src" not in edge
        assert "dst" not in edge
    # And the actual endpoints are preserved.
    assert dumped["edges"][0]["from"] == ["load", "image"]
    assert dumped["edges"][0]["to"] == ["band", "image"]


def test_edge_endpoints_parsed_into_src_dst() -> None:
    graph = load_graph(json.dumps(_SAMPLE))
    edge = graph.edges[0]
    assert edge.src == ("load", "image")
    assert edge.dst == ("band", "image")


def test_migrate_is_identity_for_1_0() -> None:
    data = dict(_SAMPLE)
    assert migrate(data) == data


def test_load_missing_fields_uses_defaults() -> None:
    graph = load_graph(json.dumps({"nodes": [], "edges": []}))
    assert graph.version == SCHEMA_VERSION
    assert graph.meta.seed == 0
    assert tuple(graph.meta.resolution) == (768, 768)


def test_save_and_load_file_round_trip(tmp_path: Path) -> None:
    graph = Graph.model_validate(_SAMPLE)
    path = tmp_path / "g.gnode"
    save_graph_file(graph, path)
    reloaded = load_graph_file(path)
    assert reloaded.model_dump() == graph.model_dump()
    # Serialized JSON on disk is valid JSON with the alias schema.
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["edges"][0]["from"] == ["load", "image"]


def test_dump_is_pretty_json() -> None:
    graph = Graph.model_validate(_SAMPLE)
    text = dump_graph(graph)
    assert text.startswith("{")
    # indent=2 was requested; ensure it parses and preserves node ids.
    parsed = json.loads(text)
    assert [n["id"] for n in parsed["nodes"]] == ["load", "band", "view"]
