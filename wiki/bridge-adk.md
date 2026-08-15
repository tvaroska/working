---
type: concept
up: "[[bridge]]"
related:
  - "[[bridge-patterns]]"
  - "[[bridge-disposition]]"
  - "[[bridge-collect]]"
  - "[[bridge-gcp-substrate]]"
tags: [bridge, adk]
status: review
updated: 2026-08-14
---

# Running on Google ADK — as standard as possible

> The Bridge is the flagship showcase of the **Gemini Enterprise Agent Platform**. So it runs on **Google ADK**, and it uses ADK **the standard way**: every runtime concern maps to a native ADK construct, and we hand-roll nothing the platform already provides. Using the platform natively *is* the demonstration.

## The principle

**Prefer the ADK-native construct over bespoke plumbing — every time.** When a runtime concern (an agent, a pause for a human, a document, a durable session) has a first-class ADK answer, we use that answer as-is. A wrapper we write ourselves both *hides* the platform we are showcasing and becomes ours to maintain. So the default is always the stock construct; a custom layer needs a specific, recorded justification.

Concretely, each concern lands on its native construct:

| Concern | ADK-native construct | Not this |
|---|---|---|
| An agent that reasons | `LlmAgent` | a hand-rolled `async` loop |
| Orchestration / turns | stock `Runner` | a service that hides a runner |
| A capability the agent invokes | a **tool** (`FunctionTool`) | inline branching in app code |
| A sub-capability that reasons | a subagent as **`AgentTool`** | inlining its reasoning into the parent |
| Pause for a human | `LongRunningFunctionTool` + id-matched `FunctionResponse` | app-owned task-parking |
| A document (bytes) | **artifact** (`ArtifactService`, versioned) | an inline payload on session state |
| Durable session / state | `SessionService` | a bespoke store adapter |
| Local ↔ deployed | swap the service backend (`InMemory…` ↔ `Gcs…` / Vertex) | a custom durability layer |

The reward for staying standard: the same agent code runs locally and on the Agent Runtime by swapping service backends, and a reader who knows ADK already knows how the Bridge works.

## The one inversion we keep — and why it's still standard

The Bridge disposes documents for **KYC/compliance**, so the accept/reject of a genuine candidate document must be **deterministic and auditable** — never a model's improvised call. But real intake is messy: a **deletion request**, a **wrong/unrelated file**, an out-of-scope message. A purely deterministic pipeline can't route those; reasoning can.

The standard ADK shape resolves the tension cleanly:

- The agent is an **`LlmAgent`** — it *routes intent* and handles the messy edges.
- The compliance decision stays a **pure function**, exposed to the agent as an **authoritative tool** (`run_disposition_gate`). The LLM must call it and relay its verdict; **it cannot mint an acceptance.**

This is still just "an agent with a tool" — the most ordinary ADK pattern there is. The LLM sits *in front of* the deterministic gate, not in place of it. Same guardrail as the [[bridge-collect|Collect]] loop, where the LLM chooses which document to request but a code gate owns "satisfied."

## The main agent orchestrates; extraction is a subagent

The `document_bridge` agent's job is *intent and completeness*, not OCR. So the one interpretive step — turning a document's bytes into structured fields — is peeled into its own **`extraction_agent`**, attached as an **`AgentTool`**. The main agent calls it, gets `{classification, key_fields, signals}` back, and keeps control to run the gate and decide.

A turn reads as: **receive** the artifact → **interpret the skill** (candidate doctypes, policy, satisfaction rule) → **extract** (subagent) → **decide** (the authoritative gate) → work out **what's still needed** → **return** the ledger. Control returns to the main agent at every step — that's why extraction is an `AgentTool`, not a `sub_agents` handoff.

