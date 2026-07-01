# gnode frontend

The node-based editor UI for [gnode](../README.md) — React 19 + Vite +
TypeScript + [React Flow](https://reactflow.dev/) (`@xyflow/react`). It talks to
the FastAPI backend (Milestone 2) over `/api/*`.

## Develop

```bash
npm ci                 # or: make front-install
npm run dev            # Vite dev server on http://localhost:5173
```

The dev server proxies `/api/*` to the backend on `http://127.0.0.1:8080`, so run
the backend alongside it:

```bash
# from the repo root
make serve             # uvicorn on 127.0.0.1:8080
```

## Quality gate

```bash
npm run check          # biome check + tsc -b   (or: make front-check)
npm run build          # tsc -b && vite build
```

- **Biome** — lint + format (`npm run format` writes fixes).
- **`tsc`** — type checking (project references: `src/` + tooling).

## Layout

- `src/api/client.ts` — typed fetch wrappers for the backend API.
- `src/types.ts` — TS types mirroring the backend contract (catalog + `.gnode`).
- `src/hooks/` — data hooks (e.g. `useNodes` loads the node catalog).
- `src/App.tsx` — app shell (canvas, palette, config panel land across M3 WI-2+).
