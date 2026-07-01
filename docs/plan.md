# gnode — Implementation Plan

> Companion to [`design-draft.md`](design-draft.md) (the spec) and the project
> context notes. This document is the **build plan**: settled decisions, the
> engine architecture, the node model, and a phased milestone breakdown.
>
> **Architecture in one line:** gnode is a **React 19 + Vite + `@xyflow/react` +
> TypeScript** node editor over a **FastAPI** backend, driving a **numpy
> evaluation engine**. The editor side follows standard React Flow / FastAPI
> patterns — node catalog → palette, custom typed-port nodes, schema-driven
> config panel, `isValidConnection` type checking, debounced validation,
> static-serve + Vite proxy. The substance unique to gnode is the **evaluation
> engine**: pure pixel-matrix nodes, pull-based lazy evaluation, structural
> caching, deterministic seeds, and multi-output auxiliary maps (noise fields,
> corruption heatmaps). Everything here is written from scratch.

---

## 0. Build order (decided)

1. **Milestone 1 — Engine + full MVP node catalog, headless & tested (no UI).**
2. **Milestone 2 — FastAPI service layer** (catalog, validate, evaluate/preview, images, graph save/load).
3. **Milestone 3 — React frontend** (canvas, palette, config panel, live preview).
4. **Milestone 4 — Free-code hardening + phase-2 nodes.**

Building the engine first (headless, with a CLI runner and golden-image tests)
lets us validate against the §9 "Datamosh" example graph and the reference
functions **before any UI exists**. The frontend-library choice is therefore
*not* on the critical path and can be finalized during Milestone 1.

---

## 1. Settled decisions (design draft §13)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | IMAGE range | **float32, 0–255 internally**; clip only at output/I-O | Matches the reference functions; no per-node normalization churn. |
| 2 | Cache key / array hashing | **Structural hashing — no array hashing.** One hardened `structural_key()`: `hash(type, canonical(params), upstream_keys, resolution, seed?, engine/schema-version salt)` | Purity ⇒ the key alone identifies an output. **A false hit returns the _wrong_ image — the system's worst failure mode**, so canonicalization (stable ordering, float-repr, enum, free-code code-hash) is exhaustively tested (§5); the version salt invalidates cache across engine/schema upgrades. |
| 3 | Free-code sandbox | **MVP: restricted-exec** (whitelisted builtins, no network/import); **Phase 2: subprocess isolation + timeout/memory cap** | Honest model: restricted-exec is *not* a real security boundary in Python — **treat `.gnode` files as trusted input only** and warn loudly on foreign graphs containing code nodes. Free-code can also break the determinism guarantee (§3.7). |
| 4 | Frontend library | **React Flow (`@xyflow/react`)** *(decided)* | DOM/React rendering fits gnode's rich widgets (code editor, color, vec2, thumbnails, a11y); mature typed React node editor. Built clean-room. Not blocking until Milestone 3. |
| 5 | Mask model | **Optional `mask` input on glitch nodes (MVP)**; add an "apply-with-mask" wrapper node later | Regional effects compose cleanly; wrapper is a later convenience. |
| 6 | Resolution / shape | **Shapes flow with the data.** `meta.resolution` is only Load's normalization target / canvas default — *not* a global invariant | Nodes legitimately change shape (transpose swaps H/W; crop/pad/resize), so the engine never assumes one shape for all `IMAGE` arrays. A `mask`/`field` must match the array it modulates — enforced by boundary checks (§3.1). |

**RNG reconciliation (important).** The context note says the JS prototype used
*mulberry32* with per-node derivation and "keep this contract." The reference
Python functions use `np.random.default_rng(seed)` (PCG64). On the **Python
engine** we standardize on numpy's `Generator`, deriving a per-node stream from
the global seed + node id (via `SeedSequence`). This **preserves the contract**
(same graph + seed ⇒ identical output; per-node derivation) while using the
PRNG the reference code already relies on. mulberry32 was the prototype's
JS-side mechanism; it is intentionally *not* carried into the Python engine.
Outputs will match the reference functions, not the JS prototype, bit-for-bit.
**Determinism caveat:** nodes that re-encode through an external codec (JPEG
databend via Pillow/libjpeg) are deterministic only *per environment* — exact
bytes can shift with the codec version, so those nodes are pinned or tested with
tolerance (§5), not byte-exact across platforms.

