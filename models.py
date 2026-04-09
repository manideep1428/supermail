"""Typed models for the Supermail environment."""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

try:
    from openenv.core.env_server.types import Action, Observation, State
except ImportError:  # pragma: no cover - local fallback when OpenEnv is absent
    class Action(BaseModel):
        """Fallback OpenEnv Action model."""

    class Observation(BaseModel):
        """Fallback OpenEnv Observation model."""

        done: bool = False
        reward: float | None = None
        metadata: Dict[str, Any] = Field(default_factory=dict)

    class State(BaseModel):
        """Fallback OpenEnv State model."""

        episode_id: str
        step_count: int = 0


PriorityLabel = Literal["urgent", "normal", "spam"]
CategoryLabel = Literal["billing", "delivery", "technical", "general"]
ResolutionLabel = Literal["respond_immediately", "assign_to_team", "ignore"]


class SupportAction(Action):
    """Action submitted by the agent on each step."""

    priority: PriorityLabel | None = Field(
        default=None,
        description="Priority decision for the email.",
    )
    category: CategoryLabel | None = Field(
        default=None,
        description="Category decision for the email when required.",
    )
    action: ResolutionLabel | None = Field(
        default=None,
        description="Recommended operational action when required.",
    )
    notes: str = Field(
        default="",
        description="Optional short explanation for audit logging.",
    )


class SupportObservation(Observation):
    """Observation returned by the environment."""

    task_id: str = Field(default="", description="Stable task identifier.")
    task_type: str = Field(default="", description="Difficulty level.")
    benchmark: str = Field(default="supermail", description="Benchmark name.")
    objective: str = Field(default="", description="What the agent must decide.")
    email: str = Field(default="", description="Incoming support email body.")
    context: Dict[str, str] = Field(
        default_factory=dict,
        description="Structured metadata about the customer or ticket.",
    )
    required_fields: List[str] = Field(
        default_factory=list,
        description="Decision fields required to finish the task.",
    )
    allowed_values: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Allowed label values for each decision field.",
    )
    history: List[str] = Field(
        default_factory=list,
        description="Compact summaries of prior attempts in the episode.",
    )
    feedback: str = Field(default="", description="Step-level grader feedback.")
    score: float = Field(default=0.01, description="Current cumulative score.")
    attempts_remaining: int = Field(
        default=0,
        description="How many attempts remain before the episode ends.",
    )


class SupportState(State):
    """Server-side state exposed by the environment."""

    task_id: str | None = None
    difficulty: str | None = None
    score: float = 0.01
    matched_fields: List[str] = Field(default_factory=list)
    attempts_remaining: int = 0
