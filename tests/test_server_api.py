"""API tests for the server foundation (M2 WI-1): /api/nodes and /api/validate."""

from __future__ import annotations

from fastapi.testclient import TestClient

from gnode.server.app import create_app


def test_list_nodes_returns_catalog() -> None:
    with TestClient(create_app()) as client:
        resp = client.get("/api/nodes")
    assert resp.status_code == 200
    catalog = resp.json()
    types = {n["type"] for n in catalog}
    assert "displace.band" in types
    # Count production nodes only — other test modules register throwaway
    # `_test.*`/`_prop.*` nodes into the shared registry during the session.
    assert len({t for t in types if not t.startswith("_")}) == 29
    band = next(n for n in catalog if n["type"] == "displace.band")
    assert {"category", "title", "inputs", "outputs", "params_schema"} <= set(band)


def test_validate_valid_graph() -> None:
    graph = {
        "meta": {"seed": 1, "resolution": [8, 8]},
        "nodes": [{"id": "s", "type": "util.seed", "params": {"value": 3}}],
        "edges": [],
    }
    with TestClient(create_app()) as client:
        resp = client.post("/api/validate", json=graph)
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


def test_validate_unknown_type() -> None:
    graph = {"nodes": [{"id": "x", "type": "does.not.exist", "params": {}}], "edges": []}
    with TestClient(create_app()) as client:
        resp = client.post("/api/validate", json=graph)
    body = resp.json()
    assert body["valid"] is False
    assert any("unknown type" in e for e in body["errors"])
