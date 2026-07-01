"""API tests for image upload/serve (M2 WI-2)."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from gnode.server.app import create_app
from gnode.server.workspace import WorkspaceImageStore

if TYPE_CHECKING:
    from pathlib import Path


def _png_bytes(h: int = 16, w: int = 24) -> bytes:
    arr = np.random.default_rng(0).integers(0, 256, (h, w, 3)).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(arr, "RGB").save(buf, "PNG")
    return buf.getvalue()


def test_upload_then_fetch(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        resp = client.post(
            "/api/images", files={"file": ("photo.png", _png_bytes(16, 24), "image/png")}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert (body["width"], body["height"]) == (24, 16)
        fetched = client.get(f"/api/images/{body['image_id']}")
    assert fetched.status_code == 200
    assert fetched.headers["content-type"].startswith("image/")


def test_upload_rejects_non_image(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        resp = client.post(
            "/api/images", files={"file": ("note.txt", b"not an image", "text/plain")}
        )
    assert resp.status_code == 400


def test_get_missing_image_is_404(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        resp = client.get("/api/images/deadbeefcafe.png")
    assert resp.status_code == 404


def test_get_invalid_id_is_400(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        resp = client.get("/api/images/nodothere")
    assert resp.status_code == 400


def test_workspace_store_rejects_traversal(tmp_path: Path) -> None:
    images = tmp_path / "images"
    images.mkdir(parents=True, exist_ok=True)
    store = WorkspaceImageStore(images)
    for bad in ["../secret.png", "..", "sub/child.png", "/abs.png"]:
        with pytest.raises(ValueError, match="image id"):
            store.load(bad)
