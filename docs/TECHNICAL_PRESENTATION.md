# GlobalCart Retail Intelligence Engine — Technical Presentation

## 1. Overview

**GlobalCart Retail Intelligence Engine** is a production-style **Advanced RAG (Retrieval-Augmented Generation)** pipeline for:

- **Product search** — by name or description  
- **SKU lookup** — by product ID or model number  
- **Regional pricing** — results scoped by user country (e.g. Ghana → GHS, Netherlands → EUR)  
- **Policy summaries** — warranties, returns, regional policies  
- **Security guardrails** — blocks jailbreak attempts and never exposes internal data (supplier margins, internal notes)

The MVP runs as a single Jupyter notebook and is extended with modular **pipelines**, **API**, and **evaluation** for production use.

**Main entry points:**

| What | Where |
|------|--------|
| Full RAG demo (notebook) | [retail-intelligence.ipynb](../retail-intelligence.ipynb) |
| Project readme | [README.md](../README.md) |
| Roadmap | [docs/ROADMAP.md](ROADMAP.md) |

---

## 2. Architecture

### 2.1 High-level flow

Each step below is linked to the file(s) or folder where it is implemented.

```
User Query + (optional) Country
         │
         ▼
┌─────────────────────┐  ← Notebook §8; app.rag (intent)
│ Intent classification│  product_lookup | sku_lookup | policy_question | availability_check
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌──────────────────────┐  ← Notebook §7; region filter in retrieval
│ Region detection    │────▶│ Metadata filter       │  (country → region)
└──────────┬──────────┘     └──────────┬───────────┘
           │                           │
           ▼                           ▼
┌─────────────────────────────────────────────────┐  ← build_vector_index.py; run_retrieval.py; app.rag.hybrid_search
│ Hybrid retrieval (vector + BM25)                │
│ • FAISS (sentence-transformers all-MiniLM-L6-v2)│
│ • BM25 (rank-bm25)                              │
│ • Fusion: 0.6 vector + 0.4 BM25, normalized      │
└──────────┬──────────────────────────────────────┘
           │
           ▼
┌─────────────────────┐  ← Notebook §9; app.rag (hierarchical rank)
│ Hierarchical rank   │  policy_first vs product_first by intent
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌──────────────────────┐  ← Notebook §10; app.rag (guardrails)
│ Security guardrails │────▶│ Refusal if jailbreak  │  (no internal_notes, margins)
└──────────┬──────────┘     └──────────────────────┘
           │
           ▼
┌─────────────────────┐  ← Notebook §11; app.rag (context builder)
│ Context builder     │  Safe fields only → truncated context (e.g. 2000 chars)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐  ← Notebook §12; app.rag (LLM)
│ LLM (OpenRouter)    │  gpt-4o-mini, RAG prompt with context + query
└──────────┬──────────┘
           │
           ▼
      Response to user  ← Gradio in notebook; Streamlit frontend → /api/chat
```

---

### 2.1.1 How to explain each step during the presentation

Use these talking points when walking through the flow. Each step has a **one-liner**, **what to say**, and **why it matters**.

**30-second version:** “The user sends a query and optional country. We classify intent, detect region, run hybrid search (vector + keyword), reorder by intent, run security checks, build a safe context from the top docs, and send that plus the query to an LLM that answers only from context. The answer goes back to the UI.”

**2-minute version:** Walk the diagram step by step: intent (product vs SKU vs policy) → region filter (so we only show that country’s data) → hybrid retrieval (semantic + BM25, best of both) → hierarchical rank (policy first or product first) → guardrails (block jailbreaks, no internal data) → context (safe fields only) → LLM (RAG with strict prompt) → response. Mention that sensitive data is dropped at ingestion and never reaches the index or the model.

---

#### Step 0: User input

| One-liner | What to say | Why it matters |
|-----------|-------------|-----------------|
| **Query + optional country** | “The user sends a question—for example ‘What does the Solar Inverter cost in Ghana?’—and can optionally choose their country in the UI. We use both to tailor retrieval and the answer.” | The same query can mean different things in different regions (currency, availability, policies). Capturing country up front keeps answers accurate and compliant. |

