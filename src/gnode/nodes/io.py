"""I/O nodes: Load, Save, Viewer.

These are the only side-effecting nodes; they reach the outside world through
the injected ``ctx.store`` (an ``ImageStore``), never direct disk access.
"""

from __future__ import annotations

from gnode.core.image import ensure_image, fit
from gnode.core.node import In, Node, NodeParams
from gnode.core.params import Text
from gnode.core.registry import register_node
from gnode.core.types import PortType


@register_node
class LoadImage(Node):
    type = "io.load_image"
    category = "I/O"
    title = "Load Image"
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        image_id: str = Text("", description="id/path resolved by the image store")

    def evaluate(self, inputs, params, ctx):
        if ctx.store is None:
            raise RuntimeError("io.load_image: no image store configured")
        image = ensure_image(ctx.store.load(params.image_id))
        return {"image": fit(image, ctx.resolution)}


@register_node
class SaveImage(Node):
    type = "io.save_image"
    category = "I/O"
    title = "Save Image"
    inputs = {"image": In(PortType.IMAGE)}
    outputs = {"image": PortType.IMAGE}

    class Params(NodeParams):
        path: str = Text("", description="id/path for the image store")

    def evaluate(self, inputs, params, ctx):
        image = inputs["image"]
        if ctx.store is not None and params.path:
            ctx.store.save(params.path, image)
        return {"image": image}


@register_node
class Viewer(Node):
    type = "io.viewer"
    category = "I/O"
    title = "Viewer"
    inputs = {"image": In(PortType.IMAGE)}
    outputs = {"image": PortType.IMAGE}

    def evaluate(self, inputs, params, ctx):
        return {"image": inputs["image"]}
