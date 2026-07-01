"""Colour / channel nodes: Channel Shift, CMY/Synthwave Split, Chroma Shift,
Gradient Map, Bitcrush, Bit Rotate."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from gnode.core.node import In, Node, NodeParams
from gnode.core.params import Slider
from gnode.core.registry import register_node
from gnode.core.types import PortType
from gnode.lib import artistic, glitch
from gnode.nodes._common import apply_mask, luminance

_MASK = In(PortType.MASK, required=False)

_GREEN_GRADE = [(0.0, (6.0, 20.0, 16.0)), (0.5, (28.0, 118.0, 90.0)), (1.0, (232.0, 255.0, 242.0))]


@register_node
class ChannelShift(Node):
    type = "color.channel_shift"
    category = "Colour"
    title = "Channel Shift"
    inputs = {"image": In(PortType.IMAGE), "mask": _MASK}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        off: int = Slider(10, min=-100, max=100, step=1)
        dy: int = Slider(0, min=-100, max=100, step=1)

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        out = artistic.channel_shift(image, off=params.off, dy=params.dy)
        return {"image": apply_mask(image, out, inputs.get("mask"))}


@register_node
class Split(Node):
    type = "color.split"
    category = "Colour"
    title = "CMY / Synthwave Split"
    inputs = {"image": In(PortType.IMAGE), "mask": _MASK}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        mode: Literal["synthwave", "cmy"] = "synthwave"
        offset: int = Slider(6, min=0, max=40, step=1)
        angle: float = Slider(0.0, min=0.0, max=360.0, step=1.0)

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        if params.mode == "synthwave":
            out = glitch.synthwave_split(image, offset=params.offset)
        else:
            out = glitch.cmy_split(image, offset=params.offset, angle=params.angle)
        return {"image": apply_mask(image, out, inputs.get("mask"))}


@register_node
class ChromaShift(Node):
    type = "color.chroma_shift"
    category = "Colour"
    title = "Chroma Shift (VHS)"
    inputs = {"image": In(PortType.IMAGE), "mask": _MASK}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        dx: int = Slider(8, min=-60, max=60, step=1)
        dy: int = Slider(0, min=-60, max=60, step=1)
        bleed: float = Slider(1.15, min=0.0, max=3.0, step=0.05)

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        out = artistic.chroma_shift(image, dx=params.dx, dy=params.dy, bleed=params.bleed)
        return {"image": apply_mask(image, out, inputs.get("mask"))}


@register_node
class GradientMap(Node):
    type = "color.gradient_map"
    category = "Colour"
    title = "Gradient Map"
    inputs = {"image": In(PortType.IMAGE), "mask": _MASK}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        stops: list[tuple[float, tuple[float, float, float]]] = Field(
            default_factory=lambda: list(_GREEN_GRADE)
        )

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        out = artistic.gradient_map(luminance(image), params.stops)
        return {"image": apply_mask(image, out, inputs.get("mask"))}


@register_node
class Bitcrush(Node):
    type = "color.bitcrush"
    category = "Colour"
    title = "Bitcrush / Posterize"
    inputs = {"image": In(PortType.IMAGE), "mask": _MASK}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        levels: int = Slider(6, min=2, max=64, step=1)

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        out = artistic.bitcrush(image, levels=params.levels)
        return {"image": apply_mask(image, out, inputs.get("mask"))}


@register_node
class BitRotate(Node):
    type = "color.bit_rotate"
    category = "Colour"
    title = "Bit Rotate"
    inputs = {"image": In(PortType.IMAGE), "mask": _MASK}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        channel: Literal[0, 1, 2] = 1
        bits: int = Slider(3, min=1, max=7, step=1)

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        out = artistic.bit_rotate(image, channel=params.channel, bits=params.bits)
        return {"image": apply_mask(image, out, inputs.get("mask"))}
