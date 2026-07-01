"""Artistic glitch toolkit — richer than the parametric studio: gradient-map
colour grading, per-channel wave warp, CMY misregistration, luminance pixel
sorting, JPEG databending, block mosh, scanlines."""

import numpy as np
from io import BytesIO
from PIL import Image
import PIL.ImageFile as IF

IF.LOAD_TRUNCATED_IMAGES = True  # ty: ignore[invalid-assignment]  # Pillow stub types this False


def gradient_map(L, stops):
    """Map luminance (0..255) through colour stops [(pos0..1,(r,g,b)),...]."""
    x = L / 255.0
    pos = np.array([s[0] for s in stops], np.float32)
    cols = np.array([s[1] for s in stops], np.float32)
    out = np.empty(L.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(x, pos, cols[:, c])
    return out


def warp(ch, amp, freq, phase=0.0, axis=0):
    """Sinusoidal displacement. axis=0: columns slide vertically (wave runs
    left-right). axis=1: rows slide horizontally (wave runs top-bottom)."""
    h, w = ch.shape
    out = np.empty_like(ch)
    if axis == 0:
        for x in range(w):
            d = int(round(amp * np.sin(2 * np.pi * freq * x / w + phase)))
            out[:, x] = np.roll(ch[:, x], d)
    else:
        for y in range(h):
            d = int(round(amp * np.sin(2 * np.pi * freq * y / h + phase)))
            out[y, :] = np.roll(ch[y, :], d)
    return out


def shift2d(ch, dy, dx):
    return np.roll(np.roll(ch, dy, axis=0), dx, axis=1)


def pixel_sort(img, low, high, max_span=0, axis=1, coverage=1.0):
    """Sort pixels by luminance within threshold-masked spans. axis=1 sorts
    along rows (horizontal), axis=0 along columns (vertical). coverage limits
    to a centred band on the perpendicular axis."""
    a = img if axis == 1 else np.swapaxes(img, 0, 1)
    out = a.copy()
    h, w = a.shape[:2]
    lum = a.mean(2)
    c = h / 2
    y0, y1 = int(c - coverage * h / 2), int(c + coverage * h / 2)
    for y in range(max(0, y0), min(h, y1)):
        x = 0
        rl = lum[y]
        while x < w:
            while x < w and not (low < rl[x] < high):
                x += 1
            s = x
            while x < w and (low < rl[x] < high):
                x += 1
            e = x
            if e - s > 1:
                ss = s
                while ss < e:
                    ee = e if max_span <= 0 else min(ss + max_span, e)
                    seg = out[y, ss:ee]
                    out[y, ss:ee] = seg[np.argsort(seg.mean(1))]
                    ss = ee
    return out if axis == 1 else np.swapaxes(out, 0, 1)


def channel_shift(img, off, dy=0):
    out = img.copy()
    out[..., 0] = shift2d(img[..., 0], dy, off)
    out[..., 2] = shift2d(img[..., 2], -dy, -off)
    return out


def databend_jpeg(rgb, seed, quality=90, n=30):
    buf = BytesIO()
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(buf, "JPEG", quality=quality)
    data = bytearray(buf.getvalue())
    rng = np.random.default_rng(seed)
    sos = data.find(b"\xff\xda")
    start = sos + 14 if sos != -1 else 2000
    for _ in range(n):
        i = int(rng.integers(start, len(data) - 2))
        if data[i] == 0xFF:
            continue
        v = int(rng.integers(0, 256))
        data[i] = 0xFE if v == 0xFF else v
    return np.asarray(Image.open(BytesIO(bytes(data))).convert("RGB")).astype(np.float32)


def block_mosh(img, seed, n=10, max_h=60, max_w=260, max_shift=120):
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    out = img.copy()
    for _ in range(n):
        bh, bw = int(rng.integers(8, max_h)), int(rng.integers(40, max_w))
        y, x = int(rng.integers(0, h - bh)), int(rng.integers(0, max(1, w - bw)))
        dx = int(rng.integers(-max_shift, max_shift + 1))
        tx = int(np.clip(x + dx, 0, w - bw))
        out[y : y + bh, tx : tx + bw] = img[y : y + bh, x : x + bw]
    return out


def scanlines(img, strength=0.12, gap=3):
    out = img.copy()
    out[::gap] *= 1 - strength
    return out


# ---------- maximalist / community-style additions ----------


def shift2d_rgb(img, dy, dx):
    return np.roll(np.roll(img, dy, axis=0), dx, axis=1)


def screen(a, b):
    return 255 - (255 - a) * (255 - b) / 255.0


def echo(img, ghosts):
    """Screen-blend shifted ghost copies. ghosts: [(dy,dx,alpha),...]."""
    out = img.copy()
    for dy, dx, al in ghosts:
        g = shift2d_rgb(img, dy, dx)
        out = out * (1 - al) + screen(out, g) * al
    return out


def chroma_shift(img, dx=8, dy=0, bleed=1.15):
    """VHS chroma bleed: displace Cb/Cr, keep luma sharp."""
    R, G, B = img[..., 0], img[..., 1], img[..., 2]
    Y = 0.299 * R + 0.587 * G + 0.114 * B
    Cb = -0.168736 * R - 0.331264 * G + 0.5 * B
    Cr = 0.5 * R - 0.418688 * G - 0.081312 * B
    Cb = shift2d(Cb, dy, dx) * bleed
    Cr = shift2d(Cr, -dy, -dx) * bleed
    R2 = Y + 1.402 * Cr
    G2 = Y - 0.344136 * Cb - 0.714136 * Cr
    B2 = Y + 1.772 * Cb
    return np.stack([R2, G2, B2], -1)


def bitcrush(img, levels=6):
    step = 255.0 / (levels - 1)
    return np.round(img / step) * step


def vignette(img, strength=0.5):
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    return img * (1 - strength * np.clip(r - 0.35, 0, 1))[..., None]


def byte_corrupt(img, seed, n=4000):
    b = bytearray(np.clip(img, 0, 255).astype(np.uint8).tobytes())
    rng = np.random.default_rng(seed)
    for _ in range(n):
        i = int(rng.integers(0, len(b)))
        b[i] = int(rng.integers(0, 256))
    return np.frombuffer(bytes(b), np.uint8).reshape(img.shape).astype(np.float32)


def drag(img, seed, rows_frac=0.5, decay=0.82, min_len=30, max_len=200):
    """Datamosh-style horizontal pixel drag/smear on random rows."""
    rng = np.random.default_rng(seed)
    out = img.copy()
    h, w = img.shape[:2]
    ys = rng.choice(h, size=int(h * rows_frac), replace=False)
    for y in ys:
        x = int(rng.integers(0, w - 10))
        L = int(rng.integers(min_len, max_len))
        for xi in range(x + 1, min(w, x + L)):
            out[y, xi] = decay * out[y, xi - 1] + (1 - decay) * img[y, xi]
    return out


def row_displace(img, seed, n=80, max_shift=140, big_prob=0.5):
    rng = np.random.default_rng(seed)
    out = img.copy()
    h, w = img.shape[:2]
    cuts = np.sort(rng.choice(np.arange(1, h), size=min(n - 1, h - 2), replace=False))
    bounds = np.concatenate(([0], cuts, [h]))
    for y0, y1 in zip(bounds[:-1], bounds[1:]):
        sh = (
            int(rng.integers(-max_shift, max_shift))
            if rng.random() < big_prob
            else int(rng.integers(-8, 8))
        )
        if sh:
            out[y0:y1] = np.roll(out[y0:y1], sh, axis=1)
    return out


def bit_rotate(img, channel=1, bits=3):
    """Rotate the bits of one channel -> full-frame colour banding chaos."""
    out = img.copy()
    v = np.clip(out[..., channel], 0, 255).astype(np.uint8)
    out[..., channel] = (((v << bits) | (v >> (8 - bits))) & 0xFF).astype(np.float32)
    return out


def databend_both(rgb, seed, quality=88, n=40):
    """Databend from both scan directions (normal + vertically flipped) so
    corruption doesn't spare the top/left of the frame."""
    a = databend_jpeg(rgb, seed, quality, n)
    b = databend_jpeg(rgb[::-1], seed + 100, quality, n)[::-1]
    return np.maximum(a, b) * 0.5 + (a + b) * 0.25  # blend, keep brightness sane
