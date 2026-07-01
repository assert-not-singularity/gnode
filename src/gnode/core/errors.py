"""Engine error types (plan §3.2, §3.4).

Errors are per-node where possible so the UI can mark the offending node with a
red border + tooltip rather than crashing the whole graph.
"""

from __future__ import annotations


class GnodeError(Exception):
    """Base class for all gnode engine errors."""


class GraphError(GnodeError):
    """Structural problem with a graph (unknown node type, bad edge, cycle)."""


class NodeEvalError(GnodeError):
    """A node raised while evaluating. Carries the node id for UI attribution."""

    def __init__(self, node_id: str, node_type: str, message: str) -> None:
        self.node_id = node_id
        self.node_type = node_type
        super().__init__(f"node '{node_id}' ({node_type}): {message}")


class NodeContractError(GnodeError):
    """A node (or a value crossing a boundary) violated the declared contract:
    wrong output ports, wrong dtype/shape, or a mutated input.

    ``node_id`` is attached by the engine when the violation surfaces during a
    graph evaluation, so callers can attribute it to a specific node."""

    node_id: str | None = None


class EvaluationCancelledError(GnodeError):
    """Raised to unwind a superseded/cancelled evaluation (plan §3.4, §6)."""
