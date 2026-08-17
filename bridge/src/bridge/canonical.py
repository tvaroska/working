"""Issuer canonicalization (sense A) for the classified ledger (M1.5).

Sense-A canonicalization produces the **canonical issuer string** stamped onto each
``LedgerEntry`` (``issuer`` field). It is distinct from ``is_satisfied``'s
distinct-issuer count (sense B), which consumes already-canonical issuers and **does not
re-canonicalize** (see ``agents/src/agents/address/satisfaction.py``).

The normalizer strips corporate suffixes (``Ltd/Inc/LLC/GmbH/...``) but **preserves
"co" / "company"** (docs/lessons-learned A4), handles camelCase fragmentation (testing
the joined last-two tokens for fragmented suffixes like ``GmbH`` → ``Gmb H``), and is
**idempotent** (re-canonicalizing a canonical issuer produces the same result).

**Import discipline (hard invariant):** Uses stdlib ``re`` only — never imports
``agents``, ``contract``, or ``seams``. ``bridge/`` never imports ``agents/``
(guarded by ``bridge/tests/test_no_agents_import.py``). Parity with
``wiki/evals/address/expected.json`` (``issuer_raw`` → ``issuer``) is asserted via
the shared suite (``test_canonical.py``), not via import.

Keep this module out of ``bridge/__init__.py`` (preserves cheap ``import bridge`` +
the no-agents-guard clarity, same rule ``aggregate.py`` and ``ledger.py`` follow).
"""

from __future__ import annotations

import re

__all__ = ["canonicalize_issuer"]

#: Corporate suffix tokens that are stripped during canonicalization.
#: "co" and "company" are **NOT** included (lessons A4).
SUFFIXES = frozenset(
    {
        "ltd",
        "limited",
        "inc",
        "incorporated",
        "llc",
        "gmbh",
        "plc",
        "corp",
        "corporation",
        "llp",
        "lp",
        "ag",
        "sa",
        "nv",
        "bv",
        "pty",
    }
)


def canonicalize_issuer(raw: str | None) -> str | None:
    """Canonicalize a raw issuer name to its normalized form.

    Transforms raw issuer names (``"PowerCo"``, ``"Power Co."``, ``"PowerCo Ltd"``)
    into a canonical lowercase-hyphenated form (``"power-co"``). The algorithm:

    1. Null/empty passthrough: returns ``None`` for ``None`` or whitespace-only input.
    2. Split camelCase into tokens (so ``PowerCo`` → ``Power Co``, and fragmented
       suffixes like ``GmbH`` → ``Gmb H`` can be re-joined).
    3. Tokenize on non-alphanumeric characters.
    4. Strip trailing corporate-suffix tokens using :data:`SUFFIXES`, testing the
       **joined last-two tokens** first (handles ``Gmb`` + ``H`` → ``gmbh``).
    5. Guard against over-stripping (if all tokens would be removed, keep them).
    6. Lowercase remaining tokens and join with ``-``.

    The function is **idempotent**: ``canonicalize_issuer(canonicalize_issuer(x)) ==
    canonicalize_issuer(x)``. Notably, **"co" is not a suffix** and is preserved
    (lessons A4).

    Args:
        raw: The raw issuer name, or ``None``.

    Returns:
        The canonical issuer string (e.g. ``"power-co"``), or ``None`` if the input
        was ``None`` or empty.

    Examples:
        >>> canonicalize_issuer("PowerCo")
        'power-co'
        >>> canonicalize_issuer("Power Co.")
        'power-co'
        >>> canonicalize_issuer("PowerCo Ltd")
        'power-co'
        >>> canonicalize_issuer("AquaUtil")
        'aqua-util'
        >>> canonicalize_issuer("Foo GmbH")
        'foo'
        >>> canonicalize_issuer(None)
        >>> canonicalize_issuer("   ")
    """
    # Step 1: null/empty passthrough
    if raw is None or raw.strip() == "":
        return None

    s = raw.strip()

    # Step 2: split camelCase into tokens (two passes)
    # Pass a: insert space between lowercase/digit and uppercase
    # (PowerCo → Power Co, ...GmbH → ...Gmb H)
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    # Pass b: insert space inside acronym run before a capitalized word
    # (defensive; harmless on the fixtures)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)

    # Step 3: tokenize on non-alphanumeric and drop empty tokens
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", s) if t]

    if not tokens:
        return None

    # Step 4: strip trailing corporate-suffix tokens
    # Test joined last-two tokens first, then single last token, repeat while matching
    original_tokens = tokens.copy()
    while tokens:
        # Test joined last-two tokens (handles fragmented suffixes like Gmb + H → gmbh)
        if len(tokens) >= 2:
            joined = (tokens[-2] + tokens[-1]).lower()
            if joined in SUFFIXES:
                tokens = tokens[:-2]
                continue

        # Test single last token
        if tokens[-1].lower() in SUFFIXES:
            tokens = tokens[:-1]
            continue

        # No match, stop
        break

    # Step 5: guard against over-stripping
    if not tokens:
        tokens = original_tokens

    # Step 6: lowercase and join with hyphen
    return "-".join(t.lower() for t in tokens)
