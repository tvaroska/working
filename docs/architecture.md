# Architecture — A2A Document Bridge

> A single-read synthesis of the system design. The authoritative, per-topic spec lives in `wiki/` (start at `wiki/bridge.md`); this document consolidates it for engineers onboarding to the build. Where a section says "see `wiki/…`", that file is the source of truth.
>
> **Status:** Phase 1 (Address) built — local path end-to-end (480 tests green); GCP adapters + Terraform written and plan-tested, deployed GCP path not yet applied. Phases 2–4 not started. See `PLAN.md` / `docs/roadmap.md` for live status; this doc describes the settled design. **Last updated:** 2026-08-15.
>
> **Stack (ADR-0001):** Python 3.12+ / Google ADK / FastAPI / Pydantic (core + agents) · React + TypeScript + Vite (three surfaces + A2UI renderer) · Cloud SQL for PostgreSQL · Terraform · pytest + Playwright · uv + pnpm. Fulfillment-graph durability uses runtime session persistence. See `docs/decisions/adr-0001-stack.md`. *(ADK caveat: as of Phase 1 the agent loop is hand-rolled and ADK-ready, not hosted under ADK — see ADR-0001 status note and `docs/tech-debt.md` §1.)*

---

## 1. What it is

The Bridge **manages the process of collecting documents from the outside world** so a servicer's internal agent never touches it — it asks once and receives documentation already gathered, chased, normalized, and ready to act on.

The durable value is **mediation**, not extraction. Extraction (PDF → JSON) is delegated to dedicated services (Gemini, Document AI) behind a swappable seam; the Bridge owns the multi-turn, multi-party, multi-format relationship end to end.

**Two audiences:** (1) teams evaluating the **Gemini Enterprise Agent Platform** — the Bridge is the flagship end-to-end showcase; (2) servicers who could adopt it as a managed mediation product.

**Core vs. demos:** the **Bridge core** is an independent, reusable project. Each demo (Address, Benefits, RFP) is a self-contained implementation — skills + a thin driver — that consumes the core **without changing it**. That separation is the reusability claim. See `wiki/bridge.md`, `wiki/bridge-demo-suite.md`.

---

## 2. Design principles

1. **Mediation over extraction.** Extraction lives behind a seam; the mediation around it never moves when the engine is swapped.
2. **Sense A vs Sense B — the mediator boundary.** The Bridge evaluates *one artifact against declared rules* (sense A: legible? right type? unexpired?). The **agent** decides *requirements, completeness of a set, or acceptance of a deal* (sense B) and holds final authority. The Bridge best-efforts an **advisory** assessment of set-completeness — interpreting the skill's prose satisfaction description over its classified ledger to propose what's outstanding and chase it — but never *enforces* done; the app must always be ready to decide. See `wiki/bridge-disposition.md`.
3. **No workflow DSL.** `pattern` is a **selector over a closed set of built-in flows** the Bridge owns in code. Industries differ in *which documents* and *what policy*, not in *flow*. A new industry is new **skills**, not new code. See `wiki/bridge-patterns.md`.
4. **Everything behind a seam.** Every managed-service boundary has a local adapter (fast dev/test) and a GCP adapter (deployed), built together and verified by one shared test suite. See `wiki/bridge-seams.md`.
5. **Agent-first.** Each phase builds its processing agent (the sense-B counterparty) before the Bridge code, against a mock Bridge that persists as the permanent test double. See `wiki/bridge-implementation-plan.md`.
6. **Solicited/pull spine.** The servicer always asks first; the Bridge mints the exchange context at request time. Cold, unsolicited push is a deferred edge.

---

## 3. Aggregate model (the data spine)

The unit of work is an **exchange** — a durable, multi-turn interaction with a party about a set of documents. See `wiki/bridge-aggregate-model.md`.

