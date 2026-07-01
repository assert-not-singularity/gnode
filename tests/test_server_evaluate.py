"""API tests for /api/evaluate (M2 WI-3): previews, map previews, per-node
errors, and request validation."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from gnode.core.node import Node
from gnode.core.registry import register_node
from gnode.core.types import PortType
from gnode.server.app import create_app

if TYPE_CHECKING:
    from pathlib import Path


@register_node
class _BadOutput(Node):
    type = "_test.bad_output"
    category = "Test"
    title = "BadOutput"
    outputs = {"image": PortType.IMAGE}

    def evaluate(self, inputs, params, ctx):
        return {}  # violates the declared-output contract -> NodeContractError


def _png(h: int = 32, w: int = 32) -> bytes:
    arr = np.random.default_rng(1).integers(0, 256, (h, w, 3)).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(arr, "RGB").save(buf, "PNG")
    return buf.getvalue()


def _upload(client: TestClient) -> str:
    resp = client.post("/api/images", files={"file": ("x.png", _png(), "image/png")})
    assert resp.status_code == 200, resp.text
    return resp.json()["image_id"]


def test_evaluate_returns_image_preview(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        image_id = _upload(client)
        graph = {
            "meta": {"seed": 3, "resolution": [32, 32]},
            "nodes": [
                {"id": "load", "type": "io.load_image", "params": {"image_id": image_id}},
                {"id": "grade", "type": "color.gradient_map", "params": {}},
                {"id": "view", "type": "io.viewer", "params": {}},
            ],
            "edges": [
                {"from": ["load", "image"], "to": ["grade", "image"]},
                {"from": ["grade", "image"], "to": ["view", "image"]},
            ],
        }
        resp = client.post("/api/evaluate", json={"graph": graph, "targets": ["view"]})
    assert resp.status_code == 200
    preview = resp.json()["previews"]["view"]
    assert preview["kind"] == "image"
    assert preview["data_url"].startswith("data:image/png;base64,")
    assert (preview["width"], preview["height"]) == (32, 32)


def test_evaluate_map_preview(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        image_id = _upload(client)
        graph = {
            "meta": {"seed": 1, "resolution": [32, 32]},
            "nodes": [
                {"id": "load", "type": "io.load_image", "params": {"image_id": image_id}},
                {"id": "m", "type": "mask.from_luminance", "params": {"low": 0.1, "high": 0.9}},
            ],
            "edges": [{"from": ["load", "image"], "to": ["m", "image"]}],
        }
        resp = client.post("/api/evaluate", json={"graph": graph, "targets": ["m"]})
    assert resp.json()["previews"]["m"]["kind"] == "map"


def test_evaluate_node_error_is_reported(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        graph = {
            "meta": {"seed": 1, "resolution": [16, 16]},
            "nodes": [
                {"id": "load", "type": "io.load_image", "params": {"image_id": "missing.png"}},
                {"id": "view", "type": "io.viewer", "params": {}},
            ],
            "edges": [{"from": ["load", "image"], "to": ["view", "image"]}],
        }
        resp = client.post("/api/evaluate", json={"graph": graph, "targets": ["view"]})
    assert resp.status_code == 200
    assert "load" in resp.json()["errors"]


def test_evaluate_invalid_graph_is_400(tmp_path: Path) -> None:
    # Viewer's required `image` input is unconnected -> validation fails.
    graph = {"nodes": [{"id": "v", "type": "io.viewer", "params": {}}], "edges": []}
    with TestClient(create_app(tmp_path)) as client:
        resp = client.post("/api/evaluate", json={"graph": graph, "targets": ["v"]})
    assert resp.status_code == 400


def test_evaluate_contract_error_is_structured(tmp_path: Path) -> None:
    # A contract violation must return 200 with a per-node error, not a 500.
    graph = {
        "meta": {"resolution": [8, 8]},
        "nodes": [{"id": "bad", "type": "_test.bad_output", "params": {}}],
        "edges": [],
    }
    with TestClient(create_app(tmp_path)) as client:
        resp = client.post("/api/evaluate", json={"graph": graph, "targets": ["bad"]})
    assert resp.status_code == 200
    assert "bad" in resp.json()["errors"]


def test_evaluate_unknown_target_is_400(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        image_id = _upload(client)
        graph = {
            "meta": {"resolution": [16, 16]},
            "nodes": [{"id": "load", "type": "io.load_image", "params": {"image_id": image_id}}],
            "edges": [],
        }
        resp = client.post("/api/evaluate", json={"graph": graph, "targets": ["nope"]})
    assert resp.status_code == 400
