"""
Metadata Filtering: strict document access restrictions and security.
- Only allow specific metadata fields to leave the retriever (no internal/raw fields).
- Enforce filter dimensions (country, category) before returning docs.
"""
from typing import Any, Dict, List, Optional

# Fields allowed to be returned to the pipeline/LLM. Anything else is stripped.
ALLOWED_RETURN_FIELDS = frozenset({
    "country",
    "product_id",
    "category",
    "item_name",
    "price_local",
    "currency",
    "technical_specs",
    "searchable_text",
    "score",  # added by retriever
})

# Categories that are allowed in retrieval (e.g. Policy for warranty queries).
# If None, no category allow-list (all categories allowed).
ALLOWED_CATEGORIES: Optional[frozenset[str]] = None  # None = allow all


def filter_doc_metadata(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strip any metadata field not in ALLOWED_RETURN_FIELDS for strict access control.
    Returns a new dict with only allowed keys.
    """
    return {k: v for k, v in doc.items() if k in ALLOWED_RETURN_FIELDS}


def filter_docs_metadata(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply filter_doc_metadata to each doc."""
    return [filter_doc_metadata(d) for d in docs]


def allow_category(doc: Dict[str, Any], allowed_categories: Optional[frozenset[str]]) -> bool:
    """
    Return True if the doc is allowed by category filter.
    If allowed_categories is None, always True.
    """
    if allowed_categories is None:
        return True
    cat = (doc.get("category") or "").strip().lower()
    return cat in {c.lower() for c in allowed_categories}