---

#### Step 1: Intent classification

| One-liner | What to say | Why it matters |
|-----------|-------------|-----------------|
| **We detect what the user is asking for** | “Before we search, we classify the intent: product lookup—general search; SKU lookup—they mentioned a product ID like NL-L-5042; policy question—warranty, returns, refunds; or availability check—stock and quantity.” | Intent drives which documents we prioritize. For a policy question we push policy docs to the top; for a SKU we rely more on keyword match so the exact ID is found.” |

**Where:** Notebook §8; app.rag (intent). Logic: SKU pattern (e.g. `XX-XXX-1234`), then keywords (warranty, return, policy → policy_question; stock, available → availability), else product_lookup.

---

#### Step 2: Region detection and metadata filter

| One-liner | What to say | Why it matters |
|-----------|-------------|-----------------|
| **We infer or use the user’s region and filter by it** | “We map the user’s country—from the UI or from the query—to a canonical region, e.g. Ghana or Netherlands. Then we filter retrieved results so we only keep products and policies for that region. So ‘price in Ghana’ only sees Ghana rows and GHS.” | Without this, we might show EUR prices to someone in Ghana or mix policies from different countries. Filtering keeps answers regionally correct. |

**Where:** Notebook §7; region filter in retrieval. Mapping examples: "ghana"/"gh" → Ghana, "netherlands"/"nl"/"dutch" → Netherlands.

---

#### Step 3: Hybrid retrieval (vector + BM25)

| One-liner | What to say | Why it matters |
|-----------|-------------|-----------------|
| **We search with both meaning and keywords, then combine** | “We run two searches in parallel: a vector search using embeddings—so we match by meaning, e.g. ‘kettle with timer’ finds ‘Smart Kettle Pro’—and BM25 keyword search, which is strong for exact SKUs and specs like ‘50W’ or ‘IPX5’. We normalize both score lists and combine them with fixed weights, e.g. 60% vector and 40% BM25, and take the top-k.” | Vector alone can miss exact IDs and specs; keyword alone can miss paraphrased questions. Hybrid gives us both semantic and lexical recall. |

**Where:** [build_vector_index.py](../pipelines/indexing/build_vector_index.py) (FAISS); notebook §4–6; app.rag.hybrid_search. Model: sentence-transformers `all-MiniLM-L6-v2`; index: FAISS (cosine via L2-normalized inner product).

---

#### Step 4: Hierarchical ranking

| One-liner | What to say | Why it matters |
|-----------|-------------|-----------------|
| **We reorder results by intent so the right doc type is first** | “We don’t just take the top-k by score. We reorder by intent: for policy questions we put policy documents first, then products; for product or SKU lookups we put products first, then policies. So the context the LLM sees starts with the most relevant type of document.” | This avoids answering a warranty question with a product snippet or a price question with a policy paragraph. |

**Where:** Notebook §9; app.rag (hierarchical rank). doc_type in metadata: "policy" vs "product".

---

#### Step 5: Security guardrails and refusal

| One-liner | What to say | Why it matters |
|-----------|-------------|-----------------|
| **We block jailbreaks and never send internal data to the LLM** | “Before we build context or call the LLM, we check the user query for jailbreak patterns—e.g. ‘ignore instructions’, ‘reveal supplier margin’, ‘internal notes’. If we detect that, we return a fixed refusal message and never call the model. We also never put internal data—supplier names, margins, internal notes—into the index or the context; that column is dropped at ingestion.” | This protects confidential data and prevents prompt injection from leaking internal information. |

**Where:** Notebook §10; app.rag (guardrails). Sensitive data is dropped in [clean_data.py](../pipelines/ingestion/clean_data.py); context uses safe fields only.

---

#### Step 6: Context builder

| One-liner | What to say | Why it matters |
|-----------|-------------|-----------------|
| **We turn the top documents into a short, safe text block** | “We take the top-k retrieved documents and build a single context string using only safe fields: product name, ID, price, currency, specs, stock, policy text, region. We deliberately exclude anything internal. We truncate to a character limit—e.g. 2000—so we stay within the model’s window. That string is what we send to the LLM as the only source of facts.” | The model is instructed to answer only from this context, so we control what it can and cannot say. |

