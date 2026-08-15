# ADR-0008 — Long-running collection lifecycle (expiry, context/credential validity, progress notification, retention)

- **Status:** Accepted
- **Date:** 2026-08-15
- **Resolves:** the "Undecided — raised, not yet resolved" items in `wiki/bridge-open-questions.md` surfaced by `wiki/bridge-long-running.md`
- **Context:** `wiki/bridge-long-running.md`, `wiki/bridge-proactive.md`, `wiki/bridge-aggregate-model.md`, `wiki/bridge-zones.md`, `docs/decisions/adr-0001-stack.md`

## Context

`wiki/bridge-long-running.md` establishes the shape of a collection that runs for **days or weeks**: a durable A2A task that sits idle and is woken only by a party turn, a clock alarm, or an HITL resume. That model exposed four questions the design had no answer for, because the demo path never ran longer than a fast-forwarded virtual clock:

1. **Expiry** — the task lifecycle has **no TTL**; the escalation ladder runs forever and abandoned exchanges accumulate.
2. **Context/credential validity** — the party responds inbound carrying its leg's context, handed out-of-band; nothing said how long that stays valid.
3. **Progress notification** — over weeks, polling is wasteful and streams don't survive; push webhooks were parked in Phase 4.
4. **Artifact retention** — versioning across weeks of resubmissions has no retention story.

These are policy/lifecycle decisions, independent of (and layered on) the runtime and transport decisions (ADR-0001).

## Decision

### 1. No TTL and no Bridge auto-abandon — terminal close is the app's explicit call

There is **no wall-clock TTL** on a task or exchange, and the **Bridge never auto-closes a stalled collection**. A task may stay open for weeks by design. When a party goes silent, the [[bridge-proactive|escalation ladder]] runs its course (`on_track → overdue → reminder → escalated`) and then **holds at `escalated`** — surfacing the stall on the read-model / dashboard escalation queue, but taking no terminal action.

- **Terminal close is the app's decision**, made via the existing `cancel_task` (→ `CANCELED`). This keeps terminal authority with the app, exactly parallel to sense-B completeness ownership (ADR-0004/0006): the Bridge advises ("this leg has stalled past SLA"), the app decides ("close it").
- No new policy knob and no `abandoned_sla` state — the ladder's terminal rung is simply a durable `escalated` status the app acts on. The SLA policy still owns *cadence / deadline / max_nudges* (when to nudge and escalate); it does **not** own *whether to close*.
- **Trade-off, stated plainly:** a stalled exchange can remain open indefinitely (accumulating at `escalated`). The safeguard is **visibility, not auto-expiry** — a stall is always escalated on the dashboard, never silent; closing it is an operational/app action. If accumulation ever becomes a real problem, a policy-driven auto-close can be added later without breaking this model (it would move from "app decides" to "app-configured default," a strictly additive change).

### 2. Context lifetime is decoupled from credential lifetime

The **exchange context identifier is durable and long-lived** — it is the A2A `context`, minted at request time, with no expiry (it lives as long as the exchange, subject to (1)). A weeks-long collection must not depend on a weeks-old bearer token.

- **Access is authorized per inbound turn at the Agent Gateway**, scoped to the leg's context (`wiki/bridge-zones.md` — a party can address only its own leg). Authorization is re-established on each turn, not carried as a long-lived secret.
- The out-of-band link handed to the party **resolves to a leg** and is **renewable/re-issuable without losing the context** — refreshing or re-minting a party's credential never orphans the collection. Short-lived credential, durable context.
- Implication: no design may embed a long-TTL bearer token as the sole key to a weeks-long exchange. Credential expiry is a recoverable event (re-issue the link), not a terminal one.

### 3. Inbound-triggered push notification is pulled forward to Phase 3

**Progress notification via A2A push-notification config is pulled forward from Phase 4 to Phase 3**, landing alongside the durable substrate that makes weeks real. Over a weeks-long window the servicer registers a webhook (standard A2A `PushNotificationConfig`) and the Bridge calls it on task-state change, instead of anyone polling or holding a stream.

- This is distinct from, and does **not** advance, **Bridge-as-outbound-client** (Agent-Card *discovery*, the Bridge dialing counterparties, real party-channel SLA sends) — that stays **Phase 4** (`wiki/bridge-a2a-edge.md`, `docs/roadmap.md`). Push here is the servicer opting in to be called back about *its own* exchange; it is inbound-first in spirit.
- Until it lands, `tasks/get` (poll) and `tasks/resubscribe` (re-attach) from ADR-0001 are the interim surfaces; the docs must not imply push exists before Phase 3.

