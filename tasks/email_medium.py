"""Medium support triage task."""

from .base import TaskDefinition

TASK = TaskDefinition(
    task_id="email_medium",
    difficulty="medium",
    objective="Decide the email priority and category.",
    email=(
        "Subject: Need an update on shipment timing\n\n"
        "Hello team,\n"
        "Our office chairs were supposed to ship this week, but the tracking page "
        "has not changed in two days. Can you confirm the delivery date when you "
        "have a moment?\n"
        "Best,\n"
        "Ravi"
    ),
    context={
        "customer_tier": "standard",
        "channel": "email",
        "shipping_method": "ground",
        "tracking_status": "label created",
    },
    expected={
        "priority": "normal",
        "category": "delivery",
    },
    field_weights={
        "priority": 0.5,
        "category": 0.5,
    },
)
