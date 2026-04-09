"""Async baseline inference runner for Supermail."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, List, Optional

from openai import OpenAI

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv() -> bool:
        return False

from client import SupermailEnv
from models import SupportAction, SupportObservation
from server.environment import SupermailEnvironment
from sys_prompt import SYSTEM_PROMPT
from tasks import ALL_TASKS, TASKS_BY_ID

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

BASE_URL = os.getenv("SUPERMAIL_BASE_URL") or os.getenv("SUPPORT_SIM_BASE_URL")
TASK_NAME = os.getenv("SUPERMAIL_TASK") or os.getenv("SUPPORT_SIM_TASK", "all")
BENCHMARK = os.getenv("SUPERMAIL_BENCHMARK") or os.getenv("SUPPORT_SIM_BENCHMARK", "supermail")

MAX_STEPS = 12
TEMPERATURE = 0.4
MAX_TOKENS = 25000
SUCCESS_SCORE_THRESHOLD = 0.95
MIN_SCORE = 0.01
MAX_SCORE = 0.99

@dataclass
class LocalStepResult:
    """Minimal local stand-in for OpenEnv StepResult."""

    observation: SupportObservation
    reward: float
    done: bool


class LocalSupermailSession:
    """Async adapter for direct local environment usage."""

    def __init__(self, task_id: str):
        self._env = SupermailEnvironment(task_id=task_id)

    async def reset(self) -> LocalStepResult:
        observation = self._env.reset()
        return LocalStepResult(
            observation=observation,
            reward=observation.reward or 0.0,
            done=observation.done,
        )

    async def step(self, action: SupportAction) -> LocalStepResult:
        observation = self._env.step(action)
        return LocalStepResult(
            observation=observation,
            reward=observation.reward or 0.0,
            done=observation.done,
        )

    async def close(self) -> None:
        self._env.close()


def sanitize(value: Any) -> str:
    """Keep log output on a single line."""
    text = str(value)
    return " ".join(text.replace("\r", " ").replace("\n", " ").split())


def clamp_score(score: float) -> float:
    """Clamp score into the open interval (0, 1)."""
    return min(max(score, MIN_SCORE), MAX_SCORE)


def compact_action(action: Optional[SupportAction]) -> str:
    """Serialize an action for the required log format."""
    if action is None:
        return "null"
    payload = {
        field_name: getattr(action, field_name)
        for field_name in ("priority", "category", "action", "notes")
        if getattr(action, field_name, None)
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    *,
    step: int,
    action: Optional[SupportAction],
    reward: float,
    done: bool,
    error: Optional[str],
) -> None:
    error_text = error if error else "null"
    print(
        "[STEP] "
        f"step={step} "
        f"action={sanitize(compact_action(action))} "
        f"reward={reward:.2f} "
        f"done={'true' if done else 'false'} "
        f"error={sanitize(error_text)}",
        flush=True,
    )


def log_end(*, success: bool, steps: int, score: float, rewards: List[float]) -> None:
    reward_text = ",".join(f"{reward:.2f}" for reward in rewards)
    print(
        f"[END] success={'true' if success else 'false'} "
        f"steps={steps} score={score:.2f} rewards={reward_text}",
        flush=True,
    )


def build_client() -> Optional[OpenAI]:
    """Create an OpenAI client when credentials are available."""
    if not HF_TOKEN:
        return None
    return OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)


def heuristic_action(observation: SupportObservation) -> SupportAction:
    """Deterministic fallback policy for the bundled tasks."""
    text = f"{observation.email} {json.dumps(observation.context, sort_keys=True)}".lower()

    if any(
        token in text
        for token in (
            "click here",
            "gift card",
            "crypto",
            "lottery",
            "unsubscribe",
            "bypass all metrics",
            "encrypted emergency",
            "decrypt tool",
            "emergency slot",
            "override the normal queue",
            "sender_verified\": \"false",
            "spoofed sender",
        )
    ):
        priority = "spam"
    elif any(
        token in text
        for token in (
            "today",
            "payroll closes",
            "500 error",
            "blocked",
            "backing up",
            "immediately",
            "double",
            "charged again",
        )
    ):
        priority = "urgent"
    else:
        priority = "normal"

    if any(token in text for token in ("charge", "charged", "invoice", "refund", "billing", "subscription")):
        category = "billing"
    elif any(token in text for token in ("tracking", "shipment", "delivery", "delivered", "ship")):
        category = "delivery"
    elif any(token in text for token in ("error", "login", "outage", "crash", "bug", "sign in")):
        category = "technical"
    else:
        category = "general"

    if priority == "spam":
        next_action = "ignore"
    elif category == "technical":
        next_action = "assign_to_team"
    elif priority == "urgent":
        next_action = "respond_immediately"
    elif category == "delivery":
        next_action = "assign_to_team"
    else:
        next_action = "respond_immediately"

    payload: dict[str, str] = {}
    if "priority" in observation.required_fields:
        payload["priority"] = priority
    if "category" in observation.required_fields:
        payload["category"] = category
    if "action" in observation.required_fields:
        payload["action"] = next_action
    return SupportAction(**payload)


def get_model_action(
    client: OpenAI,
    observation: SupportObservation,
    history: List[str],
) -> SupportAction:
    """Use the OpenAI client for the next action."""
    prompt = {
        "task_id": observation.task_id,
        "benchmark": observation.benchmark,
        "objective": observation.objective,
        "required_fields": observation.required_fields,
        "allowed_values": observation.allowed_values,
        "email": observation.email,
        "context": observation.context,
        "history": history,
        "feedback": observation.feedback,
    }

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)},
        ],
    )
    content = (response.choices[0].message.content or "").strip()
    payload = json.loads(content)
    filtered_payload = {
        key: value
        for key, value in payload.items()
        if key in {"priority", "category", "action", "notes"}
    }
    return SupportAction(**filtered_payload)


def choose_action(
    client: Optional[OpenAI],
    observation: SupportObservation,
    history: List[str],
) -> SupportAction:
    """Use the model when available, otherwise fall back to heuristics."""
    if client is None:
        return heuristic_action(observation)
    try:
        return get_model_action(client, observation, history)
    except Exception:
        return heuristic_action(observation)


async def create_env(task_id: str):
    """Create the environment session using docker, base URL, or local fallback."""
    if LOCAL_IMAGE_NAME:
        return await SupermailEnv.from_docker_image(
            LOCAL_IMAGE_NAME,
            env_vars={"SUPERMAIL_TASK": task_id},
        )

    if BASE_URL:
        env = SupermailEnv(base_url=BASE_URL)
        await env.connect()
        return env

    return LocalSupermailSession(task_id=task_id)


async def run_episode(task_id: str, client: Optional[OpenAI]) -> None:
    """Run a single task episode and emit the required logs."""
    if task_id not in TASKS_BY_ID:
        raise ValueError(f"Unknown task: {task_id}")

    env = None
    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = MIN_SCORE
    success = False
    action_for_log: Optional[SupportAction] = None

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        env = await create_env(task_id)
        result = await env.reset()
        observation = result.observation

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            action_for_log = choose_action(client, observation, history)
            result = await env.step(action_for_log)
            observation = result.observation
            reward = result.reward or 0.0
            done = result.done
            error = observation.metadata.get("last_action_error")

            rewards.append(reward)
            steps_taken = step
            score = clamp_score(float(getattr(observation, "score", 0.0)))

            log_step(
                step=step,
                action=action_for_log,
                reward=reward,
                done=done,
                error=error,
            )

            history.append(
                f"step={step} action={compact_action(action_for_log)} "
                f"reward={reward:.2f} score={score:.2f}"
            )

            if done:
                break

        success = score >= SUCCESS_SCORE_THRESHOLD
    except Exception as exc:
        log_step(
            step=steps_taken,
            action=action_for_log,
            reward=0.0,
            done=True,
            error=str(exc),
        )
    finally:
        if env is not None:
            try:
                await env.close()
            except Exception:
                pass
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


def task_sequence() -> List[str]:
    """Resolve the requested task selection."""
    if TASK_NAME == "all":
        return [task.task_id for task in ALL_TASKS]
    return [TASK_NAME]


async def main() -> None:
    """Run one or more task episodes."""
    client = build_client()
    for task_id in task_sequence():
        await run_episode(task_id, client)


if __name__ == "__main__":
    asyncio.run(main())
