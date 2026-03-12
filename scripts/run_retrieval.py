"""
Run retrieval against the FAISS+BM25 index: run a query (and optional country)
and print top results. Use this to test the hybrid retriever without starting the API.
"""
import os
import sys
from pathlib import Path

# Quiet HuggingFace / sentence-transformers logs when running as CLI
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.rag.hybrid_search import HybridRetriever


def main():
    query = "How much does the Solar Inverter cost?"
    country = None
    if len(sys.argv) >= 2:
        query = sys.argv[1]
    if len(sys.argv) >= 3:
        country = sys.argv[2]

    print(f"Query: {query}")
    if country:
        print(f"Country filter: {country}")
    print("-" * 60)

    retriever = HybridRetriever(top_k=5)
    results = retriever.search(query=query, country=country, top_k=5)

    for i, doc in enumerate(results, 1):
        print(f"[{i}] {doc.get('item_name', '')} | {doc.get('country', '')} | {doc.get('price_local', '')} {doc.get('currency', '')}")
        specs = (doc.get("technical_specs") or "")[:80]
        if len(doc.get("technical_specs") or "") > 80:
            specs += "..."
        print(f"    {specs}")
        print()
    if not results:
        print("No results. Run scripts/run_indexing.py first to build the index.")


if __name__ == "__main__":
    main()
