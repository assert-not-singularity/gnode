"""Node base class, input-port spec, and the contract-enforcing run wrapper
(plan §3.2).

A node declares metadata as ``ClassVar``s, a nested ``Params`` model, and an
``evaluate``. ``run`` wraps ``evaluate`` and enforces the contract: the returned
dict must match the declared output ports, and (under ``GNODE_STRICT``) no input
array may be mutated. Set ``GNODE_STRICT=1`` in tests to turn the non-mutation
check on everywhere; it is off by default because snapshotting inputs is costly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

import numpy as np
from pydantic import BaseModel, ConfigDict

from gnode.core.errors import NodeContractError

if TYPE_CHECKING:
    from gnode.core.context import NodeContext
    from gnode.core.types import PortType

STRICT = os.environ.get("GNODE_STRICT", "").lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class In:
    """An input-port declaration: its type and whether it is required."""

    type: PortType
    required: bool = True


class NodeParams(BaseModel):
    """Base params model. Nodes override with a nested ``Params``."""

    model_config = ConfigDict(extra="forbid")


class Node:
    """Base class for all nodes. Subclasses set the ``ClassVar``s, define a nested
    ``Params(NodeParams)``, and implement ``evaluate``."""

    type: ClassVar[str]
    category: ClassVar[str]
    title: ClassVar[str]
    inputs: ClassVar[dict[str, In]] = {}
    outputs: ClassVar[dict[str, PortType]] = {}
    uses_seed: ClassVar[bool] = False

    @classmethod
    def params_model(cls) -> type[NodeParams]:
        """This node's params model — a nested ``class Params(NodeParams)`` if
        defined, else the empty base."""
        return getattr(cls, "Params", NodeParams)

    def run(self, inputs: dict[str, Any], params: NodeParams, ctx: NodeContext) -> dict[str, Any]:
        """Contract-enforcing entry point the engine calls."""
        snapshots = (
            {k: v.copy() for k, v in inputs.items() if isinstance(v, np.ndarray)} if STRICT else {}
        )
        result = self.evaluate(inputs, params, ctx)

        declared = set(type(self).outputs)
        if set(result) != declared:
            raise NodeContractError(
                f"{type(self).type}: outputs {sorted(result)} != declared {sorted(declared)}"
            )
        for key, before in snapshots.items():
            if not np.array_equal(before, inputs[key]):
                raise NodeContractError(f"{type(self).type}: mutated input '{key}'")
        return result

    def evaluate(
        self, inputs: dict[str, Any], params: NodeParams, ctx: NodeContext
    ) -> dict[str, Any]:
        raise NotImplementedError
