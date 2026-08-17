"""Skill types and loading logic.

The skill registry loads Agent Skills folders (SKILL.md + assets) and is the source
of the dynamic Agent Card (name/description) and process-skill policy (disposition
thresholds, SLA cadence/deadline/max-nudges).

See:
- wiki/bridge-skills.md (Agent Skills format, the two skill kinds, card as discovery)
- ADR-0002 (disposition thresholds: 0.55 resubmit / 0.85 auto-approve)
- docs/lessons-learned.md C1 (SLA: deadline 3 / cadence 2 / max_nudges 2)
"""

import os
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel

__all__ = [
    "SkillKind",
    "DispositionThresholds",
    "SlaPolicy",
    "SkillPolicy",
    "Skill",
    "resolve_default_skills_dir",
    "parse_skill_md",
    "load_skill",
]


class SkillKind(str, Enum):
    """The two kinds of skills (wiki/bridge-skills.md).

    PROCESS: servicer-facing capability (e.g., address-proof) — advertised on the
        Agent Card and carries a policy (thresholds, SLA).
    DOCTYPE: internal extraction target (e.g., gov-id, utility-bill) — not carded,
        no policy.
    """

    PROCESS = "process"
    DOCTYPE = "doctype"


class DispositionThresholds(BaseModel, frozen=True):
    """Disposition confidence thresholds (ADR-0002)."""

    resubmit_below: float = 0.55
    auto_approve_at: float = 0.85


class SlaPolicy(BaseModel, frozen=True):
    """SLA policy for a process skill (lessons-learned.md C1)."""

    deadline: int  # ticks until overdue
    cadence: int  # ticks between nudges
    max_nudges: int  # escalation ladder depth


class SkillPolicy(BaseModel, frozen=True):
    """Process skill policy: disposition thresholds, retry, and SLA."""

    thresholds: DispositionThresholds
    max_resubmissions: int = 3
    sla: SlaPolicy | None = None


class Skill(BaseModel, frozen=True):
    """A loaded Agent Skill (SKILL.md + assets).

    Process skills carry a policy (thresholds, SLA); doctype skills do not.
    """

    name: str
    description: str
    kind: SkillKind
    metadata: dict[str, str]
    body: str = ""
    path: Path
    policy: SkillPolicy | None = None
    candidate_doctypes: tuple[str, ...] = ()

    def asset_path(self, rel: str) -> Path:
        """Resolve an asset path relative to the skill folder.

        Args:
            rel: Relative asset path (e.g., "assets/schema.json").

        Returns:
            Absolute path to the asset.

        Example:
            # M1.6/M1.7 parse schema.json / validation.yaml from asset_path(...)
            schema_path = skill.asset_path(skill.metadata["bridge-schema"])
        """
        return self.path / rel


def resolve_default_skills_dir() -> Path:
    """Resolve the default skills directory.

    Resolution order:
    1. BRIDGE_SKILLS_DIR env var (if set)
    2. Walk up from this file to the first ancestor containing skills/
    3. Fallback to cwd()/skills

    Returns:
        Path to the skills directory.

    Note:
        This is the single documented place bridge/ references the shared repo
        skills/ tree. Env-var seam selection (C3: BRIDGE_SEAM_*) is deferred;
        BRIDGE_SKILLS_DIR is the swap point analogous to the address agent's
        BRIDGE_CARD_URL.
    """
    if "BRIDGE_SKILLS_DIR" in os.environ:
        return Path(os.environ["BRIDGE_SKILLS_DIR"])

    # Walk up from __file__ to the first ancestor containing skills/
    current = Path(__file__).resolve().parent
    while current != current.parent:
        skills_dir = current / "skills"
        if skills_dir.is_dir():
            return skills_dir
        current = current.parent

    # Fallback to cwd()/skills
    return Path.cwd() / "skills"


