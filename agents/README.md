# Agents — M0 Contract Tracer Bullet

An address `LlmAgent` asks a mock Document Bridge once and receives back an eval-sourced document over canonical A2A (JSON-RPC 2.0). This is the **input/output design validation** for the Bridge's contract with agent callers. See [Milestone 0](../PLAN.md) and the [M0 spec](../docs/milestone-0-contract-tracer.md).

## Prerequisites

- Python 3.12+
- `uv` (the package manager; fallback to `.venv/bin/python` / `.venv/bin/pytest` if unavailable)

**Real-model credentials** (`GOOGLE_API_KEY` or Vertex AI environment config) are required **only** for the manual agent driver (step 3 below). The test suite is fully hermetic and does not need credentials or a running server.

## Layout

```
agents/
  src/
    contract/          Pydantic models: CollectRequest, ExchangeTurn, CollectionStatus, LedgerEntry
    bridge_client/     BridgeClient port + A2A adapter (message/send → tasks/get polling) — M0 tracer-bullet double; superseded from Sprint 1 by native RemoteA2aAgent (adr-0009)
    agents/
      mock_bridge/     a2a-sdk mock server (permanent Sprint-1 contract double)
      address/         Address LlmAgent + manual driver
  tests/               Pytest suite; test_round_trip.py is the M0 validation gate
```

## Run the test

```bash
uv run pytest
```

**This is the zero-setup path.** The test suite is fully hermetic:
- It spins up its own mock server on a free port in a daemon thread.
- It drives the agent with a scripted model stub (`ScriptedToolCallModel`), not a real model.
- It does **not** need a running server, API credentials, or any environment setup.

The round-trip test (`test_round_trip_agent_mock_agent`) proves:
1. The `CollectRequest` payload survives the full A2A envelope and matches the eval-sourced document in `wiki/evals/address/expected.json`.
2. The async `message/send` → `Task{WORKING}` → `tasks/get` polling → `COMPLETED` path is actually exercised (not skipped by a blocking sleep).

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

**Environment variables** (both optional):
- `GOOGLE_API_KEY` — API key for Gemini (or configure Vertex AI in your environment)
- `ADDRESS_AGENT_MODEL` (default: `gemini-2.0-flash`) — model id for the agent
- `BRIDGE_BASE_URL` (default: `http://127.0.0.1:8080`) — the mock's address

## Native A2A consumer (Sprint 1, adr-0009)

From Sprint 1 the demos consume the Bridge through ADK's platform-native `RemoteA2aAgent` rather than the M0 `BridgeClient` poll loop (kept only as a tracer-bullet double). `bridge_client.build_bridge_remote_agent(agent_card_url)` returns a card-configured consumer — the mock→real / local→GCP swap is a **different Agent Card URL**, not different agent code. The native construct gives progress (`TaskStatusUpdateEvent.status.message`) and **park/resume** (`INPUT_REQUIRED` → `LongRunningFunctionTool` pause → `FunctionResponse` resume) for free.

`tests/test_native_consumer.py` covers this end to end: the wire contract (raw client), the `RemoteA2aAgent` pause/resume spike, and the port's `BridgeParkedError` guard. `RemoteA2aAgent` is `@a2a_experimental` (ADK 2.7.0) — pinned via `use_legacy=True` until validated.

## Lint

```bash
uv run ruff check
```

## See also

- [`../PLAN.md`](../PLAN.md) — active development tracker (Milestone 0)
- [`../docs/milestone-0-contract-tracer.md`](../docs/milestone-0-contract-tracer.md) — M0 spec
- [`../wiki/bridge.md`](../wiki/bridge.md) — root of the design spec
- [`../wiki/bridge-a2a-consumer.md`](../wiki/bridge-a2a-consumer.md) / [`../docs/decisions/adr-0009-native-a2a-consumer.md`](../docs/decisions/adr-0009-native-a2a-consumer.md) — the native `RemoteA2aAgent` consumer that supersedes this port from Sprint 1
