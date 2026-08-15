---
type: root
down:
  - "[[bridge-aggregate-model]]"
  - "[[bridge-edges]]"
  - "[[bridge-patterns]]"
  - "[[bridge-adk]]"
  - "[[bridge-artifacts]]"
  - "[[bridge-skills]]"
  - "[[bridge-gcp-substrate]]"
  - "[[bridge-demo-suite]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# A2A Document Bridge

> Collecting documents from the outside world is slow, messy, and human-paced. The Bridge **manages that process** so a servicer's agent never touches it — it asks once and receives documentation already gathered, chased, normalized, and ready to act on.

**Why it exists.** An expert doesn't chase paperwork — an assistant does. The assistant emails the five carriers, re-reads the one reply that came back as a photo, notices two are in different currencies, nudges the one who's late, and only walks in when there's **one clean view** to decide on. The Bridge is that assistant for a servicer's agent: the internal agent stays precise and impatient; the Bridge absorbs a world that is neither. Extraction (PDF → JSON) is already covered well by dedicated services — the durable value is **mediation**: owning the multi-turn, multi-party, multi-format relationship end to end. Extraction itself sits behind a [[bridge-seams|seam]] with swappable engines — Gemini or Document AI, chosen by config — because work a purpose-built service already does well is exactly the thing you should delegate and be able to swap.

**How it works.** [[bridge-patterns|A2A]] is the protocol the exchanges run on — a servicer's agent and the Bridge (and agent counterparties) speak it natively, so a solicitation, a chase, and a delivery are all just tracked tasks in one shared vocabulary. Parties who *aren't* agents still get folded into the same model through the human-facing edge. The servicer's agent sees one uniform interface; who's on the other end is the Bridge's problem.

**Who it's for.** Two audiences, in order. First, teams **evaluating the Gemini Enterprise Agent Platform** — the Bridge is the flagship showcase of what the platform makes possible end to end: Agent Runtime, Skill Registry, Memory Bank, Agent Gateway, Agent Identity, A2A and A2UI wired into one real, deployed system rather than a toy. Second, servicers who could **adopt it as a product** — a managed mediation service their agent calls once and gets clean, ready-to-act documentation back. The seams, the managed-GCP wiring, and the trust boundary *are* the demonstration; the extraction inside is delegated to dedicated services.

**Core vs. demos.** The **Bridge core** is the independent, reusable project — the platform showcase itself. Each demo is a **self-contained implementation** — skills plus a thin driver that consume the core, with **no change to the core**. That separation *is* the reusability claim. The demos are separate implementations, but they run against **one deployed core at once** — a single Agent Card and one dashboard serve them all together (see [[bridge-demo-suite|one core, many demos]]).

**What "done" looks like.** Three demo implementations on the one deployed core: **Address** (warm-up — the pull spine carrying a *bounded* [[bridge-collect|Collect]]: prove an address with either **one government ID** or **two bills from different companies**), **Benefits** (depth, the full fan-out → normalize → compare → negotiate → bind arc), and **RFP** (breadth, a different industry and the *full, emergent* Collect at scale, added *live* with no redeploy). See [[bridge-demo-suite|the demo implementations]].

**Committed vs aspirational.** The architecture is split into a **minimal showcase** (the committed core — the Address pull spine with a bounded Collect, both edges, dual-path fulfillment, proactive follow-up, the seams and network zones) and an **aspirational** vision beyond it (the benefits arc, the RFP/Collect demo, party memory, cold inbound). See [[bridge-open-questions|scope — minimal vs aspirational]] and [[bridge-stages|build phases]].

**Scope.** Core motion is **solicited/pull** — the servicer asks first and the Bridge mints the exchange's context identifier at request time. Cold, unsolicited push is a **deferred edge**, not the shape it's built around.

## Read next

**Start here — the model**
- [[bridge-aggregate-model|aggregate model]] — exchange / task / session / party; read this first

**How it's built** (dive as you like)
- [[bridge-adk|running on Google ADK]] — the platform principle: native constructs, as standard as possible
- [[bridge-artifacts|documents as artifacts]] — versioned ADK artifacts, moved across the wire by reference
- [[bridge-edges|two edges]] — A2A for agents, A2UI for humans
- [[bridge-patterns|exchange patterns]] — Request / Negotiate / Deliver / Collect
- [[bridge-long-running|long-running collection]] — the durable A2A task; days/weeks with no held connection
- [[bridge-a2a-consumer|A2A consumer]] — how an agent calls the Bridge: `RemoteA2aAgent`, `input-required` pause, status updates
- [[bridge-skills|skills]] — demos as configuration
- [[bridge-gcp-substrate|GCP substrate]] — seams, network zones, deploy, proactive engine

**Context**
- [[bridge-demo-suite|demo implementations]] — the three demos, build phases, and status
