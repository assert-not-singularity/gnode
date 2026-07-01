"""Free-code node (plan §3.7, §5).

The free-code node runs user Python in a restricted namespace. This is a
*trusted-input* model, not a real sandbox, so we assert the documented behaviour:
the default passthrough works, a body that modifies the image works, and casual
escapes (``import``, un-whitelisted builtins like ``open``) plus a missing
``process`` fail with a clear error. Per plan §3.7 we do **not** assert
determinism for arbitrary code.
"""

from __future__ import annotations

import numpy as np
import pytest

from gnode.core.registry import get_node

from .conftest import make_image, node_ctx

_NODE_TYPE = "custom.free_code"


def _run(code: str, inputs: dict) -> dict:
    node = get_node(_NODE_TYPE)
    params = type(node).params_model().model_validate({"code": code})
    return node.run(inputs, params, node_ctx(node_id="fc"))


def test_default_passthrough_returns_input() -> None:
    node = get_node(_NODE_TYPE)
    img = make_image()
    # Default code is the identity passthrough.
    params = type(node).params_model()()  # defaults
    out = node.run({"image": img}, params, node_ctx(node_id="fc"))
    assert np.array_equal(out["image"], img)


def test_body_can_modify_image() -> None:
    img = make_image()
    code = "def process(image, inputs, params, np, tk, ctx):\n    return {'image': image * 0.5}\n"
    out = _run(code, {"image": img})
    assert np.array_equal(out["image"], img * 0.5)


def test_toolkit_available() -> None:
    # The 'tk' toolkit exposes lib helpers; using it should work.
    img = make_image()
    code = (
        "def process(image, inputs, params, np, tk, ctx):\n"
        "    return {'image': tk.artistic.bitcrush(image, levels=4)}\n"
    )
    out = _run(code, {"image": img})
    from gnode.lib import artistic

    assert np.array_equal(out["image"], artistic.bitcrush(img, levels=4))


def test_import_is_blocked() -> None:
    code = (
        "def process(image, inputs, params, np, tk, ctx):\n"
        "    import os\n"
        "    return {'image': image}\n"
    )
    with pytest.raises(ImportError):
        _run(code, {"image": make_image()})


def test_unwhitelisted_builtin_blocked() -> None:
    code = (
        "def process(image, inputs, params, np, tk, ctx):\n"
        "    open('secrets.txt')\n"
        "    return {'image': image}\n"
    )
    with pytest.raises(NameError):
        _run(code, {"image": make_image()})


def test_missing_process_raises_clear_error() -> None:
    with pytest.raises(RuntimeError, match="must define process"):
        _run("x = 1\n", {"image": make_image()})


def test_wrong_return_shape_raises_clear_error() -> None:
    code = (
        "def process(image, inputs, params, np, tk, ctx):\n"
        "    return image\n"  # not a dict
    )
    with pytest.raises(RuntimeError, match="must return"):
        _run(code, {"image": make_image()})
