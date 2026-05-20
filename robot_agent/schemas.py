"""Pydantic schemas for the robot sub-agent."""

from __future__ import annotations

from typing import Literal, Optional

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
