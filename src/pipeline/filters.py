from __future__ import annotations

import re

from app.config import SAFETY_EXCLUDE_PATTERNS


def is_safety_stop(why_stopped: str | None) -> bool:
    if not why_stopped or not why_stopped.strip():
        return False
    text = why_stopped.lower()
    return any(re.search(pattern, text) for pattern in SAFETY_EXCLUDE_PATTERNS)
