# gnode — Design Draft (Node-Based Glitch Art Editor)

> Working draft for a node-based glitch art application modeled on **ComfyUI**.
> Purpose of this document: an implementation-ready spec that can be handed to **Claude Code**.

---

## 1. Vision & Scope

A visual graph editor where an **input image** starts as a node and flows through arbitrarily chainable **glitch nodes** to one or more **output nodes**. Every wire carries a **pixel matrix** (numpy array), not a rendered image — previews are derived from it. Beyond images, nodes can produce and pass along **auxiliary data** (noise patterns, masks, displacement fields, optionally depth maps) that modulate other nodes.

**Core principles**
- Node-based, directed acyclic graph (DAG), pull-based lazy evaluation.
- Non-destructive: nodes never mutate their inputs, they return new arrays.
- Deterministic: same graph + same seed ⇒ identical result.
- Incremental: only "dirty" nodes are recomputed (caching).
- Extensible: a new node = a new file; registration is automatic.
- **Free-code node** from day one, so you're not limited to the built-in set.

**Non-goals (v1)**
- No video / no timeline (single image only; batch can come later).
- No mandatory GPU (numpy/CPU is enough; GPU optional in phase 2).
- No cloud / multi-user.

---

## 2. Architecture Overview

```
┌─────────────────────────────┐        WebSocket / REST        ┌──────────────────────────────┐
│  Frontend (Node Editor)     │  ── graph JSON, run, params ─▶ │  Backend (Python)            │
│  - Canvas, Nodes, Wires     │                                │  - Graph model + scheduler   │
│  - Param widgets (sliders…) │  ◀── preview PNGs, progress ── │  - Node registry             │
│  - Live preview thumbnails  │                                │  - Evaluation + cache        │
└─────────────────────────────┘                                │  - Node library (numpy)      │
                                                                └──────────────────────────────┘
```

Recommendation: a **Python backend** (reusing the existing numpy toolkits, see §11) plus a **web frontend** built on a node-editor library. Communication like ComfyUI: the graph is sent as JSON to the backend, evaluated there, and previews are returned as PNG/data-URL over WebSocket.

---

## 3. Data Model

### 3.1 Port Types

Ports are typed; only compatible types can be connected. The image matrix is the central type.

| Type       | Representation (numpy)             | Range / convention                            |
|------------|------------------------------------|-----------------------------------------------|
| `IMAGE`    | `float32 [H, W, 3]`                | 0–255, RGB, no alpha in v1                     |
| `MASK`     | `float32 [H, W]`                   | 0–1 (selection / opacity)                      |
| `MAP`      | `float32 [H, W]`                   | free (noise, depth, gradient ramp); normalizable to 0–1 |
| `FIELD`    | `float32 [H, W, 2]`                | (dy, dx) pixel offsets for warps / displacement |
| `INT`      | `int`                              |                                               |
| `FLOAT`    | `float`                            |                                               |
| `BOOL`     | `bool`                             |                                               |
| `VEC2`     | `(float, float)`                   | e.g. an offset                                 |
| `COLOR`    | `(r, g, b)` 0–255                   |                                               |
| `ENUM`     | `str` from a fixed set             | e.g. `axis ∈ {"horizontal","vertical"}`       |
| `SEED`     | `int`                              | its own type so seeds can be wired explicitly  |
| `STRING`   | `str`                              |                                               |
| `ANY`      | passthrough (free-code / reroute)  | type-checked at runtime                        |

Pin down the conventions (important for implementation): **RGB**, **float32**, **0–255**, **origin top-left**, axis 0 = rows (y), axis 1 = columns (x). Clip only at the output node.

### 3.2 Node Interface

Every node declares a category, typed inputs/outputs, params (widget-backed), and a pure `evaluate` function.

```python
class NodeSpec:
    type: str                       # unique ID, e.g. "displace.band"
    category: str                   # e.g. "Displacement"
    title: str                      # UI label
    inputs:  dict[str, PortSpec]    # name -> {type, required, default_link?}
    outputs: dict[str, PortSpec]    # name -> {type}
    params:  dict[str, ParamSpec]   # name -> {type, default, min, max, step, widget, choices?}

    def evaluate(self, inputs: dict, params: dict, ctx: Context) -> dict:
        """Pure function. `inputs` holds resolved upstream values,
        `params` the widget values, `ctx` global state (seed, resolution, rng)."""
        return {"image": ...}       # dict: output_name -> value
```

`Context` (`ctx`) carries: the global `seed`, target `resolution`, `rng_for(node_id)` (deterministic node-local RNG derived from the global seed + node ID + optional node seed param), and a progress callback.

