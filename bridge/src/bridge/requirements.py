"""Requirements + best-effort completeness + explanation relay (M1.9).

The Bridge's **advisory** completeness checker: reads the classified ledger and applies
the Address **prose** satisfaction rule (one accepted gov-id OR ≥2 accepted utility-bills
from **distinct canonical issuers**) to propose what's still outstanding. This is
**advisory only** — the app (the consumer) still owns the final "done" decision
(wiki/bridge-collect.md, sense B). The advisory must stay **terminal-outcome-parity**
with the app's ``is_satisfied`` (same done verdict + accepted-issuer set), never
ledger-identical (docs/lessons-learned.md A2).

Emits the app-owned ``RequirementsList`` artifact and relays per-doc ``reason_code`` +
``message`` on rejected ``LedgerEntry``s **verbatim** — the Bridge transports the domain
prose; it never authors or edits it (ADR-0013).

**Parity by discipline, not by import** — ``bridge/`` MUST NEVER import ``agents/``
(guarded by ``bridge/tests/test_no_agents_import.py``). This module re-implements the
satisfaction rule fresh, mirroring the constants and exact semantics from
``agents/src/agents/address/satisfaction.py``. Parity is held by the shared test suite
asserting terminal-outcome equality across every scenario in
``wiki/evals/address/expected.json``.

Import discipline: ``contract`` + ``bridge.{disposition}`` + stdlib/pydantic/yaml only.
Never ``agents``, never ``seams``/``adapters``. Keep this out of ``bridge/__init__.py``
(preserve cheap ``import bridge`` + no-agents-guard clarity).
"""

from __future__ import annotations

import yaml
from contract import (
    CollectionStatus,
    Disposition,
    LedgerEntry,
    Requirement,
    RequirementsList,
    RequirementStatus,
)
from pydantic import BaseModel

from .disposition import Gate
from .skills import Skill

__all__ = [
    "GOV_ID",
    "UTILITY_BILL",
    "REQUIRED_DISTINCT_ISSUERS",
    "PROOF_REQUIRED",
    "DISTINCT_ISSUER_NEEDED",
    "UNSUPPORTED_DOCTYPE",
    "ILLEGIBLE",
    "SkillExplanations",
    "load_explanations",
    "AdvisoryResult",
    "advisory_satisfaction",
    "propose_requirements",
    "explain_rejection",
]

# Doctype constants (mirrored from agents/address/satisfaction.py)
GOV_ID = "gov-id"
UTILITY_BILL = "utility-bill"
REQUIRED_DISTINCT_ISSUERS = 2

# Reason code constants (free strings, per-skill — ADR-0013 §2/§54)
PROOF_REQUIRED = "proof-required"
DISTINCT_ISSUER_NEEDED = "distinct-issuer-needed"
UNSUPPORTED_DOCTYPE = "unsupported-doctype"
ILLEGIBLE = "illegible"


class SkillExplanations(BaseModel, frozen=True):
    """App/skill-authored domain prose the Bridge relays verbatim (ADR-0013).

    Loaded from a skill asset (e.g., ``skills/address-proof/assets/explanations.yaml``).
    The Bridge reads it and relays the prose as-is; it authors no prose.
    """

    item: str = ""
    doctype_hint: str | None = None
    reasons: dict[str, str] = {}

    def message_for(self, reason_code: str | None) -> str | None:
        """Return the human message for a reason_code, or None if missing."""
        if reason_code is None:
            return None
        return self.reasons.get(reason_code)


