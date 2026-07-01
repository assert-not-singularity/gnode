"""Shared helpers for node implementations (mask blending, luminance).

Masks are first-class (plan §1.5): a glitch node computes its effect on the full
image, then blends it back through an optional ``mask`` input.
"""

from __future__ import annotations

import numpy as np

from gnode.core.errors import NodeContractError
from gnode.core.image import ensure_mask


def luminance(img: np.ndarray) -> np.ndarray:
    """Mean-channel luminance ``[H, W]`` (0..255) from an IMAGE ``[H, W, 3]``."""
    return img.mean(axis=2)


def apply_mask(original: np.ndarray, effect: np.ndarray, mask: np.ndarray | None) -> np.ndarray:
    """Blend ``effect`` back over ``original`` through an optional MASK (0..1):
    where the mask is 0 the original shows, where 1 the effect shows. A mask must
    match the image's ``[H, W]`` (shape-compat boundary check, plan §3.1)."""
    if mask is None:
        return effect
    m = ensure_mask(mask)
    if m.shape != original.shape[:2]:
        raise NodeContractError(f"mask shape {m.shape} does not match image {original.shape[:2]}")
    weight = np.clip(m, 0.0, 1.0)[..., None]
    return original * (1.0 - weight) + effect * weight
