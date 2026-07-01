"""Texture / finish nodes: Scanlines, Vignette, Grain."""

from __future__ import annotations

import numpy as np

from gnode.core.node import In, Node, NodeParams
from gnode.core.params import SeedField, Slider, Toggle
from gnode.core.registry import register_node
from gnode.core.types import PortType
from gnode.lib import artistic
from gnode.nodes._common import apply_mask


@register_node
class Scanlines(Node):
    type = "texture.scanlines"
    category = "Texture"
    title = "Scanlines"
    inputs = {"image": In(PortType.IMAGE)}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        strength: float = Slider(0.12, min=0.0, max=1.0, step=0.01)
        gap: int = Slider(3, min=1, max=16, step=1)

    def evaluate(self, inputs, params, ctx):
        out = artistic.scanlines(inputs["image"], strength=params.strength, gap=params.gap)
        return {"image": out}


@register_node
class Vignette(Node):
    type = "texture.vignette"
    category = "Texture"
    title = "Vignette"
    inputs = {"image": In(PortType.IMAGE)}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        strength: float = Slider(0.5, min=0.0, max=1.0, step=0.01)

    def evaluate(self, inputs, params, ctx):
        return {"image": artistic.vignette(inputs["image"], strength=params.strength)}


@register_node
class Grain(Node):
    type = "texture.grain"
    category = "Texture"
    title = "Grain"
    inputs = {
        "image": In(PortType.IMAGE),
        "mask": In(PortType.MASK, required=False),
        "seed": In(PortType.SEED, required=False),
    }
    outputs = {"image": PortType.IMAGE}
    uses_seed = True

    class Params(NodeParams):
        amount: float = Slider(12.0, min=0.0, max=64.0, step=1.0)
        mono: bool = Toggle(True)
        seed: int | None = SeedField()

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        h, w, _ = image.shape
        shape = (h, w, 1) if params.mono else image.shape
        noise = ctx.rng.normal(0.0, params.amount, shape).astype(np.float32)
        return {"image": apply_mask(image, image + noise, inputs.get("mask"))}
