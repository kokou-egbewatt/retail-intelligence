"""
Query service: thin wrapper around RAG pipeline for use by API or other callers.
"""

from typing import Optional

from app.rag.pipeline import RAGResponse, run_rag


def query(query: str, country: Optional[str] = None) -> RAGResponse:
    """Run the RAG pipeline and return the response."""
    return run_rag(query=query, country=country)