---

## 2. Repository layout (standalone app)

Standard, fast tooling — `uv`, `ruff`, `ty`, `pytest` (Python) and Biome + `tsc`
(frontend); the quality gate is spec'd in §2.1. Standalone — the app *is* the
product, so it lives at the top level (not nested under a `tools/` dir).

```text
gnode/
├── pyproject.toml            # uv; deps: numpy, Pillow, imageio; optional: scipy (Sobel/filters)
│                             #   groups: [dev] ruff+ty+pytest+hypothesis, [server] fastapi+uvicorn
├── Makefile                  # setup / check / lint / typecheck / test / dev / serve / build
├── docs/
│   ├── design-draft.md
│   └── plan.md               # (this file)
├── reference/                # UNCHANGED validated numpy funcs (provenance)
├── src/gnode/
│   ├── lib/                  # productionized impl layer (promoted from reference/)
│   │   ├── glitch.py         #   band_displace(_sine), pixel_sort, channel_shift,
│   │   └── artistic.py       #   synthwave/cmy split, block_mosh, databend*, byte_corrupt,
│   │                         #   drag, row_displace, chroma_shift, bitcrush, bit_rotate,
│   │                         #   vignette, echo, warp, gradient_map, scanlines, add_noise
│   ├── core/
│   │   ├── types.py          # PortType enum + conventions (RGB, float32, 0–255, top-left)
│   │   ├── node.py           # Node base class: ports (ClassVars), Params model, evaluate()
│   │   ├── registry.py       # @register_node + pkgutil discovery of gnode.nodes.*
│   │   ├── params.py         # typed widget-field factories: Slider()/ColorField()/SeedField()…
│   │   ├── graph.py          # Graph/Node/Edge Pydantic models + .gnode JSON load/save
│   │   ├── context.py        # Context: seed, resolution, rng_for(node_id), progress cb
│   │   ├── rng.py            # deterministic per-node RNG derivation
│   │   ├── cache.py          # structural_key() + thread-safe bounded LRU + single-flight
│   │   ├── scheduler.py      # topo order from requested terminals (pull-based)
│   │   ├── engine.py         # orchestrates scheduler + evaluator + cache; cancellation token
│   │   ├── ports.py          # driven-adapter protocols: Cache, ImageStore, GraphStore, RNGProvider
│   │   ├── validation.py     # shared checks + can_connect() type-compat policy (emitted to UI)
│   │   ├── image.py          # ensure_image/ensure_mask guards, shape-compat, load/save, to_png
│   │   └── errors.py         # NodeEvalError, GraphError, ...
│   ├── nodes/                # one file per category (a new node = a new file)
│   │   ├── io.py             # load_image, save_image, viewer
│   │   ├── generate.py       # solid, gradient, noise, pattern
│   │   ├── transform.py      # resize/crop/pad, flip, rotate90/transpose
│   │   ├── displace.py       # band_displace, scanline_shift, wave_warp, block_mosh,
│   │   │                     #   pixel_drag, field_warp
│   │   ├── sort.py           # pixel_sort (+ intervals output)
│   │   ├── color.py          # channel_shift, cmy/synthwave split, chroma_shift,
│   │   │                     #   gradient_map, bitcrush, bit_rotate, hsv, channel ops
│   │   ├── corrupt.py        # jpeg_databend (+diff), byte_corrupt
│   │   ├── texture.py        # scanlines, vignette, grain
│   │   ├── mask.py           # mask_from_luminance, shape/gradient mask, blend, echo
│   │   ├── utility.py        # seed, random, math, vec2, color, split/merge channels, reroute
│   │   └── freecode.py       # free-code (Python) node
│   ├── cli.py                # `python -m gnode render graph.gnode -o out.png`
│   └── server/               # Milestone 2 (FastAPI) — see §7
│       ├── app.py            # app factory, CORS, routes, static mount
│       ├── __main__.py       # uvicorn 127.0.0.1:8080
│       ├── schemas.py        # request/response Pydantic models
│       └── store.py          # image store + graph workspace + persistent Engine
├── frontend/                 # Milestone 3 (React + Vite + @xyflow/react) — see §8
└── tests/                    # mirrors src/gnode/
```

