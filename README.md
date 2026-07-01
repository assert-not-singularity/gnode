<p align="center">
  <img src="docs/wordmark.svg" alt="gnode" width="520">
</p>

# gnode

A node-based glitch-art editor — think ComfyUI, but for glitch. Chain glitch
blocks on a canvas: an input image flows through displacement, sorting, channel,
and data-corruption nodes to one or more outputs. Every wire carries a pixel
matrix; nodes can also emit auxiliary maps (noise, displacement fields,
corruption heatmaps). Includes a free-code node for custom Python.

> **Status: Milestone 1 — the headless engine works.** The Python evaluation
> engine (typed ports, pull-based lazy eval, structural caching, deterministic
> seeds), the full MVP node catalog (29 nodes), `.gnode` serialization, and a CLI
> renderer are implemented and tested. The FastAPI service (M2) and React Flow
> frontend (M3) are next — see [`docs/plan.md`](docs/plan.md).

## Quick start

```bash
uv sync                                            # create the env (Python 3.12+)
uv run gnode render examples/datamosh.gnode -o out.png
uv run pytest                                      # or: make check
```

That renders the example graph (design §9 "datamosh") to `out.png`.

## Layout
- **`docs/plan.md`** — the build plan: architecture, engine design, decisions,
  milestones, quality gate. **Start here.**
- **`docs/design-draft.md`** — the design spec: data model, node interface, node
  catalog, serialization, MVP scope.
- **`src/gnode/`** — the engine. `core/` (types, node model, registry, graph,
  cache, scheduler, validation, engine), `nodes/` (the node catalog, one file per
  category), `lib/` (the numpy glitch routines), `cli.py`.
- **`reference/`** — the original validated numpy routines, kept as provenance
  (promoted into `src/gnode/lib/`).
- **`examples/`** — sample `.gnode` graphs.

## Tooling
`uv` (packages), `ruff` (lint + format), `ty` (types), `pytest`. Run the whole
gate with `make check`.

## Roadmap (short)
1. ✅ **Graph engine** — typed ports, DAG, pull-based evaluation, structural
   caching, `.gnode` JSON, deterministic seeds, CLI renderer.
2. ✅ **MVP node catalog** — displacement, sorting, colour, corruption, texture,
   masks/compositing, utility, and a free-code node.
3. **FastAPI service** — node catalog, validate, evaluate (preview PNGs), image
   upload, graph save/load.
4. **React Flow frontend** — canvas, palette, schema-driven config panel, live
   previews.
5. Free-code hardening + phase-2 nodes (generators, depth, field warp, groups…).

## License
TBD.
