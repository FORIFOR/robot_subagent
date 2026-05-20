"""LLM-free smoke tests."""

from pathlib import Path

import pytest

from robot_agent.safety import safety_check
from robot_agent.schemas import RobotCommand, Skill, SkillRegistry
from robot_agent.skills import (
    add_skill,
    find_skill,
    load_skill_registry,
    remove_skill,
    render_skill_list,
    save_skill_registry,
)

REGISTRY_PATH = Path("config/skill_registry.yaml")


def test_registry_loads():
    reg = load_skill_registry(REGISTRY_PATH)
    assert {s.id for s in reg.skills} >= {"grab_cube", "pick_apple", "place_on_plate"}


def test_render_skill_list_contains_templates():
    reg = load_skill_registry(REGISTRY_PATH)
    text = render_skill_list(reg)
    assert "Grab the {color} cube" in text


def test_safety_blocks_unknown_skill():
    reg = load_skill_registry(REGISTRY_PATH)
    cmd = RobotCommand(
        skill_id="dance",
        object="cube",
        color="red",
        vla_instruction="Dance",
        confidence=0.99,
        requires_confirmation=False,
        executable=True,
        reason="test",
    )
    result = safety_check(cmd, reg)
    assert result.level == "blocked"
    assert not result.ok


def test_safety_blocks_disallowed_color():
    reg = load_skill_registry(REGISTRY_PATH)
    cmd = RobotCommand(
        skill_id="grab_cube",
        object="cube",
        color="purple",
        vla_instruction="Grab the purple cube",
        confidence=0.9,
        requires_confirmation=True,
        executable=True,
        reason="test",
    )
    result = safety_check(cmd, reg)
    assert result.level == "blocked"


def test_safety_passes_normal_command():
    reg = load_skill_registry(REGISTRY_PATH)
    cmd = RobotCommand(
        skill_id="grab_cube",
        object="cube",
        color="red",
        vla_instruction="Grab the red cube",
        confidence=0.92,
        requires_confirmation=True,
        executable=True,
        reason="ok",
    )
    result = safety_check(cmd, reg)
    assert result.ok
    assert result.level == "needs_confirmation"


def test_safety_blocks_dangerous_words():
    reg = load_skill_registry(REGISTRY_PATH)
    cmd = RobotCommand(
        skill_id="grab_cube",
        object="cube",
        color="red",
        vla_instruction="Grab the red cube",
        confidence=0.95,
        requires_confirmation=False,
        executable=True,
        reason="人の手を避ける",
    )
    result = safety_check(cmd, reg)
    assert result.level == "blocked"


def test_find_skill():
    reg = load_skill_registry(REGISTRY_PATH)
    assert find_skill(reg, "grab_cube") is not None
    assert find_skill(reg, "nonexistent") is None


def _new_skill(skill_id: str = "move_to_home") -> Skill:
    return Skill(
        id=skill_id,
        description="ホームに戻る",
        object_required=False,
        color_required=False,
        vla_template="Move the arm to the home position",
        allowed_objects=[],
        allowed_colors=[],
    )


def _seed_registry_without_move_to_home(tmp_path) -> tuple[Path, SkillRegistry]:
    """Write a tmp registry that mirrors the live one but drops move_to_home."""
    src = load_skill_registry(REGISTRY_PATH)
    seed = SkillRegistry(skills=[s for s in src.skills if s.id != "move_to_home"])
    tmp_yaml = tmp_path / "skill_registry.yaml"
    save_skill_registry(seed, tmp_yaml)
    return tmp_yaml, seed


def test_add_and_remove_skill_roundtrip(tmp_path):
    tmp_yaml, seed = _seed_registry_without_move_to_home(tmp_path)

    reg = load_skill_registry(tmp_yaml)
    added = add_skill(reg, _new_skill())
    save_skill_registry(added, tmp_yaml)

    reloaded = load_skill_registry(tmp_yaml)
    assert find_skill(reloaded, "move_to_home") is not None

    pruned = remove_skill(reloaded, "move_to_home")
    save_skill_registry(pruned, tmp_yaml)

    final = load_skill_registry(tmp_yaml)
    assert find_skill(final, "move_to_home") is None
    assert {s.id for s in final.skills} == {s.id for s in seed.skills}


def test_add_skill_rejects_duplicate():
    reg = load_skill_registry(REGISTRY_PATH)
    with pytest.raises(ValueError, match="already exists"):
        add_skill(reg, _new_skill(skill_id="grab_cube"))


def test_remove_skill_errors_when_missing():
    reg = load_skill_registry(REGISTRY_PATH)
    with pytest.raises(ValueError, match="not found"):
        remove_skill(reg, "does_not_exist")


def test_wave_hand_registered():
    reg = load_skill_registry(REGISTRY_PATH)
    wave = find_skill(reg, "wave_hand")
    assert wave is not None
    assert wave.object_required is False
    assert "ばいばい" in wave.aliases
    assert wave.vla_template == "Wave your hand"


def test_safety_allows_wave_hand_without_object():
    reg = load_skill_registry(REGISTRY_PATH)
    cmd = RobotCommand(
        skill_id="wave_hand",
        object=None,
        color=None,
        vla_instruction="Wave your hand",
        confidence=0.9,
        requires_confirmation=True,
        executable=True,
        reason="ばいばいはwave_handに対応",
    )
    result = safety_check(cmd, reg)
    assert result.ok
    assert result.level == "needs_confirmation"


def test_safety_blocks_unknown_skill_marker():
    """Chitchat / non-robot input flows through as skill_id='unknown'."""
    reg = load_skill_registry(REGISTRY_PATH)
    cmd = RobotCommand(
        skill_id="unknown",
        object="unknown",
        color=None,
        vla_instruction="NOOP",
        confidence=0.0,
        requires_confirmation=True,
        executable=False,
        reason="ロボット命令ではありません",
    )
    result = safety_check(cmd, reg)
    assert result.level == "blocked"
    assert not result.ok


def test_make_blocked_command_is_safe():
    from robot_agent.agent import make_blocked_command

    cmd = make_blocked_command("ばいばい", "Agent parse failed: KeyError")
    reg = load_skill_registry(REGISTRY_PATH)
    assert cmd.executable is False
    assert cmd.skill_id == "unknown"
    assert safety_check(cmd, reg).level == "blocked"


def test_safety_passes_object_less_skill(tmp_path):
    """An object_required=false skill should not get blocked on object check."""
    tmp_yaml, _ = _seed_registry_without_move_to_home(tmp_path)
    reg = load_skill_registry(tmp_yaml)
    reg = add_skill(reg, _new_skill())

    cmd = RobotCommand(
        skill_id="move_to_home",
        object="none",
        color=None,
        vla_instruction="Move the arm to the home position",
        confidence=0.9,
        requires_confirmation=True,
        executable=True,
        reason="ok",
    )
    result = safety_check(cmd, reg)
    assert result.ok
    assert result.level == "needs_confirmation"