Scaffolding note: promote `reference/*.py` into `src/gnode/lib/` as the single
source of truth; keep `reference/` as untouched provenance (README already
frames it that way). Tests assert wrapper-node output equals the `lib` function
output to guard against drift.

**Layering (Ports & Adapters).** Dependencies point inward:
`frontend → HTTP API → engine → nodes → lib`. The domain core (`lib` + `core` +
`nodes`) is pure Python with **no FastAPI, React, or direct disk/network**. The
outside world enters through *driven-adapter protocols* in `ports.py` — `Cache`,
`ImageStore`, `GraphStore`, `RNGProvider` — which are injected. So `Load`/`Save`
never touch the filesystem directly; they go through an injected store (testable
with an in-memory one), and the engine can swap LRU→disk cache or CPU→GPU node
impls without edits. The CLI and the HTTP server are just two *driving adapters*
over the same core — which is exactly why the engine is testable headless.

### 2.1 Tooling & quality gate

**Package manager — `uv`.** Single `pyproject.toml` with a committed `uv.lock`;
`uv sync` for envs. Dependency groups: `dev` = `ruff` + `ty` + `pytest` +
`pytest-cov` + `hypothesis`; `server` = `fastapi` + `uvicorn[standard]`. Runtime
deps: `numpy`, `Pillow`, `imageio` (+ optional `scipy`).

**Python lint + format — `ruff`** (one tool for both). Sensible starting ruleset
in `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E","F","W","I","N","UP","B","C4","SIM","PT","PTH","TID","RET","TC","ARG","RUF"]
# E/F/W pycodestyle+pyflakes · I isort · N naming · UP pyupgrade · B bugbear
# C4 comprehensions · SIM simplify · PT pytest · PTH pathlib · TID tidy-imports
# RET returns · TC type-checking-imports · ARG unused-args · RUF ruff-native

[tool.ruff.lint.per-file-ignores]
"tests/**"         = ["ARG"]        # pytest fixtures are injected as args
"src/gnode/lib/**" = ["N", "E741"]  # keep the glitch math's short names (L, Rp, Gm…)
```

`ruff format` is the formatter (Black-compatible); `ruff check --fix` autofixes.
(Consider adding `S` (bandit) scoped to `server/` + `freecode.py` later.)

**Python types — `ty`** (Astral, fast) over `src/gnode`, config under `[tool.ty]`;
type errors are gate failures.

**Frontend — Biome + `tsc`** (the ruff/ty analogs on the JS side):
- **Biome** (`biome.json`) — one fast Rust binary for lint **and** format;
  `recommended` rules plus the React-hooks rules (`useExhaustiveDependencies`,
  `useHookAtTopLevel`). `biome check` = lint + format-check; `--write` autofixes.
- **`tsc --noEmit`** — TypeScript stays the type authority (no faster
  full-typecheck exists).
- npm scripts: `lint`=`biome check .`, `format`=`biome check --write .`,
  `typecheck`=`tsc -b --noEmit`, `check`=`biome check . && tsc -b --noEmit`.

**One gate — `make check`:** backend `ruff check` + `ruff format --check` +
`ty check src` + `pytest`; frontend `biome check` + `tsc --noEmit`. A `pre-commit`
hook running ruff + biome can be added later.

---

## 3. Core engine design (Milestone 1)

### 3.1 Port types

`PortType` enum with the design §3.1 set: `IMAGE`, `MASK`, `MAP`, `FIELD`,
`INT`, `FLOAT`, `BOOL`, `VEC2`, `COLOR`, `ENUM`, `SEED`, `STRING`, `ANY`.
Conventions pinned in `types.py`: **RGB, float32, 0–255, origin top-left,
axis 0 = rows (y), axis 1 = cols (x)**. Clip only at the output/save node.

