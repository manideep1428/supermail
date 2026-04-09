"""Supermail OpenEnv environment implementation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

try:
    from openenv.core.env_server.interfaces import Environment
except ImportError:  # pragma: no cover - local fallback when OpenEnv is absent
    class Environment:
        """Fallback OpenEnv Environment base class."""

try:
    from ..models import SupportAction, SupportObservation, SupportState
    from ..tasks import ALL_TASKS, FIELD_OPTIONS, TASKS_BY_ID, TaskDefinition
except ImportError:  # pragma: no cover
    from models import SupportAction, SupportObservation, SupportState
    from tasks import ALL_TASKS, FIELD_OPTIONS, TASKS_BY_ID, TaskDefinition


@dataclass(frozen=True)
class StepAssessment:
    """Internal grading result for one agent action."""

    reward: float
    score: float
    done: bool
    success: bool
    feedback: str
    error: str | None
    matched_fields: set[str]


class SupermailEnvironment(Environment):
    """Deterministic customer support email triage environment."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = True
    MIN_SCORE: float = 0.01
    MAX_SCORE: float = 0.99

    def __init__(self, task_id: str | None = None):
        self._requested_task_id = task_id
        self._task_order = [task.task_id for task in ALL_TASKS]
        self._next_task_index = 0
        self._task: TaskDefinition | None = None
        self._matched_fields: set[str] = set()
        self._history: list[str] = []
        self._score = self._bounded_score(0.0)
        self._state = SupportState(
            episode_id=str(uuid4()),
            step_count=0,
            score=self._score,
        )

    @property
    def benchmark(self) -> str:
        return "supermail"

    @property
    def task_name(self) -> str:
        if self._task is not None:
            return self._task.task_id
        if self._requested_task_id:
            return self._requested_task_id
        return self._task_order[self._next_task_index % len(self._task_order)]

    def reset(self) -> SupportObservation:
        """Start a fresh episode."""
        self._task = self._select_task()
        self._matched_fields = set()
        self._history = []
        self._score = self._bounded_score(0.0)
        self._state = SupportState(
            episode_id=str(uuid4()),
            step_count=0,
            task_id=self._task.task_id,
            difficulty=self._task.difficulty,
            score=self._score,
            matched_fields=[],
            attempts_remaining=self._task.max_attempts,
        )
        return self._build_observation(
            feedback=(
                f"{self._task.guidance} Required fields: "
                f"{', '.join(self._task.required_fields)}."
            ),
            reward=0.0,
            done=False,
            last_action_error=None,
            success=False,
        )

    def step(self, action: SupportAction) -> SupportObservation:  # type: ignore[override]
        """Grade one classification attempt and return the next observation."""
        if self._task is None:
            raise RuntimeError("Call reset() before step().")

        self._state.step_count += 1
        decision = self._extract_decision(action)
        assessment = self._assess(decision)

        self._matched_fields = assessment.matched_fields
        self._score = assessment.score
        self._state.score = assessment.score
        self._state.matched_fields = sorted(self._matched_fields)
        self._state.attempts_remaining = max(
            self._task.max_attempts - self._state.step_count,
            0,
        )

        compact_decision = json.dumps(decision, sort_keys=True)
        self._history.append(
            "step="
            f"{self._state.step_count} decision={compact_decision} "
            f"reward={assessment.reward:.2f} score={assessment.score:.2f} "
            f"feedback={assessment.feedback}"
        )

        return self._build_observation(
            feedback=assessment.feedback,
            reward=assessment.reward,
            done=assessment.done,
            last_action_error=assessment.error,
            success=assessment.success,
        )

    @property
    def state(self) -> SupportState:
        """Return the current environment state."""
        return self._state

    def close(self) -> None:
        """No-op close hook for API symmetry."""

    def _select_task(self) -> TaskDefinition:
        if self._requested_task_id:
            return TASKS_BY_ID[self._requested_task_id]
        task_id = self._task_order[self._next_task_index % len(self._task_order)]
        self._next_task_index += 1
        return TASKS_BY_ID[task_id]

    def _extract_decision(self, action: SupportAction) -> dict[str, str]:
        decision: dict[str, str] = {}
        for field_name in ("priority", "category", "action"):
            value = getattr(action, field_name, None)
            if value:
                decision[field_name] = value
        return decision

    def _bounded_score(self, raw_score: float) -> float:
        """Map raw progress into the open interval (0, 1)."""
        clamped_raw_score = min(max(raw_score, 0.0), 1.0)
        scaled_score = self.MIN_SCORE + (
            clamped_raw_score * (self.MAX_SCORE - self.MIN_SCORE)
        )
        return round(scaled_score, 2)

    def _assess(self, decision: dict[str, str]) -> StepAssessment:
        if self._task is None:
            raise RuntimeError("Task not initialized.")

        if not decision:
            return StepAssessment(
                reward=-0.10,
                score=round(self._score, 2),
                done=self._state.step_count >= self._task.max_attempts,
                success=False,
                feedback=(
                    "No decision fields were submitted. Provide "
                    + ", ".join(self._task.required_fields)
                    + "."
                ),
                error="empty_action",
                matched_fields=set(self._matched_fields),
            )

        matched_fields = set(self._matched_fields)
        newly_matched: list[str] = []
        mismatched_fields: list[str] = []

        for field_name in self._task.required_fields:
            predicted = decision.get(field_name)
            if predicted is None:
                continue
            if predicted == self._task.expected[field_name]:
                if field_name not in matched_fields:
                    newly_matched.append(field_name)
                matched_fields.add(field_name)
            else:
                mismatched_fields.append(field_name)

        reward = sum(self._task.field_weights[field] for field in newly_matched)
        if mismatched_fields and not newly_matched:
            reward -= 0.10
        elif not newly_matched and not mismatched_fields:
            reward -= 0.02

        if self._state.step_count > 3 and matched_fields != set(self._task.required_fields):
            reward -= 0.05

        raw_score = sum(self._task.field_weights[field] for field in matched_fields)
        score = self._bounded_score(raw_score)

        success = matched_fields == set(self._task.required_fields)
        done = success or self._state.step_count >= self._task.max_attempts

        feedback_parts: list[str] = []
        if newly_matched:
            feedback_parts.append("Matched " + ", ".join(newly_matched) + ".")
        if mismatched_fields:
            feedback_parts.append("Incorrect " + ", ".join(mismatched_fields) + ".")

        remaining_fields = [
            field for field in self._task.required_fields if field not in matched_fields
        ]
        if success:
            feedback_parts.append("All required fields are correct.")
        elif remaining_fields:
            feedback_parts.append("Still need " + ", ".join(remaining_fields) + ".")

        if done and not success:
            feedback_parts.append("Max attempts reached.")

        if not feedback_parts:
            feedback_parts.append("No new progress.")

        return StepAssessment(
            reward=round(reward, 2),
            score=score,
            done=done,
            success=success,
            feedback=" ".join(feedback_parts),
            error=None,
            matched_fields=matched_fields,
        )

    def _build_observation(
        self,
        *,
        feedback: str,
        reward: float,
        done: bool,
        last_action_error: str | None,
        success: bool,
    ) -> SupportObservation:
        if self._task is None:
            raise RuntimeError("Task not initialized.")

        required_allowed_values = {
            field_name: FIELD_OPTIONS[field_name]
            for field_name in self._task.required_fields
        }

        return SupportObservation(
            task_id=self._task.task_id,
            task_type=self._task.difficulty,
            benchmark=self._task.benchmark,
            objective=self._task.objective,
            email=self._task.email,
            context=dict(self._task.context),
            required_fields=list(self._task.required_fields),
            allowed_values=required_allowed_values,
            history=list(self._history),
            feedback=feedback,
            score=round(self._score, 2),
            attempts_remaining=max(
                self._task.max_attempts - self._state.step_count,
                0,
            ),
            done=done,
            reward=round(reward, 2),
            metadata={
                "last_action_error": last_action_error,
                "success": success,
                "score": round(self._score, 2),
                "matched_fields": sorted(self._matched_fields),
            },
        )


SupportSimEnvironment = SupermailEnvironment