**Where:** Notebook §11; app.rag (context builder). Safe fields: product_name, product_id, price, currency, specs, stock, policy_text, region, doc_type.

---

#### Step 7: LLM generation (RAG)

| One-liner | What to say | Why it matters |
|-----------|-------------|-----------------|
| **The model answers only from the context we provide** | “We call an LLM—via OpenRouter, e.g. GPT-4o-mini—with a strict prompt: here is the context, here is the user question, answer only from the context, do not invent prices, and never reveal internal data. The model generates a natural-language answer grounded in that context.” | RAG keeps answers factual and within our data; the prompt enforces safety and prevents hallucination on prices or policies. |

**Where:** Notebook §12; app.rag (LLM). Config: [.env.example](../.env.example) — OPENROUTER_API_KEY, optional OPENROUTER_MODEL.

---

#### Step 8: Response to user

| One-liner | What to say | Why it matters |
|-----------|-------------|-----------------|
| **The answer is shown in the UI** | “The response is returned to the client—either the Gradio UI in the notebook or the Streamlit frontend that calls our API. The user sees a single, coherent answer with the right currency and region.” | One pipeline serves both the demo (notebook) and the production-style UI (Streamlit → API). |

**Where:** [retail-intelligence.ipynb](../retail-intelligence.ipynb) §14 (Gradio); [frontend/chat_app.py](../frontend/chat_app.py) (Streamlit → POST /api/chat).

---

#### Optional: Offline data pipeline (for context)

If someone asks “where does the data come from?”, use this:

| One-liner | What to say | Why it matters |
|-----------|-------------|-----------------|
| **We clean once, then index; retrieval uses the index** | “Raw product data lives in CSVs—we can generate it with a script or ingest from an Excel. A cleaning step merges sources, drops internal notes, standardizes country and category, and builds one searchable text per row. An indexing step embeds that text with sentence-transformers and builds a FAISS index plus a metadata JSON. At query time we load that index and run hybrid search; we don’t re-embed the corpus on every request.” | Separating ingestion, cleaning, and indexing keeps the pipeline clear and makes it easy to refresh the index when data changes. |

**Where:** [pipelines/ingestion/clean_data.py](../pipelines/ingestion/clean_data.py) → [data/processed/products_clean.csv](../data/processed/products_clean.csv); [pipelines/indexing/build_vector_index.py](../pipelines/indexing/build_vector_index.py) → [vector_store/faiss_index/](../vector_store/faiss_index/). One command: [scripts/run_indexing.py](../scripts/run_indexing.py).

---

### 2.2 Data flow (with links)

