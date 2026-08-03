# ClearSlate frontend

The inventory UI: upload/paste a screenplay, poll breakdown progress, review
the extracted element inventory before kicking off research (Phase 2).

React + TypeScript + Vite. No external font/asset requests — everything is
bundled.

## Development

```bash
npm install
npm run dev      # http://localhost:5173, proxies /api to localhost:8000
npm run build    # tsc -b && vite build
npm run lint      # oxlint
```

The dev server proxies `/api/*` to a backend running on `localhost:8000`
(see `vite.config.ts`). Start the FastAPI backend separately:

```bash
uv run uvicorn clearslate.api.app:app --port 8000
```

## Structure

- `src/api.ts` — wire types + `createRun` / `getRun` / `getElements`
- `src/useRun.ts` — polling hook for run status + one-shot element fetch
- `src/categories.ts` — the 9 element categories, chip colors, counting
- `src/components/` — `UploadPane`, `RunProgress`, `CostEstimateCard`,
  `CategoryFilterBar`, `InventoryTable`
