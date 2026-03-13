"""
Context Query Reformulation: improve retrieval accuracy by expanding and normalizing
the user query before retrieval (synonyms, abbreviations, product-focused phrasing).
"""

import re
from typing import List, Tuple

# Expansion rules: (pattern, replacement) for retrieval-oriented reformulation.
# Applied case-insensitively; we preserve original terms and add expansions.
SYNONYM_EXPANSIONS: List[Tuple[str, str]] = [
    (r"\bprice(s?)\b", r"\g<0> cost"),
    (r"\bcost(s?)\b", r"\g<0> price"),
    (r"\bspecs?\b", r"specs technical specifications"),
    (r"\bspecifications?\b", r"specifications technical specs"),
    (r"\bhow much\b", r"how much price cost"),
    (r"\bwarranty\b", r"warranty guarantee coverage"),
    (r"\bpolicy\b", r"policy warranty return"),
    (r"\bavailable\b", r"available in stock"),
    (r"\bproduct(s?)\b", r"\g<0> item"),
]
COMPILED_EXPANSIONS = [(re.compile(p, re.I), r) for p, r in SYNONYM_EXPANSIONS]

# Abbreviations to expand (whole-word)
ABBREVS = {
    "specs": "specifications",
    "info": "information",
    "approx": "approximately",
    "qty": "quantity",
    "reviews": "reviews ratings",
}


def _expand_abbrevs(text: str) -> str:
    out = text
    for abbr, full in ABBREVS.items():
        out = re.sub(rf"\b{re.escape(abbr)}\b", full, out, flags=re.I)
    return out


def _apply_synonym_expansions(text: str) -> str:
    out = text
    for pat, repl in COMPILED_EXPANSIONS:
        out = pat.sub(repl, out)
    return out


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def reformulate_query(query: str) -> str:
    """
    Reformulate the query for better retrieval: expand abbreviations and add
    retrieval-relevant synonyms so that vector/BM25 can match more relevant docs.
    Returns a single string suitable for hybrid search.
    """
    if not query or not query.strip():
        return query
    q = query.strip()
    q = _expand_abbrevs(q)
    q = _apply_synonym_expansions(q)
    q = _normalize_whitespace(q)
    # Keep original query terms first so intent is preserved, then append expansions
    # (expansions already in-place above; we could alternatively do "original + " + expanded)
    return q
