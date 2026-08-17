"""Skill registry tests (M1.3).

Tests the LocalSkillRegistry adapter and the Skill/SkillPolicy loading logic:
1. Isolated parsing (tmp dir, minimal fixtures)
2. Real demo tree (lock C1/ADR-0002 values)
3. Agent Card generation
"""

from pathlib import Path

import pytest

from bridge.adapters.local.skill_registry import LocalSkillRegistry
from bridge.skills import (
    Skill,
    SkillKind,
    load_skill,
    parse_skill_md,
    resolve_default_skills_dir,
)

# Isolated parsing tests (tmp dir fixtures)


def test_parse_skill_md_with_frontmatter(tmp_path):
    """Verify parse_skill_md extracts YAML frontmatter and Markdown body."""
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text(
        """\
---
name: test-skill
description: A test skill
metadata:
  bridge-kind: process
---

This is the body.
"""
    )

    metadata, body = parse_skill_md(skill_md)
    assert metadata["name"] == "test-skill"
    assert metadata["description"] == "A test skill"
    assert metadata["metadata"]["bridge-kind"] == "process"
    assert body == "This is the body."


def test_parse_skill_md_no_frontmatter(tmp_path):
    """Verify parse_skill_md handles files without frontmatter."""
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("Just a body, no frontmatter.")

    metadata, body = parse_skill_md(skill_md)
    assert metadata == {}
    assert body == "Just a body, no frontmatter."


def test_parse_skill_md_malformed_frontmatter(tmp_path):
    """Verify parse_skill_md raises on malformed frontmatter."""
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("---\nname: test\n")  # No closing ---

    with pytest.raises(ValueError, match="missing closing ---"):
        parse_skill_md(skill_md)


def test_load_skill_process(tmp_path):
    """Verify load_skill loads a process skill with policy."""
    skill_dir = tmp_path / "test-process"
    skill_dir.mkdir()

    (skill_dir / "SKILL.md").write_text(
        """\
---
name: test-process
description: A process skill
metadata:
  bridge-kind: process
  bridge-candidate-doctypes: "doc-a doc-b"
  bridge-policy: assets/policy.yaml
---

Body text.
"""
    )

    assets_dir = skill_dir / "assets"
    assets_dir.mkdir()
    (assets_dir / "policy.yaml").write_text(
        """\
thresholds:
  resubmit_below: 0.6
  auto_approve_at: 0.9
retry:
  max_resubmissions: 2
sla:
  deadline: 5
  cadence: 3
  max_nudges: 1
"""
    )

    skill = load_skill(skill_dir)
    assert skill.name == "test-process"
    assert skill.kind == SkillKind.PROCESS
    assert skill.candidate_doctypes == ("doc-a", "doc-b")
    assert skill.policy is not None
    assert skill.policy.thresholds.resubmit_below == 0.6
    assert skill.policy.thresholds.auto_approve_at == 0.9
    assert skill.policy.max_resubmissions == 2
    assert skill.policy.sla is not None
    assert skill.policy.sla.deadline == 5
    assert skill.policy.sla.cadence == 3
    assert skill.policy.sla.max_nudges == 1


def test_load_skill_doctype(tmp_path):
    """Verify load_skill loads a doctype skill without policy."""
    skill_dir = tmp_path / "test-doctype"
    skill_dir.mkdir()

    (skill_dir / "SKILL.md").write_text(
        """\
---
name: test-doctype
description: A doctype skill
metadata:
  bridge-kind: doctype
  bridge-extraction-engine: gemini
  bridge-schema: assets/schema.json
---

Doctype body.
"""
    )

    skill = load_skill(skill_dir)
    assert skill.name == "test-doctype"
    assert skill.kind == SkillKind.DOCTYPE
    assert skill.policy is None
    assert skill.candidate_doctypes == ()
    assert skill.metadata["bridge-extraction-engine"] == "gemini"
    assert skill.metadata["bridge-schema"] == "assets/schema.json"


def test_load_skill_missing_name(tmp_path):
    """Verify load_skill raises if 'name' is missing."""
    skill_dir = tmp_path / "bad-skill"
    skill_dir.mkdir()

    (skill_dir / "SKILL.md").write_text(
        """\
---
description: Missing name
metadata:
  bridge-kind: process
---
"""
    )

    with pytest.raises(ValueError, match="Missing required field 'name'"):
        load_skill(skill_dir)


