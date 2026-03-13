"""
Run the full indexing pipeline: ensure clean data exists, then build FAISS index.
"""
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from pipelines.ingestion.clean_data import main as clean_main
from pipelines.indexing.build_vector_index import main as index_main


def main():
    # Ingest Task 1 xlsx if present (adds GH-K-001, UK-W-202 Policy, NL-L-5042, etc.)
    task_xlsx = project_root / "Task 1_ Global Retail Intelligence Engine Data.xlsx"
    if task_xlsx.exists():
        from pipelines.ingestion.ingest_task_data import main as ingest_task_main
        ingest_task_main()
        print("Re-running clean to merge task data...")
        clean_main()
    else:
        clean_path = project_root / "data" / "processed" / "products_data_3000.csv"
        if not clean_path.exists():
            print("Cleaned data not found. Running ingestion pipeline...")
            clean_main()
    print("Building vector index...")
    index_main()


if __name__ == "__main__":
    main()
