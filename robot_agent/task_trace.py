"""Evaluate one RobotCommand against an expected skill (Task Trace Mode)."""

from __future__ import annotations

from typing import Optional

from .schemas import (
    RobotCommand,
    SafetyResult,
    Skill,
    SkillRegistry,
    TaskTraceEvaluation,
)
from .skills import find_skill


def _render_expected_instruction(skill: Skill, command: RobotCommand) -> str:
    """Re-render the skill's template using the command's actual slots."""
    if command.color and skill.vla_template_with_color:
        template = skill.vla_template_with_color
    else:
        template = skill.vla_template
    safe = {"color": command.color or "", "object": command.object or ""}
    try:
        rendered = template.format(**safe)
    except KeyError:
        rendered = template
    return " ".join(rendered.split())


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _check_object(expected: Optional[Skill], command: RobotCommand) -> tuple[bool, Optional[str]]:
    if expected is None:
        return False, "expected skill is not in the registry"
    if not expected.object_required:
        return True, None
    if not expected.allowed_objects:
        return True, None
    if command.object in expected.allowed_objects:
        return True, None
    return False, (
        f"object mismatch: expected one of {sorted(expected.allowed_objects)}, "
        f"actual={command.object}"
    )


def _check_instruction(expected: Optional[Skill], command: RobotCommand) -> tuple[bool, Optional[str]]:
    if expected is None:
        return False, "expected skill is not in the registry"
    rendered = _render_expected_instruction(expected, command)
    if _normalize(command.vla_instruction) == _normalize(rendered):
        return True, None
    # Allow colored-instruction even when expected has no color slot, e.g.
    # "Grab the cube" template matched by "Grab the red cube".
    template_prefix = expected.vla_template.split("{", 1)[0].strip()
    if template_prefix and _normalize(command.vla_instruction).startswith(_normalize(template_prefix)):
        # ensure all non-placeholder words from the template still appear
        keywords = [
            w
            for w in expected.vla_template.split()
            if not w.startswith("{") and len(w) >= 3
        ]
        actual = _normalize(command.vla_instruction)
        if all(_normalize(k) in actual for k in keywords):
            return True, None
    return False, (
        f"instruction mismatch: actual={command.vla_instruction!r}, expected≈{rendered!r}"
    )


def evaluate_task_trace(
    command: RobotCommand,
    safety: SafetyResult,
    registry: SkillRegistry,
    expected_skill: str,
) -> TaskTraceEvaluation:
    notes: list[str] = []
    expected = find_skill(registry, expected_skill)

    skill_match = command.skill_id == expected_skill
    if not skill_match:
        notes.append(
            f"skill mismatch: expected={expected_skill}, actual={command.skill_id}"
        )

    object_match, obj_note = _check_object(expected, command)
    if obj_note:
        notes.append(obj_note)

    instruction_ok, instr_note = _check_instruction(expected, command)
    if instr_note:
        notes.append(instr_note)

    executable_ok = bool(command.executable)
    if not executable_ok:
        notes.append("command.executable is false")

    safety_ok = bool(safety.ok)
    if not safety_ok:
        notes.append(f"safety blocked: {safety.reason}")

    checks = [skill_match, object_match, instruction_ok, executable_ok, safety_ok]
    score = sum(1 for x in checks if x) / len(checks)

    return TaskTraceEvaluation(
        expected_skill=expected_skill,
        skill_match=skill_match,
        object_match=object_match,
        instruction_ok=instruction_ok,
        executable_ok=executable_ok,
        safety_ok=safety_ok,
        score=score,
        notes=notes,
    )
