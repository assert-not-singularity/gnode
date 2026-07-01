<p align="center">
  <img src="docs/wordmark.svg" alt="gnode" width="520">
</p>

# gnode

A node-based glitch-art editor — think ComfyUI, but for glitch. Chain glitch
blocks on a canvas: an input image flows through displacement, sorting, channel,
and data-corruption nodes to one or more outputs. Every wire carries a pixel
matrix; nodes can also emit auxiliary maps (noise, displacement fields,
corruption heatmaps). Includes a free-code node for custom Python.

> **Status: design / prototype phase.** This repo currently holds the design
> spec, validated numpy reference implementations for the nodes, and a working
> single-file parametric prototype. The application itself is not built yet.

## Layout
- **`docs/design-draft.md`** — the full design spec: data model, node interface,
  node catalog, execution/caching, serialization, tech stack, MVP scope.
  **Start here.**
- **`reference/`** — validated numpy implementations of the glitch techniques.
  Each node in the spec maps almost 1:1 onto a function here. See
  `reference/README.md`.

## Roadmap (short)
1. Graph engine — typed ports, DAG, pull-based evaluation, caching — plus JSON
   serialization.
2. Frontend node editor (litegraph.js or React Flow) with live previews and
   slider widgets.
3. MVP node set (spec §12), wrapping the functions in `reference/`.
4. Free-code node, masks/compositing, generators, then phase-2 nodes.

## License
TBD.
