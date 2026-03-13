import os
import json
from pathlib import Path
from typing import Any, List, Optional

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from app.rag.metadata_filter import filter_docs_metadata


def _is_offline_mode() -> bool:
    return os.environ.get("HF_HUB_OFFLINE", "").strip() == "1" or os.environ.get("TRANSFORMERS_OFFLINE", "").strip() == "1"


def _load_sentence_transformer(model_name: str):
    """Load model; use cache only when offline env is set or on connection error."""
    try:
        if _is_offline_mode():
            return SentenceTransformer(model_name, local_files_only=True)
        return SentenceTransformer(model_name)
    except Exception as e:
        err_str = str(e).lower()
        if "nodename nor servname" in err_str or "connection" in err_str or "network" in err_str or "client has been closed" in err_str:
            return SentenceTransformer(model_name, local_files_only=True)
        raise

# Default index path relative to project root
def _default_index_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "vector_store" / "faiss_index"


class HybridRetriever:
    def __init__(
        self,
        index_dir: Optional[Path] = None,
        model_name: str = "all-MiniLM-L6-v2",
        top_k: int = 5,
    ):
        self.index_dir = index_dir or _default_index_path()
        self.model_name = model_name
        self.top_k = top_k
        self._index: Optional[faiss.Index] = None
        self._metadata: list[dict[str, Any]] = []
        self._model: Optional[SentenceTransformer] = None
        self._bm25: Optional[BM25Okapi] = None
        self._tokenized_corpus: Optional[list[list[str]]] = None

    def _ensure_loaded(self) -> None:
        if self._index is not None:
            return
        if not self.index_dir.exists():
            raise FileNotFoundError(
                f"Vector index not found at {self.index_dir}. Run scripts/run_indexing.py first."
            )
        self._index = faiss.read_index(str(self.index_dir / "index.faiss"))
        with open(self.index_dir / "metadata.json", "r", encoding="utf-8") as f:
            self._metadata = json.load(f)
        self._model = _load_sentence_transformer(self.model_name)
        # BM25 on searchable_text
        corpus = [m.get("searchable_text", "") for m in self._metadata]
        self._tokenized_corpus = [doc.lower().split() for doc in corpus]
        self._bm25 = BM25Okapi(self._tokenized_corpus)

    def _filter_by_country(self, indices: list[int], country: Optional[str]) -> list[int]:
        if not country or not country.strip():
            return indices
        country_lower = country.strip().lower()
        return [
            i for i in indices
            if self._metadata[i].get("country", "").lower() == country_lower
        ]

    def _filter_by_countries(self, indices: List[int], countries: Optional[List[str]]) -> List[int]:
        """Keep only docs whose country is in the given list (any of Ghana, Nigeria, etc.)."""
        if not countries or not any(c and str(c).strip() for c in countries):
            return indices
        allowed = {str(c).strip().lower() for c in countries if c and str(c).strip()}
        return [
            i for i in indices
            if self._metadata[i].get("country", "").lower() in allowed
        ]

    def _filter_by_category(self, indices: List[int], allowed_categories: Optional[List[str]]) -> List[int]:
        """Keep only docs whose category is in allowed_categories (case-insensitive)."""
        if not allowed_categories:
            return indices
        allowed = {c.strip().lower() for c in allowed_categories if c}
        return [
            i for i in indices
            if (self._metadata[i].get("category") or "").strip().lower() in allowed
        ]

    def search(
        self,
        query: str,
        country: Optional[str] = None,
        countries: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        prefer_policy: bool = False,
        allowed_categories: Optional[List[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Run hybrid search (vector + BM25), optionally filter by country/countries and category.
        When prefer_policy is True (warranty/policy queries), boost docs with category Policy.
        countries: if set, return docs from any of these countries (e.g. Ghana and Nigeria).
        country: single country (used if countries is not set). Backward compatible.
        allowed_categories: if set, strict filter to only these categories (e.g. ["Policy"]).
        Returns list of metadata dicts (allowed fields only) with score, ordered by relevance.
        """
        k = top_k or self.top_k
        # When asking for multiple countries, fetch more so we get results per country
        if countries and len(countries) > 1:
            k = min(k * len(countries), 20)  # cap at 20
        self._ensure_loaded()

        # Vector search
        q_emb = self._model.encode([query])
        q_emb = np.array(q_emb, dtype=np.float32)
        faiss.normalize_L2(q_emb)
        has_country_filter = country or (countries and len(countries) > 0)
        overfetch = (k * 20) if (has_country_filter or allowed_categories) else (k * 3)
        vector_k = min(overfetch, len(self._metadata))
        scores_vec, indices_vec = self._index.search(q_emb, vector_k)
        indices_vec = indices_vec[0].tolist()
        scores_vec = scores_vec[0].tolist()

        # BM25 search
        tokenized_query = query.lower().split()
        bm25_scores = self._bm25.get_scores(tokenized_query)
        order_bm25 = np.argsort(bm25_scores)[::-1][: vector_k]
        indices_bm25 = order_bm25.tolist()
        scores_bm25_list = bm25_scores.tolist()

        # Reciprocal rank fusion: score = 1/(rank_vec) + 1/(rank_bm25)
        rank_vec = {idx: r for r, idx in enumerate(indices_vec, 1)}
        rank_bm25 = {int(idx): r for r, idx in enumerate(indices_bm25, 1)}
        all_indices = set(indices_vec) | set(indices_bm25)
        fused = []
        for idx in all_indices:
            rv = rank_vec.get(idx, 1000)
            rb = rank_bm25.get(idx, 1000)
            score = 1.0 / rv + 1.0 / rb
            # Hierarchical retrieval: boost Policy docs for policy-style queries
            if prefer_policy and (self._metadata[idx].get("category") or "").strip().lower() == "policy":
                score += 1.5
            fused.append((idx, score))
        fused.sort(key=lambda x: -x[1])

        # Apply country filter: prefer countries list (multi-country), else single country
        ordered_indices = [idx for idx, _ in fused]
        if countries and len(countries) > 0:
            filtered = self._filter_by_countries(ordered_indices, countries)
        else:
            filtered = self._filter_by_country(ordered_indices, country)
        if not filtered and (country or (countries and len(countries) > 0)):
            filtered = ordered_indices[:k]
        else:
            filtered = filtered[:k] if filtered else ordered_indices[:k]

        if allowed_categories:
            # Apply category filter to full ordered list so we get enough matches
            category_filtered = self._filter_by_category(ordered_indices, allowed_categories)
            if category_filtered:
                filtered = category_filtered[:k]
            else:
                filtered = ordered_indices[:k]  # fallback if no category match

        # For generic queries (e.g. "give me 5 products' prices"), fused scores can be
        # low and results arbitrary; ensure we have enough by falling back to diverse docs
        if len(filtered) < k and not country:
            step = max(1, len(self._metadata) // k)
            fallback = [min(i * step, len(self._metadata) - 1) for i in range(k)]
            fallback = list(dict.fromkeys(fallback))[:k]  # unique, preserve order
            filtered = filtered + [i for i in fallback if i not in filtered][: k - len(filtered)]

        results = []
        for idx in filtered:
            meta = dict(self._metadata[idx])
            meta["score"] = next(s for i, s in fused if i == idx)
            results.append(meta)
        # Strict metadata filtering: only allowed fields returned
        return filter_docs_metadata(results)
