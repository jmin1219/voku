"""
Finance database operations.

Uses SQLite for operational data storage. All finance tables live in voku.db
alongside other domains (fitness, etc.).

Design:
- Categories: Voku's spending taxonomy (hierarchical)
- Merchants: Entities Voku knows about
- MerchantPatterns: Learned mappings from raw text to merchants
- Transactions: Denormalized for fast queries
"""

import sqlite3
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.services.finance.models import (
    Category,
    Merchant,
    MerchantPattern,
    Transaction,
    EnrichedTransaction,
)


# Default category taxonomy
SEED_CATEGORIES = [
    # Top-level categories
    ("Food", None),
    ("Subscriptions", None),
    ("Personal Care", None),
    ("Vices", None),
    ("Shopping", None),
    ("Transport", None),
    ("Transfer", None),
    
    # Food subcategories
    ("Delivery", "Food"),
    ("Groceries", "Food"),
    ("Eating Out", "Food"),
    ("Meal Prep", "Food"),
    
    # Subscriptions subcategories
    ("Streaming", "Subscriptions"),
    ("Software", "Subscriptions"),
    
    # Personal Care subcategories
    ("Grooming", "Personal Care"),
    
    # Shopping subcategories
    ("Clothes", "Shopping"),
    ("Tech", "Shopping"),
    ("Home", "Shopping"),
    
    # Transport subcategories
    ("Transit", "Transport"),
    ("Rideshare", "Transport"),
    
    # Transfer subcategories
    ("Load", "Transfer"),
]


