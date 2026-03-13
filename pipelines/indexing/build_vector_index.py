"""
Build FAISS vector index from cleaned product data.
- Loads data/processed/products_clean.csv
- Embeds internal_notes with sentence-transformers
- Stores vectors in FAISS and metadata (country, product_id, category) in JSON
- Saves under vector_store/faiss_index

Offline: set HF_HUB_OFFLINE=1 or TRANSFORMERS_OFFLINE=1 to load the model from cache only
(no network). Requires the model to have been downloaded once (e.g. on a machine with internet).
"""
import json
import os
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


def _load_model():
    """Load SentenceTransformer model; use cache only when HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE=1 or after network error."""
    offline = os.environ.get("HF_HUB_OFFLINE", "").strip() == "1" or os.environ.get("TRANSFORMERS_OFFLINE", "").strip() == "1"
    try:
        if offline:
            print("Loading sentence-transformers model (offline, from cache)...")
            return SentenceTransformer(MODEL_NAME, local_files_only=True)
        print("Loading sentence-transformers model...")
        return SentenceTransformer(MODEL_NAME)
    except Exception as e:
        err_str = str(e).lower()
        if offline or "nodename nor servname" in err_str or "connection" in err_str or "network" in err_str or "client has been closed" in err_str:
            print("Network unavailable or offline. Trying to load model from cache only...")
            try:
                return SentenceTransformer(MODEL_NAME, local_files_only=True)
            except Exception as e2:
                raise RuntimeError(
                    "Could not load the embedding model. Either:\n"
                    "  1. Run this script once with internet so the model is downloaded to cache, or\n"
                    "  2. Set HF_HUB_OFFLINE=1 and ensure the model is already in cache (e.g. ~/.cache/huggingface/).\n"
                    f"Original error: {e}\nFallback error: {e2}"
                ) from e2
        raise


def main():
    base = Path(__file__).resolve().parent.parent.parent
    clean_path = base / "data" / "processed" / "products_data_3000.csv"
    store_dir = base / "vector_store" / "faiss_index"
    store_dir.mkdir(parents=True, exist_ok=True)

    if not clean_path.exists():
        raise FileNotFoundError(
            f"Cleaned data not found: {clean_path}. Run pipelines/ingestion/clean_data.py first."
        )

    df = pd.read_csv(clean_path)
    texts = df["Internal_Notes"].fillna("").astype(str).tolist()

    model = _load_model()
    print("Creating embeddings...")
    embeddings = model.encode(texts, show_progress_bar=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product = cosine when normalized
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    # Metadata for filtering and display
    metadata = []
    for _, row in df.iterrows():
        metadata.append({
            "country": str(row.get("Country", "")).strip(),
            "product_id": str(row.get("Product_ID", "")).strip(),
            "category": str(row.get("Category", "")).strip(),
            "item_name": str(row.get("Item_Name", "")).strip(),
            "price_local": row.get("Price_Local"),
            "currency": str(row.get("Currency", "")).strip(),
            "technical_specs": str(row.get("Technical_Specs", "")).strip(),
            "internal_notes": str(row.get("Internal_Notes", "")).strip(),
        })

    faiss.write_index(index, str(store_dir / "index.faiss"))
    with open(store_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=0)

    print(f"Index built: {len(metadata)} vectors -> {store_dir}")


if __name__ == "__main__":
    main()
