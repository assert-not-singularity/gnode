"""
Vertical "Glitch B": band displacement + pixel sort (stays grayscale) +
edge-only red/cyan chromatic aberration via channel_shift.

Key point: channel_shift only rolls the R and B channels, so colour appears
ONLY at edges (where luminance has a gradient). Flat areas and the smooth
pixel-sort smears stay neutral grey -- unlike synthwave_split/cmy_split,
which rebuild the whole frame from luminance and thus tint everything.

Vertical stripes are achieved by transposing before the stripe/sort passes
and transposing back before the (horizontal) aberration.
"""
import numpy as np
from PIL import Image
import glitch as g

SRC = "/mnt/user-data/uploads/26602675.png"

def b_vertical(seed=7, max_shift=65):
    src = np.asarray(Image.open(SRC).convert("RGB"))
    t = src.transpose(1, 0, 2)                       # -> vertical orientation
    t = g.band_displace(t, seed=seed, n_bands=50, max_shift=max_shift,
                        p_big=0.42, small_shift=5)   # vertical stripes
    t = g.pixel_sort(t, low=0.18, high=0.85,         # wide window, no span cap
                     band=(150, 330), seed=seed)     # central strip only
    out = t.transpose(1, 0, 2)                        # back to normal
    # edge-only red/cyan aberration (R and B rolled oppositely, G untouched)
    out = g.channel_shift(out, rshift=(1, 7), gshift=(0, 0), bshift=(-1, -7))
    return np.clip(out, 0, 255).astype(np.uint8)

if __name__ == "__main__":
    for seed in (5, 7, 3):
        Image.fromarray(b_vertical(seed)).save(f"bv_seed{seed}.png")
    print("done")
