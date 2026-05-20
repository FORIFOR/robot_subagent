"""Sub Agent: natural language -> RobotCommand.

Configured to work with any OpenAI-compatible endpoint, including Ollama.

- `OPENAI_BASE_URL` overrides the OpenAI endpoint (e.g. http://localhost:11434/v1).
- `OPENAI_API_KEY` may be a dummy value when pointing at Ollama (the SDK still
  refuses to instantiate the client without one).
- `ROBOT_AGENT_MODEL` picks the model id.

We deliberately do NOT use `output_type=RobotCommand` here: Ollama's
OpenAI-compat layer is unreliable for structured output / tool use, so we ask
the model for JSON and validate it with Pydantic ourselves. This matches the
"安定版" path documented in README.
"""

from __future__ import annotations

import json
import os
import re

from agents import (
    Agent,
    Runner,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)
from openai import AsyncOpenAI

from .prompts import ROBOT_AGENT_INSTRUCTIONS
from .schemas import RobotCommand
from .skills import find_skill, load_skill_registry, render_skill_list

DEFAULT_MODEL = "qwen3:14b"

_JSON_HINT = """\

出力は必ず次のJSONオブジェクトだけにしてください。Markdownのコードフェンスや
前後の説明文は禁止です。

{
  "skill_id": "grab_cube",
  "object": "cube",
  "color": "red",
  "vla_instruction": "Grab the red cube",
  "confidence": 0.9,
  "requires_confirmation": true,
  "executable": true,
  "reason": "登録済みスキルで処理可能です"
}
"""


def configure_llm_client() -> None:
    """Point the Agents SDK at the OpenAI-compatible endpoint in env vars."""
    base_url = os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY", "ollama")
    if base_url:
        client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        set_default_openai_client(client)
        # Ollama only implements /v1/chat/completions, not /v1/responses.
        set_default_openai_api("chat_completions")
        # Avoid Agents SDK trying to ship traces to api.openai.com with the
        # dummy Ollama key (it would 401 on every call).
        set_tracing_disabled(True)


def extract_json(text: str) -> dict:
    """Pull the first {...} object out of a (possibly fenced) model response."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"JSON object not found in model output: {text!r}")
    return json.loads(match.group(0))


def build_robot_agent(model: str | None = None) -> Agent:
    configure_llm_client()
    chosen = model or os.getenv("ROBOT_AGENT_MODEL", DEFAULT_MODEL)
    return Agent(
        name="Robot Command Sub Agent",
        model=chosen,
        instructions=ROBOT_AGENT_INSTRUCTIONS + _JSON_HINT,
    )


def _normalize_color(value: object) -> str | None:
    """Treat empty strings / 'null' / 'none' as missing."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"null", "none", "n/a"}:
        return None
    return s


def postprocess_command(command: RobotCommand) -> RobotCommand:
    """Belt-and-suspenders fixups for small local models.

    A 7-14B Ollama model often returns `executable=false` *only* because the
    user did not specify a color. If the registry says color is optional,
    we override that and rewrite the vla_instruction to the colorless
    template. We also stop pretending color="" is a real value.
    """
    registry = load_skill_registry()
    skill = find_skill(registry, command.skill_id)
    if skill is None:
        return command

    command.color = _normalize_color(command.color)

    if not skill.color_required and command.color is None:
        # Force-execute on the colorless template.
        command.executable = True
        command.requires_confirmation = True
        command.vla_instruction = skill.vla_template.format(object=command.object)
        if command.confidence > 0.85:
            command.confidence = 0.78
        if "色" not in command.reason:
            command.reason = (
                command.reason.rstrip("。 ")
                + "。色指定はありませんが、color_required=false のため実行候補として扱います。"
            )
    elif command.color and skill.vla_template_with_color:
        # If LLM forgot to switch to the colored template, fix it.
        if "{color}" not in command.vla_instruction.replace(command.color, "{color}"):
            command.vla_instruction = skill.vla_template_with_color.format(
                color=command.color, object=command.object
            )

    return command


def make_blocked_command(user_text: str, reason: str) -> RobotCommand:
    """Synthetic 'blocked' command used when the LLM output is unusable."""
    return RobotCommand(
        skill_id="unknown",
        object="unknown",
        color=None,
        vla_instruction="NOOP",
        confidence=0.0,
        requires_confirmation=True,
        executable=False,
        reason=f"{reason}: {user_text}",
    )


_DEFAULTS_FOR_NULLS: dict[str, object] = {
    "skill_id": "unknown",
    "vla_instruction": "NOOP",
    "confidence": 0.0,
    "executable": False,
    "requires_confirmation": True,
    "reason": "ロボット命令として解釈できません",
}
# Note: `object` and `color` stay nullable. Object-less skills (wave_hand,
# move_to_home) legitimately return object=null; coercing to "unknown"
# would make the safety gate reject them on allowed_objects.


def _coerce_nulls(data: dict) -> dict:
    """Fill in safe defaults for fields the LLM left as null/missing.

    `color` is allowed to stay null; everything else has a non-null fallback.
    """
    for key, default in _DEFAULTS_FOR_NULLS.items():
        if data.get(key) is None:
            data[key] = default
    return data


def normalize_command(user_text: str, *, model: str | None = None) -> RobotCommand:
    """Robust LLM call: never raises; non-robot input returns a blocked command."""
    try:
        registry = load_skill_registry()
        skill_text = render_skill_list(registry)

        prompt = f"""\
以下のskill_registryだけを使って、ユーザー命令をRobotCommand JSONへ変換してください。

skill_registry:
{skill_text}

ユーザー命令:
{user_text}

ロボット命令ではない (雑談・挨拶・無関係な発話) 場合は、必ず以下の形で返してください。
{{
  "skill_id": "unknown",
  "object": "unknown",
  "color": null,
  "vla_instruction": "NOOP",
  "confidence": 0.0,
  "requires_confirmation": true,
  "executable": false,
  "reason": "ロボット命令ではありません"
}}

JSONのみを返してください。
"""

        agent = build_robot_agent(model=model)
        result = Runner.run_sync(agent, prompt, max_turns=1)
        raw = result.final_output
        if isinstance(raw, RobotCommand):
            return postprocess_command(raw)
        data = extract_json(str(raw))
        data = _coerce_nulls(data)
        command = RobotCommand.model_validate(data)
        return postprocess_command(command)
    except Exception as e:
        return make_blocked_command(user_text, f"Agent parse failed: {e!r}")