**Important for the user's "multiple outputs" idea:** a node may have several outputs. Examples:
- `Band Displace` → `image` (IMAGE) **and** optionally `field` (FIELD, the displacement it used).
- `JPEG Databend` → `image` **and** optionally `diff` (MAP, |before−after| as a corruption heatmap).
- Generators (`Noise`, `Gradient`, `Depth`) → `map` (MAP), which other nodes consume as an amplitude/mask source.

### 3.3 Graph Model

- `Graph = { nodes: Node[], edges: Edge[], meta }`.
- `Node = { id, type, params, pos }`.
- `Edge = { from: [node_id, out_port], to: [node_id, in_port] }`.
- An input accepts **one** edge; an output may fan out to **many** inputs.
- Cycles are forbidden (DAG check on connect).

---

## 4. Evaluation & Caching Model

- **Pull-based / lazy:** evaluation starts from the requested terminal nodes (`Viewer`, `Save`) and works backward, topologically sorted.
- **Caching:** each node caches its output dict under a key
  `hash(node.type, node.params, [upstream_output_hashes], ctx.seed_slice, ctx.resolution)`.
  If nothing upstream changed, the cache hits. Array hashing e.g. via `xxhash` over the bytes (for large arrays optionally over a downsample, with a small collision risk — decision in §13).
- **Dirty propagation:** a param change marks the node + all descendants dirty; a re-run recomputes only those.
- **Live preview:** while editing a slider, re-evaluate with debounce (as in the existing "Glitch Studio" prototype). Stream previews as downscaled PNGs to node thumbnails and the viewer.
- **Determinism:** always derive RNG from `ctx.rng_for(node_id)`, never global `np.random` without a seed.

---

## 5. Seed & Randomization Model

- A global `seed` in the graph meta, prominent in the frontend with a "Reroll" button (as in the prototype).
- Every stochastic node has an optional `seed` param **and** a `SEED` input. Priority: wired `SEED` > node param > global seed derived via node ID.
- A dedicated `Seed` node (output `SEED`) lets you couple several nodes to the same seed or vary them deliberately.
- A `Random` node (range → FLOAT/INT, seeded) for parametric variation.

---

## 6. Node Catalog (v1 = MVP, ⊕ = phase 2)

Categories are deliberately cleanly separated. All glitch nodes get (where sensible) an optional `mask` input (MASK) so effects can act regionally — this replaces the earlier `coverage`/`band` hacks with real masks.

### I/O
- **Load Image** — file/upload → `image`. Optional: `width`,`height` (INT outputs).
- **Save Image** — `image` → file (params: `path`, `format`, `quality`).
- **Viewer / Preview** — terminal node, shows `IMAGE` or `MAP`; multiple allowed.

### Sources / Generators
- **Solid Color** — `COLOR`,`W`,`H` → `image`.
- **Gradient** — linear/radial, color stops → `image` or `map`.
- **Noise** — `type ∈ {white, value, perlin, simplex, ⊕blue}`, `scale`, `seed` → `map`.
- **Pattern** — `checker`/`stripes`/`halftone dots`, `cell`, `angle` → `map`.
- **Depth Estimate** ⊕ — monocular depth (e.g. MiDaS / Depth-Anything) → `map`. Optional in v1; fallback "luminance-as-depth".
- **Voronoi / Cellular** ⊕ → `map`.

### Transform (non-destructive / structural)
- **Resize / Crop / Pad**, **Flip**, **Rotate90 / Transpose** (ENUM). *Transpose is the clean way to get "vertical instead of horizontal stripes": transpose → displacement/sort → transpose back.*

### Displacement
- **Band Displace** — `n_bands`,`max_shift`,`width_var`,`center_bias` (sine envelope),`noise`,`width_amp_corr` (narrower ⇒ more amplitude),`amp_rand`,`axis`,`seed`; outputs `image`,⊕`field`. *(matches the final Studio displacement)*
- **Scanline / Slice Shift** — simplified row/column displacement (`n`,`max_shift`,`big_prob`,`seed`).
- **Wave Warp** — `amp`,`freq`,`phase`,`axis`,`per_channel` (BOOL) → `image`.
- **Field Warp** — displaces `image` by a `FIELD`/`MAP` input (`strength`). Lets you use noise/depth maps as a distortion source.
- **Block Mosh** — `n`,`block_h/w range`,`max_shift`,`seed` (the "slabs" you like).
- **Pixel Drag / Smear** — datamosh streaks: `rows_frac`,`decay`,`len range`,`direction`,`seed`.

### Sorting
- **Pixel Sort** — `threshold_low/high`,`max_span` (0=uncapped),`axis`,`sort_key ∈ {luminance,hue,saturation}`,`mask` input. Outputs `image`,⊕`intervals` (MAP of the sorted spans).

