"""Local skill registry adapter (skeleton — M1.3 fills in behavior).

In-memory skill registry for the local development environment. Loads Agent Skills
folders and provides the dynamic Agent Card and process-skill policy. Satisfies the
SkillRegistrySeam protocol. Real behavior lands in M1.3.
"""

__all__ = ["LocalSkillRegistry"]


class LocalSkillRegistry:
    """Local (directory-backed) skill registry adapter.

    Skeleton conforming to SkillRegistrySeam. Methods raise NotImplementedError
    until M1.3 implements the real Agent Skills folder loading + policy logic.
    """

    async def list_skills(self) -> list[object]:
        """List all available skills."""
        raise NotImplementedError("M1.3: skill directory loading")

    async def get_skill(self, name: str) -> object | None:
        """Retrieve a skill by name, or None if not found."""
        raise NotImplementedError("M1.3: skill directory loading + policy")
