# gnode

Node-based, glitch-first image editor: chain glitch nodes on a canvas; an input
image flows through displacement / sorting / channel / data-corruption nodes to
one or more outputs. Every wire carries a pixel matrix (numpy array); nodes may
also emit auxiliary maps (noise fields, corruption heatmaps).

**Read first:** [`docs/plan.md`](docs/plan.md) is the build plan and the source of
truth for decisions, architecture, and milestone order. [`docs/design-draft.md`](docs/design-draft.md)
is the spec (data model, node interface, node catalog). `reference/` holds
validated numpy reference implementations that most nodes wrap.

## Ground rules

- **Clean-room / public repo.** gnode is developed clean-room and will be
  open-sourced. Do **not** copy, adapt, vendor, or reference any external or
  proprietary codebase anywhere in this repo — code, comments, commit messages,
  docs, or agent files. Write everything from scratch; rely only on general,
  publicly-known patterns, and never name or attribute a private source.
- **Docs are the contract.** When you change a load-bearing decision, update
  `plan.md` / `design-draft.md` in the same change so the docs never lie.

## Architecture invariants (don't violate without updating the plan)

- **Nodes are pure functions.** Never mutate inputs; return new arrays. A
  base-class wrapper asserts this in debug/test.
- **Determinism.** Same graph + seed ⇒ identical output. Derive all randomness
  from `ctx.rng_for(node_id)` (numpy `default_rng` + `SeedSequence`); never touch
  global `np.random`. *Caveats:* codec-based nodes (JPEG databend) are
  deterministic only per-environment; free-code only if the user's code is.
- **Image conventions.** `IMAGE` = float32, 0–255, RGB, origin top-left,
  axis 0 = rows (y), axis 1 = cols (x). Clip only at the output/save node.
  Enforced by `ensure_image()` / `ensure_mask()` guards at node boundaries —
  don't re-assume conventions per node.
- **Structural cache keys — no array hashing.** One hardened `structural_key()` =
  `hash(type, canonical(params), upstream_keys, resolution, version-salt, seed?, code-hash?)`.
  `canonical()` is the danger zone: a bug there is a *false hit that returns the
  wrong image* — the worst failure in the system. Test it hard.
- **Shapes flow with the data.** `meta.resolution` is only Load's normalization
  target / canvas default, not a global invariant (transpose/crop/pad/resize
  change shape). A `mask`/`field` must match the array it modulates (boundary check).
- **Hexagonal.** Dependencies point inward: `frontend → HTTP API → engine →
  nodes → lib`. The core (`lib` + `core` + `nodes`) is pure Python — no FastAPI,
  React, or direct disk/network. The outside enters via `ports.py` protocols
  (`Cache`, `ImageStore`, `GraphStore`, `RNGProvider`), injected. `Load`/`Save`
  use an injected store, never direct I/O.
- **One type-compat policy.** `can_connect(src, dst)` in `core/validation.py`,
  emitted in the node catalog; the frontend consumes it (no hardcoded checks).
- **Extensibility.** A new node = a new file + `@register_node`. Never edit the
  engine to add a node. Node `type` ids and the `.gnode` JSON schema are a stable
  public contract.
- **Free-code = trusted input only.** Restricted-`exec` is not a security
  boundary; warn on foreign graphs containing code nodes.

## Tooling

- Python: `uv` (env/deps), `ruff` (lint + format, curated ruleset — see
  `plan.md` §2.1), `ty` (typecheck), `pytest` (+ `hypothesis`). Python 3.12+/3.14.
  `from __future__ import annotations`, full type hints, Pydantic v2.
- Frontend (Milestone 3): React 19 + Vite + TypeScript + React Flow
  (`@xyflow/react`); **Biome** (lint + format) + `tsc --noEmit` (types). TS types
  generated from the backend JSON schema.
- One gate — `make check`: backend `ruff check` + `ruff format --check` +
  `ty check` + `pytest`; frontend `biome check` + `tsc --noEmit`. Never claim
  green without running it.

## Testing bar (see `plan.md` §5)

Node ≡ reference (exact equality); `structural_key()` canonicalization +
cache-invalidation matrix; input non-mutation; determinism (same graph+seed
twice); property-based engine invariants (Hypothesis); codec nodes tested with
tolerance against pinned deps, not byte-exact. Tests mirror `src/gnode/`.

## Build order

M1 engine + full MVP node catalog (headless, CLI runner, pytest) → M2 FastAPI
service (catalog / validate / evaluate / images / graphs) → M3 React frontend →
M4 free-code hardening + phase-2 nodes.
