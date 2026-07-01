"""Deterministic per-node RNG derivation (plan §3.5).

Contract: the same global seed + node id (+ optional node seed) yields an
identical numpy stream, via ``SeedSequence``. Nodes must draw randomness only
through ``Context.rng_for`` — never touch global ``np.random``.

Python's built-in ``hash`` is per-process salted, so we derive seeds with a
stable BLAKE2b hash to keep results reproducible across runs and machines.
"""

from __future__ import annotations

import hashlib

import numpy as np


def _stable_hash(text: str) -> int:
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def derive_seed(global_seed: int, node_id: str, node_seed: int | None = None) -> int:
    """A stable integer seed for a node from the global seed + node id."""
    suffix = "" if node_seed is None else str(node_seed)
    return _stable_hash(f"{global_seed}:{node_id}:{suffix}")


def rng_for(global_seed: int, node_id: str, node_seed: int | None = None) -> np.random.Generator:
    """A per-node numpy Generator seeded deterministically."""
    return np.random.default_rng(
        np.random.SeedSequence(derive_seed(global_seed, node_id, node_seed))
    )
