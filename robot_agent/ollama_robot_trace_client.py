"""Streaming Ollama /api/chat for Task Trace Mode.

Bypasses the OpenAI Agents SDK so we can:
  - capture the raw model output (not just the parsed RobotCommand)
  - measure first-token latency and tokens/sec
  - sample CPU / RAM / GPU / VRAM around the call

The parsing path mirrors `agent.normalize_command`: extract JSON, coerce
nulls, and run `postprocess_command` so optional-color skills behave the
same as in normal mode.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

import httpx

from .agent import _coerce_nulls, extract_json, postprocess_command
from .prompts import ROBOT_AGENT_INSTRUCTIONS
from .schemas import LLMTraceMetrics, PromptMessage, PromptTrace, RobotCommand
from .skills import load_skill_registry, render_skill_list
from .system_metrics import SystemMetricsSampler

_TRACE_SYSTEM_MESSAGE = (
    "あなたはロボット命令をJSONに変換する安全な分類器です。"
    "必ずJSONのみを返してください。"
)


def ollama_base_url() -> str:
    explicit = os.getenv("OLLAMA_BASE_URL")
    if explicit:
        return explicit.rstrip("/")
    base = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    return base[:-3] if base.endswith("/v1") else base


def _build_final_user_prompt(user_text: str, skill_text: str) -> str:
    return f"""\
{ROBOT_AGENT_INSTRUCTIONS}

以下のskill_registryだけを使って、ユーザー命令をRobotCommand JSONへ変換してください。

skill_registry:
{skill_text}

ユーザー命令:
{user_text}

ロボット命令ではない (雑談・挨拶・無関係な発話) 場合は、必ず以下の形で返してください。
{{
  "skill_id": "unknown",
  "object": null,
  "color": null,
  "vla_instruction": "NOOP",
  "confidence": 0.0,
  "requires_confirmation": true,
  "executable": false,
  "reason": "ロボット命令ではありません"
}}

重要:
- reasonは必ず入れる。null禁止。実行可能なら判断理由を日本語で書く。
- 出力は JSON のみ。Markdown や説明文は禁止。
"""


def build_prompt_trace(
    user_text: str,
    model: str,
    *,
    temperature: float = 0.0,
) -> PromptTrace:
    """Construct the PromptTrace shown alongside the model's response."""
    registry = load_skill_registry()
    skill_text = render_skill_list(registry)
    final_user_prompt = _build_final_user_prompt(user_text, skill_text)
    messages = [
        PromptMessage(role="system", content=_TRACE_SYSTEM_MESSAGE),
        PromptMessage(role="user", content=final_user_prompt),
    ]
    return PromptTrace(
        model=model,
        endpoint=f"{ollama_base_url()}/api/chat",
        temperature=temperature,
        user_text=user_text,
        system_message=_TRACE_SYSTEM_MESSAGE,
        final_user_prompt=final_user_prompt,
        skill_registry_text=skill_text,
        messages=messages,
        request_options={"temperature": temperature, "stream": True},
    )


def trace_ollama_robot_parse(
    user_text: str,
    model: str,
    *,
    temperature: float = 0.0,
) -> tuple[RobotCommand, str, LLMTraceMetrics, PromptTrace]:
    """Run one streaming chat and return command, raw text, metrics, prompt trace."""
    prompt_trace = build_prompt_trace(user_text, model, temperature=temperature)
    url = prompt_trace.endpoint
    payload = {
        "model": model,
        "stream": True,
        "messages": [m.model_dump() for m in prompt_trace.messages],
        "options": {"temperature": temperature},
    }

    sampler = SystemMetricsSampler(interval_s=0.1)
    sampler.start()
    started = time.perf_counter()
    first_token_time_s: Optional[float] = None
    chunks: list[str] = []
    final_raw: Optional[dict[str, Any]] = None

    try:
        with httpx.stream("POST", url, json=payload, timeout=None) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = data.get("message") or {}
                content = message.get("content") or ""
                if content:
                    if first_token_time_s is None:
                        first_token_time_s = time.perf_counter() - started
                    chunks.append(content)
                if data.get("done") is True:
                    final_raw = data

        total_time_s = time.perf_counter() - started
        summary = sampler.stop().to_dict()
        raw_output = "".join(chunks).strip()

        parsed = extract_json(raw_output)
        parsed = _coerce_nulls(parsed)
        command = postprocess_command(RobotCommand.model_validate(parsed))

        eval_count: Optional[int] = None
        eval_duration_s: Optional[float] = None
        tokens_per_second: Optional[float] = None
        if final_raw:
            eval_count = final_raw.get("eval_count")
            eval_duration_ns = final_raw.get("eval_duration")
            if eval_duration_ns:
                eval_duration_s = float(eval_duration_ns) / 1_000_000_000
            if eval_count and eval_duration_s and eval_duration_s > 0:
                tokens_per_second = float(eval_count) / eval_duration_s

        metrics = LLMTraceMetrics(
            total_time_s=total_time_s,
            first_token_time_s=first_token_time_s,
            eval_count=eval_count,
            eval_duration_s=eval_duration_s,
            tokens_per_second=tokens_per_second,
            cpu_peak_percent=summary.get("cpu_peak_percent"),
            cpu_avg_percent=summary.get("cpu_avg_percent"),
            ram_peak_mb=summary.get("ram_peak_mb"),
            ram_peak_percent=summary.get("ram_peak_percent"),
            gpu_peak_percent=summary.get("gpu_peak_percent"),
            gpu_avg_percent=summary.get("gpu_avg_percent"),
            vram_peak_mb=summary.get("vram_peak_mb"),
            vram_total_mb=summary.get("vram_total_mb"),
        )
        return command, raw_output, metrics, prompt_trace

    except Exception:
        sampler.stop()
        raise
