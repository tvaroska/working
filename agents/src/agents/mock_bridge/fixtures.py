"""Fixture loading and turn construction for the mock Bridge.

This module loads eval data from wiki/evals/address/expected.json and builds
ExchangeTurn responses for the mock server.
"""

import json
import os
from pathlib import Path

from contract import CollectionStatus, Disposition, ExchangeTurn, Extraction, LedgerEntry


def load_gov_id_clean_entry(evals_path: Path | None = None) -> LedgerEntry:
    """Load the gov-id-clean entry from the address evals fixture.

    Args:
        evals_path: Explicit path to expected.json; if None, reads from
            ADDRESS_EVALS_PATH env var or falls back to
            repo_root/wiki/evals/address/expected.json.

    Returns:
        The gov-id-clean LedgerEntry.

    Raises:
        FileNotFoundError: If the fixture file doesn't exist.
        ValueError: If the gov-id-clean entry is not found in the fixture.

    Note:
        The repo-root resolution (parents[4]) is a local-dev convenience; a
        packaged/installed layout would need packaged data (out of scope for M0).
    """
    if evals_path is None:
        evals_path_str = os.environ.get("ADDRESS_EVALS_PATH")
        if evals_path_str:
            evals_path = Path(evals_path_str)
        else:
            # Resolve repo root from this file: parents[4] == /home/boris/working
            repo_root = Path(__file__).resolve().parents[4]
            evals_path = repo_root / "wiki/evals/address/expected.json"

    with open(evals_path) as f:
        data = json.load(f)

    for entry in data.get("documents", []):
        if entry["id"] == "gov-id-clean":
            # The raw eval entry has extra keys (issuer_raw, expected_disposition,
            # expected_gate, artifact, synthetic, note) that fail LedgerEntry's
            # extra="forbid". Build LedgerEntry explicitly:
            ext = Extraction.model_validate(entry["extraction"])
            le = LedgerEntry(
                id=entry["id"],
                doctype=entry["doctype"],
                issuer=entry["issuer"],
                disposition=Disposition(entry["expected_disposition"]),
                extraction=ext,
            )
            return le

    raise ValueError("gov-id-clean entry not found in the fixture")


def build_exchange_turn(context_id: str, ledger_entry: LedgerEntry) -> ExchangeTurn:
    """Build an ExchangeTurn wrapping one ledger entry.

    Args:
        context_id: The A2A context_id to stamp on the turn.
        ledger_entry: The LedgerEntry to include in the ledger.

    Returns:
        An ExchangeTurn with terminal=True and the single ledger entry.
    """
    return ExchangeTurn(
        context_id=context_id,
        status=CollectionStatus(
            ledger=[ledger_entry],
            outstanding=[],
            terminal=True,
        ),
    )