### Color / Channel
- **Channel Shift (RGB Split)** — `off`,`dy`, or separate `r/g/b` offsets.
- **CMY / Synthwave Split** — `offset`,`mode ∈ {redcyan, magenta_cyan, cmy}`.
- **Chroma Shift (VHS)** — shift Cb/Cr (`dx`,`dy`,`bleed`), keep luma sharp.
- **Gradient Map** — grade luminance through color stops (the "color grade" heart of the art pieces).
- **Bitcrush / Posterize** — `levels` per channel.
- **Bit Rotate / Bitplane** — `channel`,`bits` (full-frame color chaos).
- **Channel Mixer / Swap / Invert** — swap/mix/invert channels.
- **HSV Adjust** — `hue`,`sat`,`val`,`contrast`.

### Data Corruption
- **JPEG Databend** — `quality`,`n`,`seed`,`direction ∈ {normal, both}` (both = corrupt from both scan directions, so top/left isn't spared). Outputs `image`,⊕`diff`.
- **Byte Corrupt** — raw byte corruption, `n`,`mode ∈ {random, shift}`,`seed`. *Impl. note: apply as grain **after** a re-encode — applied before a JPEG encode it turns the whole image into static.*
- **Bitplane Glitch** ⊕ — XOR/rotate entire bitplanes.

### Texture / Finish
- **Scanlines** — `strength`,`gap`.
- **Vignette** — `strength`.
- **Grain / Add Noise** — `amount`,`mono/color`,`seed`.
- **CRT** ⊕ — curvature + bloom + scanline combined.

### Mask & Compositing
- **Mask from Luminance** — `low`,`high` → `mask`.
- **Mask from Edges** — Sobel → `mask`.
- **Mask from Depth** ⊕ — range over a depth `map` → `mask`.
- **Shape / Gradient Mask** — linear/radial/rect → `mask`.
- **Blend / Composite** — two `IMAGE` + `mode ∈ {normal, screen, multiply, lighten, darken, difference, add}` + `opacity` + optional `mask`.
- **Echo / Ghost** — screen-blend several offset copies (`offsets[]`,`alpha`).

### Utility
- **Seed** (→ `SEED`), **Random** (range → number), **Math** (a op b), **Vec2**, **Color**.
- **Split Channels** / **Merge Channels** (IMAGE ↔ 3× MAP).
- **Reroute**, **Note/Comment**. **Group / Subgraph** ⊕.

### Custom
- **Free Code (Python)** — see §7.

---

## 7. Free-Code Node (Contract)

A node with an editable Python field, so you can try out techniques before they become a "real" node.

**Ports (configurable):** default `image_in: IMAGE` + `in0..inN: ANY`; outputs `image_out: IMAGE` + `out0..outM: ANY`.
**Param:** `code: STRING` (multiline, editor with syntax highlighting).

**Execution contract:** the code defines a function with a fixed signature:

```python
def process(image, inputs, params, np, tk, ctx):
    # image : float32 [H,W,3] 0..255 (or None if nothing is wired)
    # inputs: dict of the other inputs (in0..inN)
    # np    : numpy
    # tk    : toolkit namespace (pixel_sort, channel_shift, databend_jpeg, ...)
    # ctx   : .seed, .rng(), .resolution
    out = image.copy()
    # ... arbitrary transformation ...
    return {"image_out": out}      # dict of the declared outputs
```

**Sandbox / security:** a local desktop app ⇒ arbitrary code is tolerable, but:
- Run in a dedicated namespace with whitelisted builtins; no network imports.
- Optionally `RestrictedPython` or a subprocess with timeout/memory limits (decision in §13).
- Clear UI warning when importing foreign graphs that contain code nodes.

---

## 8. Serialization (Graph JSON)

```json
{
  "version": "1.0",
  "meta": { "seed": 7, "resolution": [768, 768] },
  "nodes": [
    { "id": "n1", "type": "io.load_image", "pos": [40, 200],
      "params": { "path": "portrait.png" } },
    { "id": "n2", "type": "color.gradient_map", "pos": [300, 200],
      "params": { "stops": [[0,[6,20,16]],[0.5,[28,118,90]],[1,[232,255,242]]] } },
    { "id": "n3", "type": "corrupt.jpeg_databend", "pos": [560, 200],
      "params": { "quality": 88, "n": 42, "seed": 17, "direction": "both" } },
    { "id": "n4", "type": "displace.block_mosh", "pos": [820, 200],
      "params": { "n": 20, "max_shift": 190, "seed": 9 } },
    { "id": "n5", "type": "io.viewer", "pos": [1080, 200], "params": {} }
  ],
  "edges": [
    { "from": ["n1","image"], "to": ["n2","image"] },
    { "from": ["n2","image"], "to": ["n3","image"] },
    { "from": ["n3","image"], "to": ["n4","image"] },
    { "from": ["n4","image"], "to": ["n5","image"] }
  ]
}
```

The format is intentionally close to litegraph.js/ComfyUI so an existing editor can be reused with a minimal adapter. A `.gnode` file = this JSON.

---

## 9. Example Graph (reproduces "Datamosh")

An anchor for the implementation — this graph produces the bright full-frame datamosh already built:

```
Load Image
   └▶ Gradient Map (green grade)
         └▶ JPEG Databend (direction=both, n=42, seed=17)
               └▶ Block Mosh (n=20, max_shift=190, seed=9)
                     └▶ Byte Corrupt (n=20000, seed=5)      # grain AFTER databend
                           └▶ Pixel Drag (rows_frac=0.28, seed=3)
                                 └▶ Channel Shift (off=10, dy=1)
                                       └▶ Chroma Shift (dx=8, bleed=1.15)
                                             └▶ Viewer / Save
```

A second branch shows the multi-output idea: `JPEG Databend.diff` → `Mask from Luminance` → the `mask` input of a `Pixel Sort`, so only heavily corrupted regions get additionally sorted.

---

## 10. UI / UX

- Infinite canvas, zoom/pan; nodes with title, color-coded ports (color per type), live thumbnail.
- Node search via double-click / `Tab` (fuzzy), categorized as in §6.
- Param widgets: slider (with live update as in the prototype), number, toggle, dropdown (ENUM), color picker, vec2, seed field + reroll, code editor.
- Viewer node at full resolution + a "before/after" compare slider is desirable.
- Errors shown on the node (red border + tooltip with exception), not as a global crash.
- Quality floor: visible keyboard focus, `prefers-reduced-motion` respected, responsive panel.

---

## 11. Tech Stack Suggestion

**Recommendation (fastest path to ComfyUI parity):**
- **Backend:** Python + **FastAPI** + WebSocket. The node library builds directly on the existing numpy functions (`glitch.py`, `artistic.py`) — most nodes are thin wrappers. Dependencies: `numpy`, `Pillow`, `imageio`; optional `scipy` (Sobel/filters), `xxhash` (cache keys).
- **Frontend:** **litegraph.js** (what ComfyUI itself uses) for maximum node-editor maturity, *or* **React Flow** / **Rete.js** if React is preferred. Previews as data-URL over WS.
- **Packaging (optional):** **Tauri** or **Electron** for a desktop app; otherwise `localhost` in the browser is enough.

**Reuse note:** the already-validated functions cover most of the MVP catalog and should serve as the reference implementation of the nodes:
`band_displace`, `band_displace_sine` (incl. `width_var`/`center_bias`), `pixel_sort` (with `max_span`), `channel_shift`, `synthwave_split`, `cmy_split`, `block_mosh`, `databend_jpeg`, `databend_both`, `byte_corrupt`, `drag`, `row_displace`, `chroma_shift`, `bitcrush`, `bit_rotate`, `vignette`, `echo`, `warp`, `gradient_map`, `scanlines`, `add_noise`. These files are included and can seed a `nodes/` directory.

---

## 12. MVP Boundary

**MVP (first implementation):** graph engine + caching, JSON serialization, frontend with editor/previews/sliders, seed system, and this node set:
Load/Save/Viewer, Band Displace, Scanline Shift, Wave Warp, Block Mosh, Pixel Drag, Pixel Sort, Channel Shift, CMY/Synthwave Split, Chroma Shift, Gradient Map, Bitcrush, Bit Rotate, JPEG Databend, Byte Corrupt, Scanlines, Vignette, Grain, Mask-from-Luminance, Blend/Composite, Echo, Seed/Random/Math, Split/Merge Channels, **Free Code**.

**Phase 2:** Depth Estimate, Field Warp from depth, noise variants (perlin/blue), Voronoi, subgraphs/groups, CRT, GPU backend, batch/multi-image, preset library.

---

## 13. Open Decisions (please settle before implementation)

1. **IMAGE range:** 0–255 (closer to our functions) vs. 0–1 (numerically cleaner). Suggestion: internally 0–255 float32, convert only at I/O.
2. **Array hashing for caching:** full byte hash (correct, slower) vs. downsample hash (fast, minimal collision risk).
3. **Free-code sandbox:** naked exec (fast, unsafe) vs. RestrictedPython vs. subprocess isolation.
4. **Frontend library:** litegraph.js (ComfyUI parity) vs. React Flow (modern stack, more custom work).
5. **Mask model:** optional `mask` input on every glitch node vs. a dedicated "apply-with-mask" wrapper node. Suggestion: both — an input on the node, and a wrapper for combinations.
6. **Resolution handling:** fixed graph resolution (Load rescales) vs. resolution flowing through with resolution-independent nodes.

---

*End of draft. Handoff to Claude Code: start with §11 (stack) + §12 (MVP), use the included `glitch.py`/`artistic.py` as node references, then work through §6.*
