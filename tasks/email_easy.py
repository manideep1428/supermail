"""Easy support triage task."""

from .base import TaskDefinition

TASK = TaskDefinition(
    task_id="email_easy",
    difficulty="easy",
    objective="Decide the email priority only.",
    email=(
        "Subject: Charged twice after cancellation\n\n"
        "Hi support,\n"
        "I canceled our Pro plan last month, but my company card was charged again "
        "today. Please fix this before payroll closes this evening.\n"
        "Thanks,\n"
        "Alicia"
    ),
    context={
        "customer_tier": "business",
        "channel": "email",
        "sentiment": "frustrated",
        "order_status": "active billing dispute",
    },
    expected={
        "priority": "urgent",
    },
    field_weights={
        "priority": 1.0,
    },
)
