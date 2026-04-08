"""Client wrapper for the Supermail environment."""

from __future__ import annotations

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult

try:
    from .models import SupportAction, SupportObservation, SupportState
except ImportError:  # pragma: no cover
    from models import SupportAction, SupportObservation, SupportState


class SupermailEnv(EnvClient[SupportAction, SupportObservation, SupportState]):
    """Type-safe client for the deployed Supermail environment."""

    def _step_payload(self, action: SupportAction) -> Dict:
        payload: Dict[str, str] = {}
        for field_name in ("priority", "category", "action", "notes"):
            value = getattr(action, field_name)
            if value:
                payload[field_name] = value
        return payload

    def _parse_result(self, payload: Dict) -> StepResult[SupportObservation]:
        obs_data = payload.get("observation", {})
        observation = SupportObservation(
            task_id=obs_data.get("task_id", ""),
            task_type=obs_data.get("task_type", ""),
            benchmark=obs_data.get("benchmark", "supermail"),
            objective=obs_data.get("objective", ""),
            email=obs_data.get("email", ""),
            context=obs_data.get("context", {}),
            required_fields=obs_data.get("required_fields", []),
            allowed_values=obs_data.get("allowed_values", {}),
            history=obs_data.get("history", []),
            feedback=obs_data.get("feedback", ""),
            score=obs_data.get("score", 0.0),
            attempts_remaining=obs_data.get("attempts_remaining", 0),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> SupportState:
        return SupportState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            task_id=payload.get("task_id"),
            difficulty=payload.get("difficulty"),
            score=payload.get("score", 0.0),
            matched_fields=payload.get("matched_fields", []),
            attempts_remaining=payload.get("attempts_remaining", 0),
        )


SupportSimEnv = SupermailEnv
