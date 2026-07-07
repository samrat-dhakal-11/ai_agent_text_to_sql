"""
guardrails.py
=============
Lightweight, transparent guardrails for the chatbot. Two layers:

1. INPUT guardrail  -> screens the user's raw message before it reaches the LLM.
2. SQL guardrail    -> screens any SQL the agent tries to execute, allowing
                       only read-only SELECT statements against the domain data.

These are intentionally simple, rule-based checks (no external service
required) so the app runs fully offline except for the LLM call itself.
"""

import re

# ----------------------------------------------------------------------
# 1. INPUT GUARDRAIL
# ----------------------------------------------------------------------
_BLOCKED_PATTERNS = [
    r"ignore (all|previous|prior) instructions",
    r"system prompt",
    r"reveal.*(api key|password|secret)",
    r"\bdrop\s+table\b",
    r"\bdelete\s+from\b",
    r"\bshutdown\b",
    r"\brm\s+-rf\b",
]

_MAX_MESSAGE_LENGTH = 2000


def check_input(message: str):
    """Returns (allowed: bool, reason: str | None)."""
    if not message or not message.strip():
        return False, "Message can't be empty."

    if len(message) > _MAX_MESSAGE_LENGTH:
        return False, f"Message is too long (max {_MAX_MESSAGE_LENGTH} characters)."

    lowered = message.lower()
    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, lowered):
            return False, "That request was blocked by the assistant's safety guardrails."

    return True, None


# ----------------------------------------------------------------------
# 2. SQL GUARDRAIL
# ----------------------------------------------------------------------
_WRITE_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "create",
    "truncate", "attach", "detach", "pragma", "replace", "vacuum",
]


def check_sql(query: str):
    """Returns (allowed: bool, reason: str | None). Only single, read-only
    SELECT statements are permitted."""
    if not query or not query.strip():
        return False, "Empty query."

    cleaned = query.strip().rstrip(";")

    if ";" in cleaned:
        return False, "Multiple statements are not allowed."

    first_word = cleaned.strip().split(None, 1)[0].lower() if cleaned.strip() else ""
    if first_word not in ("select", "with"):
        return False, "Only read-only SELECT queries are permitted."

    lowered = cleaned.lower()
    for kw in _WRITE_KEYWORDS:
        if re.search(rf"\b{kw}\b", lowered):
            return False, f"Query blocked: '{kw.upper()}' is not permitted (read-only mode)."

    return True, None