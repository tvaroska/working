"""Domain models for the A2A Document Bridge contract.

These models define the shape of data exchanged between agents and the Bridge:
- CollectRequest (inbound): what the agent sends
- ExchangeTurn with CollectionStatus (outbound): what the Bridge returns
- LedgerEntry: one classified document in the ledger
- Extraction: the extraction payload (fields + confidence signals)

Field names mirror wiki/evals/address/expected.json so eval data validates cleanly.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Disposition(StrEnum):
    """The classification verdict for a document."""

    ACCEPTED = "accepted"
    PENDING = "pending"
    REJECTED = "rejected"


class RequirementStatus(StrEnum):
    """The per-item status vocabulary of the app-owned requirements list.

    The whole "language" of the requirements artifact (wiki/bridge-collect.md):
    ``required``/``optional`` are the Bridge's mechanical chase knob, while
    ``satisfied``/``waived`` mark items the app no longer needs chased.
    """

    REQUIRED = "required"
    OPTIONAL = "optional"
    SATISFIED = "satisfied"
    WAIVED = "waived"


class ExtractedFields(BaseModel):
    """The extracted fields from a document.

    Doctype-specific key_fields are modeled as an open dict in M0;
    typed per-doctype schemas are Sprint 1.
    """

    model_config = ConfigDict(extra="forbid")

    doctype: str
    issuer: str | None = None  # canonical issuer; absent for gov-id
    key_fields: dict[str, str] = Field(default_factory=dict)


class Extraction(BaseModel):
    """The full extraction payload for a document.

    Includes the extracted fields plus confidence signals (overall_confidence,
    field_confidence, legible, flagged_fields). These signals are carried but
    not acted on in M0 (disposition logic is Sprint 1).
    """

    model_config = ConfigDict(extra="forbid")

    fields: ExtractedFields
    overall_confidence: float | None = None
    field_confidence: dict[str, float] = Field(default_factory=dict)
    legible: bool | None = None
    flagged_fields: list[str] = Field(default_factory=list)


class LedgerEntry(BaseModel):
    """One classified document in the ledger.

    Note: the raw eval entry has extra keys (issuer_raw, expected_disposition,
    expected_gate, artifact, synthetic, note), so validating the whole raw entry
    will fail under extra="forbid". Build LedgerEntry explicitly, mapping
    expected_disposition → disposition and extraction block via Extraction.model_validate.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    doctype: str
    issuer: str | None = None  # canonical issuer
    disposition: Disposition
    extraction: Extraction

    # App-authored explanation of *why* this document got its disposition (ADR-0013).
    # reason_code is a stable machine key minted by the app's deterministic gate
    # ("code decides" — the Bridge keys idempotent chase on it); message is the
    # human-facing prose the Bridge relays verbatim over A2UI (a servicing agent's
    # LLM may author it — "LLM routes" the words, never the verdict). Both are None
    # for an accepted doc that needs no explanation. reason_code is a free string,
    # not an enum: the vocabulary is per-skill, so the Bridge stays domain-agnostic.
    reason_code: str | None = None
    message: str | None = None


class CollectionStatus(BaseModel):
    """The classified ledger container returned to the agent.

    Contains the ledger of classified documents, a best-effort list of
    outstanding document references, and a terminal flag.
    """

    model_config = ConfigDict(extra="forbid")

    ledger: list[LedgerEntry] = Field(default_factory=list)
    outstanding: list[str] = Field(default_factory=list)
    terminal: bool = False


class Requirement(BaseModel):
    """One item in the app-owned requirements list (ADR-0013).

    ``item`` is a human label ("proof of address"); ``status`` tunes the Bridge's
    mechanical chase; ``doctype_hint`` is a best-effort steer for what to upload.
    ``reason_code``/``message`` carry the app-authored *why* an item is outstanding
    (e.g. ``distinct-issuer-needed`` + "Both bills are from Power Co. — send a bill
    from a different provider."). See :class:`LedgerEntry` for the field split.
    """

    model_config = ConfigDict(extra="forbid")

    item: str
    status: RequirementStatus
    doctype_hint: str | None = None
    reason_code: str | None = None
    message: str | None = None


class RequirementsList(BaseModel):
    """The **app-owned** artifact: what's needed, whether it's done, and why (ADR-0013).

    Distinct from the Bridge-owned :class:`CollectionStatus` ("what we have"): the
    app decides *what's needed* and *is it done*; the Bridge proposes a best-effort
    list but holds no final word (wiki/bridge-collect.md). Travels inside A2A
    parts/artifacts alongside :class:`ExchangeTurn`, not nested in CollectionStatus,
    preserving the two-owner split.
    """

    model_config = ConfigDict(extra="forbid")

    requirements: list[Requirement] = Field(default_factory=list)
    done: bool = False


class ExchangeTurn(BaseModel):
    """The outbound envelope's domain payload returned by the Bridge.

    Contains the A2A context_id (exchange identifier) and the collection status.
    """

    model_config = ConfigDict(extra="forbid")

    context_id: str
    status: CollectionStatus


class CollectRequest(BaseModel):
    """The inbound request sent by an agent to the Bridge.

    Identifies the party (counterparty reference), the process skill requested,
    and optionally the context_id to continue an existing exchange.
    """

    model_config = ConfigDict(extra="forbid")

    party: str
    skill: str
    context_id: str | None = None
