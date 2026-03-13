"""
Build the RAG prompt: system + context (retrieved docs) + user query for the LLM.
Supports single region or multiple (e.g. Ghana and Nigeria) so the LLM can answer per country.
"""
from typing import Any, List, Optional

from app.rag.intent_classifier import Intent


def build_rag_prompt(
    query: str,
    context_docs: list[dict[str, Any]],
    country: str | None = None,
    countries: Optional[List[str]] = None,
    intent: Optional[Intent] = None,
) -> str:
    """
    Assemble system instructions, retrieved context, and user query.
    Context is formatted from hybrid search results (item_name, price, specs, etc.).
    countries: when multiple (e.g. Ghana and Nigeria), instruct LLM to answer per region.
    intent: optional; adds a "stay on track" instruction for the LLM.
    """
    lines = [
        "You are a helpful retail assistant for GlobalCart. Answer only using the provided product and policy context. "
        "When the user asks for products, prices, or a list (e.g. 'give me 5 products', 'prices', 'any products', 'however abstract'), list the products from the context with name, price, and currency. "
        "If the user asks for more than one country (e.g. Ghana and Nigeria), give the price or details for each country separately. "
        "If the answer is not in the context, say you don't have that information. "
        "Never mention suppliers, margins, internal notes, or warehouse details."
    ]
    if intent and intent != Intent.GENERIC:
        intent_hint = {
            Intent.PRICING: "Focus on prices and currency only.",
            Intent.PRICE_COMPARISON: (
                "The user wants to compare product or item prices across regions. "
                "Present prices for each country clearly (e.g. by country or side by side) so they can compare."
            ),
            Intent.PRODUCT_INFO: "Focus on specs, features, and product details.",
            Intent.WARRANTY_POLICY: "Focus on warranty, return policy, and coverage.",
            Intent.AVAILABILITY: "Focus on availability and stock.",
            Intent.LIST_PRODUCTS: "List products from the context with name, price, and currency.",
        }.get(intent)
        if intent_hint:
            lines.append(f"Stay on track: {intent_hint}")
    if countries and len(countries) > 1:
        lines.append(f"User asked about these regions: {', '.join(countries)}. For each region, give the price or details from the context for that country only.")
        if intent == Intent.PRICE_COMPARISON:
            lines.append("Format the answer as a comparison: show the same product/item with its price and currency per country so the user can compare.")
    elif countries and len(countries) == 1:
        lines.append(f"User region: {countries[0]}. Use only pricing and availability for this region.")
    elif country:
        lines.append(f"User region: {country}. Use only pricing and availability for this region.")
    lines.append("")
    lines.append("--- Context ---")
    for i, doc in enumerate(context_docs[:5], 1):
        parts = [
            f"Product: {doc.get('item_name', '')}",
            f"ID: {doc.get('product_id', '')}",
            f"Country: {doc.get('country', '')}",
            f"Price: {doc.get('price_local', '')} {doc.get('currency', '')}",
            f"Specs: {doc.get('technical_specs', '')}",
        ]
        lines.append("\n".join(parts))
        lines.append("")
    lines.append("--- End context ---")
    lines.append("")
    lines.append(f"User question: {query}")
    lines.append("Answer:")
    return "\n".join(lines)
