"""Runtime environment configuration for Supermail."""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv() -> bool:
        return False


load_dotenv()

IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") or os.getenv("IMAGE_NAME")
BASE_URL = os.getenv("SUPERMAIL_BASE_URL") or os.getenv("SUPPORT_SIM_BASE_URL")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
TASK_NAME = os.getenv("SUPERMAIL_TASK") or os.getenv("SUPPORT_SIM_TASK", "all")
BENCHMARK = os.getenv("SUPERMAIL_BENCHMARK") or os.getenv("SUPPORT_SIM_BENCHMARK", "supermail")
