"""Sorting nodes: Pixel Sort."""

from __future__ import annotations

from typing import Literal

from gnode.core.node import In, Node, NodeParams
from gnode.core.params import Slider
from gnode.core.registry import register_node
from gnode.core.types import PortType
from gnode.lib import artistic
from gnode.nodes._common import apply_mask


@register_node
class PixelSort(Node):
    type = "sort.pixel_sort"
    category = "Sorting"
    title = "Pixel Sort"
    inputs = {"image": In(PortType.IMAGE), "mask": In(PortType.MASK, required=False)}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        low: float = Slider(0.20, min=0.0, max=1.0, step=0.01)
        high: float = Slider(0.82, min=0.0, max=1.0, step=0.01)
        max_span: int = Slider(0, min=0, max=1024, step=1)  # 0 = uncapped
        axis: Literal["horizontal", "vertical"] = "horizontal"

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        sort_axis = 1 if params.axis == "horizontal" else 0
        out = artistic.pixel_sort(
            image, params.low, params.high, max_span=params.max_span, axis=sort_axis
        )
        return {"image": apply_mask(image, out, inputs.get("mask"))}
