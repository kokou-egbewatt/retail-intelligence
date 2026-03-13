"""
Intent Classification: classify user intent so the pipeline and LLM stay on track
(product info, pricing, warranty, list products, restricted, out-of-scope).
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Intent(str, Enum):
    PRODUCT_INFO = "product_info"       # specs, features, description
    PRICING = "pricing"                 # price, cost, how much
    WARRANTY_POLICY = "warranty_policy" # warranty, return, guarantee
    AVAILABILITY = "availability"       # in stock, available
    LIST_PRODUCTS = "list_products"    # give me N products, list, show products
    GENERIC = "generic"                 # general product/catalog question
    RESTRICTED = "restricted"           # supplier, margin, internal (block)
    OUT_OF_SCOPE = "out_of_scope"       # off-topic (politely refuse)


# Keywords per intent (order: more specific first; first match wins for blocking)
INTENT_KEYWORDS = {
    Intent.RESTRICTED: [
        "supplier", "margin", "internal notes", "warehouse", "profit",
        "cost price", "wholesale", "confidential", "vendor name", "back office",
    ],
    Intent.WARRANTY_POLICY: [
        "warranty", "warranties", "guarantee", "return policy", "coverage",
        "policy", "policies", "refund", "replacement",
    ],
    Intent.PRICING: [
        "price", "prices", "cost", "how much", "costs", "pricing",
    ],
    Intent.AVAILABILITY: [
        "available", "availability", "in stock", "out of stock", "when in stock",
    ],
    Intent.LIST_PRODUCTS: [
        "list", "show me", "give me", "name some", "examples of",
        "few products", "some products", "any products", "5 products", "10 products",
    ],
    Intent.PRODUCT_INFO: [
        "specs", "specifications", "features", "technical", "description",
        "what is", "tell me about", "details",
    ],
}

# Out-of-scope: topics we don't support (keep minimal to avoid false positives)
OUT_OF_SCOPE_PATTERNS = [
    r"^(who|what company|which company)\s+(are you|is this)",
    r"\b(politics|sports|weather|recipe|cooking)\b",
    r"^(tell me a joke|sing a song)",
]
COMPILED_OUT_OF_SCOPE = [re.compile(p, re.I) for p in OUT_OF_SCOPE_PATTERNS]


@dataclass
class IntentResult:
    intent: Intent
    block: bool = False
    message: Optional[str] = None  # refusal/redirect message when block or out_of_scope


def classify_intent(query: str) -> IntentResult:
    """
    Classify user intent. Returns IntentResult with block=True and message set
    for RESTRICTED or OUT_OF_SCOPE so the pipeline can block or redirect.
    """
    q = (query or "").strip().lower()
    if not q:
        return IntentResult(Intent.GENERIC)

    # 1. Restricted (security: stay on track, block)
    for kw in INTENT_KEYWORDS.get(Intent.RESTRICTED, []):
        if kw in q:
            return IntentResult(
                Intent.RESTRICTED,
                block=True,
                message=(
                    "I can't provide that information. I can help with product specs, "
                    "pricing for your region, availability, and warranty instead."
                ),
            )

    # 2. Out-of-scope (politely refuse)
    for pat in COMPILED_OUT_OF_SCOPE:
        if pat.search(q):
            return IntentResult(
                Intent.OUT_OF_SCOPE,
                block=True,
                message="I can only help with GlobalCart products, pricing, warranty, and availability.",
            )

    # 3. In-scope intents (first match)
    for intent, keywords in INTENT_KEYWORDS.items():
        if intent in (Intent.RESTRICTED,):
            continue
        for kw in keywords:
            if kw in q:
                return IntentResult(intent)

    return IntentResult(Intent.GENERIC)
