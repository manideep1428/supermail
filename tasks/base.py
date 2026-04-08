"""Task definitions shared by the Supermail environment."""

from __future__ import annotations

from dataclasses import dataclass, field

BENCHMARK_NAME = "supermail"

PRIORITY_OPTIONS = ("urgent", "normal", "spam")
CATEGORY_OPTIONS = ("billing", "delivery", "technical", "general")
ACTION_OPTIONS = ("respond_immediately", "assign_to_team", "ignore")

FIELD_OPTIONS = {
    "priority": list(PRIORITY_OPTIONS),
    "category": list(CATEGORY_OPTIONS),
    "action": list(ACTION_OPTIONS),
}


@dataclass(frozen=True)
class TaskDefinition:
    """Single deterministic support triage task."""

    task_id: str
    difficulty: str
    objective: str
    email: str
    context: dict[str, str]
    expected: dict[str, str]
    field_weights: dict[str, float]
    max_attempts: int = 4
    benchmark: str = BENCHMARK_NAME
    guidance: str = field(
        default=(
            "Read the email and submit only the labels required for this task."
        )
    )

    @property
    def required_fields(self) -> list[str]:
        return list(self.expected.keys())
