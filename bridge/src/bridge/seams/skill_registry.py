"""Skill registry seam: directory of Agent Skills folders.

The skill registry loads Agent Skills folder format (SKILL.md + assets) and is the
source of the dynamic Agent Card (name/description) and process-skill policy
(disposition thresholds, SLA cadence/deadline/max-nudges). See wiki/bridge-seams.md
and M1.3 for the full contract.

CAVEAT: @runtime_checkable Protocols check method presence only, not signatures.
This is the desired behavior for M1.1 conformance smoke tests — real behavior and
signature validation are pinned by the shared suite in M1.2+. Keep every Protocol
method-only (no data attributes) or isinstance will raise/misbehave.

M1.3 defines the Skill/SkillPolicy types (bridge.skills) and how the card/policy are
surfaced (the registry *is* the card source — agent_skills/build_agent_card methods).
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from a2a.types import AgentCapabilities, AgentCard, AgentSkill

    from bridge.skills import Skill

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

    The concrete Skill/SkillPolicy types are defined in bridge.skills (M1.3).
    """

    async def list_skills(self) -> list["Skill"]:
        """List all available skills.

        Returns:
            List of Skill instances (bridge.skills.Skill).
        """
        ...

    async def get_skill(self, name: str) -> "Skill | None":
        """Retrieve a skill by name, or None if not found.

        Args:
            name: The skill name.

        Returns:
            The Skill instance (bridge.skills.Skill), or None if not found.
        """
        ...

    def agent_skills(self) -> list["AgentSkill"]:
        """Generate AgentSkill entries for the Agent Card.

        Only PROCESS skills are advertised (servicer-facing capabilities). DOCTYPE
        skills are internal to extraction and are not carded.

        Returns:
            List of a2a.types.AgentSkill instances, one per process skill.
        """
        ...

    def build_agent_card(
        self,
        *,
        base_url: str,
        version: str = "0.0.0",
        capabilities: "AgentCapabilities | None" = None,
    ) -> "AgentCard":
        """Build the Agent Card from the registry's process skills.

        The card's name/description derive from the registry (if exactly one process
        skill, reuse its description; otherwise summarize the advertised skills).
        Interface URL/capabilities/version are edge concerns (args with defaults).

        Args:
            base_url: The externally reachable base URL (e.g., http://127.0.0.1:8080).
            version: The card version. Defaults to "0.0.0".
            capabilities: Agent capabilities. Defaults to AgentCapabilities(
                streaming=True, push_notifications=False).

        Returns:
            An a2a.types.AgentCard with a JSONRPC interface and the registry's skills.
        """
        ...
