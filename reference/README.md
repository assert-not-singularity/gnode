# reference implementations

These numpy functions are the reference implementation for gnode's nodes — most
nodes in the design spec (`../docs/design-draft.md`) are thin wrappers around one
of these.

- **`glitch.py`** — parametric core: `band_displace` / `band_displace_sine`
  (`width_var`, `center_bias`, `width_amp_corr`, `amp_rand`), `pixel_sort`
  (`max_span`), `channel_shift`, `synthwave_split`, `cmy_split`, `block_glitch`,
  `databend`.
- **`artistic.py`** — richer / maximalist set: `gradient_map`, `warp`,
  `cmy_print`, `pixel_sort`, `channel_shift`, `block_mosh`, `databend_jpeg`,
  `databend_both`, `byte_corrupt`, `drag`, `row_displace`, `chroma_shift`,
  `bitcrush`, `bit_rotate`, `vignette`, `echo`, `scanlines`, `add_noise`.
- **`b_vertical.py`** — small example recipe (vertical "Glitch B").

**Convention:** images are `float32 [H, W, 3]`, range 0–255, RGB. Functions are
deterministic given a seed. These are CPU/numpy references — the eventual node
backend can reuse them directly or port them.
