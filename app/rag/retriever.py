"""
Retriever interface: re-export HybridRetriever for backwards compatibility.
"""
from app.rag.hybrid_search import HybridRetriever

__all__ = ["HybridRetriever"]
