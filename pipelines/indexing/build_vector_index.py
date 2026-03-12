"""
Build FAISS vector index from cleaned product data.
- Loads data/processed/products_clean.csv
- Embeds searchable_text with sentence-transformers
- Stores vectors in FAISS and metadata (country, product_id, category) in JSON
- Saves under vector_store/faiss_index
"""
import json
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


def main():
    base = Path(__file__).resolve().parent.parent.parent
    clean_path = base / "data" / "processed" / "products_clean.csv"
    store_dir = base / "vector_store" / "faiss_index"
    store_dir.mkdir(parents=True, exist_ok=True)

    if not clean_path.exists():
        raise FileNotFoundError(
            f"Cleaned data not found: {clean_path}. Run pipelines/ingestion/clean_data.py first."
        )

    df = pd.read_csv(clean_path)
    texts = df["searchable_text"].fillna("").astype(str).tolist()

    print("Loading sentence-transformers model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
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
            "searchable_text": str(row.get("searchable_text", "")).strip(),
        })

    faiss.write_index(index, str(store_dir / "index.faiss"))
    with open(store_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=0)

    print(f"Index built: {len(metadata)} vectors -> {store_dir}")


if __name__ == "__main__":
    main()