def parse_skill_md(path: Path) -> tuple[dict, str]:
    """Parse a SKILL.md file into frontmatter and body.

    SKILL.md format: YAML frontmatter fenced by --- ... --- then Markdown body.

    Args:
        path: Path to the SKILL.md file.

    Returns:
        A tuple of (metadata_dict, body).

    Raises:
        ValueError: If the file cannot be parsed or frontmatter is malformed.
    """
    if not path.exists():
        raise ValueError(f"SKILL.md not found: {path}")

    content = path.read_text(encoding="utf-8")

    # Handle no frontmatter case
    if not content.startswith("---\n"):
        return ({}, content)

    # Split on the closing --- fence
    parts = content[4:].split("\n---\n", 1)
    if len(parts) != 2:
        # Malformed frontmatter (no closing fence)
        raise ValueError(f"Malformed frontmatter in {path}: missing closing ---")

    frontmatter_str, body = parts
    try:
        metadata = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML frontmatter in {path}: {e}") from e

    if not isinstance(metadata, dict):
        raise ValueError(f"Frontmatter in {path} must be a dict, got {type(metadata)}")

    return (metadata, body.strip())


def load_skill(folder: Path) -> Skill:
    """Load a skill from an Agent Skills folder.

    Args:
        folder: Path to the skill folder (must contain SKILL.md).

    Returns:
        A Skill instance.

    Raises:
        ValueError: If the skill is malformed or required fields are missing.
    """
    skill_md_path = folder / "SKILL.md"
    metadata, body = parse_skill_md(skill_md_path)

    # Required fields
    name = metadata.get("name")
    if not name:
        raise ValueError(f"Missing required field 'name' in {skill_md_path}")

    description = metadata.get("description", "")

    # bridge-kind determines the skill type
    skill_metadata = metadata.get("metadata", {})
    if not isinstance(skill_metadata, dict):
        raise ValueError(
            f"'metadata' in {skill_md_path} must be a dict, got {type(skill_metadata)}"
        )

    bridge_kind = skill_metadata.get("bridge-kind")
    if not bridge_kind:
        raise ValueError(f"Missing required 'metadata.bridge-kind' in {skill_md_path}")

    try:
        kind = SkillKind(bridge_kind)
    except ValueError as e:
        raise ValueError(f"Invalid bridge-kind '{bridge_kind}' in {skill_md_path}") from e

    # Convert metadata values to strings for uniformity
    skill_metadata_str = {k: str(v) for k, v in skill_metadata.items()}

    # Process skills have policy and candidate doctypes
    policy = None
    candidate_doctypes = ()

    if kind == SkillKind.PROCESS:
        # Load candidate doctypes
        doctypes_str = skill_metadata.get("bridge-candidate-doctypes", "")
        if doctypes_str:
            candidate_doctypes = tuple(doctypes_str.split())

        # Load policy if specified
        policy_path_str = skill_metadata.get("bridge-policy")
        if policy_path_str:
            policy_file = folder / policy_path_str
            if not policy_file.exists():
                raise ValueError(f"Policy file not found: {policy_file}")

            try:
                policy_data = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in {policy_file}: {e}") from e

            # Build SkillPolicy from the YAML
            thresholds_data = policy_data.get("thresholds", {})
            thresholds = DispositionThresholds(
                resubmit_below=thresholds_data.get("resubmit_below", 0.55),
                auto_approve_at=thresholds_data.get("auto_approve_at", 0.85),
            )

            retry_data = policy_data.get("retry", {})
            max_resubmissions = retry_data.get("max_resubmissions", 3)

            sla_data = policy_data.get("sla")
            sla = None
            if sla_data:
                sla = SlaPolicy(
                    deadline=sla_data["deadline"],
                    cadence=sla_data["cadence"],
                    max_nudges=sla_data["max_nudges"],
                )

            policy = SkillPolicy(
                thresholds=thresholds, max_resubmissions=max_resubmissions, sla=sla
            )

    return Skill(
        name=name,
        description=description,
        kind=kind,
        metadata=skill_metadata_str,
        body=body,
        path=folder,
        policy=policy,
        candidate_doctypes=candidate_doctypes,
    )
