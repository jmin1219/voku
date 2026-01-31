"""
Finance module data models.

These dataclasses define the contracts between components:
- Parser outputs RawTransaction
- Categorizer transforms to EnrichedTransaction
- DB stores/retrieves all entity types
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawTransaction:
    """
    Output from parser. No enrichment — just what's in the PDF.
    
    amount: Negative = spending, positive = deposit
    transaction_type: "spending" | "deposit"
    """
    date: datetime
    amount: float
    balance: float | None
    raw_description: str
    transaction_type: str


@dataclass
class EnrichedTransaction:
    """
    RawTransaction + merchant/category info from categorizer.
    Ready for database insertion.
    """
    date: datetime
    amount: float
    balance: float | None
    raw_description: str
    transaction_type: str
    merchant: str
    vendor: str | None
    category: str


@dataclass
class Merchant:
    """
    A merchant entity Voku knows about.
    Merchants have a default category but patterns can override.
    """
    name: str
    default_category: str
    notes: str | None = None
    created_at: datetime | None = None


@dataclass 
class MerchantPattern:
    """
    A learned mapping from raw PDF text to merchant.
    
    Example:
        raw_pattern: "DOORDASHPRINKLECHIC"
        merchant: "DoorDash"
        vendor: "Prinkle Chic"
        category_override: None (uses merchant default)
    """
    raw_pattern: str
    merchant: str
    vendor: str | None = None
    category_override: str | None = None
    created_at: datetime | None = None


@dataclass
class Category:
    """
    A spending category in Voku's taxonomy.
    Categories can have parents (e.g., "Delivery" parent is "Food").
    """
    name: str
    parent: str | None = None
    created_at: datetime | None = None


@dataclass
class Transaction:
    """
    Stored transaction with all fields.
    Denormalized — includes resolved merchant/category for fast queries.
    """
    id: str
    date: datetime
    amount: float
    balance: float | None
    raw_description: str
    merchant: str | None
    vendor: str | None
    category: str | None
    transaction_type: str
    source: str
    notes: str | None
    hash: str
    created_at: datetime | None = None
