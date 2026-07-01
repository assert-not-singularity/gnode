"""Free-code node — arbitrary user Python (plan §3.7).

TRUSTED INPUT ONLY. Restricted-``exec`` is *not* a real security boundary; a
whitelisted builtins namespace with no ``__import__`` merely blocks casual
imports. Importing an untrusted ``.gnode`` that contains a code node runs
arbitrary code. Determinism holds only if the user's code respects it.
"""

from __future__ import annotations

import builtins
from types import SimpleNamespace
from typing import Any

import numpy as np

from gnode.core.node import In, Node, NodeParams
from gnode.core.params import CodeField
from gnode.core.registry import register_node
from gnode.core.types import PortType
from gnode.lib import artistic, glitch
from gnode.nodes._common import apply_mask, luminance

_ALLOWED_BUILTINS = [
    "abs",
    "all",
    "any",
    "bool",
    "dict",
    "divmod",
    "enumerate",
    "filter",
    "float",
    "int",
    "len",
    "list",
    "map",
    "max",
    "min",
    "pow",
    "print",
    "range",
    "reversed",
    "round",
    "set",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
]
_SAFE_BUILTINS = {name: getattr(builtins, name) for name in _ALLOWED_BUILTINS}

_TOOLKIT = SimpleNamespace(
    glitch=glitch, artistic=artistic, apply_mask=apply_mask, luminance=luminance
)

_DEFAULT_CODE = "def process(image, inputs, params, np, tk, ctx):\n    return {'image': image}\n"


@register_node
class FreeCode(Node):
    type = "custom.free_code"
    category = "Custom"
    title = "Free Code (Python)"
    inputs = {
        "image": In(PortType.IMAGE, required=False),
        "mask": In(PortType.MASK, required=False),
    }
    outputs = {"image": PortType.IMAGE}
    uses_seed = True

    class Params(NodeParams):
        code: str = CodeField(_DEFAULT_CODE)

    def evaluate(self, inputs, params, ctx):
        namespace: dict[str, Any] = {"__builtins__": _SAFE_BUILTINS}
        exec(compile(params.code, "<free_code>", "exec"), namespace)
        process = namespace.get("process")
        if not callable(process):
            raise RuntimeError("free code must define process(image, inputs, params, np, tk, ctx)")
        result = process(inputs.get("image"), inputs, params.model_dump(), np, _TOOLKIT, ctx)
        if not isinstance(result, dict) or not ({"image", "image_out"} & set(result)):
            raise RuntimeError(
                "process(...) must return a dict with an 'image' (or 'image_out') array"
            )
        out = result.get("image", result.get("image_out"))
        original = inputs.get("image")
        if original is not None:
            out = apply_mask(original, out, inputs.get("mask"))
        return {"image": out}
