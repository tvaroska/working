"""Fixture loading and turn construction for the mock Bridge.

This module loads eval data from wiki/evals/address/expected.json and builds
ExchangeTurn responses for the mock server.
"""

import json
import os
from pathlib import Path

from contract import CollectionStatus, Disposition, ExchangeTurn, Extraction, LedgerEntry


def _resolve_evals_path(evals_path: Path | None) -> Path:
    """Resolve the path to expected.json.

    Args:
        evals_path: Explicit path to expected.json; if None, reads from
            ADDRESS_EVALS_PATH env var or falls back to
            repo_root/wiki/evals/address/expected.json.

    Returns:
        Path to expected.json.

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
    return evals_path


def load_entry(entry_id: str, evals_path: Path | None = None) -> LedgerEntry:
    """Load any entry from the address evals fixture.

    Args:
        entry_id: The id of the entry to load (e.g., "gov-id-clean",
            "bill-powerco-clean", "bill-aquautil-clean").
        evals_path: Explicit path to expected.json; if None, reads from
            ADDRESS_EVALS_PATH env var or falls back to
            repo_root/wiki/evals/address/expected.json.

    Returns:
        The requested LedgerEntry.

    Raises:
        FileNotFoundError: If the fixture file doesn't exist.
        ValueError: If the entry is not found in the fixture.

    Note:
        The raw eval entry has extra keys (issuer_raw, expected_disposition,
        expected_gate, artifact, synthetic, note) that fail LedgerEntry's
        extra="forbid". This function maps explicitly to the LedgerEntry fields.
    """
    evals_path = _resolve_evals_path(evals_path)

    with open(evals_path) as f:
        data = json.load(f)

    for entry in data.get("documents", []):
        if entry["id"] == entry_id:
            # The raw eval entry has extra keys that fail LedgerEntry's
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

    raise ValueError(f"{entry_id} entry not found in the fixture")


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
        Reimplemented as load_entry("gov-id-clean", evals_path) for back-compat.
    """
    return load_entry("gov-id-clean", evals_path)


def build_exchange_turn(
    context_id: str,
    ledger: LedgerEntry | list[LedgerEntry],
    *,
    terminal: bool = True,
    outstanding: list[str] | None = None,
) -> ExchangeTurn:
    """Build an ExchangeTurn wrapping ledger entries.

    Args:
        context_id: The A2A context_id to stamp on the turn.
        ledger: A single LedgerEntry or a list of LedgerEntry to include.
        terminal: Whether this turn is terminal (default True).
        outstanding: Outstanding doctype refs (default []).

    Returns:
        An ExchangeTurn with the specified ledger and flags.

    Notes:
        Back-compatible with the original single-entry signature:
        build_exchange_turn("ctx-1", entry) still works.
    """
    if outstanding is None:
        outstanding = []

    # Normalize ledger to a list
    ledger_list = [ledger] if isinstance(ledger, LedgerEntry) else ledger

    return ExchangeTurn(
        context_id=context_id,
        status=CollectionStatus(
            ledger=ledger_list,
            outstanding=outstanding,
            terminal=terminal,
        ),
    )