| Stage | Input (link) | Output (link) | Deeper explanation |
|--------|--------------|----------------|---------------------|
| **Raw data** | [data/raw/products_raw.csv](../data/raw/products_raw.csv), [data/raw/task1_data.csv](../data/raw/task1_data.csv) | — | **products_raw.csv** is the main product catalog (or generated by [scripts/generate_retail_dataset.py](../scripts/generate_retail_dataset.py)). **task1_data.csv** is produced by [pipelines/ingestion/ingest_task_data.py](../pipelines/ingestion/ingest_task_data.py) from the Task 1 Excel file (or from hardcoded extra rows for NL-L-5042, Netherlands warranty, etc.). Both use the same schema: Product_ID, Country, Category, Item_Name, Price_Local, Currency, Technical_Specs, Internal_Notes. |
| **Cleaning** | Raw CSVs above | [data/processed/products_clean.csv](../data/processed/products_clean.csv) | [pipelines/ingestion/clean_data.py](../pipelines/ingestion/clean_data.py) **concatenates** raw + task1, **drops** the `Internal_Notes` column (sensitive data never leaves this step), **standardizes** country (e.g. UK → United Kingdom) and category (title case), and **builds** a single `searchable_text` field = `Item_Name + " " + Technical_Specs` used for both vector and keyword indexing. This is the only place where confidential fields are removed. |
| **Indexing** | [data/processed/products_clean.csv](../data/processed/products_clean.csv) | [vector_store/faiss_index/index.faiss](../vector_store/faiss_index/index.faiss), [vector_store/faiss_index/metadata.json](../vector_store/faiss_index/metadata.json) | [pipelines/indexing/build_vector_index.py](../pipelines/indexing/build_vector_index.py) loads the clean CSV, embeds each row’s `searchable_text` with **sentence-transformers** `all-MiniLM-L6-v2`, builds a **FAISS** `IndexFlatIP` (inner product on L2-normalized vectors = cosine similarity), and saves one JSON metadata record per vector (country, product_id, category, item_name, price_local, currency, technical_specs, searchable_text). BM25 is built at **runtime** from the same metadata (e.g. in app.rag or notebook) over `searchable_text` (or equivalent). |
| **Retrieval** | Query + optional country | Top-k documents | Implemented in the notebook (sections 4–6, 7) and in **app.rag** ([scripts/run_retrieval.py](../scripts/run_retrieval.py) uses `HybridRetriever`). Vector search runs against the FAISS index; BM25 runs on the tokenized corpus; scores are normalized and fused (e.g. 0.6 vector + 0.4 BM25). Results are **filtered by country** when a region is provided, then **hierarchically ordered** (policy vs product first) based on intent. |
| **Generation** | Context string + user query | Answer text | The **context** is built from the top-k docs using **safe fields only** (no internal_notes), truncated (e.g. 2000 chars), and passed with the user query to **OpenRouter** (e.g. `openai/gpt-4o-mini`) via a fixed RAG system prompt. Implemented in the notebook §12 and in `app.rag` pipeline. |

**One-command indexing:** [scripts/run_indexing.py](../scripts/run_indexing.py) runs the full pipeline: if `Task 1_ Global Retail Intelligence Engine Data.xlsx` exists, it calls `ingest_task_data` then `clean_data`, then always runs `build_vector_index`. Otherwise it runs `clean_data` (if clean CSV is missing) then `build_vector_index`.

---

### 2.3 Components (where they live and what they do)

| Component | Technology | Where in repo | Role in depth |
|-----------|------------|----------------|----------------|
| **Embeddings** | sentence-transformers `all-MiniLM-L6-v2` | [pipelines/indexing/build_vector_index.py](../pipelines/indexing/build_vector_index.py), notebook §3 | Produces 384-d vectors from product/policy text. Used for semantic similarity so queries like “kettle with timer” match “Smart Kettle Pro” and its specs even without exact keywords. |
| **Vector index** | FAISS (IndexFlatIP, L2-normalized) | [vector_store/faiss_index/](../vector_store/faiss_index/), built by [build_vector_index.py](../pipelines/indexing/build_vector_index.py) | Exact k-NN (no approximate search in this MVP). Enables fast similarity search over thousands of vectors; metadata is stored separately in JSON for filtering by country and for building context. |
| **Keyword index** | BM25 (rank-bm25) | Notebook §5; app.rag (e.g. hybrid_search) | Sparse, lexical matching. Critical for **SKU lookup** (e.g. “NL-L-5042”) and exact spec terms (e.g. “50W”, “IPX5”) that embeddings might underweight. Tokenized on whitespace; no stemming in current setup. |
| **Hybrid fusion** | 0.6 vector + 0.4 BM25 (normalized) | Notebook §6; app.rag.hybrid_search | Score normalization (min–max per retriever) then linear combination so that both semantic and keyword signals contribute. Weights can be tuned per intent later (see [ROADMAP](ROADMAP.md)). |
| **LLM** | OpenRouter → `openai/gpt-4o-mini` | Notebook §12; app.rag pipeline | Receives a strict RAG prompt: answer only from context, do not invent prices, never reveal internal data. Model is configurable via `.env` (e.g. OPENROUTER_MODEL); see [.env.example](../.env.example). |
| **Notebook UI** | Gradio | [retail-intelligence.ipynb](../retail-intelligence.ipynb) §14 | In-notebook chat interface; calls the same `run_query()` pipeline (intent → retrieval → guardrails → context → LLM). |
| **API** | FastAPI | Referenced in [Dockerfile](../Dockerfile) (`app.main`), not yet in repo | Intended to expose e.g. `POST /api/chat` with query and optional country; used by the Streamlit frontend and by evaluation. |
| **Frontend** | Streamlit | [frontend/chat_app.py](../frontend/chat_app.py) | Chat UI; sends `POST {API_URL}/api/chat` with `query` and `country`. Uses `STREAMLIT_CHAT_API_URL` (default `http://localhost:8000`). Sidebar explains how to run API and set `OPENROUTER_API_KEY`. |

