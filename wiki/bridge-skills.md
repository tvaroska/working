---
type: atom
related:
  - "[[bridge]]"
  - "[[bridge-patterns]]"
  - "[[bridge-seams]]"
tags: [bridge]
status: review
updated: 2026-08-06
---

# Skills — demos as configuration

> Once the primitives are the architecture, every demo is the same machine, configured by **two kinds of skill**. Adding a document type — or a whole demo — is a runtime upload with **no code change and no redeploy**.

Skills are authored in the open **[Agent Skills format](https://agentskills.io)** (the Anthropic-originated standard: a folder with a `SKILL.md` — YAML frontmatter `name` + `description`, plus a Markdown body — optionally bundling `assets/`, `references/`, `scripts/`). The Bridge is a skills host: it installs skill folders and consumes them. Two Bridge-specific *kinds* are distinguished by a `metadata.bridge-kind` field, because one document type is used across many processes and one process consumes many document types:

```
document-type skill               parameterizes a TASK
    = schema + prompt             what to extract from one doc kind (Gemini)
    + engine binding (optional)   Document AI: a processor plus an entity→field map
    + per-document validation     is THIS document acceptable
    + four disposition signals    legibility / type match / confidence / completeness

process skill                     parameterizes an EXCHANGE — a lean catalog
    = exchange pattern            extract | request | negotiate | deliver | collect
    + policy                      reminders, SLA, retries, escalation, thresholds
    + candidate doctypes          which doctype skills may appear (label space)
```

A doctype skill binds to the [[bridge-seams|extraction seam]] engine-agnostically: schema and prompt drive the Gemini adapter, an optional processor mapping drives the Document AI adapter, and a doctype no Document AI processor covers is simply Gemini-only (its capability envelope). A doctype skill is reusable and pattern-agnostic; a process skill is a **lean catalog** — it holds **no** requirement slots, conditional logic, or **formal** completeness rules. It **may** carry a **prose satisfaction description** (natural language, never a rule language/DSL). The completeness *decision* is the **agent's**, asserted at runtime; the Bridge best-efforts an advisory assessment from that prose description (see [[bridge-collect|Collect]]). A one-shot extract is a single-doctype process skill. A full **demo implementation** is exactly this configuration plus a thin driver — it consumes the [[bridge|core Bridge]] without changing it, which is why adding a demo is adding configuration, not forking the platform.

## Packaged as Agent Skills

Every skill is one Agent Skills folder. Frontmatter `name` (lowercase, hyphens, ≤64 chars, matches the directory) and `description` (what it does + when to use, ≤1024 chars) are the **discovery surface**; the structured Bridge config lives in `metadata` (string→string) plus bundled `assets/`, and the extraction prompt / process notes are the `SKILL.md` body. `bridge-*` metadata keys are namespaced to avoid collisions per the spec's guidance.

**Doctype skill** — `utility-bill/`:
```
utility-bill/
├── SKILL.md                # frontmatter + extraction prompt (body)
├── assets/
│   ├── schema.json         # extraction schema (Gemini constrained JSON)
│   └── validation.yaml     # per-document rules + disposition-signal config
└── references/
    └── issuer-canonicalization.md   # optional: issuer-key rules, loaded on demand
```
```markdown
---
name: utility-bill
description: A utility bill (electricity, water, gas) from a service provider. Use as
  proof of address. Extracts and canonicalizes the issuer/company, account-holder name,
  service address, and statement date; validates the bill is recent and shows an address.
license: Proprietary. LICENSE.txt has complete terms
metadata:
  bridge-kind: doctype
  bridge-extraction-engine: gemini
  bridge-docai-processor: ""        # optional Document AI processor id
  bridge-schema: assets/schema.json
  version: "1.0"
---

Extract the fields defined in `assets/schema.json` from the supplied bill. Canonicalize
the issuer to a stable key (`PowerCo` / `Power Co.` / `PowerCo Ltd` → `power-co`) — see
`references/issuer-canonicalization.md`. Validation rules live in `assets/validation.yaml`.
```

**Process skill** — `address-proof/`:
```
address-proof/
├── SKILL.md                # frontmatter + process notes (body)
└── assets/
    └── policy.yaml         # SLA cadence, max nudges, retry cap, thresholds
```
```markdown
---
name: address-proof
description: Collect proof of address for a party. Use when a servicer's agent needs
  address verification. A bounded Collect over candidate doctypes gov-id and utility-bill;
  the agent owns the completeness decision. The skill carries a prose satisfaction
  description (never a formal rule) the Bridge best-efforts from.
metadata:
  bridge-kind: process
  bridge-pattern: collect
  bridge-candidate-doctypes: "gov-id utility-bill"
  bridge-policy: assets/policy.yaml
---

Bounded Collect. The Bridge classifies each arriving doc against the candidate doctypes,
dispositions it, and chases the delta per `assets/policy.yaml`. Completeness (the OR, the
count-to-two, the distinct-issuer check) is the **agent's** — asserted per turn, never here.
```

The `bridge-pattern` value is a **selector over a closed set of built-in flows** (see [[bridge-patterns|patterns]]) — the skill *picks* a flow, it never *defines* one; there is no workflow DSL. Industry-agnosticism comes from the skills plus the agent's per-turn decisions, not author-defined flow.

## Why it matters — progressive disclosure *is* the Agent Card

Skills live in the GCP **Skill Registry** behind a [[bridge-seams|seam]] (local adapter = a directory of skill folders for dev). The Agent Skills **progressive-disclosure** model maps directly onto the Bridge's discovery surface: an agent host loads only `name` + `description` at startup, and the full `SKILL.md` + assets only when a skill activates. The Bridge's [[bridge-a2a-edge|Agent Card]] is exactly that discovery layer — generated from the installed skills' `name`/`description`. So uploading one skill folder regenerates the card and the new capability is live; install several demos' skills and the **one** card advertises them all: a single core speaking many use-cases at once (see [[bridge-demo-suite|one core, many demos]]). This **live skill-add** is the concrete proof of the reusability thesis, and a required demo beat: adding the whole RFP implementation to the running core.

Skills are validated against the spec (`skills-ref validate ./skill-name`) in CI. Today only one flow is built and thresholds are constants (resubmit / auto-approve thresholds, a fixed retry cap); **policy** already lives in the skill (`assets/policy.yaml`), and the remaining built-in flows land as the demos do (Negotiate in Phase 2, Collect in Phases 1/3).

## Related
- [[bridge|the Bridge]], [[bridge-patterns|patterns]], [[bridge-seams|seams]]