This also settles *how completeness works* — **best-effort in the Bridge, decided by the app.** The Bridge holds the skill **and** the ledger, so it can *propose* "is this collection done?" and chase the delta: the satisfaction rule ("one gov-ID **or** two bills from different companies") lives in the skill as a **natural-language description** — no deterministic rules, no rules engine — which the LlmAgent *interprets* best-effort, extending "config not code" ([[bridge-patterns|thresholds in the skill]]) while keeping the anti-DSL stance intact. But the Bridge holds **no final word on enforcement**: the assessment is advisory, and the **app must always be ready to make the completeness decision** ([[bridge-collect|Collect]]). The app's loop keeps that decision and gains a Bridge that pre-chases rather than sitting completeness-blind.

## Off-script intents — the flexibility we can't script

A document exchange is never just "valid doc → accept." Real parties send a **deletion/erasure request**, a **wrong or unrelated file**, a question, an out-of-scope message — and intents we simply haven't thought of yet. **We can't enumerate that set up front**, and that is exactly why the root is an **`LlmAgent`** rather than a deterministic graph: a graph must name every branch at build time; a reasoning agent **routes intents it was never pre-wired for**, falling through to the right tool (`handle_deletion_request`, `reject_submission`) or escalating for review. Crucially, the flexibility lives only on the *edges* — the KYC accept/reject stays behind the deterministic gate the LLM can't overrule — so absorbing the unknown never costs us auditability at the core. A new intent discovered later is **a new tool plus a line of instruction, not a re-drawn flowchart.**

## Human review is the platform's pause, not ours

When a submission needs a person — low confidence, a flagged field, an escalation — the Bridge pauses on the platform's own construct: a **`LongRunningFunctionTool`** (`request_human_review`), resumed by an id-matched `FunctionResponse`. We deliberately **do not reimplement** this — no app-owned task-parking, no custom suspend/resume table, no bespoke `INPUT_REQUIRED` bookkeeping (that plumbing was written once and then deleted; see *What this replaced*). Leaning on the native pause **is** the point: human-in-the-loop is a headline capability of the Agent Runtime, so showing the Bridge suspend and resume *through the platform* is itself part of the demonstration. The pause's durability rides the `SessionService` backend — InMemory locally, Vertex on deploy — the same swap as every other concern, so we showcase the platform rather than out-build it.

## Documents cross the wire by reference

An ADK **artifact** lives inside the Bridge — versioned, session-scoped, addressed by filename. An A2A **`FilePart`** is how a document travels between agents. The [[bridge-edges|edge]] is the one place those two worlds meet, and it keeps them apart the standard way: **bytes never ride the A2A message.**

- **Inbound.** A submission carries a `FileWithUri`; the edge fetches it and `save_artifact`s it — a resubmission is just the next artifact **version**, so history is free.
- **Outbound.** The deliverable is the **classified ledger plus artifact references** — meaning first, bytes on demand. The servicer's agent reads the `CollectionStatus`, then pulls accepted-document bytes from a **scoped fetch endpoint** (authorized on the same per-party leg boundary), served from `InMemory` locally and a GCS **signed URL** on deploy.

This keeps the A2A message small and the trust boundary honest: a reference is not a capability — every fetch is scoped to the leg that asked. The app-facing contract (`ExchangeTurn`/`CollectionStatus`) is unchanged in shape; the artifact reference is an *additive* handle on the ledger it already reads. The full lifecycle — versioning, deletion, the two meanings of "artifact" — is [[bridge-artifacts|its own page]].

## What this replaced

Earlier framing treated ADK as *aspirational* — a hand-rolled Collect loop, app-owned task-parking for HITL, a custom session-store adapter. Making the showcase real meant **deleting** that bespoke plumbing in favour of the native constructs above, keeping only the one inversion (deterministic gate as a tool) that compliance genuinely requires.

## Read next
- [[bridge-disposition|disposition]] — the KYC decision the gate tool wraps
- [[bridge-collect|Collect]] — the same LLM-drives / code-gates split on the client side
- [[bridge-artifacts|artifacts]] — documents as versioned ADK artifacts, and how they cross the wire
- [[bridge-gcp-substrate|GCP substrate]] — the service backends that swap in on deploy

## Related
- [[bridge-patterns|exchange patterns]], [[bridge|the Bridge]]
- **Decision record:** `docs/decisions/adr-0006-adk-native-runtime.md`
