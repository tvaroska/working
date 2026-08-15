# ADR-0006 — ADK-native Bridge runtime (LlmAgent + tools, artifacts, long-running HITL)

- **Status:** Accepted
- **Date:** 2026-08-14
- **Resolves:** `docs/tech-debt.md` §1 ("ADK-ready, not ADK-hosted"); supersedes the Phase-1 implementation-status notes in `docs/decisions/adr-0001-stack.md`; **amends `docs/decisions/adr-0004-signal-provider-interface.md`** (the Bridge is no longer completeness-blind — it best-efforts an assessment — though the completeness *decision* stays the app's; see "Completeness" below)
- **Context:** `wiki/bridge-adk.md` (principle), `wiki/bridge-disposition.md`, `wiki/bridge-collect.md`, ADR-0001, ADR-0004

## Context

ADR-0001 chose Google ADK as the agent framework, but its implementation-status note (2026-08-10) records the honest gap: ADK was a *declared dependency*, not the runtime. The Collect loop was a hand-rolled `async` loop; HITL was app-owned task-parking (`TaskStatus.INPUT_REQUIRED` + an A2A resume endpoint); no ADK agent, tool, or artifact was actually executed. The "ADK showcase" was aspirational.

This ADR settles **how** the Bridge runs on real ADK. Two things forced the shape:

1. **The Bridge is a platform showcase.** Using ADK natively *is* the demonstration, so bespoke wrappers around ADK are a liability, not a convenience.
2. **Disposition must handle off-script intents.** A purely deterministic verdict-mapper only understands "candidate document → accept/reject/review." It cannot handle a **deletion/erasure request**, a **wrong or unrelated file**, or an out-of-scope message. Those require reasoning.

A prior spike built the disposition side as a deterministic ADK `Workflow` graph with `RequestInput` HITL (proven working on adk 2.7.0). It was rejected on point (2): a graph routes fixed branches, not open-ended intent.

## Decision

The Bridge runs on ADK using the most standard constructs available, per the **"as standard as possible"** principle (`wiki/bridge-adk.md`):

| Concern | Decision |
|---|---|
| **Bridge root agent** | An **`LlmAgent`** (`"document_bridge"`) that routes intent and handles the messy edges — not a deterministic graph. |
| **Extraction** | Its own **subagent** (`extraction_agent`), attached to the root via **`AgentTool`** — the main agent *calls* it and keeps control. Given one artifact + candidate doctypes it returns `{classification, key_fields, signals}`; it is the only thing that touches bytes/OCR. The engine **seam** (Gemini / Document AI, config-chosen) stays behind it, unchanged. |
| **KYC decision** | Stays a **pure function**, exposed to the agent as an **authoritative tool** `run_disposition_gate` — but it now takes the **already-extracted** result and only maps the verdict (accept/reject/review). The LLM must call it and relay its verdict; it **cannot mint an acceptance**. This is the one inversion we keep — a compliance guardrail, in standard agent+tool shape. |
| **Completeness ("what's still needed")** | **Best-effort in the Bridge; decided by the app.** The skill carries the satisfaction rule as a **natural-language description** ("one gov-ID **or** two bills from different companies") — **no deterministic rules, no final word on enforcement**. The Bridge's `LlmAgent` interprets it **best-effort**: it proposes what's still outstanding, chases the delta, and offers a "looks complete" assessment. But the **app must always be ready to make the completeness decision** and holds final authority (sense B) — the Bridge is *advisory* here. Only per-artifact disposition (sense A) is Bridge-authoritative. This keeps the app's completeness ownership (ADR-0004) and only *adds* Bridge best-effort assistance driven by the prose rule — no DSL, no rules engine, no Bridge enforcement. |
| **Human-in-the-loop** | A **`LongRunningFunctionTool`** (`request_human_review`); resume is an **id+name-matched `FunctionResponse`** fed back via `runner.run_async`. Replaces app-owned task-parking. |
| **Off-script intents** | Separate tools — `handle_deletion_request` (a real, auditable artifact erase), `reject_submission` (wrong/unrelated file). |
| **Documents** | First-class **ADK artifacts** (`ArtifactService`), referenced by filename; tools load bytes by reference via `ToolContext`. Artifact **versions model resubmissions** (attempt N = version N). Session-scoped (one case = one session). |
| **Document transfer over A2A** | Documents cross the wire **by reference** — A2A `FileWithUri`, **both directions**. Inbound: `InboundPart` gains a file **uri**; the edge fetches it and `save_artifact`s it (new version = resubmission) before the gate runs. Outbound: `LedgerEntry`/`CollectionStatus` gains an artifact **reference** (uri); the servicer's agent fetches accepted-document bytes **on demand** from a **scoped artifact-fetch endpoint** (per-party leg auth), served from `InMemoryArtifactService` locally / `Gcs` (signed URL) on deploy. Bytes never ride the A2A message. |
| **Runtime** | Stock **`Runner`** + **`InMemorySessionService`** + **`InMemoryArtifactService`** locally; **`Gcs`/Vertex** backends swap in on deploy (Phase 3) with no agent-code change. |
| **App topology** | The Bridge is **one shared, application-agnostic service**. Applications (Address, and future ones) are **separate ADK apps** that call it over **A2A**, each bringing its own Collect loop, satisfaction rule, and **skill** (candidate doctypes + policy). The Bridge is *not* a sub-agent of any app — the A2A wire is what lets one Bridge serve all. |

Consequently, the bespoke plumbing built earlier is **deleted**: the hand-rolled Collect loop is hosted as an `LlmAgent` (Phase 1, done), the custom `BaseAgent` and the `BridgeStoreSessionService` adapter are dropped, and HITL task-parking gives way to the long-running tool.

## Rationale

- **`LlmAgent` + authoritative tool** is the ordinary ADK pattern and resolves the determinism/flexibility tension: the model routes, the pure gate decides. Same split already used in Collect (LLM picks the next document, a code gate owns "satisfied").
- **`LongRunningFunctionTool` HITL** is Google's canonical human-in-loop sample; the resume contract (matching `FunctionResponse` id/name) is identical to the graph `RequestInput` path we spiked, so the mechanic is proven twice over.
- **Artifacts** are the platform's answer to binary documents: versioning gives resubmission history for free, deletion becomes a literal erase, and the `InMemory → Gcs` swap mirrors the session-service story.
- **Shared, generic Bridge over A2A** keeps industry-agnosticism in the [[bridge-skills|skills]] layer, consistent with ADR-0002 (thresholds in the skill) and `wiki/bridge-patterns.md` (closed pattern set, config not code forks).
- **Extraction as a subagent (`AgentTool`)** isolates the one interpretive step (bytes → structured fields, itself an LLM call under the Gemini engine) from the orchestration. The main agent's context stays about *intent and completeness*, not OCR; the engine seam is untouched. `AgentTool` (not `sub_agents`) because control always returns to the main agent to run the gate and decide — this is a *called capability*, not a conversational handoff.
- **Best-effort completeness in the Bridge, decision in the app** realizes the north star — "ask once, get documentation already gathered and chased" — without making the Bridge the enforcer. The Bridge holds the skill and the ledger, so it can *best-effort* "what's still needed" and chase it; the rule is a **prose description** the LlmAgent interprets, not encoded logic, so the no-DSL stance holds. But the **completeness decision stays the app's** (ADR-0004): the Bridge is advisory, has no deterministic rule and no final word, and the app must always be ready to decide. This *amends* ADR-0004 only by ending the Bridge's completeness-blindness — it does not move enforcement.

## Orchestration flow

One disposition turn inside the `document_bridge` agent:

1. **Receive** — an inbound `FileWithUri` is fetched and `save_artifact`'d (resubmission = next version).
2. **Interpret skill** — the agent reads the skill's candidate doctypes + policy + satisfaction rule, and the current ledger.
3. **Extract** — the agent calls `extraction_agent` (`AgentTool`) with the artifact + candidate doctypes → `{classification, key_fields, signals}`.
4. **Decide** — the agent calls `run_disposition_gate` (pure, authoritative) with the extracted result → accept / reject / review. Off-script inputs route to `handle_deletion_request` / `reject_submission` instead; review routes through `request_human_review` (long-running).
5. **What's still needed (best-effort)** — the agent updates the ledger and, interpreting the skill's prose satisfaction rule, *proposes* the outstanding requirement and chases it. This is advisory: the **app makes the completeness decision** on the returned status; the Bridge never enforces "done."
6. **Return** — `ExchangeTurn{CollectionStatus: ledger + artifact references}`.

This splits today's all-in-one `evaluate()`: the **extract** half (graph + classify + signals) moves into `extraction_agent`; the **decide** half (verdict mapping) stays the pure gate. Parity tests continue to pin the decide half against `DispositionService`.

## Consequences / risks

- **LLM non-determinism in routing.** The agent's *routing* is probabilistic, but the *compliance verdict* is not — it comes from the pure gate tool, which the LLM cannot overrule. Offline tests drive the agent with a scripted model double (as in Phase 1) and assert terminal-disposition parity with the deterministic `DispositionService` on genuine-candidate scenarios; deletion/wrong-file are additive.
- **Durability on the local path.** `InMemory` session/artifact services lose in-flight HITL suspensions on a bridge restart — acceptable now; real durability arrives with the GCS/Vertex backends (Phase 3). This is the deliberate answer to "stock InMemory now" rather than carrying a bespoke durable adapter.
- **Cost/latency.** An LLM turn per disposition adds latency and token cost a pure function did not. Justified by the off-script-intent capability; the gate tool keeps the expensive path off the deterministic core.
- **`ResumabilityConfig` is `[EXPERIMENTAL]`** in adk 2.7.0 — noted where long-running pause/resume relies on it.
- **The extraction subagent adds a hop.** An `AgentTool` call is an extra LLM turn versus an inline function. Accepted: extraction was always an engine (Gemini) call, and isolating it keeps the main agent's reasoning about intent/completeness uncluttered. Offline tests drive both agents with scripted model doubles.
- **Completeness is Bridge best-effort, app-decided.** The Bridge stops being completeness-blind and now proposes/chases the outstanding set from the skill's prose rule — but the app still makes the call, so the app-side satisfaction decision is *not* retired. Risk: the Bridge's best-effort assessment must never read as authoritative — the returned status marks it advisory, and the app is required to decide, never to rubber-stamp. Address's "gov-ID **or** two distinct bills" is the proof that a useful best-effort assessment is expressible from a prose skill description; an under-specified skill simply yields a weaker proposal, never a false "done."
- **By-reference transfer adds a fetch endpoint + a second round-trip.** The servicer's agent gets the ledger first, then pulls accepted bytes on demand — two hops instead of one inline blob. The trade is deliberate: the A2A message stays small and byte-free, retrieval is authorized per-fetch on the existing per-party leg boundary, and the same code path serves `InMemory` bytes locally and a GCS **signed URL** on deploy. The endpoint must scope every fetch to the requesting leg — a uri is not a capability on its own.

## Send-back contract — extended, not broken

The outbound shape the app already consumes — `ExchangeTurn{status: CollectionStatus}` with a `LedgerEntry` tuple, `_status_for(disposition)` mapping — **stays**. The redesign is internal (LlmAgent + tools + artifacts) and does not change *how* the app reads a result. The one **additive** change: `LedgerEntry`/`CollectionStatus` and inbound `InboundPart` each gain an **artifact reference** (a `FileWithUri` handle) so documents can cross the wire by reference in both directions. Existing metadata-only consumers keep working; the reference is extra, not a replacement. The app still never sees ADK events — only the A2A task status and the ledger projection.

## Alternatives considered

- **Deterministic `Workflow` graph** (spiked, working). Rejected: cannot handle deletion/wrong-file/out-of-scope intents — it routes fixed branches, not reasoning.
- **`LlmAgent` that owns accept/reject itself.** Rejected: a model improvising KYC acceptance is not auditable. The gate stays authoritative.
- **Bespoke `BridgeStoreSessionService` adapter** to back ADK with the existing Sessions seam. Rejected as non-standard; `InMemory` now, stock GCS/Vertex later.
- **App-owned task-parking for HITL** (the Phase-1 status quo). Superseded by the long-running tool.
- **Extraction as a plain `FunctionTool` over the seam** (no agent). Reasonable, and still an option if the subagent earns its keep nowhere but Gemini. Chosen against for now because extraction is genuinely interpretive (doctype hypotheses, multi-page/multi-currency reconciliation) and a subagent both models that honestly and keeps the main agent's context clean. The engine seam lives behind either shape, so this is reversible.
- **Extraction as a `sub_agents` transfer** rather than `AgentTool`. Rejected: control must return to the main agent to run the gate and decide completeness; a transfer hands off the conversation, which is the wrong relationship.
- **Bridge as an in-process sub-agent / `AgentTool` of each app.** Rejected: it would fork a Bridge per application and drop the A2A wire — the opposite of "same Bridge for all applications."

## Note — the Collect side

The client-side Collect loop (Address app) already runs as an `LlmAgent` on ADK (Phase 1): the LLM chooses which proof to request; a deterministic `is_satisfied` code gate owns "done." This ADR extends the same LLM-drives / code-gates split to the Bridge's disposition side. See `wiki/bridge-collect.md`, `wiki/bridge-adk.md`.

## Note — target version & verified spikes (folded in from the ADK-showcase mandate, 2026-08-14)

- **Target runtime: `google-adk >= 2.7.0, < 3`** (pinned in `bridge/` + `agents/` pyproject; was
  `>=1.0`, installed 2.6.2 before the bump).
- **`ResumabilityConfig` is `[EXPERIMENTAL]`** in 2.7.0 — long-running pause/resume relies on it (also
  noted under Consequences).
- **Two crux ADK-2.7.0 APIs were spiked and verified** before committing to this design: (1) HITL
  pause/resume via a long-running function call + an id/name-matched `FunctionResponse` fed back
  through `runner.run_async`; (2) an `LlmAgent` driving a tool loop under a scripted `BaseLlm` (the
  offline model double that makes CI deterministic).
- **Hard invariant:** the sense-B satisfaction / KYC verdict stays a deterministic code gate the model
  cannot override, and mock↔real parity is preserved (terminal-outcome, not ledger-identical). See
  `docs/lessons-learned.md §A2, §A3`.

This supersedes `docs/tech-debt.md §1` ("ADK is a declared dependency, not the runtime"), which is now
marked stale.
