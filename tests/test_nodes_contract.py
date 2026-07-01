"""Catalog-wide contract sweep (plan §5: non-mutation + output contract).

For every registered node we synthesize valid inputs from the declared port
types and default params, run the node through its contract-enforcing ``run``
wrapper under ``GNODE_STRICT``, and assert:

* the returned dict's keys equal the declared ``outputs``, and
* every input array is byte-unchanged (the non-mutation invariant).

This is the whole-catalog guard for the base-class contract. It complements the
per-node reference tests: here we only care that *every* node honours the
purity/output contract, not what it computes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pytest

from gnode.core.registry import all_nodes
from gnode.core.types import PortType

from .conftest import MemoryStore, make_image, make_map, make_mask, node_ctx

if TYPE_CHECKING:
    from gnode.core.node import Node

_LOAD_IMAGE_ID = "fixture"

# Some catalog defaults assume a reasonably sized image (block_mosh max_h=60 and
# max_w=260, pixel_drag max_len=200); use a fixture large enough that every
# node's default params are valid, as they are on the §9 datamosh graph (512px).
CH, CW = 320, 320


def _input_value(port_type: PortType) -> Any:
    """A valid value for a declared input port type."""
    if port_type in (PortType.IMAGE,):
        return make_image(h=CH, w=CW)
    if port_type in (PortType.MASK,):
        return make_mask(h=CH, w=CW)
    if port_type in (PortType.MAP, PortType.FIELD):
        return make_map(h=CH, w=CW)
    if port_type is PortType.SEED:
        return 123
    if port_type in (PortType.INT,):
        return 3
    if port_type in (PortType.FLOAT,):
        return 2.0
    if port_type is PortType.BOOL:
        return True
    if port_type is PortType.STRING:
        return "x"
    raise AssertionError(f"no synthesized value for port type {port_type}")


def _build_inputs(node: Node) -> dict[str, Any]:
    """All declared inputs (required and optional) with synthesized values, so
    the non-mutation check covers optional array inputs (masks) too."""
    return {name: _input_value(port.type) for name, port in type(node).inputs.items()}


# Only the production catalog. Throwaway ``_test.*`` / ``_prop.*`` nodes that
# other test modules register into the shared registry are excluded, so this
# sweep is deterministic regardless of test-collection order.
_CATALOG = sorted(t for t in all_nodes() if not t.startswith("_"))


@pytest.mark.parametrize("node_type", _CATALOG)
def test_node_output_and_nonmutation(node_type: str) -> None:
    node = all_nodes()[node_type]
    cls = type(node)
    params = cls.params_model()()  # all defaults

    store = None
    if node_type == "io.load_image":
        store = MemoryStore({_LOAD_IMAGE_ID: make_image(h=CH, w=CW)})
        params = cls.params_model().model_validate({"image_id": _LOAD_IMAGE_ID})

    inputs = _build_inputs(node)
    snapshots = {k: v.copy() for k, v in inputs.items() if isinstance(v, np.ndarray)}

    ctx = node_ctx(node_id=node_type, seed=7, resolution=(CH, CW), store=store)
    # run() enforces the contract itself under GNODE_STRICT; we also re-check here
    # so the assertion is explicit and independent of the env flag.
    result = node.run(inputs, params, ctx)

    assert set(result) == set(cls.outputs), (
        f"{node_type}: returned {sorted(result)} != declared {sorted(cls.outputs)}"
    )
    for key, before in snapshots.items():
        assert np.array_equal(before, inputs[key]), f"{node_type}: mutated input '{key}'"


def test_sweep_covers_whole_catalog() -> None:
    # Guard against the parametrization silently collapsing to nothing, and pin
    # the count so a dropped/renamed node is noticed.
    assert len(_CATALOG) == 29
