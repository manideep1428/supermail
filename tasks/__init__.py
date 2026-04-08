"""Bundled Supermail tasks."""

from .base import ACTION_OPTIONS, BENCHMARK_NAME, CATEGORY_OPTIONS, FIELD_OPTIONS, PRIORITY_OPTIONS, TaskDefinition
from .email_easy import TASK as EMAIL_EASY_TASK
from .email_medium import TASK as EMAIL_MEDIUM_TASK
from .email_hard import TASK as EMAIL_HARD_TASK

ALL_TASKS = [
    EMAIL_EASY_TASK,
    EMAIL_MEDIUM_TASK,
    EMAIL_HARD_TASK,
]

TASKS_BY_ID = {task.task_id: task for task in ALL_TASKS}

__all__ = [
    "ACTION_OPTIONS",
    "ALL_TASKS",
    "BENCHMARK_NAME",
    "CATEGORY_OPTIONS",
    "EMAIL_EASY_TASK",
    "EMAIL_HARD_TASK",
    "EMAIL_MEDIUM_TASK",
    "FIELD_OPTIONS",
    "PRIORITY_OPTIONS",
    "TASKS_BY_ID",
    "TaskDefinition",
]
