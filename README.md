<p align="center">
  <img src="docs/wordmark.svg" alt="gnode" width="520">
</p>

<p align="center">
  <em>A node-based glitch-art editor — think ComfyUI, but for glitch.</em>
</p>

---

Chain glitch blocks on a canvas: an input image flows through displacement,
sorting, channel, and data-corruption nodes to one or more outputs. Every wire
carries a pixel matrix (a numpy array); nodes can also emit auxiliary maps —
noise, displacement fields, corruption heatmaps. Drop in a **free-code node** to
run your own numpy when the catalog runs out.

The engine is a pure-Python DAG with **deterministic, seeded** evaluation (same
graph + seed ⇒ identical pixels), **structural caching** (tweak one slider and
only the affected subgraph re-runs), and typed ports validated before a node
ever runs. It's usable three ways: a **CLI** that renders a `.gnode` file to PNG,
a **FastAPI** service, and a **React Flow** web editor with live per-node previews.

> **Status — the full stack is up.** The headless engine, the 29-node MVP
> catalog, `.gnode` serialization, the FastAPI service (catalog / validate /
> evaluate / images / graphs), and the React Flow editor (canvas, palette,
> schema-driven config panel, live previews, save/load/export) all work.
> Next up: free-code hardening and phase-2 nodes — see [`docs/plan.md`](docs/plan.md).

## Quick start

### Render a graph (headless)

```bash
uv sync                                            # create the env (Python 3.12+)
uv run gnode render examples/datamosh.gnode -o out.png
```

That renders the example "datamosh" graph (design §9) to `out.png`.

### Run the editor

Two processes — the API and the web frontend:

```bash
# 1. backend  →  http://127.0.0.1:8080
make serve

# 2. frontend →  http://127.0.0.1:5173   (proxies /api to the backend)
make front-install     # first time only
make front-dev
```

Open <http://127.0.0.1:5173>, drag nodes from the palette, wire them up, and
watch each node render live. Save graphs to the workspace or export a `.gnode`
file and a PNG.

## The node catalog (29 nodes)

| Category | Nodes |
| --- | --- |
| **Displacement** | Band Displace · Scanline Shift · Wave Warp · Block Mosh · Pixel Drag |
| **Sorting** | Pixel Sort |
| **Colour** | Channel Shift · CMY / Synthwave Split · Chroma Shift (VHS) · Gradient Map · Bitcrush / Posterize · Bit Rotate |
| **Data Corruption** | JPEG Databend · Byte Corrupt |
| **Texture** | Scanlines · Vignette · Grain |
| **Mask** | Mask from Luminance · Blend / Composite · Echo / Ghost |
| **Utility** | Seed · Random · Math · Split Channels · Merge Channels |
| **I/O** | Load Image · Save Image · Viewer |
| **Custom** | Free Code (Python) |

Adding a node is a new file plus a `@register_node` decorator — the engine, API
catalog, and frontend pick it up automatically. Node `type` ids and the `.gnode`
JSON schema are a stable public contract.

## Architecture

gnode is **hexagonal**: dependencies point inward,
`frontend → HTTP API → engine → nodes → lib`. The core (`lib` + `core` + `nodes`)
is pure Python — no FastAPI, React, or direct disk/network. The outside world
enters through injected `ports.py` protocols (`Cache`, `ImageStore`,
`GraphStore`, `RNGProvider`), so `Load`/`Save` never touch the filesystem
directly. A few load-bearing invariants:

- **Nodes are pure functions** — never mutate inputs; return new arrays.
- **`IMAGE` convention** — float32, 0–255, RGB, origin top-left (row = y, col = x);
  clipping happens only at the save node.
- **Structural cache keys, never array hashing** — a graph's cache key is
  `hash(type, canonical(params), upstream_keys, resolution, seed?, code-hash?)`.
- **One type-compat policy** — `can_connect()` lives in the engine and is emitted
  in the catalog; the frontend consumes it rather than hardcoding rules.

See [`docs/plan.md`](docs/plan.md) (build plan, decisions, quality gate) and
[`docs/design-draft.md`](docs/design-draft.md) (data model, node interface,
serialization).

## Project layout

- **`src/gnode/`** — `core/` (types, node model, registry, graph, cache,
  scheduler, validation, engine), `nodes/` (the catalog, one file per category),
  `lib/` (the numpy glitch routines), `server/` (FastAPI app + schemas), `cli.py`.
- **`frontend/`** — React 19 + Vite + TypeScript + React Flow editor.
- **`reference/`** — the original validated numpy routines, kept as provenance.
- **`examples/`** — sample `.gnode` graphs.
- **`docs/`** — the plan and design spec.

## Development

One gate covers both halves of the stack:

```bash
make check          # backend: ruff check + ruff format --check + ty + pytest
make front-check    # frontend: biome check + tsc -b
```

**Backend** — `uv` (env/deps), `ruff` (lint + format), `ty` (types),
`pytest` (+ `hypothesis`), Pydantic v2, Python 3.12+.
**Frontend** — Vite + TypeScript + React Flow, with **Biome** (lint + format) and
`tsc`; TS types mirror the backend schema.

## License

To be determined — gnode will be released under an open-source license. Until a
`LICENSE` file is added, no license is granted and all rights are reserved.
