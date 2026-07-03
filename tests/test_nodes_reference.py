"""Node ≡ reference equality (plan §5, top-priority guard against drift).

Each wrapper node (no mask) must produce *exactly* what the underlying
``gnode.lib`` function produces on the same fixture image with the same args and
resolved seed. Determinism makes this an exact ``np.array_equal`` assertion, so
any accidental change to a node's argument wiring is caught immediately.

``jpeg_databend`` is excluded from exact equality: it re-encodes through
Pillow/libjpeg whose exact bytes are per-environment (plan §1). It gets a
structural/determinism check instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pytest

from gnode.core.registry import discover, get_node
from gnode.lib import artistic, glitch
from gnode.nodes._common import luminance
from gnode.nodes.color import _GREEN_GRADE

from .conftest import make_image, node_ctx

if TYPE_CHECKING:
    from collections.abc import Callable

    from gnode.core.node import Node

discover()  # populate the registry so get_node() resolves the real catalog

# Large enough that block_mosh/pixel_drag default params are valid.
RH, RW = 128, 288
SEED = 4242


def _run(node: Node, params_kwargs: dict[str, Any], img: np.ndarray, *, seed: int) -> np.ndarray:
    cls = type(node)
    params = cls.params_model().model_validate(params_kwargs)
    ctx = node_ctx(node_id=cls.type, seed=seed, resolution=(RH, RW))
    return node.run({"image": img}, params, ctx)["image"]


# Each entry: (node_type, params, reference-callable taking (img, seed) -> array).
# For non-seeded nodes the reference ignores seed.
def _wave_ref(img: np.ndarray, _seed: int) -> np.ndarray:
    chans = [artistic.warp(img[..., c], 8.0, 3.0, 0.0, 1) for c in range(3)]
    return np.stack(chans, axis=2)


_CASES: list[tuple[str, dict[str, Any], Callable[[np.ndarray, int], np.ndarray]]] = [
    (
        "displace.band",
        {},
        lambda img, seed: glitch.band_displace_sine(
            img, seed=seed, n_bands=24, max_shift=60, noise=0.18, power=1.3, width_var=0.6
        ),
    ),
    (
        "displace.scanline",
        {},
        lambda img, seed: artistic.row_displace(img, seed=seed, n=80, max_shift=140, big_prob=0.5),
    ),
    ("displace.wave", {}, _wave_ref),
    (
        "displace.block_mosh",
        {},
        lambda img, seed: artistic.block_mosh(
            img, seed=seed, n=10, max_h=60, max_w=260, max_shift=120
        ),
    ),
    (
        "displace.pixel_drag",
        {},
        lambda img, seed: artistic.drag(
            img, seed=seed, rows_frac=0.5, decay=0.82, min_len=30, max_len=200
        ),
    ),
    (
        "sort.pixel_sort",
        {},
        lambda img, _seed: artistic.pixel_sort(img, 0.20, 0.82, max_span=0, axis=1),
    ),
    (
        "color.channel_shift",
        {},
        lambda img, _seed: artistic.channel_shift(img, off=10, dy=0),
    ),
    ("color.split", {}, lambda img, _seed: glitch.synthwave_split(img, offset=6)),
    (
        "color.chroma_shift",
        {},
        lambda img, _seed: artistic.chroma_shift(img, dx=8, dy=0, bleed=1.15),
    ),
    (
        "color.gradient_map",
        {},
        lambda img, _seed: artistic.gradient_map(luminance(img), list(_GREEN_GRADE)),
    ),
    ("color.bitcrush", {}, lambda img, _seed: artistic.bitcrush(img, levels=6)),
    ("color.bit_rotate", {}, lambda img, _seed: artistic.bit_rotate(img, channel=1, bits=3)),
    (
        "corrupt.byte_corrupt",
        {},
        lambda img, seed: artistic.byte_corrupt(img, seed, n=4000),
    ),
    ("texture.scanlines", {}, lambda img, _seed: artistic.scanlines(img, strength=0.12, gap=3)),
    ("texture.vignette", {}, lambda img, _seed: artistic.vignette(img, strength=0.5)),
]


@pytest.mark.parametrize(("node_type", "params", "ref"), _CASES, ids=[c[0] for c in _CASES])
def test_node_matches_lib_reference(
    node_type: str,
    params: dict[str, Any],
    ref: Callable[[np.ndarray, int], np.ndarray],
) -> None:
    img = make_image(seed=11, h=RH, w=RW)
    node = get_node(node_type)
    got = _run(node, params, img, seed=SEED)
    expected = ref(img, SEED)
    assert np.array_equal(got, expected), f"{node_type} diverged from its lib reference"


def test_pixel_sort_is_not_a_noop() -> None:
    # Regression guard: the low/high thresholds are normalized 0..1, but
    # luminance is 0..255 (IMAGE convention) — a missing `/ 255.0` silently
    # excludes almost every pixel from the sortable band, so the node just
    # returns the input unchanged. `test_node_matches_lib_reference` alone
    # can't catch this: it compares the node to the same lib function it
    # wraps, so both sides go stale together.
    img = make_image(seed=11, h=RH, w=RW)
    node = get_node("sort.pixel_sort")
    got = _run(node, {}, img, seed=SEED)
    assert not np.array_equal(got, img), "pixel_sort must not be a no-op on real image data"


def test_split_cmy_mode_matches_reference() -> None:
    # The non-default branch of color.split also maps 1:1 to a lib function.
    img = make_image(seed=12, h=RH, w=RW)
    node = get_node("color.split")
    got = _run(node, {"mode": "cmy", "offset": 7, "angle": 30.0}, img, seed=SEED)
    expected = glitch.cmy_split(img, offset=7, angle=30.0)
    assert np.array_equal(got, expected)


def test_jpeg_databend_not_byte_pinned_but_deterministic() -> None:
    # Codec caveat (plan §1): assert shape/dtype + within-process determinism,
    # NOT byte-exactness against a pinned value.
    img = make_image(seed=13, h=RH, w=RW)
    node = get_node("corrupt.jpeg_databend")
    params = type(node).params_model().model_validate({"quality": 88, "n": 30})

    def once() -> dict[str, np.ndarray]:
        ctx = node_ctx(node_id="corrupt.jpeg_databend", seed=SEED, resolution=(RH, RW))
        return node.run({"image": img}, params, ctx)

    a, b = once(), once()
    assert a["image"].shape == img.shape
    assert a["image"].dtype == np.float32
    assert a["diff"].shape == (RH, RW)
    assert np.array_equal(a["image"], b["image"])  # deterministic within-process
    assert np.array_equal(a["diff"], b["diff"])
