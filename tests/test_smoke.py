"""Scaffold smoke test — verifies the toolchain (uv env, numpy, package import)
and two invariants that hold for the promoted lib routines: determinism and
non-mutation of inputs."""

from __future__ import annotations

import numpy as np

from gnode.lib import glitch


def _fixture(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(32, 48, 3)).astype(np.float32)


def test_lib_importable_and_deterministic() -> None:
    img = _fixture()
    a = glitch.band_displace(img, seed=7)
    b = glitch.band_displace(img, seed=7)
    assert np.array_equal(a, b)
    assert a.shape == img.shape


def test_band_displace_does_not_mutate_input() -> None:
    img = _fixture()
    before = img.copy()
    glitch.band_displace(img, seed=3)
    assert np.array_equal(img, before)
