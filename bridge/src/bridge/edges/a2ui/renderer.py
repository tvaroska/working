"""A2UI reference renderer (demo furniture, not the product) (M1.10).

This is a **reference/demo renderer**, NOT the product. It proves the
content-not-pixels contract (wiki/bridge-a2ui-edge.md) without a real frontend:
a plain-text rendering of the declarative A2uiScreen. Any host renders the same
`A2uiScreen` in its own design system — the frontend is TypeScript/React/MUI,
not this Python text renderer.

The project ships this as demo furniture to validate the declarative shapes,
not as a production UI.

Import discipline: .views only. Never agents. Keep this out of bridge/__init__.py.
"""

from __future__ import annotations

from .views import A2uiScreen

__all__ = ["render_screen"]


def render_screen(screen: A2uiScreen) -> str:
    """Render a declarative A2uiScreen as plain text (demo furniture).

    This is a **reference/demo renderer, not the product**. It proves the
    content-not-pixels contract without a real frontend. Any host renders
    the same declarative A2uiScreen in its own design system.

    Args:
        screen: The declarative A2uiScreen to render.

    Returns:
        A plain-text rendering (multi-line string).

    Notes:
        - Renders sent (id + disposition, plus verbatim message for rejected)
        - Renders accepted summary
        - Renders outstanding list
        - Renders next-action prompt (verbatim)
        - Renders "Done." when screen.status.done
    """
    lines = []
    status = screen.status

    # Sent section
    lines.append("Sent:")
    if not status.sent:
        lines.append("  (none)")
    else:
        for doc in status.sent:
            disposition_str = doc.disposition.value
            doc_line = f"  - {doc.id} ({doc.doctype}): {disposition_str}"
            if doc.message:
                # Verbatim message relay for rejected docs
                doc_line += f" — {doc.message}"
            lines.append(doc_line)

    lines.append("")

    # Accepted section
    lines.append("Accepted:")
    if not status.accepted:
        lines.append("  (none)")
    else:
        for doc in status.accepted:
            lines.append(f"  - {doc.id} ({doc.doctype})")

    lines.append("")

    # Outstanding section
    lines.append("Outstanding:")
    if not status.outstanding:
        lines.append("  (none)")
    else:
        for item in status.outstanding:
            lines.append(f"  - {item}")

    lines.append("")

    # Next section
    if status.next:
        lines.append("Next:")
        lines.append(f"  {status.next}")
        lines.append("")

    # Done marker
    if status.done:
        lines.append("Done.")

    return "\n".join(lines)
