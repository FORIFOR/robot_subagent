"""Safety gate between the sub-agent and the robot.

Levels:
  - safe                : ok to execute now
  - needs_confirmation  : ok, but only after explicit user 'y'
  - blocked             : do not execute even with confirmation
"""

from __future__ import annotations

from .schemas import RobotCommand, SafetyResult, SkillRegistry
from .skills import find_skill

BLOCKED_WORDS = [
    "人",
    "顔",
    "壊",
    "投げ",
    "ぶつけ",
    "倒せ",
    "危険",
]

CONFIDENCE_FLOOR = 0.65


def safety_check(command: RobotCommand, registry: SkillRegistry) -> SafetyResult:
    if command.skill_id == "unknown" or command.vla_instruction == "NOOP":
        return SafetyResult(
            ok=False,
            level="blocked",
            reason=command.reason or "ロボット命令ではないため実行しません",
        )

    skill = find_skill(registry, command.skill_id)

    if skill is None:
        return SafetyResult(
            ok=False,
            level="blocked",
            reason=f"未登録のskill_idです: {command.skill_id}",
        )

    if skill.object_required and not command.object:
        return SafetyResult(
            ok=False,
            level="blocked",
            reason=f"{command.skill_id} はobject指定が必須です",
        )

    if (
        command.object
        and skill.allowed_objects
        and command.object not in skill.allowed_objects
    ):
        return SafetyResult(
            ok=False,
            level="blocked",
            reason=f"objectが許可されていません: {command.object}",
        )

    if skill.color_required and not command.color:
        return SafetyResult(
            ok=False,
            level="blocked",
            reason=f"{command.skill_id} は色指定が必須です",
        )

    if command.color and command.color not in skill.allowed_colors:
        return SafetyResult(
            ok=False,
            level="blocked",
            reason=f"colorが許可されていません: {command.color}",
        )

    text = f"{command.vla_instruction} {command.reason}"
    if any(word in text for word in BLOCKED_WORDS):
        return SafetyResult(
            ok=False,
            level="blocked",
            reason="危険または未対応の可能性がある語が含まれています",
        )

    if not command.executable:
        return SafetyResult(
            ok=False,
            level="blocked",
            reason="Agentが実行不可と判定しました",
        )

    if command.confidence < CONFIDENCE_FLOOR:
        return SafetyResult(
            ok=True,
            level="needs_confirmation",
            reason=f"confidenceが低いため確認が必要です: {command.confidence:.2f}",
        )

    if command.requires_confirmation:
        return SafetyResult(
            ok=True,
            level="needs_confirmation",
            reason="実行可能ですが、実機操作のため確認が必要です",
        )

    return SafetyResult(
        ok=True,
        level="safe",
        reason="実行可能です",
    )
