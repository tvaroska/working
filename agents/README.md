# Agents — Address service agent

The address service agent is a durable ADK `Workflow` graph (ADR-0010): a
`RemoteA2aAgent` **collect** node → a deterministic Sense-B **gate** node → a
**present** node, running on one shared, resumable session. It asks a Document
Bridge to collect an address proof and loops (chase → re-check) until the
deterministic gate says the requirement is satisfied — "LLM routes, code decides."
Documents travel over canonical A2A (JSON-RPC 2.0). See [PLAN.md](../PLAN.md),
[wiki/bridge-service-agent-architecture.md](../wiki/bridge-service-agent-architecture.md),
and [ADR-0010](../docs/decisions/adr-0010-durable-consumer-construct.md).

## Prerequisites

- Python 3.12+
- `uv` (the package manager; fallback to `.venv/bin/python` / `.venv/bin/pytest` if unavailable)

**Real-model credentials** (Vertex AI application-default credentials + `GOOGLE_CLOUD_PROJECT`) are required **only** for the manual agent driver (step 3 below). The driver defaults to Vertex AI in the **global** region and the `gemini-3.7-flash` model. The test suite is fully hermetic and does not need credentials or a running server.

## Layout

```
agents/
  src/
    bridge_client/     Native RemoteA2aAgent Bridge consumer (build_bridge_remote_agent) + pure A2A wire helpers (adr-0009)
    agents/
      mock_bridge/     a2a-sdk mock server (permanent Sprint-1 contract double)
      address/         Address service agent — durable Workflow graph (graph.py) + config + manual driver
  tests/               Pytest suite; test_durable_graph.py is the S1-6 validation gate
../contract/           Shared contract package: CollectRequest, ExchangeTurn, CollectionStatus, LedgerEntry (ADR-0011)
```

## Run the test

```bash
uv run pytest
```

**This is the zero-setup path.** The test suite is fully hermetic:
- It spins up its own mock server on a free port in a daemon thread.
- The graph is deterministic (code gate + code presenter), so no model is called.
- It does **not** need a running server, API credentials, or any environment setup.

`test_durable_graph.py` drives the durable `Workflow` graph end to end against the live mock over canonical A2A — the Collect loop runs, the deterministic gate routes, and the terminal `ExchangeTurn` (matching `wiki/evals/address/expected.json`) lands in session state — and asserts a parked (`input-required`) leg resumes across a fresh Runner pointed at the same session store. The `message/send` → `Task{WORKING}` → `tasks/get` → `COMPLETED` wire ordering is locked separately by `test_native_consumer.py` Test A, and the send-path `CollectRequest` DataPart + durable context threading by `test_interceptor.py`.

## Start the mock

```bash
uv run python -m agents.mock_bridge
```

On startup, the server prints:
- Base URL: `http://127.0.0.1:8080` (or your `MOCK_BRIDGE_HOST`/`MOCK_BRIDGE_PORT`)
- Agent Card: `/.well-known/agent-card.json`
- JSON-RPC endpoint: `/`
- Hold duration

**Environment variables** (all optional):
- `MOCK_BRIDGE_HOST` (default: `127.0.0.1`) — bind address
- `MOCK_BRIDGE_PORT` (default: `8080`) — bind port
- `MOCK_BRIDGE_HOLD_SECONDS` (default: `10.0`) — how long to hold in `WORKING` before `COMPLETED`
- `MOCK_BRIDGE_PARK` (default: unset) — if `1`/`true`, the first turn **parks** at `INPUT_REQUIRED` (a pause awaiting input, not a failure) and only a resume turn completes it. This is the Sprint-1 pause/resume tracer consumed by the native `RemoteA2aAgent` ([adr-0009](../docs/decisions/adr-0009-native-a2a-consumer.md)).

The default 10s hold exercises the poll path. For a quicker manual run, lower it: `MOCK_BRIDGE_HOLD_SECONDS=2`.