These conventions are **enforced, not assumed**: `image.py` provides
`ensure_image()` / `ensure_mask()` guards applied at node boundaries (debug/test
mode) so a node that returns the wrong dtype/range/rank fails loudly instead of
poisoning downstream nodes.

**Shapes flow with the data** (decision §1.6): `meta.resolution` is only Load's
normalization target and the canvas default — the engine never assumes all
`IMAGE` arrays share one shape (transpose swaps H/W; crop/pad/resize change it).
Where a `mask` or `field` modulates an `IMAGE`, a **shape-compat check** at the
node boundary requires them to match (or applies an explicit resize rule).

Wire and handle colors are assigned **per port type** (frontend
`getTypeColor(type)`) so wire compatibility reads at a glance. Type
compatibility itself is **one policy** — `can_connect(src, dst)` in
`validation.py` — emitted in the node catalog so the frontend enforces the same
rule it does (no duplicated `===`; see §3.6, §7).

### 3.2 Node model

Class-based: ports declared as `ClassVar` dicts and params as a nested Pydantic
model, so the config schema is emitted for free via `model_json_schema()`:

```python
class Node:
    type: ClassVar[str]                      # unique id, e.g. "displace.band"
    category: ClassVar[str]                  # "Displacement"
    title: ClassVar[str]                     # UI label
    inputs:  ClassVar[dict[str, PortType]]   # name -> type  (optional/required flag)
    outputs: ClassVar[dict[str, PortType]]   # name -> type  (may be many)
    uses_seed: ClassVar[bool] = False        # cache-key hint (see §3.4)

    class Params(BaseModel): ...             # widget-annotated fields (Field json_schema_extra)

    def evaluate(self, inputs: dict, params: Params, ctx: Context) -> dict:
        return {"image": ...}                # output_name -> value
```

- **Multiple outputs + auxiliary maps are first-class** (the key differentiator):
  `displace.band → {image, field}`, `corrupt.jpeg_databend → {image, diff}`,
  generators → `{map}`. Edges address a specific `(node, output_port)`; a
  `diff` heatmap can feed `mask.from_luminance → pixel_sort.mask`.
- **Params vs inputs.** Params are widget values; inputs are wired ports
  (arrays *and* scalars like `SEED`/`FLOAT`). Where both exist (e.g. seed),
  precedence is **wired input > param > global-seed-derived** (helper
  `ctx.resolve_seed(inputs, params)`).
- **Registry & discovery.** `@register_node` populates a global dict; the server
  imports `gnode.nodes.*` via stdlib `pkgutil.walk_packages` to register
  everything. The catalog serializes each node to a descriptor:
  `{type, category, title, inputs[], outputs[], params_schema, widgets}`.
- **Enforced contract (makes purity testable).** A base-class wrapper runs each
  `evaluate` and, in debug/test mode, asserts the returned dict keys equal the
  declared `outputs` and that **no input array was mutated** (byte-compare
  before/after). The non-destructive invariant thus becomes a test, not a hope.
- **Side-effecting I/O is isolated.** `Load`/`Save` are the only nodes that touch
  the outside world, and they do so through an injected `ImageStore` (§2 ports),
  not direct disk I/O — so the processing core stays pure and cacheable. `Load`
  is a source keyed by `image_id`; `Save` is a sink. `Context` stays **thin** (a
  data holder + `rng_for()`); the free-code toolkit is passed explicitly, not
  bolted onto `ctx`.

### 3.3 Params & widgets

Each node's `Params` is a Pydantic model. Widget hints come from **typed field
factories** in `params.py` — `Slider(min, max, step)`, `ColorField()`,
`SeedField()`, `Vec2Field()`, `CodeField()`, `Enum(...)` — rather than free-form
`json_schema_extra` dicts, so a mistake in widget metadata fails at import, not
silently in the UI. Each factory still emits standard Pydantic `Field` +
`json_schema_extra`, so the JSON Schema stays the single serialized contract.
Widget vocabulary: `number`, `slider`, `int`, `toggle`(bool),
`enum`(dropdown via `Literal`/`Enum`), `color`(COLOR), `vec2`, `seed`(+reroll),
`string`, `code`(multiline). The frontend's schema-driven `ConfigPanel` walks the
emitted JSON Schema (enum/number/bool/string/array/nested-object) and picks a
control per `widget` hint — including the gnode-specific slider/color/vec2/
seed/code controls.

