"""Mask & compositing nodes: Mask from Luminance, Blend/Composite, Echo/Ghost."""

from __future__ import annotations

from typing import Literal

import numpy as np

from gnode.core.node import In, Node, NodeParams
from gnode.core.params import Slider
from gnode.core.registry import register_node
from gnode.core.types import PortType
from gnode.lib import artistic
from gnode.nodes._common import apply_mask, luminance


@register_node
class MaskFromLuminance(Node):
    type = "mask.from_luminance"
    category = "Mask"
    title = "Mask from Luminance"
    inputs = {"image": In(PortType.IMAGE)}
    outputs = {"mask": PortType.MASK}

    class Params(NodeParams):
        low: float = Slider(0.2, min=0.0, max=1.0, step=0.01)
        high: float = Slider(0.8, min=0.0, max=1.0, step=0.01)

    def evaluate(self, inputs, params, ctx):
        norm = luminance(inputs["image"]) / 255.0
        mask = ((norm >= params.low) & (norm <= params.high)).astype(np.float32)
        return {"mask": mask}


def _screen(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return 255.0 - (255.0 - a) * (255.0 - b) / 255.0


_MODES = {
    "normal": lambda _a, b: b,
    "screen": _screen,
    "multiply": lambda a, b: a * b / 255.0,
    "lighten": np.maximum,
    "darken": np.minimum,
    "difference": lambda a, b: np.abs(a - b),
    "add": lambda a, b: a + b,
}


@register_node
class Blend(Node):
    type = "mask.blend"
    category = "Mask"
    title = "Blend / Composite"
    inputs = {
        "a": In(PortType.IMAGE),
        "b": In(PortType.IMAGE),
        "mask": In(PortType.MASK, required=False),
    }
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        mode: Literal["normal", "screen", "multiply", "lighten", "darken", "difference", "add"] = (
            "normal"
        )
        opacity: float = Slider(1.0, min=0.0, max=1.0, step=0.01)

    def evaluate(self, inputs, params, ctx):
        base, top = inputs["a"], inputs["b"]
        blended = _MODES[params.mode](base, top)
        mixed = base * (1.0 - params.opacity) + blended * params.opacity
        return {"image": apply_mask(base, mixed, inputs.get("mask"))}


@register_node
class Echo(Node):
    type = "mask.echo"
    category = "Mask"
    title = "Echo / Ghost"
    inputs = {"image": In(PortType.IMAGE), "mask": In(PortType.MASK, required=False)}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        n: int = Slider(3, min=1, max=8, step=1)
        dx: int = Slider(6, min=-100, max=100, step=1)
        dy: int = Slider(0, min=-100, max=100, step=1)
        alpha: float = Slider(0.4, min=0.0, max=1.0, step=0.01)
        decay: float = Slider(0.7, min=0.0, max=1.0, step=0.01)

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        ghosts = [
            (params.dy * i, params.dx * i, params.alpha * (params.decay ** (i - 1)))
            for i in range(1, params.n + 1)
        ]
        out = artistic.echo(image, ghosts)
        return {"image": apply_mask(image, out, inputs.get("mask"))}