### 4. Artifacts are retained via the backend's object-lifecycle policy — concrete window TBD

Artifact versions (resubmissions) are retained for at least the **life of the exchange**, and beyond terminal state by a **backend-enforced retention window**. The *mechanism* is decided: retention is a `Gcs` object-lifecycle policy on deploy, **not bespoke Bridge GC** — consistent with ADR-0001's "stock backends, no bespoke plumbing." The *value* (post-terminal window, and any compliance floor) is **deliberately left to deploy-time policy and not fixed here** — it is a per-deployment/compliance concern, not an architecture decision. This ADR commits to "backend-enforced retention exists"; the number is set at deploy.

## Rationale

- **No auto-abandon** keeps terminal authority where every other "is it done / is it over" call already lives — with the app (sense B, ADR-0004/0006). The Bridge's job is to *surface* the stall (escalate, make it visible), not to unilaterally end a relationship; a human-paced weeks-long collection is exactly where a premature auto-close would be most damaging. No new lifecycle state, no timer on the aggregate — a stall is a durable `escalated` the app acts on.
- **Decoupling context from credential** is the only way a weeks-long inbound collection is robust: any secret with a sensible TTL will expire before the party responds, so the context cannot *be* the secret. Per-turn Gateway authorization is already the trust model (`wiki/bridge-zones.md`); this states its long-running consequence.
- **Pulling push forward** follows the same principle as ADR-0001: use the standard A2A mechanism for the job. Weeks-scale polling is wasteful and streams don't survive — push is the canonical answer, and it does not require the deferred outbound *client* machinery.
- **Retention via backend lifecycle** avoids bespoke GC and gives a compliance-legible story for free; leaving the *number* to deploy keeps a compliance/ops concern out of the architecture.

## Consequences / risks

- **Stalled exchanges accumulate.** With no auto-close, `escalated` legs pile up until the app cancels them. The mitigation is operational: the dashboard's escalation queue must make stalls impossible to miss, and the app needs an explicit close path. This is the deliberate cost of keeping terminal authority with the app.
- **The durable `escalated` status is now load-bearing.** It must persist across restarts (Phase-3 substrate) and drive the read-model, since it is the *only* signal that a weeks-long collection has stalled.
- **Pulling push into Phase 3** adds scope to Phase 3 (webhook registration, delivery, retry/backoff, per-leg auth on the callback). Justified: weeks-scale is not usable on poll-only. Tracked in `docs/roadmap.md` (deferred hardening).
- **Credential re-issue flow** must be built so a refreshed link re-binds to the same context — a real path, not just a stated invariant; until then, long-lived local demos rely on the permissive local authenticator.
- **Retention number is deferred to deploy** — deployments in regulated contexts must set it deliberately; the architecture guarantees the mechanism, not a default.
- These are **design decisions ahead of implementation**: today none is built (the durable substrate itself is Phase 3). The ADR sets the target; `wiki/bridge-long-running.md` status block tracks the gap.

## Alternatives considered

- **Fixed platform TTL on tasks/exchanges.** Rejected: a blunt wall-clock cap contradicts "a task may legitimately stay open for weeks" and ignores per-skill SLA differences.
- **Bridge auto-abandons after the SLA ladder is exhausted** (→ `CANCELED(abandoned_sla)`, or a new `EXPIRED` state). Rejected: it moves terminal authority from the app to the Bridge, which contradicts sense-B ownership, and a premature auto-close is most damaging exactly in the human-paced weeks-long case. The Bridge escalates and makes the stall visible; the app decides to close. (Auto-close remains a strictly-additive future option if accumulation proves painful.)
- **Long-TTL bearer token as the exchange key.** Rejected: any responsible TTL expires before a weeks-long party responds; makes the collection fragile and the token a standing liability.
- **Keep push in Phase 4, poll-only until then.** Rejected for weeks-scale: polling for weeks is wasteful and operationally poor; push is the standard mechanism and is separable from the outbound client.
- **Bespoke artifact GC in the Bridge.** Rejected: backend object-lifecycle policy is the stock answer (ADR-0001), less to own.

## Note

This ADR is lifecycle/policy on top of the runtime and transport decisions (ADR-0001); it introduces **no new aggregate state** (a stall is a durable `escalated`; terminal close reuses the app's `cancel_task` → `CANCELED`) and **no new transport** (push is standard A2A `PushNotificationConfig`). See `wiki/bridge-long-running.md`.