---

## 3. Security and guardrails (deeper)

- **Data stripping:** The only place that ever sees `Internal_Notes` is the ingestion/cleaning step. [clean_data.py](../pipelines/ingestion/clean_data.py) **drops** the column before writing [products_clean.csv](../data/processed/products_clean.csv). The vector index and metadata are built from the clean CSV only, so internal notes **never** appear in [vector_store/faiss_index/metadata.json](../vector_store/faiss_index/metadata.json) or in any retrieval path.  
- **Context sanitization:** In the notebook (§10) and (when implemented) in app.rag, `sanitize_context()` runs on the assembled context string and removes any residual mentions of `internal_notes`, `supplier_name`, `profit_margin` (regex-based). This is a safety net in case new fields are added later.  
- **Jailbreak detection:** `is_jailbreak(query)` checks the **user query** (not the context) against: (1) a list of regex patterns (e.g. “ignore (your )?(safety )?instructions”, “reveal supplier”, “show (me )?(the )?(supplier )?margin”, “internal notes”, “override safety”, “jailbreak”), and (2) protected keywords combined with trigger phrases (“show”, “reveal”, “give”, “tell”, “what is”, “internal”). If matched, the pipeline **short-circuits** and returns a fixed refusal message without calling the LLM.  
- **Refusal message:** A single, non–data-bearing message (e.g. “I cannot provide internal financial or supplier information.”) is returned so the model cannot be prompted to leak via the system prompt.  
- **Safe fields only:** The context builder only includes: product_name, product_id, price, currency, specs, stock, policy_text, region, doc_type. So even if the index contained a stray sensitive field, it would not be added to the context string.

**Relevant code:** Notebook sections 10 (guardrails) and 11 (context builder); evaluation in [evaluation/test_queries.py](../evaluation/test_queries.py) (`test_security_red_team_restricted`, `test_security_red_team_injection`).

---

## 4. Supported regions (MVP)

| Region | Currency |
|--------|----------|
| Ghana | GHS |
| Netherlands | EUR |

**Deeper:** Region detection (notebook §7) uses a mapping from query/country parameter to a canonical region (e.g. "ghana", "gh" → Ghana; "netherlands", "nl", "dutch", "holland" → Netherlands). The **retrieval** layer filters FAISS/BM25 results by the `country` field in metadata so that, for example, “price in Ghana” returns only Ghana rows (and thus GHS). The [frontend](../frontend/chat_app.py) already lists more countries (Nigeria, South Africa, Kenya, Germany, UK, France, US, Canada); extending support is a Phase 2 item in the [roadmap](ROADMAP.md).

---

## 5. Stack summary

