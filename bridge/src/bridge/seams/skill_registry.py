"""Skill registry seam: directory of Agent Skills folders.

The skill registry loads Agent Skills folder format (SKILL.md + assets) and is the
source of the dynamic Agent Card (name/description) and process-skill policy
(disposition thresholds, SLA cadence/deadline/max-nudges). See wiki/bridge-seams.md
and M1.3 for the full contract.

CAVEAT: @runtime_checkable Protocols check method presence only, not signatures.
This is the desired behavior for M1.1 conformance smoke tests — real behavior and
signature validation are pinned by the shared suite in M1.2+. Keep every Protocol
method-only (no data attributes) or isinstance will raise/misbehave.

M1.3 defines the Skill/policy aggregate types and how the card/policy are surfaced.
"""

from typing import Protocol, runtime_checkable

__all__ = ["SkillRegistrySeam"]


@runtime_checkable
class SkillRegistrySeam(Protocol):
    """Seam for skill directory and policy loading.

    Local adapter: LocalSkillRegistry (bridge.adapters.local)
    GCP adapter: DatabaseSkillRegistry or GcsSkillRegistry (Sprint 2)

    The registry is the source of the dynamic Agent Card (name/description from
    SKILL.md) and the process-skill policy:
    - Disposition thresholds: 0.55 (resubmit) / 0.85 (auto-approve) per ADR-0002
    - SLA: cadence, deadline, max-nudges (per lessons-learned.md C1)

    Note: The concrete Skill/policy types are defined by M1.3; signatures use
    `object` here as a placeholder.
    """

    async def list_skills(self) -> list[object]:
        """List all available skills.

        # M1.3 defines the Skill type.
        """
        ...

    async def get_skill(self, name: str) -> object | None:
        """Retrieve a skill by name, or None if not found.

        # M1.3 defines the Skill type and how policy is surfaced.
        """
        ...
