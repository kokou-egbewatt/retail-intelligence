"""
Prompt injection detection: detect attempts to override instructions
(e.g. "ignore previous instructions", "disregard", "new instructions")
and block the request with a refusal.
"""
import re
from dataclasses import dataclass
from typing import Optional

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"forget\s+(everything|all\s+above)",
    r"new\s+instructions?\s*:",
    r"override\s+(previous|prior)",
    r"you\s+are\s+now\s+(a|in)",
    r"pretend\s+you\s+are",
    r"act\s+as\s+if\s+you",
    r"from\s+now\s+on\s+you",
    r"system\s*:\s*you\s+are",
    r"\[INST\]",
    r"<\|im_start\|>",
]
COMPILED = [re.compile(p, re.I) for p in INJECTION_PATTERNS]

REFUSAL_MESSAGE = (
    "I can't follow that request. I'm designed to answer only product and policy questions "
    "within my guidelines. How can I help you with our products or warranty today?"
)


@dataclass
class InjectionResult:
    is_injection: bool
    message: Optional[str] = None  # refusal message if injection detected


def detect_prompt_injection(query: str) -> InjectionResult:
    """If prompt injection is detected, return InjectionResult(is_injection=True, message=refusal)."""
    q = query.strip()
    for pat in COMPILED:
        if pat.search(q):
            return InjectionResult(is_injection=True, message=REFUSAL_MESSAGE)
    return InjectionResult(is_injection=False)