| Concept | Realized as | Owner |
|---|---|---|
| **Party** | a stable counterparty reference | Backend (not a Bridge aggregate) |
| **Exchange** | the A2A context (1:1, no separate ID) | Bridge — groups the tasks |
| **Requirement item** | one item in a Collect exchange | Agent (what) + Bridge (state) |
| **Task / Artifact** | one runtime session, one per task | Bridge |

**Invariants:** one task = one runtime session (keyed 1:1); one turn = one runtime invocation; each task owns isolated, resumable state; interrupt/resume is recovered from the **persisted session** (crash-safe multi-day HITL). The Exchange may start as a *view* over its tasks and earns a standalone record only when exchange-only state appears (Requirements artifact, program membership, reopen). Address stays a view (a classified ledger derivable from tasks).

### Long-running collection (days → weeks)

A real collection is human-paced — a party takes days or **weeks** to respond. Over that horizon the exchange is **not a running process**: it is a **durable A2A task with no built-in TTL** that mostly sits idle and is woken only by a party turn, a clock alarm, or an HITL resume. The mediation runs *on wake*, at zero compute in between. This is a primary reason to speak canonical A2A (ADR-0007): A2A models a task as a long-lived, resumable, independently-addressable resource. See `wiki/bridge-long-running.md`.

- **What must survive weeks + restarts** → the durable substrate: persisted `SessionService` (Vertex), `GcsArtifactService`, Cloud Tasks timers + a persisted SLA read-model. Committed in design; the durable homes land **Phase 3**, so today's local path tolerates "days, if nobody restarts," not "weeks."
- **Chasing over time** → the clock, not a held connection — the proactive-follow-up ladder fires a scheduled callback days apart (§8).
- **Learning of progress without a held connection** → `tasks/get` (poll), `tasks/resubscribe` (re-attach after disconnect), and push-notification webhooks (*Phase 4*; a pull-forward candidate for weeks-scale).
- **Servicer loop is event-driven, not process-bound** → `next_requirements` is a pure function of `(status, ledger)`; the loop's continuation lives in the durable exchange, woken by push/`tasks/get`, not a process that stays alive for weeks.
- **Undecided:** exchange lifetime/expiry (no TTL today), context-token validity over weeks, artifact retention. See `wiki/bridge-open-questions.md`.

---

## 4. Two edges (how parties connect)

The Bridge is **not a pure A2A server** — it meets parties at their level of digital maturity. See `wiki/bridge-edges.md`.

- **A2A edge (agents)** — task lifecycle, artifact versioning, event streaming, and a **dynamic Agent Card** at the well-known discovery location, populated from installed skills (so a live skill-add regenerates it, no redeploy). Phase 1 is **inbound-only**: a party responds carrying the exchange context token — no A2A client, no outbound. The edge speaks **canonical A2A** on the `a2a-sdk` (target; today a bespoke REST mapping — ADR-0007, `tech-debt` §9). See `wiki/bridge-a2a-edge.md`.
- **A2UI edge (humans)** — the Bridge emits declarative **A2UI** (what to show, what it gets back) and ingests a structured response. **Content and protocol, not pixels** — any host renders it; the reference renderer is demo furniture. Powers Path B, HITL review, party status, dashboards. See `wiki/bridge-a2ui-edge.md`.

Both edges enter through the same trust boundary (Agent Gateway) and the Bridge stays source of truth for exchange identity on both.

### Dual-path fulfillment

A party responds — indistinguishably to the requester — in one of two modes, decided only by *what kind of response arrives*. See `wiki/bridge-dual-path.md`.

| Mode | Party | Arrives | Bridge does |
|---|---|---|---|
| **Path A — structured** | has an agent | structured data on the A2A edge | **validate-only** (schema + disposition, no extraction) |
| **Path B — portal** | no agent | PDF / text / form via A2UI | **extract → normalize → disposition → HITL if flagged** |
| **Operator-fulfilled** | internal human | upload on party's behalf | as Path B, lower priority |

**Migration payoff:** a Path-B party that later builds an agent flips to Path A by **config only** — history preserved, servicer code unchanged (full migration is Phase 4).

