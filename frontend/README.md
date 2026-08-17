# A2A Document Bridge — Frontend

React + TypeScript + Vite + MUI **pnpm workspace** for the Document Bridge UI
surfaces (Frontend v1): three actor surfaces + a time-warp presenter control,
presented as a Split-Screen Theater and a scrubbable Timeline.

## Workspace layout

A single host-shell app mounts four **surface packages** as routed React
modules; a shared package holds the theme, primitives, the SSE hook, and the
shared contract types. This is the **single-host-shell** deviation from a
per-surface Vite-app-each layout (plan §3): it keeps one build/dev/preview/e2e
target and one `dist/` for Playwright, while the surfaces stay separable
packages. The four **BFF servers** remain four separate uvicorn processes
(`agents/`); the Vite dev proxy forwards each prefix to its backend port.

```
frontend/
  apps/
    theater/               Host shell: AppBar + router + Split-Screen Theater + Timeline; owns vite/playwright config
  packages/
    shared/                @bridge/shared — theme, Panel, Badges, useSse (B2 close discipline), domain/contract (snake→camel)
    agent-console/         @bridge/agent-console — Processing-Agent Console + domain/sense (sense-B derivation)
    ops-dashboard/         @bridge/ops-dashboard — Servicer Ops Dashboard + domain/readModel (per-exchange projection)
    provider-portal/       @bridge/provider-portal — A2UI Path-B portal + domain/outstanding
    timewarp/              @bridge/timewarp — virtual-clock control (no SSE — B4) + domain/clock
  e2e/                     One-shot SSE stub (sse.ts, B1) + theater.spec.ts + smoke.spec.ts + README.md
```

Surface packages are consumed as TypeScript **source** (their `exports` point at
`src/index.ts`); `.npmrc` sets `shamefully-hoist=true` so all deps resolve from
the root `node_modules`. Root scripts fan out recursively (`pnpm -r ...`).

## Development

```bash
# Install dependencies (CI uses --frozen-lockfile; commit pnpm-lock.yaml)
pnpm install

# Dev server (http://localhost:5173) — host shell, proxies to the BFF ports
pnpm dev

# Lint & format (recursive / whole tree)
pnpm lint
pnpm format
pnpm format:check

# Unit tests (Vitest, recursive across packages)
pnpm test

# Build for production (recursive: tsc per package + vite build for the shell)
pnpm build

# Preview production build (http://localhost:4173)
pnpm preview

# E2E tests (Playwright) — requires a built app; webServer previews dist/
pnpm build && pnpm test:e2e
```

## BFF port map

The surfaces talk to four Python BFF servers under `agents/` (start them with
`scripts/run-*.sh`; see `agents/README.md`). The Vite dev proxy
(`apps/theater/vite.config.ts`) forwards each prefix:

| Prefix      | Port | Transport         | Surface                       |
| ----------- | ---- | ----------------- | ----------------------------- |
| `/console`  | 8010 | SSE               | Processing-Agent Console      |
| `/ops`      | 8011 | SSE               | Servicer Ops Dashboard        |
| `/portal`   | 8012 | REST              | Provider Portal (A2UI Path-B) |
| `/timewarp` | 8013 | REST (no SSE, B4) | Time-warp presenter control   |

## Wire mapping (snake→camel, B3)

The wire is **snake_case** (`key_fields`, `doctype_hint`, `collection_status`);
components consume **camelCase** only. Each surface hand-maps at its own
`src/domain/` boundary (`sense.ts`, `readModel.ts`, `outstanding.ts`,
`clock.ts`), with the shared contract mappers in `packages/shared/src/domain/
contract.ts`. Real domain logic (sense-B derivation, ops read-model projection)
lives in `domain/` and is unit-tested directly with Vitest — do not recompute
completeness or mint a disposition in TS (invariant: _LLM routes, code decides_).
See `docs/lessons-learned.md §B3`.

## SSE discipline (B1/B2/B4)

- **B1** — Playwright stubs the whole scripted stream (all frames + terminal
  `done`) as a single response body; `e2e/sse.ts` builds it. `EventSource`
  closes on `done`, so the connection end never triggers a reconnect.
- **B2** — every SSE client sets a `finished` flag so the expected server close
  after `done` is not surfaced as an error (`packages/shared/src/useSse.ts`).
- **B4** — the time-warp server has no background task; "Play" is a browser
  `setInterval` calling the REST `/timewarp/step` endpoint. Not e2e-tested.

## Tech stack

- **Framework:** React 19 + TypeScript 6
- **Build:** Vite 8
- **UI:** MUI 9 + Emotion
- **Routing:** react-router-dom 7
- **Testing:** Vitest (unit, per package), Playwright (e2e, at the root)
- **Linting:** ESLint (flat config) + Prettier
- **Package manager:** pnpm 10.33.0 (workspace)
