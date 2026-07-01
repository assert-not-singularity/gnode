"""Utility nodes: Seed, Random, Math, Split/Merge Channels."""

from __future__ import annotations

from typing import Literal

import numpy as np

from gnode.core.node import In, Node, NodeParams
from gnode.core.params import Number, SeedField, Toggle
from gnode.core.registry import register_node
from gnode.core.types import PortType


@register_node
class Seed(Node):
    type = "util.seed"
    category = "Utility"
    title = "Seed"
    outputs = {"seed": PortType.SEED}

    class Params(NodeParams):
        value: int = Number(0, min=0)

    def evaluate(self, inputs, params, ctx):
        return {"seed": int(params.value)}


@register_node
class Random(Node):
    type = "util.random"
    category = "Utility"
    title = "Random"
    outputs = {"value": PortType.FLOAT}
    uses_seed = True

    class Params(NodeParams):
        min: float = Number(0.0)
        max: float = Number(1.0)
        integer: bool = Toggle(False)
        seed: int | None = SeedField()

    def evaluate(self, inputs, params, ctx):
        if params.integer:
            return {"value": int(ctx.rng.integers(int(params.min), int(params.max) + 1))}
        return {"value": float(ctx.rng.uniform(params.min, params.max))}


@register_node
class Math(Node):
    type = "util.math"
    category = "Utility"
    title = "Math"
    inputs = {"a": In(PortType.FLOAT, required=False), "b": In(PortType.FLOAT, required=False)}
    outputs = {"value": PortType.FLOAT}

    class Params(NodeParams):
        a: float = Number(0.0)
        b: float = Number(0.0)
        op: Literal["add", "sub", "mul", "div", "min", "max"] = "add"

    def evaluate(self, inputs, params, ctx):
        a = float(inputs["a"]) if "a" in inputs else params.a
        b = float(inputs["b"]) if "b" in inputs else params.b
        ops = {
            "add": a + b,
            "sub": a - b,
            "mul": a * b,
            "div": a / b if b != 0 else 0.0,
            "min": min(a, b),
            "max": max(a, b),
        }
        return {"value": float(ops[params.op])}


@register_node
class SplitChannels(Node):
    type = "util.split_channels"
    category = "Utility"
    title = "Split Channels"
    inputs = {"image": In(PortType.IMAGE)}
    outputs = {"r": PortType.MAP, "g": PortType.MAP, "b": PortType.MAP}

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        return {
            "r": image[..., 0].copy(),
            "g": image[..., 1].copy(),
            "b": image[..., 2].copy(),
        }


@register_node
class MergeChannels(Node):
    type = "util.merge_channels"
    category = "Utility"
    title = "Merge Channels"
    inputs = {"r": In(PortType.MAP), "g": In(PortType.MAP), "b": In(PortType.MAP)}
    outputs = {"image": PortType.IMAGE}

    def evaluate(self, inputs, params, ctx):
        return {
            "image": np.stack([inputs["r"], inputs["g"], inputs["b"]], axis=2).astype(np.float32)
        }
