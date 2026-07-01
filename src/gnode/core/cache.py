"""Structural cache key + thread-safe LRU with single-flight (plan §3.4).

The key alone identifies a node's output (nodes are pure + deterministic), so no
numpy array hashing is needed. **A false hit returns the wrong image** — the
system's worst failure — so canonicalization is defined precisely and tested
hard (see ``tests``): the key is a BLAKE2b digest of a JSON blob serialized with
sorted keys, which gives stable key ordering and deterministic scalar
formatting (Python's ``json`` renders floats via ``repr``). The version salt
invalidates the whole cache across engine/schema upgrades.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# Bump when an engine/algorithm change should invalidate all cached outputs.
ENGINE_CACHE_VERSION = "1"


def structural_key(
    node_type: str,
    params: dict[str, Any],
    input_keys: dict[str, str],
    resolution: tuple[int, int],
    *,
    seed: int | None = None,
    code_hash: str | None = None,
) -> str:
    """Content-free structural key for a node's output dict.

    ``params`` must be JSON-native (pass ``model.model_dump(mode="json")``).
    ``input_keys`` maps each wired input port to ``"<upstream_key>#<out_port>"``.
    """
    payload = {
        "v": ENGINE_CACHE_VERSION,
        "type": node_type,
        "params": params,
        "inputs": input_keys,
        "res": [resolution[0], resolution[1]],
        "seed": seed,
        "code": code_hash,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.blake2b(blob.encode("utf-8"), digest_size=16).hexdigest()


class LRUCache:
    """Thread-safe bounded LRU of ``structural_key -> output dict``, with a
    single-flight ``compute_if_absent`` so concurrent identical keys compute
    once. Stored dicts are treated as read-only (the non-mutation node contract
    guarantees consumers never mutate them)."""

    def __init__(self, maxsize: int = 256) -> None:
        self._max = maxsize
        self._data: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self._inflight: dict[str, threading.Lock] = {}

    def get(self, key: str) -> dict | None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return self._data[key]
            return None

    def put(self, key: str, value: dict) -> None:
        with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)
            while len(self._data) > self._max:
                self._data.popitem(last=False)

    def compute_if_absent(self, key: str, factory: Callable[[], dict]) -> dict:
        hit = self.get(key)
        if hit is not None:
            return hit
        with self._lock:
            keylock = self._inflight.setdefault(key, threading.Lock())
        with keylock:
            hit = self.get(key)
            if hit is None:
                hit = factory()
                self.put(key, hit)
            with self._lock:
                self._inflight.pop(key, None)
            return hit

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)
