# Feature — Processing Agents & Mock Bridge

**Status:** 📋 Planned (0%) · **Release:** 1 → ongoing · **Spec:** `wiki/bridge-implementation-plan.md`, `wiki/bridge-address-demo.md`, `wiki/bridge-collect.md`

Every phase is **agent-first**: the processing agent (the counterparty that owns per-turn decisions, sense B) is built before the Bridge code for that phase. The agent defines the A2A contract, so the multi-turn negotiation is nailed before the Bridge is committed. *The difference between demos is the agent, not the Bridge.*

## Scope
- **Address processing agent** (Release 1) — bounded Collect loop; satisfaction function `gov-id OR 2 distinct bills`; emits requirements list per turn.
- **Mock Document Bridge** (Release 1, permanent) — speaks the A2A multi-turn contract, injects fixture arrivals, reports a ledger, fakes chase/timeout. Persists as the contract double / agent-side test harness for every later phase.
- **Benefits agent** (Release 2) — fan-out, read comparison, drive revise loop, decide bind.
- **RFP agent** (Release 2) — emergent policy: posts and mutates Requirements per turn, handles conditionals, asserts done.
- **Simulated counterparty agents** (Release 2, demo furniture — *not* processing agents) — Path-A carrier agents built in **different frameworks** (Google ADK + LangGraph) to prove A2A interoperability; the LangGraph one drives the multi-turn negotiate loop. See `docs/features/benefits-demo.md`.

## Key rule
The mock Bridge is a **maintained artifact, not throwaway** — agent regressions are caught against it without standing up the platform.

## Build components (Release 1)

- Address processing agent — the Collect loop runs as an `LlmAgent` on ADK (the LLM chooses which proof to request; a deterministic `is_satisfied` code gate owns "done" — `gov-id OR 2 distinct bills`), emitting a per-turn requirements list (`agents/src/agents/address/`). The loop is transport- and policy-agnostic behind a `BridgeClient` port, which is what makes the mock→real swap a no-op for the agent core.
- Mock Document Bridge — the A2A multi-turn contract, fixture arrivals, ledger reporting, faked chase/timeout (`agents/src/agents/mock_bridge/`); the permanent contract double. Parity with the real Bridge is **terminal-outcome, not ledger-identical** (`docs/lessons-learned.md §A2`).

Later-release agents (Benefits, RFP, simulated ADK/LangGraph carriers) are Release 2+.