## Run in the ADK dev UI (`adk web`)

The address agent is a standard ADK agent package — it exposes a module-level
`app` (a resumable `App` wrapping the durable graph; the ADK loader picks `app`
up ahead of `root_agent`), so the ADK dev UI can serve it directly with
park/resume support:

**Terminal 1** — start the mock Bridge:
```bash
MOCK_BRIDGE_HOLD_SECONDS=2 uv run python -m agents.mock_bridge
```

**Terminal 2** — launch the dev UI pointed at the address agent folder:
```bash
cd agents
cp src/agents/address/.env.example src/agents/address/.env   # first run only; set GOOGLE_CLOUD_PROJECT
uv run adk web src/agents/address
```

Open the printed URL, pick **address**, and chat. Point `adk web` at
`src/agents/address` (not `src/agents`) so only the agent is listed — `mock_bridge`
is an A2A server, not an ADK agent. Vertex AI credentials/region are read from the
folder's `.env` (`GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_LOCATION=global`,
`GOOGLE_CLOUD_PROJECT`); the model and Bridge card URL follow the same env vars as
the manual driver below.

## Run the agent manually

Two-terminal flow (the server and agent must run in separate terminals):

**Terminal 1** — start the mock with a short hold:
```bash
MOCK_BRIDGE_HOLD_SECONDS=2 uv run python -m agents.mock_bridge
```

**Terminal 2** — run the agent:
```bash
uv run python -m agents.address
```

The graph is deterministic today (code gate + code presenter), so this default run makes **no model call and needs no credentials**. It drives the graph for one Collect exchange and prints the terminal `collection_status` (the collected `ExchangeTurn`). Credentials are only needed once an `LlmAgent` presenter is dropped into the graph's present node.

**Environment variables** (all optional):
- `GOOGLE_CLOUD_PROJECT` — Vertex AI project (required for the real model)
- `GOOGLE_GENAI_USE_VERTEXAI` (driver default: `TRUE`) — route Gemini through Vertex AI
- `GOOGLE_CLOUD_LOCATION` (driver default: `global`) — Vertex AI region
- `ADDRESS_AGENT_MODEL` (default: `gemini-3.7-flash`) — model id for the agent
- `BRIDGE_CARD_URL` — the Bridge's Agent Card URL (the single mock→real / local→GCP swap point)
- `BRIDGE_BASE_URL` (default: `http://127.0.0.1:8080`) — used to derive the card URL when `BRIDGE_CARD_URL` is unset

## Native A2A consumer (adr-0009)

The demos consume the Bridge through ADK's platform-native `RemoteA2aAgent`. `bridge_client.build_bridge_remote_agent(agent_card_url, collect_request=...)` returns a card-configured consumer, run **directly as the collect node** of the durable `Workflow` graph (`BaseAgent` subclasses the workflow `BaseNode`, so no `AgentTool` adapter is needed); the structured `CollectRequest` is injected on the send path by a `RequestInterceptor`. The mock→real / local→GCP swap is a **different Agent Card URL**, not different agent code. The native construct gives progress (`TaskStatusUpdateEvent.status.message`) and **park/resume** (`INPUT_REQUIRED` → `LongRunningFunctionTool` pause → `FunctionResponse` resume) for free.

The Collect loop is the graph itself (ADR-0010): collect node → deterministic gate node → present node, on **one shared, resumable session**. The gate reads the latest collected `ExchangeTurn` back from the session, records it to state under `collection_status`, and routes — loop back to collect if not done, advance to present when done. The deterministic gate decides "done"; the model can never mint it ("LLM routes, code decides"). One durable exchange **`context_id`** spans the loop's rounds, threaded through session state (`bridge_exchange_context_id`) and stamped on each send by the interceptor. Because the whole graph runs on one durable session, a parked leg survives a process restart and resumes with no webhook (ADR-0010).

