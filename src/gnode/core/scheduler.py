"""Topological ordering from requested terminals (plan §3.4).

Pull-based: from the target nodes we walk *incoming* edges (dependencies) and
emit a post-order, so sources come before the nodes that consume them. Only the
subgraph feeding the targets is visited.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gnode.core.errors import GraphError

if TYPE_CHECKING:
    from gnode.core.graph import Graph, GraphNode

# incoming[node_id][in_port] = (src_node_id, src_out_port)
Incoming = dict[str, dict[str, tuple[str, str]]]


def build_incoming(graph: Graph) -> Incoming:
    incoming: Incoming = {}
    for edge in graph.edges:
        src_node, src_port = edge.src
        dst_node, dst_port = edge.dst
        ports = incoming.setdefault(dst_node, {})
        if dst_port in ports:
            # Fail loudly rather than silently pick one edge — an input takes one
            # wire (validation also flags this; the engine must never mis-evaluate).
            raise GraphError(f"input '{dst_node}.{dst_port}' has multiple incoming edges")
        ports[dst_port] = (src_node, src_port)
    return incoming


def reachable_order(
    graph: Graph, targets: list[str]
) -> tuple[list[str], dict[str, GraphNode], Incoming]:
    """Topologically ordered subgraph feeding ``targets`` (sources first).

    Returns ``(order, node_map, incoming)``. Raises ``GraphError`` on an unknown
    target/edge or a cycle.
    """
    node_map = graph.node_map()
    incoming = build_incoming(graph)
    for target in targets:
        if target not in node_map:
            raise GraphError(f"unknown target node '{target}'")

    order: list[str] = []
    visiting, done = 1, 2
    state: dict[str, int] = {}

    def visit(node_id: str, path: tuple[str, ...]) -> None:
        marker = state.get(node_id)
        if marker == done:
            return
        if marker == visiting:
            raise GraphError("cycle detected: " + " -> ".join([*path, node_id]))
        state[node_id] = visiting
        for _in_port, (src_node, _src_port) in incoming.get(node_id, {}).items():
            if src_node not in node_map:
                raise GraphError(f"edge references unknown node '{src_node}'")
            visit(src_node, (*path, node_id))
        state[node_id] = done
        order.append(node_id)

    for target in targets:
        visit(target, ())
    return order, node_map, incoming
