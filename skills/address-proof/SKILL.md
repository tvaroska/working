---
name: address-proof
description: Collect proof of address for a party. Use when a servicer's agent needs address
  verification. A bounded Collect over candidate doctypes gov-id and utility-bill; the agent owns the
  completeness decision. The skill carries a prose satisfaction description (never a formal rule) the
  Bridge best-efforts an advisory assessment from.
metadata:
  bridge-kind: process
  bridge-pattern: collect
  bridge-candidate-doctypes: "gov-id utility-bill"
  bridge-policy: assets/policy.yaml
  version: "1.0"
---

Bounded Collect. The Bridge classifies each arriving doc against the candidate doctypes, dispositions
it, and chases the delta per `assets/policy.yaml`. Completeness (the OR, the count-to-two, the
distinct-issuer check) is the **agent's** — asserted per turn, never encoded here as a formal rule.
