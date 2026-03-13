"""
Security guardrail: block requests that ask for restricted data
(supplier, margin, internal notes, warehouse, profit, etc.)
and return a safe refusal response.
"""
import re
from dataclasses import dataclass
from typing import Optional

# Phrases that indicate request for restricted/internal data
RESTRICTED_PATTERNS = [
    r"\bsupplier(s)?\b",
    r"\bmargin(s)?\b",
    r"\binternal\s+notes?\b",
    r"\bwarehouse\b",
    r"\bprofit\b",
    r"\bcost\s+price\b",
    r"\bwholesale\s+price\b",
    r"\bconfidential\b",
    r"\bback.?office\b",
    r"\bvendor\s+name\b",
]
COMPILED_RESTRICTED = [re.compile(p, re.I) for p in RESTRICTED_PATTERNS]

REFUSAL_MESSAGE = (
    "I can't provide that information. Supplier, margin, and internal operational "
    "details are confidential. I can help with product specs, pricing for your region, "
    "availability, and warranty instead."
)


@dataclass
class SecurityResult:
    allowed: bool
    message: Optional[str] = None  # refusal message if not allowed


def check_restricted_data(query: str) -> SecurityResult:
    """
    If the query asks for restricted data (supplier, margin, internal notes, etc.),
    return SecurityResult(allowed=False, message=refusal).
    """
    q = query.strip()
    for pat in COMPILED_RESTRICTED:
        if pat.search(q):
            return SecurityResult(allowed=False, message=REFUSAL_MESSAGE)
    return SecurityResult(allowed=True)