### 3.4 Evaluation & caching

- **Pull-based lazy eval** from requested terminals (Viewer/Save), topologically
  ordered; upstream inputs resolved before a node runs.
- **Structural cache key** — one hardened, exhaustively-tested `structural_key()`:
  `hash(type, canonical(params), tuple(upstream_keys), resolution,
  engine/schema-version-salt [, resolved_seed if uses_seed] [, code_hash for free-code])`.
  Identical key ⇒ identical output (purity + determinism), so the output dict is
  cached under it — **no numpy array hashing**. `uses_seed` keeps a global-seed
  reroll from invalidating deterministic branches. **`canonical()` is the danger
  zone:** stable key ordering, deterministic float formatting (repr round-trip),
  enum normalization — a bug here yields a *false hit that silently returns the
  wrong image*, the system's worst failure mode, so it gets its own test matrix
  (§5). The version salt invalidates the whole cache across engine/schema upgrades.
- **Dirty propagation is implicit:** changing a param changes that node's key →
  descendants' keys change → misses cascade only along the affected path;
  untouched branches keep hitting.
- **Cache store:** thread-safe bounded LRU (`structural_key → output dict`) with
  **single-flight** so concurrent identical keys compute once. The server holds
  one persistent Engine (shared cache across requests) and runs `evaluate` in an
  executor, off the async event loop; a **cancellation token** in `Context` lets
  a superseded live-preview eval bail instead of burning cores or clobbering a
  newer result (§6).
- **Errors** are per-node (`NodeEvalError` carrying node id + exception) so the UI
  shows a red border + tooltip rather than crashing the graph (design §10).

### 3.5 Determinism / RNG

`ctx.rng_for(node_id)` → `np.random.default_rng(SeedSequence(derive(global_seed,
node_id, node_seed)))`. Never touch global `np.random`. See the RNG
reconciliation note in §1.

### 3.6 Serialization (`.gnode` = JSON)

Pydantic `Graph`/`Node`/`Edge` exactly per design §8 (`version`,
`meta{seed, resolution}`, `nodes[{id,type,params,pos}]`,
`edges[{from:[node,port], to:[node,port]}]`). Round-trip load/save; on load,
validate unknown node types, DAG (no cycles), and port existence/type
compatibility using the **shared** `core/validation.py` — one implementation the
loader, the CLI, and the API's `/validate` all call (single source of truth).

Type compatibility is the single `can_connect(src, dst)` policy (exact match +
`ANY` for now; the one place to add coercions later); the resolved compatibility
info is emitted in the `/api/nodes` catalog so the frontend enforces the same
rule instead of hardcoding its own (§7).

**Public contract:** node `type` ids and the `.gnode` schema are now part of an
open-source contract — treat `type` ids as stable identifiers, and give the
loader a `version` **migration path** (upgrade old graphs on load). The same
schema/engine version salts the cache key (§3.4) so upgrades never serve stale
cached outputs.

### 3.7 Free-code node

Signature `def process(image, inputs, params, np, tk, ctx) -> dict`. MVP: compile
once, `exec` in a curated namespace (`np`, `tk` toolkit, `ctx`) with a builtins
whitelist and no network/import; per-node try/except surfaces errors on the node.
Cache key includes a `code_hash` (editing code invalidates). Phase 2:
subprocess/thread isolation with timeout + memory cap.

**Security honesty:** restricted-`exec` is *not* a real sandbox — Python has many
escapes. This is a **trusted-input** model: free-code runs arbitrary code, and
importing an untrusted `.gnode` is dangerous. Say so in the docs and warn in the
UI; subprocess isolation (Phase 2) limits blast radius but is not marketed as
safety. **Determinism asterisk:** arbitrary user code can be non-deterministic
(clocks, un-seeded RNG). We cache by `code_hash` + seed, but the engine-wide
"same graph + seed ⇒ identical output" guarantee does **not** extend to
free-code unless the user's code respects it.

