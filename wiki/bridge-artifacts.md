---
type: concept
up: "[[bridge]]"
related:
  - "[[bridge-adk]]"
  - "[[bridge-edges]]"
  - "[[bridge-a2a-edge]]"
  - "[[bridge-disposition]]"
  - "[[bridge-gcp-substrate]]"
tags: [bridge, adk, artifacts]
status: review
updated: 2026-08-14
---

# Documents as artifacts

> A document is bytes — a photo of a bill, a scanned ID, a PDF. On the Bridge those bytes are a first-class **ADK artifact**: versioned, session-scoped, addressed by name, and moved across the wire **by reference, never inline**. This is the platform's own answer to binary documents, so we use it as-is rather than inventing a store.

## First, two things called "artifact"

The word is overloaded in this project. Keep them apart:

| Term | What it is | Where it lives |
|---|---|---|
| **A2A / aggregate artifact** | a **metadata** payload attached to a task — the classified-ledger entry, the Requirements list (`{payload, version}`) | the [[bridge-aggregate-model|aggregate model]] |
| **ADK document artifact** *(this page)* | the actual **document bytes**, versioned and session-scoped | the ADK `ArtifactService` |

They share a name and both *version*, but one carries meaning and the other carries bytes. When this wiki says "artifact" unqualified in a runtime/ADK context, it means the **document** artifact.

## Why the platform's artifact, not our own store

Documents are exactly what `ArtifactService` exists for, so hand-rolling a blob store would both hide the platform we are showcasing and become ours to maintain ([[bridge-adk|as standard as possible]]). Using it as-is buys three things for free:

- **Versioning = resubmission history.** Each save returns a version; **attempt N is version N**. A party re-sending a clearer photo is just the next version on the same filename — the disposition history is the version list, no extra bookkeeping.
- **Deletion = a real erase.** An [[bridge-adk|off-script]] deletion/erasure request maps to `delete_artifact` — an auditable removal of the bytes, not a soft flag.
- **Session-scoped by default.** One case = one session, so a document is reachable only within the exchange that produced it — the trust boundary comes from the platform, not from our own checks.

## Crossing the wire — by reference, both directions

An ADK artifact lives *inside* the Bridge; an A2A **`FilePart`** is how a document travels *between* agents. The [[bridge-edges|edge]] is the single place those two worlds meet, and the rule is absolute: **bytes never ride the A2A message.**

- **Inbound.** A submission carries a `FileWithUri`; the edge fetches it and `save_artifact`s it (new version per resubmission), then disposition runs on the artifact.
- **Outbound.** The deliverable is the [[bridge-a2a-edge|classified ledger plus artifact references]] — meaning first, bytes on demand. The servicer's agent reads the status, then pulls accepted-document bytes from a **scoped fetch endpoint**.

A **reference is not a capability**: every fetch is authorized on the same per-party leg boundary as the rest of the exchange, so handing over a uri never widens access. This keeps the message small, the boundary honest, and competitors' documents un-cross-reachable even if a uri leaks.

## Local ↔ deployed — one more backend swap

The artifact story swaps backends exactly like sessions do ([[bridge-gcp-substrate|substrate]]): **`InMemoryArtifactService`** locally, **`GcsArtifactService`** on deploy, with **no agent-code change**. The scoped fetch endpoint serves bytes directly from memory locally and issues a **GCS signed URL** on deploy — same contract, different backend.

## Read next
- [[bridge-adk|running on Google ADK]] — why native constructs, and the runtime that saves/loads these
- [[bridge-a2a-edge|A2A edge]] — the send-back contract the references travel on
- [[bridge-aggregate-model|aggregate model]] — the *other* artifact (the metadata ledger)

## Related
- [[bridge-disposition|disposition]], [[bridge-gcp-substrate|GCP substrate]], [[bridge-edges|two edges]]
- **Decision record:** `docs/decisions/adr-0001-stack.md`
