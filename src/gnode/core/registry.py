"""Node registry, discovery, and catalog descriptors (plan §3.2).

``@register_node`` records a stateless singleton instance per node type.
``discover()`` imports every ``gnode.nodes.*`` module so the decorators run.
``catalog()`` serializes each node to a descriptor the frontend consumes.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING, Any

from gnode.core.types import TYPE_COLORS

if TYPE_CHECKING:
    from gnode.core.node import Node

_REGISTRY: dict[str, Node] = {}
_discovered = False


def register_node(cls: type[Node]) -> type[Node]:
    """Class decorator: register a node type as a stateless singleton."""
    node_type = getattr(cls, "type", None)
    if not node_type:
        raise ValueError(f"{cls.__name__} must set a `type`")
    if node_type in _REGISTRY:
        raise ValueError(f"duplicate node type '{node_type}'")
    _REGISTRY[node_type] = cls()
    return cls


def get_node(node_type: str) -> Node:
    try:
        return _REGISTRY[node_type]
    except KeyError:
        raise KeyError(f"unknown node type '{node_type}'") from None


def discover() -> None:
    """Import all ``gnode.nodes.*`` modules once so registration runs."""
    global _discovered
    if _discovered:
        return
    import gnode.nodes as pkg

    for _finder, modname, _ispkg in pkgutil.walk_packages(pkg.__path__, prefix="gnode.nodes."):
        importlib.import_module(modname)
    _discovered = True


def all_nodes() -> dict[str, Node]:
    discover()
    return dict(_REGISTRY)


def describe(node: Node) -> dict[str, Any]:
    cls = type(node)
    return {
        "type": cls.type,
        "category": cls.category,
        "title": cls.title,
        "inputs": [
            {"name": n, "type": p.type.value, "required": p.required, "color": TYPE_COLORS[p.type]}
            for n, p in cls.inputs.items()
        ],
        "outputs": [
            {"name": n, "type": t.value, "color": TYPE_COLORS[t]} for n, t in cls.outputs.items()
        ],
        "params_schema": cls.params_model().model_json_schema(),
    }


def catalog() -> list[dict[str, Any]]:
    discover()
    return [describe(n) for n in _REGISTRY.values()]