### 3.8 CLI runner (Milestone 1 deliverable)

`python -m gnode render graph.gnode -o out.png [--seed N] [--target node_id]`
renders a `.gnode` file to PNG headlessly — the harness that validates the engine
against the §9 datamosh graph and enables golden-image regression tests before
any UI exists.

---

## 4. MVP node catalog (Milestone 1 scope, design §12)

All wrap `src/gnode/lib/` functions where one exists; glitch nodes take an
optional `mask` input.

- **I/O:** Load Image, Save Image, Viewer.
- **Displacement:** Band Displace (+`field`), Scanline/Slice Shift, Wave Warp,
  Block Mosh, Pixel Drag.
- **Sorting:** Pixel Sort (+`intervals`).
- **Color/Channel:** Channel Shift (RGB split), CMY/Synthwave Split, Chroma
  Shift (VHS), Gradient Map, Bitcrush/Posterize, Bit Rotate.
- **Data Corruption:** JPEG Databend (+`diff`), Byte Corrupt (grain *after*
  re-encode).
- **Texture:** Scanlines, Vignette, Grain.
- **Mask & Compositing:** Mask from Luminance, Blend/Composite, Echo/Ghost.
- **Utility:** Seed, Random, Math, Split/Merge Channels.
- **Custom:** Free Code.

**Phase 2 (Milestone 4):** Depth Estimate, Field Warp from depth, noise variants
(perlin/blue), Voronoi, subgraphs/groups, CRT, GPU backend, batch/multi-image,
preset library, apply-with-mask wrapper.

---

## 5. Testing strategy (engine-first)

- **Node ≡ reference:** each wrapper node's output equals the direct `lib`
  function output on a small fixture image + fixed seed (determinism ⇒ exact
  equality).
- **Cache-key hardening (top priority — a false hit = wrong image):** unit-test
  `structural_key()` canonicalization (param ordering, float repr, enums,
  code-hash, version salt); an **invalidation matrix** — changing each param
  invalidates that node + descendants while unrelated branches still hit; a guard
  that two *distinct* graphs never collide to the same key.
- **Non-destructive invariant:** every node leaves its input arrays
  byte-unchanged (the base-class contract, asserted across the whole catalog).
- **Engine:** topo-sort correctness; cycle rejection; cache hit/miss via
  instrumented eval counts; dirty propagation (one param change recomputes only
  affected nodes); determinism (same graph+seed twice ⇒ identical arrays); seed
  precedence (wired SEED > param > global); eval-order independence.
- **Shape/boundary:** `mask`/`field` vs `image` shape-compat is enforced;
  shape-changing nodes (transpose/crop/pad/resize) propagate new shapes correctly.
- **Codec reproducibility caveat:** codec-based nodes (JPEG databend) are tested
  structurally / with tolerance against **pinned** Pillow/libjpeg — *not*
  byte-exact across platforms (see §1 determinism caveat).
- **Property-based (Hypothesis):** random valid DAGs — topo order is valid and
  the result is independent of evaluation order; cache never alters a result.
- **Serialization:** load→save→load identity; `version` migration of old graphs.
- **Validation:** type mismatch, missing required input, unknown type, cycle.
- **Golden graph:** build the §9 datamosh graph in code, render, snapshot a hash
  (regression guard).
- **Free-code:** sandbox blocks network/import; timeout fires; error surfaces
  cleanly. (Determinism is **not** asserted for arbitrary code — see §3.7.)
- **FE/BE contract:** frontend TS types are generated from (or checked against)
  the backend JSON schema so the catalog contract cannot silently drift.

Exit criteria (M1): `gnode render datamosh.gnode` reproduces the §9 datamosh;
full pytest green; `ruff` + `ty` clean.

---

## 6. Milestone 2 — FastAPI service layer