**Framework interoperability.** A2A is framework-agnostic: a Path-A counterparty can be built in *any* agent framework and the Bridge never notices. The Benefits demo (Phase 2) proves this explicitly — two simulated carrier agents, one **Google ADK** and one **LangGraph**, both responding over A2A, with the LangGraph carrier driving the multi-turn negotiate/revise loop. The simulated agents are demo furniture, not part of the core. See `wiki/bridge-benefits-demo.md`.

---

## 5. Exchange patterns (the closed flow set)

Each demo runs one of a few built-in patterns; the process skill *selects* one. See `wiki/bridge-patterns.md`.

| Pattern | Flow | Example |
|---|---|---|
| **Request (pull)** | ask → supply → normalize → deliver | Address, ID-only branch |
| **Negotiate** | request → respond → revise loop → finalize | Benefits (Phase 2) |
| **Deliver** | send → format per channel → confirm | outbound (deferred) |
| **Collect** | set requirements → assemble a document *set*, loop until the agent judges complete | Address (bounded) · RFP (emergent) |
| **Extract** | party pushes → normalize → deliver | deferred cold-inbound |

### Collect — the reusability keystone

Collect runs as a **multi-turn conversation, not a workflow**. Every judgment is a *turn*. See `wiki/bridge-collect.md`.

```
Bridge: collect → parse/classify → disposition (per doc) → update ledger
Bridge → agent:  "here's what I have and what I parsed"   (Collection status)
agent  → Bridge: a flat requirements list + done?          (Requirements)
Bridge: chase the outstanding items ──┐  repeat until agent says done ──┘
```

- **Requirements** (owned by the **agent**) — a flat, fixed-schema to-do list; status vocabulary `required | optional | satisfied | waived`. **Data, not rules** — conditionals are the agent adding an item next turn, never a Bridge-evaluated trigger.
- **Collection status** (owned by the **Bridge**) — the classified ledger: per-doc state, rejections, outstanding.
- **Address and RFP are the *same* loop** — the only difference is how clever the agent's per-turn reply is (fixed policy vs. mutating policy). **Same Bridge code, zero extensibility surface.** `Request` is a one-turn Collect.

---

## 6. Fulfillment graph + disposition (the Path-B pipeline)

The graph the Bridge runs when a human supplies an upload. See `wiki/bridge-fulfillment-graph.md`.

```
START → receive → extract_with_quality_gate ─┬─ pass → confidence_gate ─┬─ auto_approve → finalize
                          │                   │                         └─ hitl_review → finalize
                          │                   └─ escalated → escalate
                          └── resubmission loop (≤ 3 attempts) ──┘
```

- **Quality gate** — below resubmit threshold / unreadable → request resubmission (capped at 3, re-enters as a new artifact version on the same task).
- **Confidence gate** — at/above auto-approve threshold with no flags → auto-approve; else **HITL**.
- **HITL suspends with zero compute** for minutes/days, resumes on a webhook, recovered from the persisted session.
- **Path A skips this graph** (validate-only).

**Disposition** decides whether a submission is acceptable and routes it (accept / clarify / reject / request-more). Phase 1 = simple quality + confidence gates **plus doctype classification** against the candidate label space and **issuer canonicalization** (`PowerCo`/`Power Co.` → `power-co`). The target is a four-signal model (legibility / type match / confidence / completeness) — deferred post-golden. See `wiki/bridge-disposition.md`.

---

## 7. Skills — demos as configuration

