"""
Tests for finance database operations.

TDD: These tests define the contract for db.py.
Run with: python -m pytest tests/test_finance/test_db.py -v
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import os

from app.services.finance.db import FinanceDB
from app.services.finance.models import (
    EnrichedTransaction,
    Merchant,
    MerchantPattern,
    Category,
)


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    database = FinanceDB(db_path)
    yield database
    
    # Cleanup
    database.close()
    os.unlink(db_path)


class TestSchemaCreation:
    """Verify database schema is created correctly."""
    
    def test_creates_all_tables(self, db):
        """All required tables exist after initialization."""
        tables = db.list_tables()
        assert "categories" in tables
        assert "merchants" in tables
        assert "merchant_patterns" in tables
        assert "transactions" in tables


class TestCategories:
    """Category CRUD operations."""
    
    def test_seed_categories_creates_taxonomy(self, db):
        """Seed data creates the full category taxonomy."""
        db.seed_categories()
        
        food = db.get_category("Food")
        assert food is not None
        assert food.parent is None  # Top-level
        
        delivery = db.get_category("Delivery")
        assert delivery is not None
        assert delivery.parent == "Food"
    
    def test_get_category_returns_none_for_unknown(self, db):
        """Unknown category returns None, not error."""
        result = db.get_category("NonexistentCategory")
        assert result is None


class TestMerchants:
    """Merchant entity operations."""
    
    def test_create_and_get_merchant(self, db):
        """Can create and retrieve a merchant."""
        db.seed_categories()
        db.create_merchant("DoorDash", "Delivery", notes="Delivery platform")
        
        merchant = db.get_merchant("DoorDash")
        assert merchant is not None
        assert merchant.name == "DoorDash"
        assert merchant.default_category == "Delivery"
        assert merchant.notes == "Delivery platform"
    
    def test_get_merchant_returns_none_for_unknown(self, db):
        """Unknown merchant returns None."""
        result = db.get_merchant("UnknownMerchant")
        assert result is None
    
    def test_create_merchant_without_notes(self, db):
        """Notes field is optional."""
        db.seed_categories()
        db.create_merchant("Netflix", "Streaming")
        
        merchant = db.get_merchant("Netflix")
        assert merchant.notes is None


class TestMerchantPatterns:
    """Pattern matching and learning."""
    
    def test_create_and_get_pattern(self, db):
        """Can create and retrieve a pattern."""
        db.seed_categories()
        db.create_merchant("DoorDash", "Delivery")
        db.create_pattern(
            raw_pattern="DOORDASHPRINKLECHIC",
            merchant="DoorDash",
            vendor="Prinkle Chic"
        )
        
        pattern = db.get_pattern("DOORDASHPRINKLECHIC")
        assert pattern is not None
        assert pattern.merchant == "DoorDash"
        assert pattern.vendor == "Prinkle Chic"
        assert pattern.category_override is None
    
    def test_pattern_with_category_override(self, db):
        """Pattern can override merchant's default category."""
        db.seed_categories()
        db.create_merchant("DoorDash", "Delivery")
        db.create_pattern(
            raw_pattern="DOORDASHNOFRILLS",
            merchant="DoorDash",
            vendor="No Frills",
            category_override="Groceries"
        )
        
        pattern = db.get_pattern("DOORDASHNOFRILLS")
        assert pattern.category_override == "Groceries"
    
    def test_get_pattern_returns_none_for_unknown(self, db):
        """Unknown pattern returns None."""
        result = db.get_pattern("UNKNOWNMERCHANT123")
        assert result is None


