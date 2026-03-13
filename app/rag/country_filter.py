"""
Extract country or countries from user query or use provided value.
Used by the RAG pipeline for metadata filtering.
Supports single country or multiple (e.g. "Ghana and Nigeria", "in Ghana, Nigeria").
"""

import re
from typing import List, Optional

# Common country names (subset) for simple extraction; normalize to canonical form
COUNTRIES = [
    "Ghana",
    "Nigeria",
    "Côte d'Ivoire",
    "Ivory Coast",
    "Cote d'Ivoire",
    "South Africa",
    "Kenya",
    "Germany",
    "United Kingdom",
    "UK",
    "France",
    "Netherlands",
    "United States",
    "USA",
    "US",
    "Canada",
]
# Map aliases to canonical name for consistency
COUNTRY_ALIAS = {
    "uk": "United Kingdom",
    "usa": "United States",
    "us": "United States",
    "ivory coast": "Côte d'Ivoire",
    "cote d'ivoire": "Côte d'Ivoire",
}


def _normalize_country(c: str) -> str:
    """Return canonical country name."""
    key = c.strip().lower()
    return COUNTRY_ALIAS.get(key, c.strip())


def extract_country_from_query(query: str) -> Optional[str]:
    """
    Try to infer a single country from phrases like 'from Ghana', 'in the UK'.
    Returns None if not found. For multiple countries use extract_countries_from_query.
    """
    countries = extract_countries_from_query(query)
    return countries[0] if countries else None


def extract_countries_from_query(query: str) -> List[str]:
    """
    Extract one or more countries from the query.
    Handles: "in Ghana and Nigeria", "Ghana, Nigeria", "Ghana vs Nigeria", "from Ghana and Nigeria", etc.
    Returns a list of canonical country names (may be empty).
    """
    q = query.strip()
    found: List[str] = []
    # Split on " and ", ",", " vs ", " versus " so comparison phrases yield both countries
    for part in re.split(r"\s+and\s+|\s*,\s*|\s+vs\.?\s+|\s+versus\s+", q, flags=re.I):
        part = part.strip()
        for c in COUNTRIES:
            # Match "Ghana", "in Ghana", "from Ghana", "in the Ghana" (allow "the")
            if re.search(
                rf"(?:^|\s)(?:in|from|in\s+the)?\s*{re.escape(c)}\b", part, re.I
            ):
                canonical = _normalize_country(c)
                if canonical not in found:
                    found.append(canonical)
                break
    # If no multi-country pattern, fall back to single-country extraction
    if not found:
        single = None
        for c in COUNTRIES:
            if re.search(
                rf"\b(from|in|shopping\s+in|shopping\s+from|I\s+am\s+in)\s+{re.escape(c)}\b",
                q,
                re.I,
            ):
                single = _normalize_country(c)
                break
        if single:
            found = [single]
    return found


def resolve_country(query: str, provided_country: Optional[str]) -> Optional[str]:
    """Use provided_country if set, else try to extract a single country from query. Backward compatible."""
    countries = resolve_countries(query, provided_country)
    return countries[0] if countries else None


def resolve_countries(query: str, provided_country: Optional[str] = None) -> List[str]:
    """
    Resolve to a list of countries for filtering.
    - If provided_country is set: split by " and " or "," and normalize, then merge with any
      countries mentioned in the query (so "Ghana" in UI + "compare with Nigeria" gives both).
    - Else: extract from query via extract_countries_from_query.
    Returns list of canonical country names (empty = no country filter).
    """
    countries = []
    if provided_country and str(provided_country).strip():
        raw = str(provided_country).strip()
        parts = re.split(r"\s+and\s+|\s*,\s*", raw, flags=re.I)
        countries.extend([_normalize_country(p) for p in parts if p.strip()])
    countries.extend(extract_countries_from_query(query))
    return countries
