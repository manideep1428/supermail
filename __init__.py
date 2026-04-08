"""Supermail package exports."""

from .models import SupportAction, SupportObservation, SupportState

try:  # pragma: no cover - optional during local editing without dependencies
    from .client import SupermailEnv, SupportSimEnv
except Exception:  # pragma: no cover
    SupermailEnv = None
    SupportSimEnv = None

__all__ = [
    "SupportAction",
    "SupportObservation",
    "SupermailEnv",
    "SupportSimEnv",
    "SupportState",
]