def load_explanations(skill: Skill) -> SkillExplanations:
    """Load skill explanations from the skill's asset path (M1.9).

    Reads ``skill.asset_path(skill.metadata.get("bridge-explanations",
    "assets/explanations.yaml"))`` with ``yaml.safe_load``. Tolerates a missing file
    by returning an empty-reasons ``SkillExplanations`` (so ``message`` fields degrade
    to ``None`` rather than crashing).

    Args:
        skill: The Skill instance.

    Returns:
        A SkillExplanations instance.
    """
    explanations_path = skill.asset_path(
        skill.metadata.get("bridge-explanations", "assets/explanations.yaml")
    )

    if not explanations_path.exists():
        # Missing file: degrade gracefully to empty reasons
        return SkillExplanations()

    try:
        data = yaml.safe_load(explanations_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        # Parse error or read error: degrade gracefully
        return SkillExplanations()

    if not isinstance(data, dict):
        return SkillExplanations()

    # Extract requirement metadata
    requirement = data.get("requirement", {})
    if not isinstance(requirement, dict):
        requirement = {}

    item = requirement.get("item", "")
    doctype_hint = requirement.get("doctype_hint")

    # Extract reasons mapping
    reasons = data.get("reasons", {})
    if not isinstance(reasons, dict):
        reasons = {}

    return SkillExplanations(item=item, doctype_hint=doctype_hint, reasons=reasons)


class AdvisoryResult(BaseModel, frozen=True):
    """Result of the Bridge's advisory satisfaction check (M1.9).

    Field-for-field mirror of ``agents/src/agents/address/satisfaction.py::SatisfactionResult``
    (parity by discipline, not by import). The Bridge best-efforts this verdict and chases
    the delta, but the **app holds the final "done"** (wiki/bridge-collect.md, sense B).
    """

    done: bool
    outstanding: list[str] = []
    accepted_issuers: list[str] = []  # sorted canonical set (parity, A2)


def advisory_satisfaction(status: CollectionStatus) -> AdvisoryResult:
    """Pure function: best-effort advisory check if the address proof is satisfied (M1.9).

    Re-implements the exact logic of ``agents/address/satisfaction.py::is_satisfied``:
    - Only ACCEPTED disposition counts toward completeness
    - Gov-id OR branch: any accepted gov-id satisfies
    - Distinct-issuer count: bills with None/empty issuer are excluded
    - Issuer is already canonical (do not re-canonicalize)
    - Done if gov_id_ok OR len(bill_issuers) >= REQUIRED_DISTINCT_ISSUERS (2)
    - Outstanding is [] if done, else [GOV_ID, UTILITY_BILL]

    Args:
        status: CollectionStatus containing the classified ledger.

    Returns:
        AdvisoryResult with done, outstanding, and accepted_issuers.

    Notes:
        This is **advisory only** — the consumer's ``is_satisfied`` is authoritative.
        Parity is **terminal-outcome, not ledger-identical** (lessons A2): same done
        verdict + same accepted-issuer set across every scenario in expected.json.
    """
    accepted = [e for e in status.ledger if e.disposition == Disposition.ACCEPTED]

    gov_id_ok = any(e.doctype == GOV_ID for e in accepted)

    bill_issuers = sorted(
        {
            e.issuer
            for e in accepted
            if e.doctype == UTILITY_BILL and e.issuer  # exclude None/empty
        }
    )

    done = gov_id_ok or len(bill_issuers) >= REQUIRED_DISTINCT_ISSUERS
    outstanding = [] if done else [GOV_ID, UTILITY_BILL]

    return AdvisoryResult(done=done, outstanding=outstanding, accepted_issuers=bill_issuers)


def propose_requirements(
    status: CollectionStatus, *, explanations: SkillExplanations
) -> RequirementsList:
    """Build the app-owned RequirementsList artifact (M1.9).

    Computes the Bridge's advisory satisfaction and emits a ``RequirementsList`` with
    per-item ``reason_code`` + ``message`` sourced **verbatim** from the skill's
    explanations (ADR-0013). The Bridge decides *which* reason_code applies (code
    decides); the data (explanations.yaml) supplies the human message.

    Args:
        status: CollectionStatus containing the classified ledger.
        explanations: The skill-authored explanations (verbatim relay source).

    Returns:
        A RequirementsList artifact.

    Notes:
        - Done ledger → one ``SATISFIED`` requirement, no reason/message
        - Not done → pick reason_code: ``DISTINCT_ISSUER_NEEDED`` when exactly 1 distinct
          accepted bill issuer (and no accepted gov-id), else ``PROOF_REQUIRED``
        - No message interpolation — keep strings static so "verbatim relay" is literal
    """
    advisory = advisory_satisfaction(status)

    if advisory.done:
        # Satisfied: one requirement with status=SATISFIED, no reason/message
        req = Requirement(
            item=explanations.item,
            status=RequirementStatus.SATISFIED,
            doctype_hint=explanations.doctype_hint,
            reason_code=None,
            message=None,
        )
        return RequirementsList(requirements=[req], done=True)

    # Not done: pick the reason_code
    # DISTINCT_ISSUER_NEEDED when exactly 1 accepted bill issuer (no gov-id)
    if len(advisory.accepted_issuers) == 1:
        reason_code = DISTINCT_ISSUER_NEEDED
    else:
        reason_code = PROOF_REQUIRED

    req = Requirement(
        item=explanations.item,
        status=RequirementStatus.REQUIRED,
        doctype_hint=explanations.doctype_hint,
        reason_code=reason_code,
        message=explanations.message_for(reason_code),
    )
    return RequirementsList(requirements=[req], done=False)


def explain_rejection(
    entry: LedgerEntry, gate: Gate, *, explanations: SkillExplanations
) -> tuple[str | None, str | None]:
    """Explain a **rejected** LedgerEntry's disposition (M1.9).

    For a rejected entry only: map the gate to a reason_code and relay the
    explanations' message verbatim. Accepted + pending docs carry no explanation.

    Args:
        entry: The LedgerEntry.
        gate: The routing gate from classify_document.
        explanations: The skill-authored explanations (verbatim relay source).

    Returns:
        A tuple of (reason_code, message), or (None, None) for non-rejected.

    Notes:
        - Gate.UNSUPPORTED → (UNSUPPORTED_DOCTYPE, msg)
        - Gate.RESUBMIT → (ILLEGIBLE, msg)
        - Anything else / non-rejected → (None, None)
    """
    if entry.disposition != Disposition.REJECTED:
        return (None, None)

    if gate == Gate.UNSUPPORTED:
        code = UNSUPPORTED_DOCTYPE
    elif gate == Gate.RESUBMIT:
        code = ILLEGIBLE
    else:
        return (None, None)

    return (code, explanations.message_for(code))
