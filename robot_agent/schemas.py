"""Pydantic schemas for the robot sub-agent."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Skill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    description: str

    object_required: bool = True
    color_required: bool = False

    vla_template: str
    vla_template_with_color: Optional[str] = None

    allowed_objects: list[str] = Field(default_factory=list)
    allowed_colors: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    examples: list[dict] = Field(default_factory=list)


class SkillRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: list[Skill]


class RobotCommand(BaseModel):
    """Structured output of the Sub Agent."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(description="Selected skill id from skill_registry")
    object: Optional[str] = Field(
        default=None,
        description="Target object, e.g. cube/apple/cup. May be null for object-less skills.",
    )
    color: Optional[str] = Field(default=None, description="Target color if specified")
    vla_instruction: str = Field(description="Short English command for VLA")
    confidence: float = Field(ge=0.0, le=1.0)
    requires_confirmation: bool = True
    executable: bool = Field(
        description="Whether this command can be executed safely (false if blocked or unsupported)"
    )
    reason: str = Field(description="Short reason in Japanese")


class SafetyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    level: Literal["safe", "needs_confirmation", "blocked"]
    reason: str


class LLMTraceMetrics(BaseModel):
    """Timing + system metrics captured around one streaming LLM call."""

    model_config = ConfigDict(extra="forbid")

    total_time_s: float
    first_token_time_s: Optional[float] = None
    eval_count: Optional[int] = None
    eval_duration_s: Optional[float] = None
    tokens_per_second: Optional[float] = None
    cpu_peak_percent: Optional[float] = None
    cpu_avg_percent: Optional[float] = None
    ram_peak_mb: Optional[float] = None
    ram_peak_percent: Optional[float] = None
    gpu_peak_percent: Optional[float] = None
    gpu_avg_percent: Optional[float] = None
    vram_peak_mb: Optional[float] = None
    vram_total_mb: Optional[float] = None


class PromptMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str
    content: str


class PromptTrace(BaseModel):
    """Everything we handed to the LLM for one trace call."""

    model_config = ConfigDict(extra="forbid")

    model: str
    endpoint: str
    temperature: float
    user_text: str
    system_message: str
    final_user_prompt: str
    skill_registry_text: str
    messages: list[PromptMessage]
    request_options: dict[str, Any] = Field(default_factory=dict)


class TaskTraceEvaluation(BaseModel):
    """How well did the LLM hit the expected skill on this utterance?"""

    model_config = ConfigDict(extra="forbid")

    expected_skill: str
    skill_match: bool
    object_match: bool
    instruction_ok: bool
    executable_ok: bool
    safety_ok: bool
    score: float
    notes: list[str] = Field(default_factory=list)


class TaskTraceResult(BaseModel):
    """Full payload of `robot-agent trace-parse-json`."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    input: str
    model: str
    expected_skill: str
    prompt_trace: PromptTrace
    raw_output: str
    command: RobotCommand
    safety: SafetyResult
    evaluation: TaskTraceEvaluation
    generated_command: Optional[str] = None
    metrics: LLMTraceMetrics
    error: Optional[str] = None