- **Python:** 3.10+ (Docker uses 3.11). See [Dockerfile](../Dockerfile).
- **Dependencies:** [requirements.txt](../requirements.txt) — sentence-transformers, faiss-cpu, rank-bm25, pandas, numpy, gradio, requests, python-dotenv; FastAPI, uvicorn; Streamlit (for frontend). Note: Streamlit is used in [frontend/chat_app.py](../frontend/chat_app.py) but may need to be added to requirements if not present.
- **Config:** [.env.example](../.env.example) — `OPENROUTER_API_KEY` (required for LLM), optional `OPENROUTER_MODEL` (default gpt-4o-mini).
- **Container:** [Dockerfile](../Dockerfile) copies `app/` and `pipelines/`, installs requirements, runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`. The `app/` package is expected to exist for the image to run.

---

## 6. Repo layout — links and deeper explanation

Every path below is a link to the file or folder. “Deeper” explains what the file/folder is for and how it fits into the pipeline.

| Path | Purpose (deeper) |
|------|-------------------|
| [retail-intelligence.ipynb](../retail-intelligence.ipynb) | **Full RAG MVP in one notebook.** Sections 1–15: env setup, dataset creation, embedding (§3), FAISS (§4), BM25 (§5), hybrid retrieval (§6), region filter (§7), intent classification (§8), hierarchical ranking (§9), security guardrails (§10), context builder (§11), OpenRouter RAG (§12), end-to-end pipeline (§13), Gradio UI (§14), evaluation (§15). Running this is the fastest way to try the system without the `app/` package. |
| [README.md](../README.md) | Project overview, features, installation, usage, supported regions, notebook structure, example queries. |
| [pipelines/](../pipelines/) | **Data and index pipelines** (ingestion + indexing). No LLM or API here; only CSV → clean CSV → FAISS + metadata. |
| [pipelines/ingestion/](../pipelines/ingestion/) | **Ingestion:** scripts that produce or merge raw data and clean it. |
| [pipelines/ingestion/clean_data.py](../pipelines/ingestion/clean_data.py) | Reads [data/raw/products_raw.csv](../data/raw/products_raw.csv) and, if present, [data/raw/task1_data.csv](../data/raw/task1_data.csv); drops Internal_Notes; standardizes country/category; builds searchable_text; writes [data/processed/products_clean.csv](../data/processed/products_clean.csv). **Must be run before indexing.** |
| [pipelines/ingestion/ingest_task_data.py](../pipelines/ingestion/ingest_task_data.py) | If `Task 1_ Global Retail Intelligence Engine Data.xlsx` exists, loads it and appends extra rows (e.g. NL-L-5042, Netherlands warranty policy); otherwise writes only the extra rows. Output: [data/raw/task1_data.csv](../data/raw/task1_data.csv). Used by [run_indexing.py](../scripts/run_indexing.py) before clean. |
| [pipelines/indexing/](../pipelines/indexing/) | **Indexing:** build vector index from clean data. |
| [pipelines/indexing/build_vector_index.py](../pipelines/indexing/build_vector_index.py) | Loads [data/processed/products_clean.csv](../data/processed/products_clean.csv), embeds searchable_text with sentence-transformers, builds FAISS index, saves [vector_store/faiss_index/index.faiss](../vector_store/faiss_index/index.faiss) and [vector_store/faiss_index/metadata.json](../vector_store/faiss_index/metadata.json). |
| [scripts/](../scripts/) | **CLI and one-off jobs:** dataset generation, full indexing, retrieval test. |
| [scripts/run_indexing.py](../scripts/run_indexing.py) | **Single entry point for indexing.** Optionally runs ingest_task_data (if Task 1 xlsx exists), then clean_data, then build_vector_index. Use this to refresh the index after data changes. |
| [scripts/run_retrieval.py](../scripts/run_retrieval.py) | **CLI for hybrid retrieval only.** Accepts query and optional country; uses `app.rag.hybrid_search.HybridRetriever` and prints top-k docs. Requires the `app/` package. Useful to debug retrieval without calling the LLM. |
| [scripts/generate_retail_dataset.py](../scripts/generate_retail_dataset.py) | **Synthetic data.** Generates [data/raw/products_raw.csv](../data/raw/products_raw.csv) with many countries, categories, and Internal_Notes (for testing that they never appear in the index). Options: `--records`, `--output`. |
| [evaluation/](../evaluation/) | **Automated tests** for the RAG pipeline. |
| [evaluation/test_queries.py](../evaluation/test_queries.py) | **Five tests:** regional integrity (Ghana + Solar Inverter → GHS/Ghana), technical precision (Smart Kettle Pro specs), policy summary (UK warranty), security restricted (supplier name → refusal), security injection (ignore instructions → refusal). Calls `app.rag.pipeline.run_rag`. Use `EVAL_MOCK_LLM=1` to avoid real LLM calls in CI. |
| [frontend/](../frontend/) | **Chat UI** that talks to the backend API. |
| [frontend/chat_app.py](../frontend/chat_app.py) | **Streamlit app.** Country dropdown, chat input, sends POST to `{STREAMLIT_CHAT_API_URL}/api/chat` with query and country. Sidebar: how to run API and set OpenRouter key. |
| [data/raw/](../data/raw/) | **Raw CSVs:** [products_raw.csv](../data/raw/products_raw.csv) (main catalog or generated), [task1_data.csv](../data/raw/task1_data.csv) (from ingest_task_data). Schema includes Internal_Notes. |
| [data/processed/](../data/processed/) | **Cleaned CSV:** [products_clean.csv](../data/processed/products_clean.csv). No Internal_Notes; has searchable_text. Input to indexing. |
| [vector_store/faiss_index/](../vector_store/faiss_index/) | **FAISS index + metadata:** [index.faiss](../vector_store/faiss_index/index.faiss), [metadata.json](../vector_store/faiss_index/metadata.json). Loaded at runtime by the retriever. |
| [app/](../app/) | **Backend package** (expected by Docker and eval; not yet in repo). Should contain `main.py` (FastAPI app, `/api/chat`, health) and `rag/` (pipeline, hybrid_search, guardrails, context builder, LLM call). |
| [Dockerfile](../Dockerfile) | Builds image from `app/` and `pipelines/`, runs `uvicorn app.main:app` on port 8000. |
| [requirements.txt](../requirements.txt) | Python dependencies for backend, notebook, and tooling. |
| [.env.example](../.env.example) | Template for `.env`: OPENROUTER_API_KEY, optional OPENROUTER_MODEL. |
| [docs/](../docs/) | **Documentation.** [TECHNICAL_PRESENTATION.md](TECHNICAL_PRESENTATION.md) (this file), [ROADMAP.md](ROADMAP.md). |

---

## 7. Running and testing (step-by-step with links)

| Step | Command / action | What it uses (links) |
|------|-------------------|----------------------|
| 1. **Notebook** | `jupyter notebook retail-intelligence.ipynb` → run all cells; use Gradio (§14) or `run_query(…)` | [retail-intelligence.ipynb](../retail-intelligence.ipynb), in-memory FAISS/BM25, OpenRouter (needs `.env`) |
| 2. **Generate raw data (optional)** | `python scripts/generate_retail_dataset.py` or `python scripts/generate_retail_dataset.py --records 500` | [scripts/generate_retail_dataset.py](../scripts/generate_retail_dataset.py) → [data/raw/products_raw.csv](../data/raw/products_raw.csv) |
| 3. **Build index** | `python pipelines/ingestion/clean_data.py` then `python pipelines/indexing/build_vector_index.py` **or** `python scripts/run_indexing.py` | [clean_data.py](../pipelines/ingestion/clean_data.py), [build_vector_index.py](../pipelines/indexing/build_vector_index.py), [run_indexing.py](../scripts/run_indexing.py) |
| 4. **Retrieval only (no LLM)** | `python scripts/run_retrieval.py "How much does the Solar Inverter cost?" Ghana` | [run_retrieval.py](../scripts/run_retrieval.py), requires [app/rag/hybrid_search](../app/) |
| 5. **API** | `uvicorn app.main:app --reload` | Requires [app/](../app/) (FastAPI), [Dockerfile](../Dockerfile) |
| 6. **Frontend** | `streamlit run frontend/chat_app.py`; set `STREAMLIT_CHAT_API_URL` if API is not on localhost:8000 | [frontend/chat_app.py](../frontend/chat_app.py) |
| 7. **Evaluation** | `python evaluation/test_queries.py`; use `EVAL_MOCK_LLM=1` for CI | [evaluation/test_queries.py](../evaluation/test_queries.py), requires [app/rag/pipeline](../app/) |

---

*This document is the technical presentation for the GlobalCart Retail Intelligence Engine. All links are relative to the repo root.*
