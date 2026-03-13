# App — What Was Done Here

The `app` package is the **backend of the Global Retail Intelligence Engine**: a FastAPI service that runs a full RAG (Retrieval-Augmented Generation) pipeline so every answer is grounded in product and policy data, filtered by region, and protected by security guardrails.

---

## High-level flow

```
User query (+ optional country)
    → main.py (FastAPI app)
    → api/chat.py (POST /api/chat)
    → services/query_service.py (optional thin wrapper)
    → rag/pipeline.run_rag()
        1. country_filter: resolve country from query or request
        2. guardrails: prompt_injection + security_filter (block if unsafe)
        3. intent_classifier: classify intent (pricing, warranty, list_products, etc.); block restricted/out-of-scope
        4. query_reformulation: expand synonyms/abbreviations for better retrieval
        5. query_decomposition: split multi-part prompts into sub-queries; retrieve per sub-query and merge
        6. rag/hybrid_search: vector (FAISS) + BM25, country/category filter, strict metadata filtering (allowed fields only)
        7. prompt_builder: build prompt with context + intent hint (stay on track) + user question
        8. LLM call (OpenRouter or OpenAI)
        9. response sanitization
    → ChatResponse (text) back to client
```

---

## Directory layout and roles

| Path | Purpose |
|------|--------|
| **`main.py`** | FastAPI app: loads `.env`, mounts CORS, registers `/api` router, exposes `/health`. |
| **`index.py`** | Vercel serverless entrypoint: exposes the same FastAPI `app` for serverless deployment. |
| **`api/chat.py`** | Chat HTTP API: `POST /api/chat` with `query` and optional `country`; calls RAG pipeline and returns `ChatResponse`. |
| **`services/query_service.py`** | Thin wrapper around `run_rag()` for use by the API or other callers. |
| **`rag/pipeline.py`** | **Core RAG pipeline**: country resolution → security checks → hybrid retrieval → prompt build → LLM → sanitization. Returns `RAGResponse`. |
| **`rag/hybrid_search.py`** | **HybridRetriever**: loads FAISS index + metadata and BM25 corpus; runs vector + BM25 search, reciprocal-rank fusion, optional country filter and policy-doc boost. |
| **`rag/retriever.py`** | Re-exports `HybridRetriever` for backward compatibility. |
| **`rag/prompt_builder.py`** | Builds the RAG prompt: system instructions (answer only from context, no internal data) + retrieved context (product/policy fields) + user question. |
| **`rag/country_filter.py`** | Resolves user country: from request param or by extracting from query (e.g. “from Ghana”, “in the UK”). Used for metadata filtering. |
| **`rag/query_reformulation.py`** | Context query reformulation: expand synonyms/abbreviations to improve retrieval accuracy. |
| **`rag/query_decomposition.py`** | Query decomposition: split multi-part prompts into sub-queries; retrieve per sub-query and merge. |
| **`rag/intent_classifier.py`** | Intent classification; block restricted/out-of-scope so the LLM stays on track. |
| **`rag/metadata_filter.py`** | Strict metadata filtering: only allowed fields returned for document access and security. |
| **`guardrails/security_filter.py`** | Blocks queries that ask for restricted data (supplier, margin, internal notes, warehouse, profit, etc.); returns a safe refusal message. |
| **`guardrails/prompt_injection.py`** | Detects prompt-injection patterns (“ignore previous instructions”, etc.) and blocks with a refusal. |

---

## What was implemented

### 1. **API layer**
- **FastAPI** app with CORS and health check.
- **POST /api/chat**: body `{ "query": "...", "country": "..." }` (country optional); response `{ "response": "..." }`.
- **Vercel**: `index.py` exposes the app for serverless so the same backend can run on Vercel.

### 2. **RAG pipeline** (`rag/pipeline.py`)
- **Country**: `resolve_country(query, country)` so retrieval can be filtered by region.
- **Security (before retrieval)**:
  - **Prompt injection**: if detected → immediate block and refusal.
  - **Restricted data**: if the query asks for supplier, margin, internal notes, etc. → block and refusal.
- **Retrieval**: `HybridRetriever.search(query, country=..., prefer_policy=...)`:
  - **Hybrid**: FAISS (vector) + BM25 (keyword); reciprocal rank fusion.
  - **Metadata filter**: by `country` so only that region’s products/policies are used.
  - **Hierarchical**: for warranty/policy-style queries, `prefer_policy=True` boosts documents with `category == "Policy"`.
- **Prompt**: `build_rag_prompt(query, docs, country)` — system instructions + context from retrieved docs + user question.
- **LLM**: OpenRouter (if `OPENROUTER_API_KEY` set) or OpenAI; model configurable via env.
- **Sanitization**: response text is sanitized for leaked restricted terms before returning.

### 3. **Retrieval** (`rag/hybrid_search.py`)
- Loads **FAISS** index and **metadata.json** from `vector_store/faiss_index/`.
- Builds **BM25** over `searchable_text` for exact SKU / keyword match.
- **Vector search**: Sentence Transformer (`all-MiniLM-L6-v2`) encodes query; FAISS returns top candidates.
- **Fusion**: reciprocal rank fusion of vector and BM25 ranks; optional +1.5 boost for Policy docs when `prefer_policy=True`.
- **Country filter**: after fusion, results are filtered by `country`; top `top_k` returned with scores.

### 4. **Prompt building** (`rag/prompt_builder.py`)
- Instructs the model: answer only from context; never mention suppliers, margins, internal notes, warehouse.
- Injects user region when `country` is set.
- Formats each retrieved doc as: Product, ID, Country, Price, Specs (from metadata fields).

### 5. **Country handling** (`rag/country_filter.py`)
- `extract_country_from_query(query)`: regex over a fixed list of countries (e.g. “from Ghana”, “in the UK”).
- `resolve_country(query, provided_country)`: uses `provided_country` if present, else extraction from query.

### 6. **Guardrails**
- **security_filter**: regex patterns for supplier, margin, internal notes, warehouse, profit, etc.; returns `SecurityResult(allowed=False, message=REFUSAL_MESSAGE)` when matched.
- **prompt_injection**: regex patterns for “ignore previous instructions”, “disregard”, “new instructions”, etc.; returns `InjectionResult(is_injection=True, message=REFUSAL_MESSAGE)` when matched.

---

## Summary

In **`app`** we implemented:

1. **HTTP API** for chat (FastAPI + Vercel entrypoint).
2. **End-to-end RAG pipeline** with country resolution, security checks, hybrid retrieval (vector + BM25), country and policy-aware ranking, prompt construction, LLM call, and response sanitization.
3. **Hybrid retrieval** (FAISS + BM25) with metadata filtering and hierarchical boost for policy docs.
4. **Security**: prompt-injection detection and restricted-data blocking before retrieval; response sanitization after the LLM.

All of this ensures **region-correct answers** (e.g. Ghana → GHS), **reliable SKU/product lookup** (BM25), **policy answers from policy docs** (hierarchical retrieval), and **no exposure of internal data** (guardrails + sanitization).