def test_load_skill_missing_kind(tmp_path):
    """Verify load_skill raises if 'metadata.bridge-kind' is missing."""
    skill_dir = tmp_path / "bad-skill"
    skill_dir.mkdir()

    (skill_dir / "SKILL.md").write_text(
        """\
---
name: bad-skill
metadata:
  version: "1.0"
---
"""
    )

    with pytest.raises(ValueError, match="Missing required 'metadata.bridge-kind'"):
        load_skill(skill_dir)


def test_skill_asset_path():
    """Verify Skill.asset_path resolves relative paths."""
    skill = Skill(
        name="test",
        description="",
        kind=SkillKind.PROCESS,
        metadata={},
        path=Path("/skills/test"),
        policy=None,
    )

    assert skill.asset_path("assets/schema.json") == Path("/skills/test/assets/schema.json")


@pytest.mark.anyio
async def test_local_registry_empty_root(tmp_path):
    """Verify LocalSkillRegistry handles an empty root (no raise)."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    registry = LocalSkillRegistry(root=empty_dir)
    skills = await registry.list_skills()
    assert skills == []

    skill = await registry.get_skill("nonexistent")
    assert skill is None


@pytest.mark.anyio
async def test_local_registry_missing_root(tmp_path):
    """Verify LocalSkillRegistry handles a missing root (no raise)."""
    missing_dir = tmp_path / "nonexistent"

    registry = LocalSkillRegistry(root=missing_dir)
    skills = await registry.list_skills()
    assert skills == []


@pytest.mark.anyio
async def test_local_registry_skips_non_skill_dirs(tmp_path):
    """Verify LocalSkillRegistry skips directories without SKILL.md."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Create a directory without SKILL.md
    (skills_dir / "not-a-skill").mkdir()
    (skills_dir / "not-a-skill" / "README.md").write_text("Not a skill")

    # Create a valid skill
    skill_dir = skills_dir / "valid-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """\
---
name: valid-skill
description: Valid
metadata:
  bridge-kind: process
---
"""
    )

    registry = LocalSkillRegistry(root=skills_dir)
    skills = await registry.list_skills()
    assert len(skills) == 1
    assert skills[0].name == "valid-skill"


@pytest.mark.anyio
async def test_local_registry_list_skills_deterministic_order(tmp_path):
    """Verify list_skills returns skills in deterministic (sorted) order."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    for name in ["zebra", "alpha", "mike"]:
        skill_dir = skills_dir / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"""\
---
name: {name}
description: "{name} skill"
metadata:
  bridge-kind: process
---
"""
        )

    registry = LocalSkillRegistry(root=skills_dir)
    skills = await registry.list_skills()
    assert [s.name for s in skills] == ["alpha", "mike", "zebra"]


@pytest.mark.anyio
async def test_local_registry_get_skill(tmp_path):
    """Verify get_skill retrieves a skill by name."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    skill_dir = skills_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """\
---
name: test-skill
description: Test
metadata:
  bridge-kind: process