A conventional FastAPI SPA backend, written from scratch: app factory, CORS for
Vite `:5173`, static serve of the built frontend, `python -m gnode.server` on
`127.0.0.1:8080`, lifespan node-discovery cached at startup. One persistent
`Engine` (+ LRU cache) shared across requests. Because numpy eval is CPU-bound,
`/api/evaluate` runs in a **thread-pool executor** (off the async event loop);
the shared cache is **thread-safe + single-flight**, and each live-preview
request carries a **cancellation token** so a newer edit supersedes an in-flight
eval instead of wasting cores.

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/api/nodes` | Node catalog (descriptors) |
| `POST` | `/api/validate` | Graph → errors/warnings (shared validation) |
| `POST` | `/api/evaluate` | `{graph, targets[]}` → `{node_id: {preview_png, meta}}`; server-side structural cache; **client debounced** |
| `POST` | `/api/images` | Upload → `image_id`; `GET /api/images/{id}` |
| `GET`/`POST` | `/api/graphs` | List / save `.gnode` in workspace |
| `GET`  | `/api/graphs/{name}` | Load `.gnode` → graph |

Previews are **downscaled PNGs** (e.g. long edge ≤ 768) for node thumbnails;
full-res served on demand for the main viewer. Data-URL over JSON for MVP;
binary endpoint is an easy later optimization. Filenames validated against a
strict allowlist regex (directory-traversal guard).

The `/api/nodes` catalog carries each node's param JSON Schema **and** the
`can_connect` compatibility info; the frontend's TS types are generated from
these schemas so the two layers cannot drift (§5).

---

## 7. Milestone 3 — React frontend

React 19 + Vite + TypeScript + **React Flow (`@xyflow/react`)**, built
clean-room. Components to write:

- **`useNodes`** — fetch + cache the `/api/nodes` catalog.
- **`GlitchNode`** — custom node: typed handles colored by PortType, live
  `<img>` thumbnail, editable id, red error border on eval failure.
- **`ConfigPanel`** — schema-driven form that reads each node's params JSON
  Schema + `widget` hints and renders number/slider/int/toggle/enum/color/vec2/
  seed-reroll/string/code controls.
- **`Palette`** — categorized node list with fuzzy search; double-click or drag
  to add to the canvas.
- **`isValidConnection`** — enforce output→input and type compatibility during a
  drag using the **`can_connect` info from the catalog** (not a hardcoded `===`),
  so UI and backend agree by construction.
- **`Wire`** — typed edge, colored by source port type (no topic names — gnode
  edges are just `(from-port → to-port)`).
- **`Toolbar`** — global **seed + Reroll**, resolution, run, save/load/export.
- **`ValidationBar`**, graph-picker modal, export modal, toasts.

Additions central to gnode: **debounced `POST /api/evaluate`** on graph/param
change → refresh node thumbnails + viewer; a **Viewer panel** (full-res +
before/after compare slider); a **code editor** (CodeMirror/Monaco) in the
config panel for the free-code node. UI quality floor per design §10: visible
keyboard focus, `prefers-reduced-motion`, responsive panels, per-node error
display.

Exit criteria (M3): build the §9 datamosh graph on the canvas, drag sliders and
see live previews (cache-fast on unchanged branches), save/load `.gnode`.

---

## 8. Milestone 4 — hardening & phase-2 nodes

Free-code subprocess sandbox (timeout/memory); noise variants; depth estimate +
field-warp-from-depth; Voronoi; subgraphs/groups; CRT; optional GPU backend;
preset library; batch/multi-image; WebSocket streaming previews (upgrade from
REST); apply-with-mask wrapper node.

---

## 9. Open items for sign-off

1. **Frontend library** — ✅ decided: React Flow (`@xyflow/react`), built
   clean-room. Not on the critical path until Milestone 3.
2. **Promote `reference/` into `src/gnode/lib/`** as the single source of truth
   (keep `reference/` as provenance) — confirm this refactor.
3. **Python/tooling versions** — `uv`, `ruff`, `ty`, `pytest`, Python 3.12+/3.14.
   Default: adopt this toolchain.
```
