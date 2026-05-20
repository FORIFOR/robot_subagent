"""Direct streaming chat against Ollama's /api/chat, with timing + sys metrics.

Used by the Ink TUI's LLM Test Mode to compare local models. The OpenAI Agents
SDK is intentionally bypassed here because we want raw Ollama timing fields
(`eval_count`, `eval_duration`, `total_duration`) and the simplest possible
hot loop.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Optional

import httpx

from .system_metrics import SystemMetricsSampler


@dataclass
class LLMChatResult:
    ok: bool
    model: str
    prompt: str
    response: str
    total_time_s: float
    first_token_time_s: Optional[float]
    eval_count: Optional[int]
    eval_duration_s: Optional[float]
    tokens_per_second: Optional[float]
    ollama_raw: Optional[dict[str, Any]]
    metrics: dict[str, Any]
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def ollama_base_url() -> str:
    """Resolve Ollama root URL.

    Order: OLLAMA_BASE_URL → OPENAI_BASE_URL minus a trailing /v1 →
    http://localhost:11434.
    """
    explicit = os.getenv("OLLAMA_BASE_URL")
    if explicit:
        return explicit.rstrip("/")
    base = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    if base.endswith("/v1"):
        return base[:-3]
    return base


def list_ollama_models() -> list[str]:
    url = f"{ollama_base_url()}/api/tags"
    response = httpx.get(url, timeout=10.0)
    response.raise_for_status()
    models = response.json().get("models", [])
    return [m["name"] for m in models if "name" in m]


def chat_with_ollama_measured(
    prompt: str,
    model: str,
    *,
    system: Optional[str] = None,
    temperature: float = 0.2,
) -> LLMChatResult:
    """Stream a chat to Ollama and return timing + sys metrics around it."""
    url = f"{ollama_base_url()}/api/chat"

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {"temperature": temperature},
    }

    sampler = SystemMetricsSampler(interval_s=0.2)
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
        metrics_summary = sampler.stop().to_dict()
        response_text = "".join(chunks)

        eval_count = None
        eval_duration_s = None
        tokens_per_second = None
        if final_raw:
            eval_count = final_raw.get("eval_count")
            eval_duration_ns = final_raw.get("eval_duration")
            if eval_duration_ns:
                eval_duration_s = float(eval_duration_ns) / 1_000_000_000
            if eval_count and eval_duration_s and eval_duration_s > 0:
                tokens_per_second = float(eval_count) / eval_duration_s

        return LLMChatResult(
            ok=True,
            model=model,
            prompt=prompt,
            response=response_text,
            total_time_s=total_time_s,
            first_token_time_s=first_token_time_s,
            eval_count=eval_count,
            eval_duration_s=eval_duration_s,
            tokens_per_second=tokens_per_second,
            ollama_raw=final_raw,
            metrics=metrics_summary,
            error=None,
        )

    except Exception as e:
        total_time_s = time.perf_counter() - started
        metrics_summary = sampler.stop().to_dict()
        return LLMChatResult(
            ok=False,
            model=model,
            prompt=prompt,
            response="",
            total_time_s=total_time_s,
            first_token_time_s=first_token_time_s,
            eval_count=None,
            eval_duration_s=None,
            tokens_per_second=None,
            ollama_raw=final_raw,
            metrics=metrics_summary,
            error=str(e),
        )