class TestTransactions:
    """Transaction storage and retrieval."""
    
    def test_insert_transaction(self, db):
        """Can insert and retrieve a transaction."""
        db.seed_categories()
        
        txn = EnrichedTransaction(
            date=datetime(2026, 1, 24, 12, 25, 6),
            amount=-68.53,
            balance=207.90,
            raw_description="DOORDASHPRINKLECHIC",
            transaction_type="spending",
            merchant="DoorDash",
            vendor="Prinkle Chic",
            category="Delivery"
        )
        
        result = db.insert_transaction(txn, source="toss_cad_pdf")
        assert result is True
        
        transactions = db.get_transactions()
        assert len(transactions) == 1
        assert transactions[0].amount == -68.53
        assert transactions[0].merchant == "DoorDash"
    
    def test_duplicate_transaction_rejected(self, db):
        """Same transaction can't be inserted twice (hash dedup)."""
        db.seed_categories()
        
        txn = EnrichedTransaction(
            date=datetime(2026, 1, 24, 12, 25, 6),
            amount=-68.53,
            balance=207.90,
            raw_description="DOORDASHPRINKLECHIC",
            transaction_type="spending",
            merchant="DoorDash",
            vendor="Prinkle Chic",
            category="Delivery"
        )
        
        first = db.insert_transaction(txn, source="toss_cad_pdf")
        second = db.insert_transaction(txn, source="toss_cad_pdf")
        
        assert first is True
        assert second is False  # Duplicate rejected
        
        transactions = db.get_transactions()
        assert len(transactions) == 1  # Only one stored
    
    def test_filter_by_category(self, db):
        """Can filter transactions by category."""
        db.seed_categories()
        
        # Insert two transactions with different categories
        food_txn = EnrichedTransaction(
            date=datetime(2026, 1, 24, 12, 0, 0),
            amount=-20.00,
            balance=100.00,
            raw_description="SOMERESTAURANT",
            transaction_type="spending",
            merchant="Some Restaurant",
            vendor=None,
            category="Eating Out"
        )
        
        vape_txn = EnrichedTransaction(
            date=datetime(2026, 1, 24, 13, 0, 0),
            amount=-43.74,
            balance=56.26,
            raw_description="VAN VAPES",
            transaction_type="spending",
            merchant="Van Vapes",
            vendor=None,
            category="Vices"
        )
        
        db.insert_transaction(food_txn, source="toss_cad_pdf")
        db.insert_transaction(vape_txn, source="toss_cad_pdf")
        
        food_results = db.get_transactions(category="Eating Out")
        assert len(food_results) == 1
        assert food_results[0].category == "Eating Out"
    
    def test_filter_by_merchant(self, db):
        """Can filter transactions by merchant."""
        db.seed_categories()
        
        txn1 = EnrichedTransaction(
            date=datetime(2026, 1, 24, 12, 0, 0),
            amount=-50.00,
            balance=100.00,
            raw_description="DOORDASH1",
            transaction_type="spending",
            merchant="DoorDash",
            vendor="Vendor1",
            category="Delivery"
        )
        
        txn2 = EnrichedTransaction(
            date=datetime(2026, 1, 24, 13, 0, 0),
            amount=-30.00,
            balance=70.00,
            raw_description="UBEREATS1",
            transaction_type="spending",
            merchant="UberEats",
            vendor="Vendor2",
            category="Delivery"
        )
        
        db.insert_transaction(txn1, source="toss_cad_pdf")
        db.insert_transaction(txn2, source="toss_cad_pdf")
        
        doordash_results = db.get_transactions(merchant="DoorDash")
        assert len(doordash_results) == 1
        assert doordash_results[0].merchant == "DoorDash"


class TestSummary:
    """Monthly summary aggregation."""
    
    def test_monthly_summary_by_category(self, db):
        """Summary aggregates spending by category."""
        db.seed_categories()
        
        # Insert transactions for Jan 2026
        transactions = [
            EnrichedTransaction(
                date=datetime(2026, 1, 10, 12, 0, 0),
                amount=-50.00,
                balance=100.00,
                raw_description="DOORDASH1",
                transaction_type="spending",
                merchant="DoorDash",
                vendor=None,
                category="Delivery"
            ),
            EnrichedTransaction(
                date=datetime(2026, 1, 15, 12, 0, 0),
                amount=-30.00,
                balance=70.00,
                raw_description="DOORDASH2",
                transaction_type="spending",
                merchant="DoorDash",
                vendor=None,
                category="Delivery"
            ),
            EnrichedTransaction(
                date=datetime(2026, 1, 20, 12, 0, 0),
                amount=-43.74,
                balance=26.26,
                raw_description="VAN VAPES",
                transaction_type="spending",
                merchant="Van Vapes",
                vendor=None,
                category="Vices"
            ),
        ]
        
        for txn in transactions:
            db.insert_transaction(txn, source="toss_cad_pdf")
        
        summary = db.get_summary(month="2026-01")
        
        assert summary["Delivery"] == -80.00  # 50 + 30
        assert summary["Vices"] == -43.74
    
    def test_summary_excludes_deposits(self, db):
        """Deposits are not included in spending summary."""
        db.seed_categories()
        
        spending = EnrichedTransaction(
            date=datetime(2026, 1, 10, 12, 0, 0),
            amount=-50.00,
            balance=100.00,
            raw_description="SOMESTORE",
            transaction_type="spending",
            merchant="Some Store",
            vendor=None,
            category="Shopping"
        )
        
        deposit = EnrichedTransaction(
            date=datetime(2026, 1, 15, 12, 0, 0),
            amount=1000.00,
            balance=1100.00,
            raw_description="CAD 사기",
            transaction_type="deposit",
            merchant="Transfer",
            vendor=None,
            category="Load"
        )
        
        db.insert_transaction(spending, source="toss_cad_pdf")
        db.insert_transaction(deposit, source="toss_cad_pdf")
        
        summary = db.get_summary(month="2026-01")
        
        assert "Shopping" in summary
        assert summary["Shopping"] == -50.00
        # Load category not in spending summary (or shows separately)
        assert summary.get("Load", 0) == 0 or "deposits" in summary
