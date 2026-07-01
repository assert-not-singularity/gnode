"""Graph model + ``.gnode`` JSON load/save (plan §3.6, design §8).

The on-disk JSON matches design §8: ``edges`` use ``from``/``to`` arrays of
``[node_id, port]``. ``type`` ids and this schema are a stable public contract;
``migrate()`` is the hook for upgrading older ``version`` values on load.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"


class GraphNode(BaseModel):
    id: str
    type: str
    params: dict[str, Any] = Field(default_factory=dict)
    pos: tuple[float, float] = (0.0, 0.0)


class Edge(BaseModel):
    """A wire from ``src=(node_id, out_port)`` to ``dst=(node_id, in_port)``."""

    model_config = ConfigDict(populate_by_name=True)

    src: tuple[str, str] = Field(alias="from")
    dst: tuple[str, str] = Field(alias="to")


class GraphMeta(BaseModel):
    seed: int = 0
    resolution: tuple[int, int] = (768, 768)


class Graph(BaseModel):
    version: str = SCHEMA_VERSION
    meta: GraphMeta = Field(default_factory=GraphMeta)
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)

    def node_map(self) -> dict[str, GraphNode]:
        return {n.id: n for n in self.nodes}


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade an older graph dict to the current schema. Identity for 1.0."""
    return data


def load_graph(text: str) -> Graph:
    return Graph.model_validate(migrate(json.loads(text)))


def load_graph_file(path: str | Path) -> Graph:
    return load_graph(Path(path).read_text(encoding="utf-8"))


def dump_graph(graph: Graph) -> str:
    return json.dumps(graph.model_dump(by_alias=True, mode="json"), indent=2)


def save_graph_file(graph: Graph, path: str | Path) -> None:
    Path(path).write_text(dump_graph(graph), encoding="utf-8")
