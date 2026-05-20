"""Load, inspect, and edit the skill registry."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from .schemas import Skill, SkillRegistry

DEFAULT_SKILL_PATH = Path("config/skill_registry.yaml")


def load_skill_registry(path: Path = DEFAULT_SKILL_PATH) -> SkillRegistry:
    if not path.exists():
        raise FileNotFoundError(f"Skill registry not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return SkillRegistry.model_validate(data)


def save_skill_registry(
    registry: SkillRegistry, path: Path = DEFAULT_SKILL_PATH
) -> None:
    """Write the registry back to YAML in a deterministic, human-readable shape."""
    payload = {
        "skills": [
            _skill_to_yaml_dict(s) for s in registry.skills
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            payload,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )


def _skill_to_yaml_dict(skill: Skill) -> dict:
    """Drop None / empty optional fields so the YAML stays clean."""
    d = skill.model_dump()
    if d.get("vla_template_with_color") is None:
        d.pop("vla_template_with_color", None)
    if not d.get("examples"):
        d.pop("examples", None)
    if not d.get("aliases"):
        d.pop("aliases", None)
    return d


def render_skill_list(registry: SkillRegistry) -> str:
    """Plain-text dump used inside the agent prompt."""
    lines: list[str] = []
    for skill in registry.skills:
        lines.append(f"- id: {skill.id}")
        lines.append(f"  description: {skill.description}")
        lines.append(f"  color_required: {str(skill.color_required).lower()}")
        lines.append(f"  vla_template: {skill.vla_template}")
        if skill.vla_template_with_color:
            lines.append(f"  vla_template_with_color: {skill.vla_template_with_color}")
        lines.append(f"  allowed_objects: {', '.join(skill.allowed_objects)}")
        lines.append(f"  allowed_colors: {', '.join(skill.allowed_colors)}")
        if skill.aliases:
            lines.append(f"  aliases: {', '.join(skill.aliases)}")
        if skill.examples:
            lines.append("  examples:")
            for ex in skill.examples:
                lines.append(
                    f"    - user: {ex.get('user', '')} -> {ex.get('vla_instruction', '')}"
                )
    return "\n".join(lines)


def find_skill(registry: SkillRegistry, skill_id: str) -> Optional[Skill]:
    for skill in registry.skills:
        if skill.id == skill_id:
            return skill
    return None


def add_skill(registry: SkillRegistry, skill: Skill) -> SkillRegistry:
    """Return a new registry with `skill` appended. Rejects duplicate ids."""
    if find_skill(registry, skill.id) is not None:
        raise ValueError(f"skill_id '{skill.id}' already exists")
    return SkillRegistry(skills=[*registry.skills, skill])


def remove_skill(registry: SkillRegistry, skill_id: str) -> SkillRegistry:
    """Return a new registry with `skill_id` removed. Errors if not found."""
    if find_skill(registry, skill_id) is None:
        raise ValueError(f"skill_id '{skill_id}' not found")
    return SkillRegistry(skills=[s for s in registry.skills if s.id != skill_id])
