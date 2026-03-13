"""
Full RAG pipeline: query → country detection → security guardrails → intent classification
→ query reformulation → query decomposition → hybrid retrieval (with metadata filtering)
→ context build → LLM → grounded response. Optional response sanitization.
"""

import os
import re
from dataclasses import dataclass
from typing import Any, List, Optional

from app.guardrails.prompt_injection import detect_prompt_injection
from app.guardrails.security_filter import check_restricted_data
from app.rag.country_filter import resolve_countries
from app.rag.hybrid_search import HybridRetriever
from app.rag.intent_classifier import Intent, classify_intent
from app.rag.prompt_builder import build_rag_prompt
from app.rag.query_decomposition import decompose_query
from app.rag.query_reformulation import reformulate_query


@dataclass
class RAGResponse:
    response: str
    blocked: bool = False
    block_reason: Optional[str] = None


def _call_llm(prompt: str) -> str:
    """Call LLM via OpenRouter (if OPENROUTER_API_KEY set) or OpenAI. Falls back to message if no key."""
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    api_key = (openrouter_key or openai_key or "").strip()
    if not api_key:
        return (
            "[No OPENROUTER_API_KEY or OPENAI_API_KEY set in .env. Set one to use LLM answers.] "
            "Here is the retrieved context you could use to answer the question."
        )
    try:
        from openai import OpenAI

        if openrouter_key and openrouter_key.strip():
            # OpenRouter: OpenAI-compatible API at openrouter.ai
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key.strip(),
            )
            model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        else:
            client = OpenAI(api_key=openai_key)
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        err = str(e).lower()
        if "401" in err or "user not found" in err or "unauthorized" in err:
            return (
                "**Authentication failed.** Check your `OPENROUTER_API_KEY` in `.env` — "
                "it may be invalid or expired. Get or reset your key at [openrouter.ai](https://openrouter.ai/keys)."
            )
        return f"[LLM error: {e}] Use the context above to answer."


def _sanitize_response(text: str) -> str:
    """Remove any leaked restricted terms from the model output."""
    bad = ["supplier", "margin", "internal notes", "warehouse", "profit margin"]
    out = text
    for b in bad:
        if b.lower() in out.lower():
            out = re.sub(re.escape(b), "[redacted]", out, flags=re.I)
    return out


def _merge_retrieval_results(
    result_lists: List[List[dict]], top_k: int, id_key: str = "product_id"
) -> List[dict]:
    """Merge multiple retrieval result lists by id_key, keeping best score per doc."""
    by_id: dict = {}
    for lst in result_lists:
        for doc in lst:
            doc_id = doc.get(id_key) or id(doc)
            score = doc.get("score", 0.0)
            if doc_id not in by_id or (doc.get("score") or 0) > (
                by_id[doc_id].get("score") or 0
            ):
                by_id[doc_id] = dict(doc)
    # Sort by score descending, take top_k
    ordered = sorted(by_id.values(), key=lambda d: -(d.get("score") or 0))
    return ordered[:top_k]


def run_rag(
    query: str,
    country: Optional[str] = None,
    top_k: int = 5,
) -> RAGResponse:
    """
    1. Detect country (from query or provided).
    2. Run security guardrails (prompt injection + restricted data).
    3. Intent classification (block if restricted/out-of-scope).
    4. Query reformulation for better retrieval.
    5. Query decomposition for multi-part prompts; retrieve per sub-query and merge.
    6. Hybrid retrieve with country + optional category filter; strict metadata filtering.
    7. Build context and send to LLM (with intent hint to stay on track).
    8. Sanitize response and return.
    """
    # 1. Countries (single or multiple, e.g. Ghana and Nigeria)
    resolved_countries = resolve_countries(query, country)

    # 2. Security: prompt injection
    inj = detect_prompt_injection(query)
    if inj.is_injection:
        return RAGResponse(
            response=inj.message or "Request denied.",
            blocked=True,
            block_reason="prompt_injection",
        )

    # 2. Security: restricted data
    sec = check_restricted_data(query)
    if not sec.allowed:
        return RAGResponse(
            response=sec.message or "Request denied.",
            blocked=True,
            block_reason="restricted_data",
        )

    # 3. Intent classification (ensure LLM stays on track; block restricted/out-of-scope)
    intent_result = classify_intent(query)
    if intent_result.block and intent_result.message:
        return RAGResponse(
            response=intent_result.message,
            blocked=True,
            block_reason="intent_block",
        )

    intent = intent_result.intent
    prefer_policy = intent == Intent.WARRANTY_POLICY
    # Strict category filter only when you need policy-only docs; here we use prefer_policy to boost
    allowed_categories: Optional[List[str]] = None

    # 4. Query reformulation (improve retrieval accuracy)
    reformulated = reformulate_query(query)

    # 5. Query decomposition (multi-part prompts)
    sub_queries = decompose_query(reformulated, max_subqueries=5)
    # Reformulate each sub-query for retrieval
    sub_queries_for_retrieval = [reformulate_query(sq) for sq in sub_queries]

    retriever = HybridRetriever(top_k=top_k)
    if len(sub_queries_for_retrieval) == 1:
        docs = retriever.search(
            query=sub_queries_for_retrieval[0],
            country=resolved_countries[0] if len(resolved_countries) == 1 else None,
            countries=resolved_countries if len(resolved_countries) > 1 else None,
            top_k=top_k,
            prefer_policy=prefer_policy,
            allowed_categories=allowed_categories,
        )
    else:
        per_query_docs = [
            retriever.search(
                query=sq,
                country=resolved_countries[0] if len(resolved_countries) == 1 else None,
                countries=resolved_countries if len(resolved_countries) > 1 else None,
                top_k=top_k,
                prefer_policy=prefer_policy,
                allowed_categories=allowed_categories,
            )
            for sq in sub_queries_for_retrieval
        ]
        docs = _merge_retrieval_results(per_query_docs, top_k)

    # 6. Build prompt (with intent hint) and call LLM
    prompt = build_rag_prompt(query, docs, countries=resolved_countries, intent=intent)
    answer = _call_llm(prompt)

    # 7. Sanitize
    answer = _sanitize_response(answer)

    return RAGResponse(response=answer, blocked=False)
