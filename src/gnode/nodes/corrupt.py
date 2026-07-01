"""Data-corruption nodes: JPEG Databend, Byte Corrupt.

JPEG Databend emits a ``diff`` MAP (|before - after| luminance) — the corruption
heatmap that the §9 datamosh graph feeds into a mask. Note (plan §1 caveat):
these re-encode through Pillow/libjpeg, so exact bytes are per-environment.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

from gnode.core.node import In, Node, NodeParams
from gnode.core.params import SeedField, Slider
from gnode.core.registry import register_node
from gnode.core.types import PortType
from gnode.lib import artistic


@register_node
class JpegDatabend(Node):
    type = "corrupt.jpeg_databend"
    category = "Data Corruption"
    title = "JPEG Databend"
    inputs = {"image": In(PortType.IMAGE), "seed": In(PortType.SEED, required=False)}
    outputs = {"image": PortType.IMAGE, "diff": PortType.MAP}
    uses_seed = True

    class Params(NodeParams):
        quality: int = Slider(88, min=1, max=100, step=1)
        n: int = Slider(40, min=0, max=2000, step=1)
        direction: Literal["normal", "both"] = "normal"
        seed: int | None = SeedField()

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        if params.direction == "both":
            out = artistic.databend_both(image, ctx.seed, quality=params.quality, n=params.n)
        else:
            out = artistic.databend_jpeg(image, ctx.seed, quality=params.quality, n=params.n)
        diff = np.abs(image - out).mean(axis=2).astype(np.float32)
        return {"image": out, "diff": diff}


@register_node
class ByteCorrupt(Node):
    type = "corrupt.byte_corrupt"
    category = "Data Corruption"
    title = "Byte Corrupt"
    inputs = {"image": In(PortType.IMAGE), "seed": In(PortType.SEED, required=False)}
    outputs = {"image": PortType.IMAGE}
    uses_seed = True

    class Params(NodeParams):
        n: int = Slider(4000, min=0, max=100000, step=100)
        seed: int | None = SeedField()

    def evaluate(self, inputs, params, ctx):
        return {"image": artistic.byte_corrupt(inputs["image"], ctx.seed, n=params.n)}