class FinanceDB:
    """
    SQLite database operations for finance module.
    
    Usage:
        db = FinanceDB("path/to/voku.db")
        db.seed_categories()  # One-time setup
        db.insert_transaction(...)
        summary = db.get_summary(month="2026-01")
    """
    
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_schema()
    
    def _create_schema(self):
        """Create all tables if they don't exist."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                name TEXT PRIMARY KEY,
                parent TEXT REFERENCES categories(name),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merchants (
                name TEXT PRIMARY KEY,
                default_category TEXT REFERENCES categories(name),
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merchant_patterns (
                raw_pattern TEXT PRIMARY KEY,
                merchant TEXT NOT NULL REFERENCES merchants(name),
                vendor TEXT,
                category_override TEXT REFERENCES categories(name),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                date DATETIME NOT NULL,
                amount REAL NOT NULL,
                balance REAL,
                raw_description TEXT NOT NULL,
                merchant TEXT,
                vendor TEXT,
                category TEXT,
                transaction_type TEXT NOT NULL,
                source TEXT NOT NULL,
                notes TEXT,
                hash TEXT UNIQUE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def list_tables(self) -> list[str]:
        """List all tables in the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cursor.fetchall()]
    
    # -------------------------------------------------------------------------
    # Categories
    # -------------------------------------------------------------------------
    
    def seed_categories(self):
        """Insert default category taxonomy."""
        cursor = self.conn.cursor()
        for name, parent in SEED_CATEGORIES:
            cursor.execute(
                "INSERT OR IGNORE INTO categories (name, parent) VALUES (?, ?)",
                (name, parent)
            )
        self.conn.commit()
    
    def get_category(self, name: str) -> Optional[Category]:
        """Get a category by name."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT name, parent, created_at FROM categories WHERE name = ?",
            (name,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Category(
            name=row["name"],
            parent=row["parent"],
            created_at=row["created_at"]
        )
    
    # -------------------------------------------------------------------------
    # Merchants
    # -------------------------------------------------------------------------
    
    def create_merchant(
        self,
        name: str,
        default_category: str,
        notes: Optional[str] = None
    ):
        """Create a new merchant entity."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO merchants (name, default_category, notes)
            VALUES (?, ?, ?)
            """,
            (name, default_category, notes)
        )
        self.conn.commit()
    
    def get_merchant(self, name: str) -> Optional[Merchant]:
        """Get a merchant by name."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT name, default_category, notes, created_at FROM merchants WHERE name = ?",
            (name,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Merchant(
            name=row["name"],
            default_category=row["default_category"],
            notes=row["notes"],
            created_at=row["created_at"]
        )
    
    # -------------------------------------------------------------------------
    # Merchant Patterns
    # -------------------------------------------------------------------------
    
    def create_pattern(
        self,
        raw_pattern: str,
        merchant: str,
        vendor: Optional[str] = None,
        category_override: Optional[str] = None
    ):
        """Create a learned pattern mapping."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO merchant_patterns (raw_pattern, merchant, vendor, category_override)
            VALUES (?, ?, ?, ?)
            """,
            (raw_pattern, merchant, vendor, category_override)
        )
        self.conn.commit()
    
    def get_pattern(self, raw_pattern: str) -> Optional[MerchantPattern]:
        """Get a pattern by exact raw text match."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT raw_pattern, merchant, vendor, category_override, created_at
            FROM merchant_patterns
            WHERE raw_pattern = ?
            """,
            (raw_pattern,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return MerchantPattern(
            raw_pattern=row["raw_pattern"],
            merchant=row["merchant"],
            vendor=row["vendor"],
            category_override=row["category_override"],
            created_at=row["created_at"]
        )
    
    # -------------------------------------------------------------------------
    # Transactions
    # -------------------------------------------------------------------------
    
    def _compute_hash(self, date: datetime, amount: float, raw_description: str) -> str:
        """Compute deduplication hash for a transaction."""
        data = f"{date.isoformat()}|{amount}|{raw_description}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def insert_transaction(
        self,
        txn: EnrichedTransaction,
        source: str
    ) -> bool:
        """
        Insert a transaction. Returns False if duplicate (hash exists).
        """
        txn_hash = self._compute_hash(txn.date, txn.amount, txn.raw_description)
        txn_id = str(uuid.uuid4())
        
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO transactions (
                    id, date, amount, balance, raw_description,
                    merchant, vendor, category, transaction_type,
                    source, notes, hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    txn_id,
                    txn.date.isoformat(),
                    txn.amount,
                    txn.balance,
                    txn.raw_description,
                    txn.merchant,
                    txn.vendor,
                    txn.category,
                    txn.transaction_type,
                    source,
                    None,  # notes
                    txn_hash
                )
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Duplicate hash
            return False
    
    def get_transactions(
        self,
        category: Optional[str] = None,
        merchant: Optional[str] = None,
        limit: Optional[int] = None
    ) -> list[Transaction]:
        """Get transactions with optional filters."""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if merchant:
            query += " AND merchant = ?"
            params.append(merchant)
        
        query += " ORDER BY date DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [
            Transaction(
                id=row["id"],
                date=datetime.fromisoformat(row["date"]),
                amount=row["amount"],
                balance=row["balance"],
                raw_description=row["raw_description"],
                merchant=row["merchant"],
                vendor=row["vendor"],
                category=row["category"],
                transaction_type=row["transaction_type"],
                source=row["source"],
                notes=row["notes"],
                hash=row["hash"],
                created_at=row["created_at"]
            )
            for row in rows
        ]
    
    # -------------------------------------------------------------------------
    # Summaries
    # -------------------------------------------------------------------------
    
    def get_summary(self, month: str) -> dict[str, float]:
        """
        Get spending summary by category for a month.
        
        Args:
            month: Format "YYYY-MM" (e.g., "2026-01")
        
        Returns:
            Dict mapping category name to total spent (negative values).
            Deposits are excluded.
        """
        cursor = self.conn.cursor()
        
        # Parse month to get date range
        year, mon = month.split("-")
        start = f"{year}-{mon}-01"
        # Get first day of next month for end bound
        next_month = int(mon) + 1
        next_year = int(year)
        if next_month > 12:
            next_month = 1
            next_year += 1
        end = f"{next_year}-{next_month:02d}-01"
        
        cursor.execute(
            """
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE date >= ? AND date < ?
              AND transaction_type = 'spending'
            GROUP BY category
            """,
            (start, end)
        )
        
        return {row["category"]: row["total"] for row in cursor.fetchall()}
