"""Thin HTTP client for the OpenVLA inference server.

POSTs the normalized command to OPENVLA_URL (default http://localhost:8000/infer).
The sub-agent itself does not run VLA inference.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx
from pydantic import BaseModel, ConfigDict

from .schemas import RobotCommand


class OpenVLAResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    raw: Optional[Any] = None


def send_to_openvla(command: RobotCommand, *, timeout: float = 60.0) -> OpenVLAResult:
    url = os.getenv("OPENVLA_URL", "http://localhost:8000/infer")
    payload = {
        "instruction": command.vla_instruction,
        "skill_id": command.skill_id,
        "object": command.object,
        "color": command.color,
    }
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return OpenVLAResult(ok=True, raw=response.json())
    except Exception as e:
        return OpenVLAResult(ok=False, raw={"error": str(e)})
