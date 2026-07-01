"""Golden end-to-end test for the §9 datamosh example graph.

Environment-robust: it asserts validity, output shape/dtype, and *within-
environment* determinism (running twice yields identical bytes). It deliberately
does not pin a cross-platform hash — the JPEG Databend node re-encodes through
Pillow/libjpeg, whose exact bytes vary by codec version (plan §1 caveat)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from gnode.adapters import FilesystemImageStore
from gnode.core.context import Context
from gnode.core.engine import Engine
from gnode.core.graph import load_graph_file
from gnode.core.validation import validate_graph

_EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
_GRAPH = _EXAMPLES / "datamosh.gnode"


def _render() -> np.ndarray:
    graph = load_graph_file(_GRAPH)
    ctx = Context(
        seed=graph.meta.seed,
        resolution=tuple(graph.meta.resolution),
        store=FilesystemImageStore(_EXAMPLES),
    )
    return Engine().evaluate(graph, ["view"], ctx)["view"]["image"]


def test_datamosh_graph_valid() -> None:
    result = validate_graph(load_graph_file(_GRAPH))
    assert result.valid, result.errors


def test_datamosh_render_shape() -> None:
    image = _render()
    assert image.shape == (512, 512, 3)
    assert image.dtype == np.float32


def test_datamosh_deterministic() -> None:
    assert np.array_equal(_render(), _render())
