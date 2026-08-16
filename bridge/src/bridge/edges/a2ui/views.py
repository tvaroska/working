"""A2UI declarative view models + projection (M1.10).

The **content-not-pixels** contract between the Bridge and any host renderer
(the human-edge rendering protocol). These shapes describe **what to show**
(the party-status view) and **what comes back** (intake affordances) without
dictating *how it looks*.

These are **bridge-local** models, NOT contract types — the frontend consumes
JSON, not Python types, so there is no cross-language sharing pressure. The
A2A edge keeps plan.py/trust.py/executor bridge-local; the A2UI edge keeps
its declarative shapes here, not in contract/.

The projection (`party_status_view`, `build_screen`) consumes contract types
(`CollectionStatus`, `RequirementsList`) and relays per-doc and next-action
`message` prose **verbatim** from M1.9 (ADR-0013).

Import discipline: contract + pydantic + typing.Literal only. Never agents,
never seams/adapters. Keep this out of bridge/__init__.py (preserve cheap
import bridge + the no-agents-guard clarity).
"""

from __future__ import annotations

from typing import Literal

from contract import (
    CollectionStatus,
    Disposition,
    RequirementsList,
    RequirementStatus,
)
from pydantic import BaseModel

__all__ = [
    "DocStatus",
    "ResponseField",
    "IntakeSpec",
    "PartyStatusView",
    "A2uiScreen",
    "party_status_view",
    "build_screen",
]


class DocStatus(BaseModel, frozen=True):
    """A document's status in the party-status view.

    Field-for-field projection from LedgerEntry, carrying the verbatim `message`
    for rejected docs (ADR-0013 relay).
    """

    model_config = {"extra": "forbid"}

    id: str
    doctype: str
    issuer: str | None = None
    disposition: Disposition
    message: str | None = None  # verbatim relay from LedgerEntry (rejected only)


class ResponseField(BaseModel, frozen=True):
    """A declarative affordance describing what comes back (content-not-pixels).

    The host renderer decides *how* this displays (a file input, a text area, a
    form field) — the Bridge describes the abstract contract.
    """

    model_config = {"extra": "forbid"}

    key: str
    label: str
    input: Literal["file", "text", "form"]
    required: bool = True


class IntakeSpec(BaseModel, frozen=True):
    """What to show: the next-action prompt + intake affordances.

    The `prompt` is the next-action prose (verbatim from the requirement `message`);
    `accepts` is a declarative list of affordances (what comes back).
    """

    model_config = {"extra": "forbid"}

    prompt: str
    doctype_hint: str | None = None
    accepts: list[ResponseField]


class PartyStatusView(BaseModel, frozen=True):
    """The party-status view: sent / accepted / outstanding / next / done.

    Projection over the classified ledger + requirements (M1.9). Buckets:
    - `sent`: every LedgerEntry in status.ledger
    - `accepted`: entries with disposition == ACCEPTED
    - `outstanding`: [req.item for req in requirements.requirements if req.status == REQUIRED]
    - `next`: the first REQUIRED requirement's message (verbatim), or None when done
    - `done`: requirements.done
    """

    model_config = {"extra": "forbid"}

    sent: list[DocStatus]
    accepted: list[DocStatus]
    outstanding: list[str]
    next: str | None
    done: bool


class A2uiScreen(BaseModel, frozen=True):
    """The declarative A2UI screen: status + intake.

    `intake` is None when `status.done` — the party has nothing left to provide.
    """

    model_config = {"extra": "forbid"}

    status: PartyStatusView
    intake: IntakeSpec | None


def party_status_view(status: CollectionStatus, requirements: RequirementsList) -> PartyStatusView:
    """Pure projection: classify ledger + requirements into party-status buckets.

    This is the core of the A2UI edge: what has been sent, what's been accepted,
    what's still outstanding, and what to do next. The Bridge relays the domain
    prose verbatim (ADR-0013); it authors nothing.

    Args:
        status: CollectionStatus containing the classified ledger.
        requirements: RequirementsList from M1.9's propose_requirements.

    Returns:
        PartyStatusView with sent/accepted/outstanding/next/done.

    Notes:
        - `sent` carries verbatim `message` from the ledger for rejected docs
        - `next` is the first REQUIRED requirement's message (verbatim), or None if done
        - `done` is requirements.done (the app-owned completeness flag)
    """
    # sent: map every LedgerEntry -> DocStatus (carry message verbatim for rejected)
    sent = [
        DocStatus(
            id=entry.id,
            doctype=entry.doctype,
            issuer=entry.issuer,
            disposition=entry.disposition,
            message=entry.message,  # verbatim relay (ADR-0013)
        )
        for entry in status.ledger
    ]

    # accepted: entries with disposition == ACCEPTED
    accepted = [doc for doc in sent if doc.disposition == Disposition.ACCEPTED]

    # outstanding: [req.item for req in requirements if req.status == REQUIRED]
    outstanding = [
        req.item for req in requirements.requirements if req.status == RequirementStatus.REQUIRED
    ]

    # next: the first REQUIRED requirement's message (verbatim), or None if done
    next_msg = None
    for req in requirements.requirements:
        if req.status == RequirementStatus.REQUIRED:
            next_msg = req.message
            break

    # done: requirements.done (the app-owned completeness flag)
    done = requirements.done

    return PartyStatusView(
        sent=sent, accepted=accepted, outstanding=outstanding, next=next_msg, done=done
    )


def build_screen(status: CollectionStatus, requirements: RequirementsList) -> A2uiScreen:
    """Compose the declarative A2UI screen: status + intake.

    The intake spec is None when requirements.done; otherwise built from the first
    REQUIRED requirement (prompt = req.message, doctype_hint = req.doctype_hint).
    The affordance list is a small static default (content, not pixels).

    Args:
        status: CollectionStatus containing the classified ledger.
        requirements: RequirementsList from M1.9's propose_requirements.

    Returns:
        An A2uiScreen (JSON-serializable).

    Notes:
        The affordance list ([file, text]) is a minimal static default. A real
        frontend might enrich this based on doctype_hint (gov-id -> passport/license
        picker), but the Bridge describes the abstract contract, not the pixels.
    """
    view = party_status_view(status, requirements)

    # intake is None when done
    if requirements.done:
        return A2uiScreen(status=view, intake=None)

    # Build intake spec from the first REQUIRED requirement
    req = next(
        (r for r in requirements.requirements if r.status == RequirementStatus.REQUIRED),
        None,
    )

    if req is None:
        # Edge case: not done, but no REQUIRED requirements (shouldn't happen)
        return A2uiScreen(status=view, intake=None)

    # Compose the intake spec
    prompt = req.message or ""
    doctype_hint = req.doctype_hint
    accepts = [
        ResponseField(key="document", label="Upload a document", input="file"),
        ResponseField(key="text", label="Or paste the details", input="text", required=False),
    ]

    intake = IntakeSpec(prompt=prompt, doctype_hint=doctype_hint, accepts=accepts)

    return A2uiScreen(status=view, intake=intake)
