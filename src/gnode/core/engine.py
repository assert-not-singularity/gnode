"""Pull-based lazy evaluation engine with structural caching (plan §3.4).

Evaluates only the subgraph feeding the requested targets, in topological order.
Each node's output dict is cached under its ``structural_key``; unchanged
upstream branches hit the cache. The engine centralizes seed resolution and
hands each node a pre-seeded ``NodeContext`` — nodes never derive seeds
themselves.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

import numpy as np

from gnode.core import scheduler
from gnode.core.cache import LRUCache, structural_key
from gnode.core.context import Context, NodeContext
from gnode.core.errors import EvaluationCancelledError, NodeContractError, NodeEvalError
from gnode.core.registry import get_node

if TYPE_CHECKING:
    from gnode.core.graph import Graph
    from gnode.core.ports import Cache


def _code_hash(code: str) -> str:
    return hashlib.blake2b(code.encode("utf-8"), digest_size=8).hexdigest()


class Engine:
    """Holds a persistent cache so repeated evaluations (e.g. slider drags on the
    server) reuse unchanged branches."""

    def __init__(self, cache: Cache | None = None) -> None:
        self.cache: Cache = cache if cache is not None else LRUCache()

    def evaluate(
        self, graph: Graph, targets: list[str], ctx: Context | None = None
    ) -> dict[str, dict[str, Any]]:
        """Evaluate ``targets`` and return ``{node_id: output_dict}`` for each."""
        if ctx is None:
            ctx = Context(seed=graph.meta.seed, resolution=tuple(graph.meta.resolution))
        order, node_map, incoming = scheduler.reachable_order(graph, targets)

        keys: dict[str, str] = {}
        outputs: dict[str, dict[str, Any]] = {}

        for node_id in order:
            ctx.cancel.raise_if_cancelled()
            spec = node_map[node_id]
            node = get_node(spec.type)
            cls = type(node)

            in_values: dict[str, Any] = {}
            in_keys: dict[str, str] = {}
            for in_port, (src_node, src_port) in incoming.get(node_id, {}).items():
                in_values[in_port] = outputs[src_node][src_port]
                in_keys[in_port] = f"{keys[src_node]}#{src_port}"

            params = cls.params_model().model_validate(spec.params)
            params_dump = params.model_dump(mode="json")

            seed = (
                ctx.resolve_seed(node_id, in_values, params_dump.get("seed"))
                if cls.uses_seed
                else None
            )
            code_hash = _code_hash(params_dump["code"]) if "code" in params_dump else None

            key = structural_key(
                cls.type, params_dump, in_keys, ctx.resolution, seed=seed, code_hash=code_hash
            )
            keys[node_id] = key

            cached = self.cache.get(key)
            if cached is not None:
                outputs[node_id] = cached
                continue

            # Non-seed nodes get an rng seeded by a fixed constant so it is
            # independent of the global seed — consistent with a key that omits
            # the seed (no false hits on reroll).
            rng_seed = seed if seed is not None else 0
            node_ctx = NodeContext(
                node_id=node_id,
                seed=rng_seed,
                resolution=ctx.resolution,
                rng=np.random.default_rng(np.random.SeedSequence(rng_seed)),
                store=ctx.store,
                progress=ctx.progress,
                cancel=ctx.cancel,
            )
            try:
                result = node.run(in_values, params, node_ctx)
            except EvaluationCancelledError:
                raise
            except NodeContractError as exc:
                exc.node_id = node_id  # attribute the contract violation to this node
                raise
            except Exception as exc:
                raise NodeEvalError(node_id, cls.type, str(exc)) from exc

            self.cache.put(key, result)
            outputs[node_id] = result

        return {target: outputs[target] for target in targets}
