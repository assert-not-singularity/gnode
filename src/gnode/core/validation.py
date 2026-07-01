"""Graph validation + the single type-compatibility policy (plan §3.6).

One implementation used by the loader, the CLI, and (in M2) the API. ``can_connect``
is the sole place type-compat is decided; it is emitted in the catalog so the
frontend enforces exactly the same rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import ValidationError as PydanticValidationError

from gnode.core import registry, scheduler
from gnode.core.errors import GraphError
from gnode.core.types import PortType

if TYPE_CHECKING:
    from gnode.core.graph import Graph


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def can_connect(src: PortType, dst: PortType) -> bool:
    """The one type-compatibility policy: exact match, with ``ANY`` as a
    wildcard. The single place to add coercions later."""
    return src == PortType.ANY or dst == PortType.ANY or src == dst


def validate_graph(graph: Graph) -> ValidationResult:
    registry.discover()
    errors: list[str] = []
    warnings: list[str] = []

    # 1. duplicate ids (block the rest — everything keys off node id)
    seen: set[str] = set()
    for node in graph.nodes:
        if node.id in seen:
            errors.append(f"duplicate node id '{node.id}'")
        seen.add(node.id)
    if errors:
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    # 2. resolve node classes
    classes = {}
    for node in graph.nodes:
        try:
            classes[node.id] = type(registry.get_node(node.type))
        except KeyError:
            errors.append(f"node '{node.id}': unknown type '{node.type}'")
    node_ids = set(classes)

    # 3. params validate against each node's Params model
    for node in graph.nodes:
        cls = classes.get(node.id)
        if cls is None:
            continue
        try:
            cls.params_model().model_validate(node.params)
        except PydanticValidationError as exc:
            errors.append(f"node '{node.id}' params invalid: {exc.error_count()} error(s)")

    # 4. edges: node/port existence, one-edge-per-input, type compatibility
    input_edges: dict[tuple[str, str], int] = {}
    for edge in graph.edges:
        (src_node, src_port), (dst_node, dst_port) = edge.src, edge.dst
        src_cls, dst_cls = classes.get(src_node), classes.get(dst_node)
        if src_cls is None:
            errors.append(f"edge from unknown node '{src_node}'")
            continue
        if dst_cls is None:
            errors.append(f"edge to unknown node '{dst_node}'")
            continue
        if src_port not in src_cls.outputs:
            errors.append(f"node '{src_node}' has no output port '{src_port}'")
            continue
        if dst_port not in dst_cls.inputs:
            errors.append(f"node '{dst_node}' has no input port '{dst_port}'")
            continue
        input_edges[dst_node, dst_port] = input_edges.get((dst_node, dst_port), 0) + 1
        if not can_connect(src_cls.outputs[src_port], dst_cls.inputs[dst_port].type):
            errors.append(
                f"type mismatch: {src_node}.{src_port} "
                f"({src_cls.outputs[src_port]}) -> {dst_node}.{dst_port} "
                f"({dst_cls.inputs[dst_port].type})"
            )

    # 5. at most one edge per input port
    errors.extend(
        f"input '{node}.{port}' has {count} incoming edges (max 1)"
        for (node, port), count in input_edges.items()
        if count > 1
    )

    # 6. required inputs must be connected
    for node in graph.nodes:
        cls = classes.get(node.id)
        if cls is None:
            continue
        errors.extend(
            f"node '{node.id}': required input '{name}' is not connected"
            for name, port in cls.inputs.items()
            if port.required and (node.id, name) not in input_edges
        )

    # 7. cycles / unknown edge endpoints
    if node_ids:
        try:
            scheduler.reachable_order(graph, [n.id for n in graph.nodes if n.id in node_ids])
        except GraphError as exc:
            errors.append(str(exc))

    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)