The earlier interim wiring — a `BridgeAgentTool` call-and-return (S1-2) and an `LlmAgent` two-tool Collect loop (S1-4) — was superseded by this graph and lives on only in git history (ADR-0010).

`tests/test_native_consumer.py` covers the wire contract (raw client, Test A) and the `RemoteA2aAgent` pause/resume spike (Test B); `tests/test_interceptor.py` locks the send-path `CollectRequest` DataPart and the durable context threading; `tests/test_durable_graph.py` drives the graph end to end and asserts park/resume across a restart. `RemoteA2aAgent` is `@a2a_experimental` and `ResumabilityConfig` is `@experimental` (ADK 2.7.0, ADR-0012) — tracked in the experimental-surface register.

## Frontend-v1 demo BFF servers

The Frontend-v1 surfaces (`frontend/`) are each backed by a thin Starlette BFF
server under `agents/src/agents/address/`. These are **demo furniture** (lessons
A9) — the only agent-side code allowed to `import bridge`; the production agent
(`agent.py`/`graph.py`) imports none of them. Each module exposes a module-level
`app` built by a `create_app(...)` factory (testable without a live socket), and
snake_case JSON on the wire (the frontend `domain/` layers map to camelCase — B3).

Port map (`docs/lessons-learned.md §C2`):

| Server                              | Port | Transport        | Surface                        |
| ----------------------------------- | ---- | ---------------- | ------------------------------ |
| `agents.address.console_server:app` | 8010 | SSE              | Processing-Agent Console       |
| `agents.address.ops_server:app`     | 8011 | SSE              | Servicer Ops Dashboard         |
| `agents.address.portal_server:app`  | 8012 | REST             | Provider Portal (A2UI Path-B)  |
| `agents.address.timewarp_server:app`| 8013 | REST (no SSE, B4)| Time-warp presenter control    |
| `bridge.edges.a2a.app:create_app`   | 8000 | JSON-RPC (A2A)   | Bridge core inbound edge       |

Start one server (from `agents/`):

```bash
uv run uvicorn agents.address.console_server:app --port 8010
```

Or use the repo-root run scripts (they export the demo env — `BRIDGE_CLOCK_MODE=
virtual`, `BRIDGE_EXTRACTION_ENGINE=fixture`, `BRIDGE_SEAM_MODE=local`):

```bash
scripts/run-console.sh    # 8010 (SSE)
scripts/run-ops.sh        # 8011 (SSE)
scripts/run-portal.sh     # 8012 (REST)
scripts/run-timewarp.sh   # 8013 (REST, no SSE)
scripts/run-core.sh       # 8000 (Bridge core, --factory)
scripts/run-all.sh        # all of the above + the theater Vite dev server (5173)
```

SSE note: the console/ops servers use raw Starlette `StreamingResponse`
(`text/event-stream`) rather than `sse-starlette` — matching the repo's existing
Starlette usage and avoiding an extra dependency. Each emitter yields a
`snapshot` frame, incremental `turn`/`event` frames, then a terminal `done` event
before closing cleanly (B2). `test_{console,ops,portal,timewarp}_server.py` drive
the `create_app` factories over an ASGI test client.

## Lint

```bash
uv run ruff check
```

## See also

- [`../PLAN.md`](../PLAN.md) — active development tracker
- [`../wiki/bridge.md`](../wiki/bridge.md) — root of the design spec
- [`../wiki/bridge-service-agent-architecture.md`](../wiki/bridge-service-agent-architecture.md) — the durable service-agent graph shape
- [`../wiki/bridge-a2a-consumer.md`](../wiki/bridge-a2a-consumer.md) / [`../docs/decisions/adr-0009-native-a2a-consumer.md`](../docs/decisions/adr-0009-native-a2a-consumer.md) — the native `RemoteA2aAgent` consumer
- [`../docs/decisions/adr-0010-durable-consumer-construct.md`](../docs/decisions/adr-0010-durable-consumer-construct.md) — the durable `Workflow` graph that supersedes the interim `AgentTool` wiring
