"""Trust boundary for the inbound A2A edge — permissive-by-default (A6).

The Bridge's per-party scoping is a known footgun: it is **permissive by default** and
enforced only when a leg is opened with ``strict=True`` (docs/lessons-learned **A6**).
The rationale is back-compat with the header-free client — the M0/S1 consumer sends a
``CollectRequest`` with no caller identity, so an unauthenticated caller must remain a
no-op or every existing round-trip breaks. Tightening this to deny-by-default is a
deliberate, knowing change (a later hardening task), not the default.

Import discipline: imports nothing from ``agents`` (guarded by the no-agents test) and
nothing from the seams/adapters — it is a pure guard over two strings.
"""

from __future__ import annotations

__all__ = ["TrustBoundaryError", "authorize_leg"]


class TrustBoundaryError(Exception):
    """A caller was scoped to a party it is not authorized to act for (strict mode)."""


def authorize_leg(caller: str | None, party: str, *, strict: bool = False) -> None:
    """Authorize a caller to open/continue a leg for ``party`` (A6).

    Permissive by default: an unauthenticated / ``None`` caller is always allowed (the
    header-free client back-compat), and even a mismatched caller is allowed unless
    ``strict=True``. Under ``strict=True`` a caller that does not match ``party`` is
    rejected with :class:`TrustBoundaryError`.

    Args:
        caller: The authenticated caller identity, or ``None`` if unauthenticated.
        party: The party the leg is being opened for (``CollectRequest.party``).
        strict: When True, enforce per-party scoping (deny mismatch). Defaults to
            False (the permissive default — the deliberate footgun).

    Raises:
        TrustBoundaryError: Only when ``strict`` and ``caller`` is set and mismatched.
    """
    # Permissive: an unauthenticated caller is a no-op regardless of strict mode
    # (header-free client back-compat — A6).
    if caller is None:
        return
    # Permissive default: mismatch is allowed unless the leg opts into strict scoping.
    if not strict:
        return
    if caller != party:
        raise TrustBoundaryError(f"caller {caller!r} is not authorized to act for party {party!r}")