Skills are authored in the open **[Agent Skills format](https://agentskills.io)** (Anthropic-originated standard): each skill is a folder with a `SKILL.md` (YAML frontmatter `name` + `description`, Markdown body) optionally bundling `assets/`, `references/`, `scripts/`. The Bridge is a skills host. Two Bridge *kinds*, distinguished by `metadata.bridge-kind`. See `wiki/bridge-skills.md`.

```
document-type skill   → parameterizes a TASK   (metadata.bridge-kind: doctype)
    SKILL.md body = extraction prompt · assets/schema.json (Gemini constrained JSON)
    · optional Document AI processor binding · assets/validation.yaml · disposition signals

process skill         → parameterizes an EXCHANGE (a lean catalog; metadata.bridge-kind: process)
    metadata.bridge-pattern (selector) · assets/policy.yaml (SLA, retries, thresholds)
    · metadata.bridge-candidate-doctypes (label space)   — NO requirement slots, NO formal completeness rules
                                                          (a prose satisfaction description is allowed)
```

Structured config lives in `metadata` (string→string) + bundled `assets/`; `name`/`description` are the discovery surface. The completeness *decision* — *what's needed* and *is it done* — is the **agent's**, asserted at runtime; the skill may carry a **prose satisfaction description** (never a formal rule) the Bridge best-efforts an advisory assessment from.

**Progressive disclosure *is* the Agent Card.** The Agent Skills model loads only `name` + `description` at startup and the full skill on activation — which is exactly how the Bridge's **Agent Card** is generated from installed skills. Upload a skill folder → the card regenerates → the new capability is live. Install several demos' skills → **one card advertises them all**. This **live skill-add** is the concrete proof of the reusability thesis (and a required demo beat). Skills are validated with `skills-ref validate` in CI.

---

## 8. GCP substrate

The half that makes this a platform showcase, not a local prototype. See `wiki/bridge-gcp-substrate.md`.

### Managed-service seams (local adapter ↔ GCP adapter)

| Seam | Local | GCP |
|---|---|---|
| Sessions | embedded store | Agent Platform Sessions |
| Task store | embedded store | managed relational store → platform managed task store (future) |
| Exchange store | embedded store | managed relational store (Bridge-owned aggregate) |
| Skill registry | local packages | GCP Skill Registry |
| Memory bank | local event log | Agent Platform Memory Bank (Phase 4) |
| Scheduler/Timer | in-process **virtual clock** | Cloud Tasks |
| A2A client (outbound) | fake transport | authenticated transport + Agent Identity (Phase 4) |
| Extraction | fixture (deterministic) | **Gemini** or **Document AI** (engine-selectable) |

A config knob selects a global seam mode with per-seam overrides; the **same test suite runs against both** adapters (seam parity). Extraction differs on axis — real engines deploy either way, selected by config + per-doctype capability. Document AI is *not* a free swap: Gemini takes an arbitrary schema/prompt; Document AI needs a processor bound per doctype.

### Two-zone network model (the trust boundary)

The Bridge is a network-boundary mediator (DMZ). Isolation is enforced **at the network layer only**. See `wiki/bridge-zones.md`.

```
External zone (untrusted) ─ingress→ Bridge (DMZ) ←Agent Identity→ Internal zone (trusted)
 provider/party agents + portals    Agent Runtime                  backend / servicer agents
```

- **Agent Gateway** = external ingress: routing, access control, per-party auth scoping (a party can address only its own leg's context).
- **Agent Identity** = workload identity (mutual TLS) on the Bridge↔backend link and Bridge→managed-service calls.
- **Carrier-vs-carrier confidentiality is addressing, not a wall** — a carrier can't address another leg's context.
- **No per-customer logical multi-tenancy** — one deployment = one trust domain (cross-org scoping deferred).
- The Gateway is **deployment-only, not a seam** (no local equivalent); the deploy path provides validated deploy-spec builders.

### Proactive follow-up (the new runtime pillar)

"Remind them" has no inbound event — it needs a clock. Core from Phase 1; the concrete proof of "mediation, not extraction." See `wiki/bridge-proactive.md`.

- Durable **Scheduler/Timer seam** — in-process virtual clock (local) / **Cloud Tasks** (GCP); idempotent, crash-safe.
- **SLA/policy engine** — cadence, deadlines, max nudges, escalation ladder — read from the process-skill policy.
- **Egress via the read-model** — a stalled request stamps `overdue`/`escalated` events on the dashboard; no outbound needed yet.

---

## 9. Frontend (three surfaces, one per actor)

Make the mediation legible and validate A2UI early; A2UI hosts (content-not-pixels), split across the trust boundary. See `wiki/bridge-frontend.md`.

1. **Processing-Agent Console** (internal) — the agent's mind: ledger handed, reasoning, satisfaction check, requirements list. Where **sense B** is watchable.
2. **Servicer Ops Dashboard** (internal) — exchanges in flight, classified ledger filling live, disposition outcomes, HITL/escalation queues.
3. **Provider Portal** (external) — the only surface across the boundary; upload + disposition + outstanding.

Presentation modes: **Split-Screen Theater** (default), **Timeline**, **Architecture X-Ray** (Phase 4). A **time-warp** presenter control over the virtual clock shipped in Sprint 1.

---

## 10. Build sequence

4 phases × 2 sprints. Each phase: Sprint A proves behavior locally; Sprint B adds GCP adapters + Terraform and deploys. See `wiki/bridge-implementation-plan.md`, `wiki/bridge-stages.md`, `PLAN.md`, `docs/roadmap.md`.

| Phase | Demo | Proves |
|---|---|---|
| 1 — Address *(minimal, committed)* | pull spine + bounded Collect | mediation on the platform, one demo, end to end |
| 2 — Benefits *(aspirational)* | Negotiate arc | "one comparable view" (depth) |
| 3 — RFP *(aspirational, headline)* | emergent Collect, added live | industry-agnostic reuse = skills, not infra (breadth) |
| 4 — Maturity *(aspirational)* | core hardening | four-signal disposition, party memory, Document AI swap, multi-tenancy, security |

**Scope note:** `wiki/bridge-open-questions.md` is the authoritative minimal-vs-aspirational split. A minimal **live doctype-add** is pulled forward into Sprint 2 as the down-payment on the Phase-3 headline (see `PLAN.md` S2-core-1/2, `wiki/bridge-address-demo.md`).

---

## 11. Component map

```
                          ┌──────────────────── Bridge core ────────────────────┐
 External zone            │                                                      │   Internal zone
 ┌───────────────┐        │   ┌── A2A edge (agents) ──┐   ┌ Aggregate model ┐    │   ┌──────────────┐
 │ party agents  │──A2A──▶│   │  Agent Card (dynamic) │   │ exchange/task/  │    │   │ servicer     │
 │ + portals     │  A2UI  │──▶│  A2UI edge (humans)   │──▶│ session/party   │◀───┼──▶│ agent        │
 └───────────────┘        │   └───────────────────────┘   └────────┬────────┘    │   └──────────────┘
      │  Agent Gateway     │             │                          │             │      Agent Identity
      │  (ingress)         │      dual-path fulfillment             │             │
      ▼                    │   ┌─────────▼──────────┐      ┌────────▼────────┐    │
                           │   │ fulfillment graph  │─────▶│ disposition     │    │
                           │   │ (Path B extract)   │      │ (sense A gates) │    │
                           │   └─────────┬──────────┘      └────────┬────────┘    │
                           │             │                          │             │
                           │    ┌────────▼─────────┐       ┌────────▼────────┐    │
                           │    │ extraction seam  │       │ classified      │    │
                           │    │ fixture/Gemini/  │       │ ledger          │    │
                           │    │ Document AI      │       └─────────────────┘    │
                           │    └──────────────────┘                             │
                           │   seams: Sessions · Task/Exchange store · Skill      │
                           │   registry · Scheduler (Cloud Tasks) · Memory Bank   │
                           │   proactive follow-up (virtual clock / Cloud Tasks)  │
                           └──────────────────────────────────────────────────────┘
```

## Related
- Spec index: `wiki/bridge.md` · Scope: `wiki/bridge-open-questions.md` · Plan: `PLAN.md` · Roadmap: `docs/roadmap.md`
