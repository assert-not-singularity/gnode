"""API tests for the graph workspace (M2 WI-4): save / list / load."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from gnode.server.app import create_app

if TYPE_CHECKING:
    from pathlib import Path

_GRAPH = {
    "meta": {"seed": 5, "resolution": [64, 64]},
    "nodes": [{"id": "s", "type": "util.seed", "params": {"value": 9}}],
    "edges": [],
}


def test_save_list_load_roundtrip(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        saved = client.post("/api/graphs", json={"filename": "demo.gnode", "graph": _GRAPH})
        assert saved.status_code == 201
        assert saved.json()["filename"] == "demo.gnode"

        listing = client.get("/api/graphs").json()
        assert any(g["filename"] == "demo.gnode" and g["name"] == "demo" for g in listing)

        loaded = client.get("/api/graphs/demo.gnode").json()
    assert loaded["meta"]["seed"] == 5
    assert loaded["nodes"][0]["id"] == "s"
    assert loaded["nodes"][0]["type"] == "util.seed"
    assert loaded["edges"] == []


def test_save_invalid_filename_is_400(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        for bad in ["../evil.gnode", "no-extension", "sub/x.gnode", "x.txt"]:
            resp = client.post("/api/graphs", json={"filename": bad, "graph": _GRAPH})
            assert resp.status_code == 400, bad


def test_load_missing_is_404(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        resp = client.get("/api/graphs/nope.gnode")
    assert resp.status_code == 404


def test_list_empty_workspace(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        resp = client.get("/api/graphs")
    assert resp.json() == []
