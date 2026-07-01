"""Displacement nodes: Band Displace, Scanline Shift, Wave Warp, Block Mosh,
Pixel Drag. Seeded nodes pass ``ctx.seed`` (the engine's resolved node seed) to
the underlying lib routine so determinism + reroll flow through the cache key."""

from __future__ import annotations

from typing import Literal

import numpy as np

from gnode.core.node import In, Node, NodeParams
from gnode.core.params import SeedField, Slider
from gnode.core.registry import register_node
from gnode.core.types import PortType
from gnode.lib import artistic, glitch
from gnode.nodes._common import apply_mask

_MASK = In(PortType.MASK, required=False)
_SEED = In(PortType.SEED, required=False)


@register_node
class BandDisplace(Node):
    type = "displace.band"
    category = "Displacement"
    title = "Band Displace"
    inputs = {"image": In(PortType.IMAGE), "mask": _MASK, "seed": _SEED}
    outputs = {"image": PortType.IMAGE}
    uses_seed = True

    class Params(NodeParams):
        n_bands: int = Slider(24, min=1, max=128, step=1)
        max_shift: int = Slider(60, min=0, max=300, step=1)
        noise: float = Slider(0.18, min=0.0, max=1.0, step=0.01)
        center_bias: float = Slider(1.3, min=0.1, max=4.0, step=0.1)
        width_var: float = Slider(0.6, min=0.0, max=2.0, step=0.05)
        axis: Literal["horizontal", "vertical"] = "horizontal"
        seed: int | None = SeedField()

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        work = image if params.axis == "horizontal" else image.transpose(1, 0, 2)
        out = glitch.band_displace_sine(
            work,
            seed=ctx.seed,
            n_bands=params.n_bands,
            max_shift=params.max_shift,
            noise=params.noise,
            power=params.center_bias,
            width_var=params.width_var,
        )
        if params.axis == "vertical":
            out = out.transpose(1, 0, 2)
        return {"image": apply_mask(image, out, inputs.get("mask"))}


@register_node
class ScanlineShift(Node):
    type = "displace.scanline"
    category = "Displacement"
    title = "Scanline Shift"
    inputs = {"image": In(PortType.IMAGE), "mask": _MASK, "seed": _SEED}
    outputs = {"image": PortType.IMAGE}
    uses_seed = True

    class Params(NodeParams):
        n: int = Slider(80, min=1, max=400, step=1)
        max_shift: int = Slider(140, min=0, max=400, step=1)
        big_prob: float = Slider(0.5, min=0.0, max=1.0, step=0.01)
        seed: int | None = SeedField()

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        out = artistic.row_displace(
            image, seed=ctx.seed, n=params.n, max_shift=params.max_shift, big_prob=params.big_prob
        )
        return {"image": apply_mask(image, out, inputs.get("mask"))}


@register_node
class WaveWarp(Node):
    type = "displace.wave"
    category = "Displacement"
    title = "Wave Warp"
    inputs = {"image": In(PortType.IMAGE), "mask": _MASK}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        amp: float = Slider(8.0, min=0.0, max=100.0, step=1.0)
        freq: float = Slider(3.0, min=0.1, max=32.0, step=0.1)
        phase: float = Slider(0.0, min=0.0, max=6.283, step=0.05)
        axis: Literal["horizontal", "vertical"] = "horizontal"
        per_channel: bool = False

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        warp_axis = 1 if params.axis == "horizontal" else 0
        channels = [
            artistic.warp(
                image[..., c],
                params.amp,
                params.freq,
                params.phase + (c * 0.6 if params.per_channel else 0.0),
                warp_axis,
            )
            for c in range(3)
        ]
        out = np.stack(channels, axis=2)
        return {"image": apply_mask(image, out, inputs.get("mask"))}


@register_node
class BlockMosh(Node):
    type = "displace.block_mosh"
    category = "Displacement"
    title = "Block Mosh"
    inputs = {"image": In(PortType.IMAGE), "mask": _MASK, "seed": _SEED}
    outputs = {"image": PortType.IMAGE}
    uses_seed = True

    class Params(NodeParams):
        n: int = Slider(10, min=1, max=80, step=1)
        max_h: int = Slider(60, min=8, max=400, step=1)
        max_w: int = Slider(260, min=40, max=800, step=1)
        max_shift: int = Slider(120, min=0, max=400, step=1)
        seed: int | None = SeedField()

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        out = artistic.block_mosh(
            image,
            seed=ctx.seed,
            n=params.n,
            max_h=params.max_h,
            max_w=params.max_w,
            max_shift=params.max_shift,
        )
        return {"image": apply_mask(image, out, inputs.get("mask"))}


@register_node
class PixelDrag(Node):
    type = "displace.pixel_drag"
    category = "Displacement"
    title = "Pixel Drag"
    inputs = {"image": In(PortType.IMAGE), "mask": _MASK, "seed": _SEED}
    outputs = {"image": PortType.IMAGE}
    uses_seed = True

    class Params(NodeParams):
        rows_frac: float = Slider(0.5, min=0.0, max=1.0, step=0.01)
        decay: float = Slider(0.82, min=0.0, max=1.0, step=0.01)
        min_len: int = Slider(30, min=1, max=400, step=1)
        max_len: int = Slider(200, min=2, max=800, step=1)
        seed: int | None = SeedField()

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        out = artistic.drag(
            image,
            seed=ctx.seed,
            rows_frac=params.rows_frac,
            decay=params.decay,
            min_len=params.min_len,
            max_len=max(params.min_len + 1, params.max_len),
        )
        return {"image": apply_mask(image, out, inputs.get("mask"))}
