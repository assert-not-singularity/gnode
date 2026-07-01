"""
Real glitch-art algorithms (no filter presets):
  - band_displace : horizontal scanline / band displacement  ("stripes")
  - channel_shift : RGB channel offset (chromatic aberration / RGB split)
  - pixel_sort    : Asendorf-style brightness-threshold interval sorting
  - block_glitch  : rectangular block copy/replicate corruption
  - databend      : true byte-level corruption of the raw pixel buffer

All operate on numpy uint8 arrays of shape (H, W, 3).
"""

import numpy as np


def band_displace(arr, seed=0, n_bands=48, max_shift=70, p_big=0.45, small_shift=6):
    """Split image into horizontal bands of random height and roll each
    band horizontally. Most bands get a small shift; a subset gets a big
    one -> dramatic stripes while the overall face stays in place."""
    rng = np.random.default_rng(seed)
    h, w = arr.shape[:2]
    out = arr.copy()
    # random band boundaries (varying heights)
    cuts = np.sort(rng.choice(np.arange(1, h), size=min(n_bands - 1, h - 2), replace=False))
    bounds = np.concatenate(([0], cuts, [h]))
    for y0, y1 in zip(bounds[:-1], bounds[1:]):
        if rng.random() < p_big:
            shift = int(rng.integers(-max_shift, max_shift + 1))
        else:
            shift = int(rng.integers(-small_shift, small_shift + 1))
        if shift:
            out[y0:y1] = np.roll(arr[y0:y1], shift, axis=1)
    return out


def channel_shift(arr, rshift=(0, 5), gshift=(0, 0), bshift=(0, -5)):
    """Offset each channel independently (each shift = (dy, dx)).
    For synthwave magenta/cyan fringing: shift R and G in OPPOSITE
    directions and leave B centered -> one edge R+B (magenta), the
    other G+B (cyan)."""
    out = arr.copy()
    out[..., 0] = np.roll(arr[..., 0], rshift, axis=(0, 1))
    out[..., 1] = np.roll(arr[..., 1], gshift, axis=(0, 1))
    out[..., 2] = np.roll(arr[..., 2], bshift, axis=(0, 1))
    return out


def pixel_sort(arr, low=0.20, high=0.82, band=None, seed=0, max_span=None):
    """Asendorf-style: within each row, find contiguous spans whose
    luminance lies in (low, high) and sort those pixels by brightness.
    If `band` = (y0, y1) is given, only sort that range.
    `max_span` caps the length of each sorted segment -> shorter smears =
    less distortion (None = unlimited)."""
    out = arr.copy()
    lum = arr.mean(axis=2) / 255.0
    h, w = lum.shape
    y0, y1 = (0, h) if band is None else band
    for y in range(y0, y1):
        x = 0
        row_lum = lum[y]
        while x < w:
            while x < w and not (low < row_lum[x] < high):
                x += 1
            start = x
            while x < w and (low < row_lum[x] < high):
                x += 1
            span_end = x
            if span_end - start > 1:
                s = start
                while s < span_end:
                    e = span_end if max_span is None else min(s + max_span, span_end)
                    seg = out[y, s:e]
                    out[y, s:e] = seg[np.argsort(seg.mean(axis=1))]
                    s = e
    return out


def block_glitch(arr, seed=0, n=6, max_h=40, max_w=180, max_shift=90):
    """Copy random rectangular blocks and paste them shifted -> torn look."""
    rng = np.random.default_rng(seed)
    h, w = arr.shape[:2]
    out = arr.copy()
    for _ in range(n):
        bh = int(rng.integers(6, max_h))
        bw = int(rng.integers(40, max_w))
        y = int(rng.integers(0, h - bh))
        x = int(rng.integers(0, max(1, w - bw)))
        dx = int(rng.integers(-max_shift, max_shift + 1))
        block = arr[y : y + bh, x : x + bw]
        tx = np.clip(x + dx, 0, w - bw)
        out[y : y + bh, tx : tx + bw] = block
    return out


