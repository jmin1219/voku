"""
Merchant categorizer with LLM-powered parsing.

Transforms raw transactions into enriched transactions by:
1. Checking cached patterns first (fast path)
2. Calling LLM for unknown patterns (slow path, batched)
3. Learning new patterns for future use

Uses Groq for LLM inference (same as fitness vision).
"""

import json
import re
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

from app.services.finance.models import RawTransaction, EnrichedTransaction
from app.services.finance.db import FinanceDB

load_dotenv()


# Valid categories from taxonomy
VALID_CATEGORIES = [
    "Food", "Delivery", "Groceries", "Eating Out", "Meal Prep",
    "Subscriptions", "Streaming", "Software",
    "Personal Care", "Grooming",
    "Vices",
    "Shopping", "Clothes", "Tech", "Home",
    "Transport", "Transit", "Rideshare",
    "Transfer", "Load"
]


async def categorize_transactions(
    raw_transactions: list[RawTransaction],
    db: FinanceDB
) -> list[EnrichedTransaction]:
    """
    Transform raw transactions into enriched transactions.
    
    Process:
    1. Handle deposits specially (Transfer/Load category)
    2. Check cache for known patterns
    3. Batch unknown patterns for LLM
    4. Create merchants/patterns from LLM response
    5. Return enriched transactions
    """
    enriched = []
    unknowns = []  # (index, raw_description) for LLM batch
    
    for i, txn in enumerate(raw_transactions):
        # Handle deposits specially
        if txn.transaction_type == "deposit":
            enriched.append(EnrichedTransaction(
                date=txn.date,
                amount=txn.amount,
                balance=txn.balance,
                raw_description=txn.raw_description,
                transaction_type=txn.transaction_type,
                merchant="Transfer",
                vendor=None,
                category="Load"
            ))
            continue
        
        # Check cache
        pattern = db.get_pattern(txn.raw_description)
        
        if pattern:
            # Cache hit - use stored data
            merchant = db.get_merchant(pattern.merchant)
            category = pattern.category_override or (merchant.default_category if merchant else "Shopping")
            
            enriched.append(EnrichedTransaction(
                date=txn.date,
                amount=txn.amount,
                balance=txn.balance,
                raw_description=txn.raw_description,
                transaction_type=txn.transaction_type,
                merchant=pattern.merchant,
                vendor=pattern.vendor,
                category=category
            ))
        else:
            # Cache miss - queue for LLM
            unknowns.append((i, txn))
            enriched.append(None)  # Placeholder
    
    # Batch LLM call for unknowns
    if unknowns:
        raw_descs = [txn.raw_description for _, txn in unknowns]
        prompt = build_categorization_prompt(raw_descs)
        
        llm_response = await call_llm(prompt)
        parsed = parse_llm_response(llm_response)
        
        # Process LLM results
        for idx, txn in unknowns:
            raw_desc = txn.raw_description
            
            if raw_desc in parsed:
                result = parsed[raw_desc]
                merchant_name = result["merchant"]
                vendor = result.get("vendor")
                category = result["category"]
                
                # Validate category
                if category not in VALID_CATEGORIES:
                    category = "Shopping"  # Fallback
                
                # Create merchant if new
                if not db.get_merchant(merchant_name):
                    db.create_merchant(merchant_name, category)
                
                # Create pattern for future cache hits
                db.create_pattern(raw_desc, merchant_name, vendor=vendor)
                
                enriched[idx] = EnrichedTransaction(
                    date=txn.date,
                    amount=txn.amount,
                    balance=txn.balance,
                    raw_description=txn.raw_description,
                    transaction_type=txn.transaction_type,
                    merchant=merchant_name,
                    vendor=vendor,
                    category=category
                )
            else:
                # LLM didn't return this one - use fallback
                enriched[idx] = EnrichedTransaction(
                    date=txn.date,
                    amount=txn.amount,
                    balance=txn.balance,
                    raw_description=txn.raw_description,
                    transaction_type=txn.transaction_type,
                    merchant="Unknown",
                    vendor=None,
                    category="Shopping"
                )
    
    return enriched


def build_categorization_prompt(raw_descriptions: list[str]) -> str:
    """
    Build prompt for merchant categorization.
    
    The prompt asks the LLM to:
    1. Parse concatenated merchant strings
    2. Identify the merchant name
    3. Extract vendor if present (e.g., "Prinkle Chic" from DoorDash order)
    4. Assign appropriate category
    """
    categories_str = ", ".join(VALID_CATEGORIES)
    
    raw_list = "\n".join(f"- {desc}" for desc in raw_descriptions)
    
    return f"""Parse these merchant strings from a bank statement and categorize them.

Raw merchant strings:
{raw_list}

For each string, identify:
1. merchant: The company name (e.g., "DoorDash", "Netflix", "Raum Hair")
2. vendor: If ordering from a platform, the actual vendor (e.g., "Prinkle Chic" for a DoorDash order). Use null if not applicable.
3. category: One of: {categories_str}

Category guidelines:
- Food delivery apps (DoorDash, UberEats) → "Delivery" 
- Grocery stores or grocery delivery → "Groceries"
- Restaurants/fast food → "Eating Out"
- Meal prep services (Fresh Prep) → "Meal Prep"
- Streaming services (Netflix) → "Streaming"
- Software subscriptions → "Software"
- Hair salons/barbers → "Grooming"
- Vape shops → "Vices"

Respond with ONLY a JSON array, no markdown or explanation:
[
  {{"raw": "ORIGINAL_STRING", "merchant": "Merchant Name", "vendor": "Vendor or null", "category": "Category"}}
]"""


def parse_llm_response(response: str) -> dict[str, dict]:
    """
    Parse LLM JSON response into a lookup dict.
    
    Returns:
        Dict mapping raw_description -> {merchant, vendor, category}
    """
    # Strip markdown code blocks if present
    response = response.strip()
    if response.startswith("```"):
        # Remove ```json and ``` markers
        response = re.sub(r'^```\w*\n?', '', response)
        response = re.sub(r'\n?```$', '', response)
        response = response.strip()
    
    try:
        data = json.loads(response)
        if not isinstance(data, list):
            return {}
        
        return {
            item["raw"]: {
                "merchant": item["merchant"],
                "vendor": item.get("vendor"),
                "category": item["category"]
            }
            for item in data
            if "raw" in item and "merchant" in item and "category" in item
        }
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}


async def call_llm(prompt: str) -> str:
    """
    Call Groq LLM for text completion.
    
    Uses the same Groq API as fitness vision module.
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": 0.1,  # Low temperature for consistent parsing
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload
        )
    
    data = response.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
