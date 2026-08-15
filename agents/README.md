# Agents — M0 Contract Tracer Bullet

An address `LlmAgent` asks a mock Document Bridge once and receives back an eval-sourced document over canonical A2A (JSON-RPC 2.0). This is the **input/output design validation** for the Bridge's contract with agent callers. See [Milestone 0](../PLAN.md) and the [M0 spec](../docs/milestone-0-contract-tracer.md).

## Prerequisites

- Python 3.12+
- `uv` (the package manager; fallback to `.venv/bin/python` / `.venv/bin/pytest` if unavailable)

**Real-model credentials** (Vertex AI application-default credentials + `GOOGLE_CLOUD_PROJECT`) are required **only** for the manual agent driver (step 3 below). The driver defaults to Vertex AI in the **global** region and the `gemini-3.7-flash` model. The test suite is fully hermetic and does not need credentials or a running server.

## Layout

```
agents/
  src/
    contract/          Pydantic models: CollectRequest, ExchangeTurn, CollectionStatus, LedgerEntry
    bridge_client/     Native RemoteA2aAgent Bridge consumer (build_bridge_remote_agent) + pure A2A wire helpers (adr-0009)
    agents/
      mock_bridge/     a2a-sdk mock server (permanent Sprint-1 contract double)
      address/         Address LlmAgent (Bridge as RemoteA2aAgent sub-agent) + manual driver
  tests/               Pytest suite; test_round_trip.py is the M0 validation gate
```

## Run the test

```bash
uv run pytest
```

**This is the zero-setup path.** The test suite is fully hermetic:
- It spins up its own mock server on a free port in a daemon thread.
- It drives the agent with a scripted model stub (`ScriptedTransferModel`), not a real model.
- It does **not** need a running server, API credentials, or any environment setup.

The round-trip test (`test_round_trip_agent_bridge_agent`) proves the agent delegates to its `document_bridge` sub-agent (a native `RemoteA2aAgent`), which collects from the live mock over canonical A2A, and the eval-sourced `ExchangeTurn` (matching `wiki/evals/address/expected.json`) is relayed back into the agent's event stream. The `message/send` → `Task{WORKING}` → `tasks/get` → `COMPLETED` wire ordering is locked separately by `test_native_consumer.py` Test A.

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
`root_agent`, so the ADK dev UI can serve it directly:

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

**Terminal 2** — run the agent (needs credentials):
```bash
uv run python -m agents.address
```

The agent prints the rendered document id (`gov-id-clean`) and its structured fields (name, address, etc.).

**Environment variables** (all optional):
- `GOOGLE_CLOUD_PROJECT` — Vertex AI project (required for the real model)
- `GOOGLE_GENAI_USE_VERTEXAI` (driver default: `TRUE`) — route Gemini through Vertex AI
- `GOOGLE_CLOUD_LOCATION` (driver default: `global`) — Vertex AI region
- `ADDRESS_AGENT_MODEL` (default: `gemini-3.7-flash`) — model id for the agent
- `BRIDGE_CARD_URL` — the Bridge's Agent Card URL (the single mock→real / local→GCP swap point)
- `BRIDGE_BASE_URL` (default: `http://127.0.0.1:8080`) — used to derive the card URL when `BRIDGE_CARD_URL` is unset

## Native A2A consumer (adr-0009)

The demos consume the Bridge through ADK's platform-native `RemoteA2aAgent`. `bridge_client.build_bridge_remote_agent(agent_card_url)` returns a card-configured consumer, wired into the address agent as a **sub-agent** (`document_bridge`); the mock→real / local→GCP swap is a **different Agent Card URL**, not different agent code. The native construct gives progress (`TaskStatusUpdateEvent.status.message`) and **park/resume** (`INPUT_REQUIRED` → `LongRunningFunctionTool` pause → `FunctionResponse` resume) for free. The M0 hand-rolled `BridgeClient` port + poll loop was removed once the wire contract was validated (see the adr-0009 amendment).

`tests/test_native_consumer.py` covers the wire contract (raw client, Test A) and the `RemoteA2aAgent` pause/resume spike (Test B); `tests/test_round_trip.py` covers the address agent's transfer → sub-agent → mock path end to end. `RemoteA2aAgent` is `@a2a_experimental` (ADK 2.7.0) — pinned via `use_legacy=True` until validated.

## Lint

```bash
uv run ruff check
```

## See also

- [`../PLAN.md`](../PLAN.md) — active development tracker (Milestone 0)
- [`../docs/milestone-0-contract-tracer.md`](../docs/milestone-0-contract-tracer.md) — M0 spec
- [`../wiki/bridge.md`](../wiki/bridge.md) — root of the design spec
- [`../wiki/bridge-a2a-consumer.md`](../wiki/bridge-a2a-consumer.md) / [`../docs/decisions/adr-0009-native-a2a-consumer.md`](../docs/decisions/adr-0009-native-a2a-consumer.md) — the native `RemoteA2aAgent` consumer that supersedes this port from Sprint 1