def databend(arr, seed=0, n_corrupt=1400, mode="shift"):
    """True databending: treat the raw pixel buffer as a byte stream and
    corrupt individual bytes. 'shift' rotates a run of bytes, 'set' pokes
    random values. Kept moderate so structure survives."""
    rng = np.random.default_rng(seed)
    buf = arr.tobytes()
    b = bytearray(buf)
    n = len(b)
    header_skip = int(n * 0.05)  # leave the very top intact
    for _ in range(n_corrupt):
        i = int(rng.integers(header_skip, n - 8))
        if mode == "shift":
            run = int(rng.integers(2, 8))
            seg = b[i : i + run]
            k = int(rng.integers(1, run))
            b[i : i + run] = seg[k:] + seg[:k]
        else:
            b[i] = int(rng.integers(0, 256))
    return np.frombuffer(bytes(b), dtype=np.uint8).reshape(arr.shape).copy()


def band_displace_sine(arr, seed=0, n_bands=24, max_shift=60, noise=0.18, power=1.3, width_var=0.6):
    """Like band_displace, but the shift magnitude is weighted by a sine
    bump peaking at the image centre (sin(pi*pos)**power), plus a Gaussian
    noise term applied everywhere. So shifts grow toward the middle
    statistically, sign is random, and nothing looks uniform. Rolls axis=1;
    wrap it in a transpose to get vertical stripes.
    `width_var` sets how much band widths vary (lognormal sigma): 0 = all
    equal, higher = a mix of thin and wide stripes."""
    rng = np.random.default_rng(seed)
    h, w = arr.shape[:2]
    out = arr.copy()
    widths = rng.lognormal(0.0, width_var, size=n_bands)  # varied heights
    widths = widths / widths.sum() * h
    bounds = np.concatenate(([0], np.cumsum(widths))).round().astype(int)
    bounds[-1] = h
    bounds = np.maximum.accumulate(bounds)  # strictly increasing
    for y0, y1 in zip(bounds[:-1], bounds[1:]):
        pos = (y0 + y1) / 2 / h  # 0..1 band-centre position
        env = np.sin(np.pi * pos) ** power  # 0 at edges, 1 in middle
        base = max_shift * env * rng.choice([-1, 1])
        jitter = rng.normal(0, max_shift * noise)  # noise everywhere
        shift = int(round(base + jitter))
        if shift:
            out[y0:y1] = np.roll(arr[y0:y1], shift, axis=1)
    return out


def synthwave_split(arr, offset=6):
    """Magenta/cyan chromatic aberration for (near-)grayscale input.
    Carries luminance into R (magenta) shifted one way and G (cyan) the
    other, then fills B = max(R, G) so every edge reads magenta or cyan
    while flat areas stay neutral grey. `offset` = horizontal split in px."""
    L = arr.mean(axis=2)
    Rp = np.roll(L, offset, axis=1)  # magenta carrier (R + B)
    Gm = np.roll(L, -offset, axis=1)  # cyan carrier   (G + B)
    B = np.maximum(Rp, Gm)  # B present wherever either leads
    return np.stack([Rp, Gm, B], axis=2)


def cmy_split(arr, offset=7, angle=0):
    """Three-way cyan / magenta / yellow chromatic aberration. Three
    luminance copies are shifted along three directions 120 deg apart
    (first one at `angle`, degrees) and recombined so
        R = max(magenta, yellow)   G = max(cyan, yellow)   B = max(cyan, magenta)
    Flat areas stay neutral grey; edges fan out into C/M/Y fringes.
    `offset` = shift magnitude in px (bigger = stronger aberration)."""
    L = arr.mean(axis=2)

    def shifted(deg):
        a = np.radians(deg)
        return np.roll(
            L, (int(round(offset * np.sin(a))), int(round(offset * np.cos(a)))), axis=(0, 1)
        )

    cyan, magenta, yellow = shifted(angle), shifted(angle + 120), shifted(angle + 240)
    R = np.maximum(magenta, yellow)
    G = np.maximum(cyan, yellow)
    B = np.maximum(cyan, magenta)
    return np.stack([R, G, B], axis=2)