---
"""
    )

    registry = LocalSkillRegistry(root=skills_dir)
    skill = await registry.get_skill("test-skill")
    assert skill is not None
    assert skill.name == "test-skill"

    unknown = await registry.get_skill("unknown")
    assert unknown is None


# Real demo tree tests (lock C1/ADR-0002 values)


@pytest.mark.anyio
async def test_real_demo_tree_address_proof():
    """Verify address-proof loads with the correct ADR-0002 + C1 values."""
    # Resolve the repo skills/ directory
    skills_dir = resolve_default_skills_dir()

    registry = LocalSkillRegistry(root=skills_dir)
    skill = await registry.get_skill("address-proof")

    assert skill is not None
    assert skill.name == "address-proof"
    assert skill.kind == SkillKind.PROCESS
    assert skill.candidate_doctypes == ("gov-id", "utility-bill")

    # Verify ADR-0002 thresholds
    assert skill.policy is not None
    assert skill.policy.thresholds.resubmit_below == 0.55
    assert skill.policy.thresholds.auto_approve_at == 0.85

    # Verify C1 SLA values
    assert skill.policy.sla is not None
    assert skill.policy.sla.deadline == 3
    assert skill.policy.sla.cadence == 2
    assert skill.policy.sla.max_nudges == 2

    # Verify retry
    assert skill.policy.max_resubmissions == 3


@pytest.mark.anyio
async def test_real_demo_tree_gov_id():
    """Verify gov-id loads as a DOCTYPE skill."""
    skills_dir = resolve_default_skills_dir()

    registry = LocalSkillRegistry(root=skills_dir)
    skill = await registry.get_skill("gov-id")

    assert skill is not None
    assert skill.name == "gov-id"
    assert skill.kind == SkillKind.DOCTYPE
    assert skill.policy is None
    assert skill.candidate_doctypes == ()
    assert skill.metadata["bridge-extraction-engine"] == "gemini"
    assert skill.metadata["bridge-schema"] == "assets/schema.json"


@pytest.mark.anyio
async def test_real_demo_tree_utility_bill():
    """Verify utility-bill loads as a DOCTYPE skill."""
    skills_dir = resolve_default_skills_dir()

    registry = LocalSkillRegistry(root=skills_dir)
    skill = await registry.get_skill("utility-bill")

    assert skill is not None
    assert skill.name == "utility-bill"
    assert skill.kind == SkillKind.DOCTYPE
    assert skill.policy is None


# Agent Card generation tests


def test_agent_skills_only_process_skills(tmp_path):
    """Verify agent_skills includes only PROCESS skills, not DOCTYPE."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Create a process skill
    process_dir = skills_dir / "process-skill"
    process_dir.mkdir()
    (process_dir / "SKILL.md").write_text(
        """\
---
name: process-skill
description: A process skill for testing
metadata:
  bridge-kind: process
---
"""
    )

    # Create a doctype skill
    doctype_dir = skills_dir / "doctype-skill"
    doctype_dir.mkdir()
    (doctype_dir / "SKILL.md").write_text(
        """\
---
name: doctype-skill
description: A doctype skill
metadata:
  bridge-kind: doctype
---
"""
    )

    registry = LocalSkillRegistry(root=skills_dir)
    agent_skills = registry.agent_skills()

    # Only the process skill should be included
    assert len(agent_skills) == 1
    assert agent_skills[0].id == "process-skill"
    assert agent_skills[0].name == "Process Skill"
    assert agent_skills[0].description == "A process skill for testing"
    assert agent_skills[0].tags == ["process-skill"]
    assert agent_skills[0].input_modes == ["application/json"]
    assert agent_skills[0].output_modes == ["application/json"]


def test_build_agent_card_single_skill(tmp_path):
    """Verify build_agent_card for a registry with one process skill."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    skill_dir = skills_dir / "solo-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """\
---
name: solo-skill
description: The one and only skill
metadata:
  bridge-kind: process
---
"""
    )

    registry = LocalSkillRegistry(root=skills_dir)
    card = registry.build_agent_card(base_url="http://localhost:8080")

    assert card.name == "A2A Document Bridge"
    assert card.description == "The one and only skill"
    assert card.version == "0.0.0"
    assert len(card.skills) == 1
    assert card.skills[0].id == "solo-skill"

    # Verify interface
    assert len(card.supported_interfaces) == 1
    interface = card.supported_interfaces[0]
    assert interface.url == "http://localhost:8080/"
    assert interface.protocol_binding == "JSONRPC"
    assert interface.protocol_version == "1.0"

    # Verify capabilities
    assert card.capabilities.streaming is True
    assert card.capabilities.push_notifications is False


def test_build_agent_card_multiple_skills(tmp_path):
    """Verify build_agent_card for a registry with multiple process skills."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    for name in ["skill-a", "skill-b"]:
        skill_dir = skills_dir / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"""\
---
name: {name}
description: Skill {name}
metadata:
  bridge-kind: process
---
"""
        )

    registry = LocalSkillRegistry(root=skills_dir)
    card = registry.build_agent_card(base_url="http://localhost:8080")

    assert card.name == "A2A Document Bridge"
    assert "skill-a, skill-b" in card.description
    assert len(card.skills) == 2


@pytest.mark.anyio
async def test_real_demo_tree_agent_card():
    """Verify the real demo tree generates a card with address-proof."""
    skills_dir = resolve_default_skills_dir()

    registry = LocalSkillRegistry(root=skills_dir)
    agent_skills = registry.agent_skills()

    # address-proof should be present
    address_proof = next((s for s in agent_skills if s.id == "address-proof"), None)
    assert address_proof is not None
    assert address_proof.name == "Address Proof"

    # Doctype skills should NOT be present
    assert not any(s.id == "gov-id" for s in agent_skills)
    assert not any(s.id == "utility-bill" for s in agent_skills)

    # Build the card
    card = registry.build_agent_card(base_url="http://test")
    assert card.name == "A2A Document Bridge"
    assert card.description  # Non-empty
    assert len(card.skills) >= 1
    assert any(s.id == "address-proof" for s in card.skills)
