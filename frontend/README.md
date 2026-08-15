# A2A Document Bridge — Frontend

React + TypeScript + Vite + MUI scaffold for the Document Bridge UI surfaces.

**Sprint 0 status:** This is a navigable shell with placeholder pages for the three Sprint-1 surfaces. No domain behavior, no SSE, no wire mapping.

**Sprint 1 will split this single app** into per-surface apps (`agent-console`, `ops-dashboard`, `provider-portal`, `timewarp`) + a shared UI/domain package. See `wiki/bridge-frontend.md`.

## Development

```bash
# Install dependencies
pnpm install

# Dev server (http://localhost:5173)
pnpm dev

# Lint & format
pnpm lint
pnpm format

# Unit tests (Vitest)
pnpm test

# Build for production
pnpm build

# Preview production build (http://localhost:4173)
pnpm preview

# E2E tests (Playwright) — requires a built app
pnpm build && pnpm test:e2e
```

## Tech Stack

- **Framework:** React 19 + TypeScript 6
- **Build:** Vite 8
- **UI:** MUI 9 + Emotion
- **Routing:** react-router-dom 7
- **Testing:** Vitest (unit), Playwright (e2e)
- **Linting:** ESLint (flat config) + Prettier

## Wire Mapping (Sprint 1)

The backend snake_case domain types (e.g., `collection_status`, `ledger_entry`) will be mapped to camelCase in a future `domain/` layer. See `docs/lessons-learned.md §B3`.
