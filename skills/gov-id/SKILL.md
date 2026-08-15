---
name: gov-id
description: A government-issued photo ID (driver's license, passport, national ID). Use as proof of
  identity. Extracts full name, document number, issuing authority, and expiry date; validates the
  document is unexpired and legible.
metadata:
  bridge-kind: doctype
  bridge-extraction-engine: gemini
  bridge-schema: assets/schema.json
  version: "1.0"
---

Extract the fields defined in `assets/schema.json` from the supplied ID. Validation rules live in
`assets/validation.yaml`.
