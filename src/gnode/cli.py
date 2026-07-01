"""gnode CLI — headless renderer for ``.gnode`` graphs.

    gnode render graph.gnode -o out.png [--seed N] [--target node_id]

Validates the graph, evaluates a terminal node, and writes the image. Image
ids in the graph are resolved relative to the ``.gnode`` file's directory.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from gnode.adapters import FilesystemImageStore
from gnode.core.context import Context
from gnode.core.engine import Engine
from gnode.core.graph import Graph, load_graph_file
from gnode.core.image import ensure_image, to_uint8
from gnode.core.validation import validate_graph

_TERMINAL_TYPES = ("io.viewer", "io.save_image")


def _default_target(graph: Graph) -> str:
    """Pick a render target: a Viewer/Save node, else a sink, else the last node."""
    terminals = [n.id for n in graph.nodes if n.type in _TERMINAL_TYPES]
    if terminals:
        return terminals[-1]
    sources = {edge.src[0] for edge in graph.edges}
    sinks = [n.id for n in graph.nodes if n.id not in sources]
    return (sinks or [graph.nodes[-1].id])[-1]


def _render(args: argparse.Namespace) -> int:
    graph = load_graph_file(args.graph)
    result = validate_graph(graph)
    if not result.valid:
        for message in result.errors:
            print(f"error: {message}", file=sys.stderr)
        return 1
    if not graph.nodes:
        print("error: graph has no nodes", file=sys.stderr)
        return 1
    if args.seed is not None:
        graph.meta.seed = args.seed

    target = args.target or _default_target(graph)
    store = FilesystemImageStore(Path(args.graph).resolve().parent)
    ctx = Context(seed=graph.meta.seed, resolution=tuple(graph.meta.resolution), store=store)

    outputs = Engine().evaluate(graph, [target], ctx)
    image = outputs[target].get("image")
    if image is None:
        print(f"error: target '{target}' produced no IMAGE output", file=sys.stderr)
        return 1

    Image.fromarray(to_uint8(ensure_image(image)), "RGB").save(args.out)
    print(f"wrote {args.out} (target '{target}', seed {graph.meta.seed})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gnode", description="gnode headless renderer")
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render", help="render a .gnode graph to an image")
    render.add_argument("graph", help="path to a .gnode file")
    render.add_argument("-o", "--out", required=True, help="output image path")
    render.add_argument("--seed", type=int, default=None, help="override the graph seed")
    render.add_argument("--target", default=None, help="terminal node id to render")

    args = parser.parse_args(argv)
    if args.command == "render":
        return _render(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
