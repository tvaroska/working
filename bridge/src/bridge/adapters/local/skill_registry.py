"""Local skill registry adapter.

Directory-backed skill registry for the local development environment. Loads Agent
Skills folders (SKILL.md + assets), provides the dynamic Agent Card, and exposes
process-skill policy (disposition thresholds, SLA). Satisfies the SkillRegistrySeam
protocol.

See bridge/src/bridge/skills.py for the Skill/SkillPolicy types and loading logic.
"""

from pathlib import Path

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from a2a.utils.constants import TransportProtocol

from bridge.skills import Skill, SkillKind, load_skill, resolve_default_skills_dir

__all__ = ["LocalSkillRegistry"]


class LocalSkillRegistry:
    """Local (directory-backed) skill registry adapter.

    Loads Agent Skills folders at construction and caches them. The registry is the
    source of the dynamic Agent Card (process skills advertised as AgentSkill entries)
    and the process-skill policy (disposition thresholds, SLA).

    Missing/empty root yields an empty registry (no raise); a malformed *present*
    skill fails loud at construction.
    """

    def __init__(self, root: Path | str | None = None):
        """Initialize the registry and load skills from the given directory.

        Args:
            root: Path to the skills directory. Defaults to resolve_default_skills_dir()
                (BRIDGE_SKILLS_DIR env var, else walk up to repo skills/, else cwd/skills).
        """
        self.root = Path(root) if root else resolve_default_skills_dir()
        self._skills: dict[str, Skill] = {}

        # Load skills if the root exists
        if not self.root.exists() or not self.root.is_dir():
            # Empty/missing root → empty registry (no raise)
            return

        # Scan immediate subdirectories for SKILL.md
        for subdir in self.root.iterdir():
            if not subdir.is_dir():
                continue

            skill_md = subdir / "SKILL.md"
            if not skill_md.exists():
                # Not a skill folder, skip
                continue

            # Load the skill (will raise on malformed present skill)
            skill = load_skill(subdir)
            self._skills[skill.name] = skill

    async def list_skills(self) -> list[Skill]:
        """List all available skills.

        Returns:
            List of Skill instances, sorted by name for deterministic ordering.
        """
        return sorted(self._skills.values(), key=lambda s: s.name)

    async def get_skill(self, name: str) -> Skill | None:
        """Retrieve a skill by name, or None if not found.

        Args:
            name: The skill name.

        Returns:
            The Skill instance, or None if not found.
        """
        return self._skills.get(name)

    def agent_skills(self) -> list[AgentSkill]:
        """Generate AgentSkill entries for the Agent Card.

        Only PROCESS skills are advertised on the card (servicer-facing capabilities).
        DOCTYPE skills are internal to extraction and are not carded.

        Returns:
            List of AgentSkill instances, one per process skill.
        """
        skills = []
        for skill in sorted(self._skills.values(), key=lambda s: s.name):
            if skill.kind != SkillKind.PROCESS:
                continue

            # Title-case the skill name for display
            title = skill.name.replace("-", " ").title()

            skills.append(
                AgentSkill(
                    id=skill.name,
                    name=title,
                    description=skill.description,
                    tags=[skill.name],
                    input_modes=["application/json"],
                    output_modes=["application/json"],
                )
            )

        return skills

    def build_agent_card(
        self,
        *,
        base_url: str,
        version: str = "0.0.0",
        capabilities: AgentCapabilities | None = None,
    ) -> AgentCard:
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
            An AgentCard with a JSONRPC interface and the registry's process skills.
        """
        process_skills = self.agent_skills()

        # Default name/description
        name = "A2A Document Bridge"
        if len(process_skills) == 1:
            description = process_skills[0].description
        else:
            skill_names = ", ".join(s.id for s in process_skills)
            description = f"Document mediation services: {skill_names}"

        # Default capabilities
        if capabilities is None:
            capabilities = AgentCapabilities(
                streaming=True,
                push_notifications=False,
            )

        return AgentCard(
            name=name,
            description=description,
            version=version,
            supported_interfaces=[
                AgentInterface(
                    url=f"{base_url}/",
                    protocol_binding=TransportProtocol.JSONRPC.value,
                    protocol_version="1.0",
                )
            ],
            capabilities=capabilities,
            default_input_modes=["application/json"],
            default_output_modes=["application/json"],
            skills=process_skills,
        )
