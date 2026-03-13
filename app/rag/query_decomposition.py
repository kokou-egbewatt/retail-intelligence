"""
Query Decomposition: split complex, multi-part prompts into sub-queries for retrieval,
then merge results to improve coverage (e.g. "price of X and specs of Y" -> two retrievals).
"""

import re
from typing import List

# Splitters for multi-part queries (order matters: try " and " before single " and ")
MULTI_PART_PATTERNS = [
    r"\s+;\s+",  # "product A ; product B"
    r"\s+and\s+also\s+",  # "X and also Y"
    r"\s+also\s+",  # "X also Y"
    r"\s+and\s+(?:then\s+)?(?:what about|how about)\s+",  # "X and what about Y"
    r"\s+\.\s+(?=[A-Z])",  # "X. Y" (sentence boundary)
]

# Conjunctions that often start a second question
CONJUNCTION_START = re.compile(
    r"^\s*(?:and|also|what about|how about|and then)\s+",
    re.I,
)


def _split_by_patterns(text: str) -> List[str]:
    parts = [text]
    for pat in MULTI_PART_PATTERNS:
        new_parts: List[str] = []
        for p in parts:
            new_parts.extend(re.split(pat, p))
        parts = [x.strip() for x in new_parts if x.strip()]
    return parts


def _trim_conjunction(part: str) -> str:
    """Make sub-queries standalone (e.g. 'and what about warranty' -> 'warranty')."""
    return CONJUNCTION_START.sub("", part).strip() or part


def decompose_query(query: str, max_subqueries: int = 5) -> List[str]:
    """
    Decompose a complex query into sub-queries for multi-retrieval.
    Returns a list of non-empty strings (at least the original if no split).
    """
    if not query or not query.strip():
        return []
    q = query.strip()
    parts = _split_by_patterns(q)
    parts = [_trim_conjunction(p) for p in parts if p]
    # Dedupe while preserving order; cap to avoid runaway retrieval
    seen: set = set()
    unique: List[str] = []
    for p in parts:
        key = p.lower()
        if key not in seen and len(unique) < max_subqueries:
            seen.add(key)
            unique.append(p)
    return unique if unique else [q]
