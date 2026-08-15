---
type: atom
related:
  - "[[bridge-demo-suite]]"
  - "[[bridge-stages]]"
tags: [bridge]
status: review
updated: 2026-08-06
---

# Scope — Minimal vs Aspirational

> This note is the single source of truth for what the **minimal showcase** commits to versus what's **aspirational**.

Elsewhere, *[Minimal]* marks the committed core and *[Aspirational]* marks the vision beyond it.

**Minimal showcase — the committed core.** The smallest build that proves the thesis (mediation on the Agent Platform, one demo, end to end on the deployed path):

- **Pull spine** — request → fulfill → normalize → deliver; Address at 1 party
- **Bounded Collect** — a fixed **alternative-satisfaction** rule ({gov ID} | {2 bills, distinct issuers}) over a candidate-doctype **label space**; the Bridge classifies each arriving doc, dispositions it, and maintains a **classified ledger** of what's accepted, then chases the delta — while the **agent owns the completeness *decision*** (sense B) and the Bridge best-efforts an advisory assessment of it (from the skill's prose satisfaction description over that ledger). **No Bridge-owned typed slots.** The static, known-up-front slice of [[bridge-collect|Collect]]; Phase 3 generalizes it to emergent/agent-mutated requirements.
- **Two [[bridge-edges|edges]]** — A2A inbound (structured response) + A2UI human portal
- **[[bridge-dual-path|Dual-path fulfillment]]** — Path A validate-only, Path B extract
- **[[bridge-fulfillment-graph|Extraction graph]]** — Gemini, quality + confidence gates, suspend-and-resume HITL
- **Simple-gate [[bridge-disposition|disposition]]** — resubmit / auto-approve thresholds, capped retries
- **[[bridge-proactive|Proactive follow-up]]** — Scheduler seam + SLA from the process skill (virtual clock)
- **[[bridge-aggregate-model|Aggregate invariants]]** — task = session, Exchange = the A2A context, a stable counterparty reference
- **[[bridge-seams|Seams]]** with local + GCP adapters (Sessions, Task store, Exchange store, Skill registry, Scheduler)
- **[[bridge-seams|Extraction seam]]** — one extraction service with fixture + **Gemini** adapters (extraction delegated to dedicated services behind one swappable interface; the second engine proves the swap in a later phase)
- **[[bridge-zones|Two-zone network model]]** — Agent Gateway + Agent Identity on deploy
- **[[bridge-skills|Skills]]** — doctype + process; policy lives in the skill, and `pattern` is a **selector over a closed set of built-in flows** ([[bridge-patterns|no DSL]])

**Aspirational — the vision beyond the minimal cut.**

- **Benefits arc** — fan-out, FX, multilingual, negotiate, bind, program rollup
- **RFP / emergent [[bridge-collect|Collect]] demo** (agent-mutated Requirements, conditional items, N suppliers — the same multi-turn loop with a smarter per-turn reply, generalizing the Phase-1 bounded Collect) + whole-demo **live add** with no redeploy — **no new pattern, no code change**
- **Remaining built-in flows** — Negotiate (Phase 2) and Collect (Phases 1/3) built as code; `pattern` stays a selector, there is **no workflow DSL** ([[bridge-patterns|closed pattern set]])
- **Four-signal [[bridge-disposition|signal provider]]** — type match / wrong-doc detection (mock / model / computed)
- **[[bridge-party-memory|Party memory]]** — Memory Bank consumers (disposition pre-arming, extraction hints, outbound defaults)
- **Cold-inbound Extract edge** — email adapters, open-set classification, correlation-miss triage
- **Bridge-as-client / outbound** — Agent-Card discovery, real party-channel SLA nudges (the actual send)
- **Per-customer multi-tenancy** — one deployment = one trust domain today
- **Managed A2A task store adoption** — an [[bridge-seams|adapter swap]] the day the platform ships it
- **Document AI extraction adapter** — the second engine behind the extraction seam; the one-adapter-swap proof that extraction is delegated to swappable dedicated services
- **Hardening** — VPC Service Controls, customer-managed encryption keys, Security Command Center; schema evolution; BigQuery observability + eval loop

**Decisions.** *(Detail and rationale in `docs/decisions/`.)*

- **Thresholds** (resubmit / auto-approve, retry cap) live in the process-skill `assets/policy.yaml`; the Bridge ships coded defaults used only when the skill omits a key (skill value → default). See `docs/decisions/adr-0002-thresholds-in-skill.md`.
- **Exchange record vs. view** — Exchange is a derived view over its tasks by default; Address stays a view (classified ledger derived from tasks, one doc per task). It materializes into a standalone stored record only on first exchange-only state: an agent-owned Requirements artifact (emergent Collect, Phase 3), process-skill binding, program membership, or reopen. See `docs/decisions/adr-0003-exchange-view-vs-record.md`.
- **Signal-provider shape** — the four-signal contract is a fixed `DispositionSignals` value object (legibility / type-match / confidence+fields / completeness+rules, each optional) read through one `SignalProvider` interface; disposition consumes it engine- and provider-agnostically. Phase 1 scopes one provider (extraction-derived; populates legibility, confidence, type-match — the completeness *decision* stays the agent's, with the Bridge best-efforting an advisory assessment); model-reported/computed providers sit behind the same interface *[Aspirational]*. See `docs/decisions/adr-0004-signal-provider-interface.md`.
- **Extraction-seam doctype binding** — the doctype skill declares its binding in `metadata` + `assets/`: the Gemini binding (prompt = `SKILL.md` body, `assets/schema.json`) is always present; the Document AI binding (`metadata.bridge-docai-processor` + `assets/docai-entity-map.yaml`) is optional. The seam resolves per doctype: if the operative engine is Document AI and a processor is bound → Document AI, else fall back to Gemini (never a hard failure; Gemini-only is the doctype's capability envelope). See `docs/decisions/adr-0005-extraction-doctype-engine-binding.md`.

**Long-running lifecycle — decided (`docs/decisions/adr-0008-long-running-collection-lifecycle.md`).** *(Surfaced by [[bridge-long-running|long-running collection]] — a collection running days/weeks. Decisions recorded; implementation is Phase 3, tracked in `PLAN.md`.)*

- **Exchange lifetime / expiry.** No task TTL and **no Bridge auto-abandon** — the [[bridge-proactive|escalation ladder]] runs and then **holds at `escalated`**, surfacing the stall; **terminal close is the app's explicit `cancel_task`** (sense-B ownership). Trade-off: stalled legs stay open until the app closes them — the safeguard is visibility (escalation queue), not auto-expiry.
- **Context / credential validity over weeks.** Context is **durable and long-lived** (the A2A context, no expiry); the **credential is short-lived and re-issuable** — access is re-authorized per inbound turn at the Gateway ([[bridge-zones]]), and the out-of-band link is renewable without orphaning the context. No long-TTL bearer token may be the sole key.
- **Artifact retention.** Mechanism decided — backend object-lifecycle policy (not bespoke GC), at least the exchange life; the concrete post-terminal window is **left to deploy-time policy** (a compliance/ops concern, not fixed in the architecture).
- **Push-notification webhooks — pulled forward to Phase 3.** Inbound-triggered A2A `PushNotificationConfig` (servicer opts in to be called back about its own exchange) is separated from the still-Phase-4 Bridge-as-outbound-client. Interim: `tasks/get` / `tasks/resubscribe` (`docs/decisions/adr-0007-canonical-a2a-edge.md`).

## Related
- [[bridge-demo-suite|demo implementations]], [[bridge-stages|build phases]], [[bridge-long-running|long-running collection]]
