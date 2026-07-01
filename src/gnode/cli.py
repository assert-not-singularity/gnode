"""gnode CLI — headless renderer for ``.gnode`` graphs.

Milestone 1 target::

    gnode render graph.gnode -o out.png [--seed N] [--target node_id]

The engine wiring is added over the course of Milestone 1; this module is the
entry point declared in ``pyproject.toml``.
"""

from __future__ import annotations

import argparse
import sys


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
        print("gnode render: engine not yet wired (Milestone 1 in progress)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
