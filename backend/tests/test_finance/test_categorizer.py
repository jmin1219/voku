"""
Tests for merchant categorizer.

TDD: These tests define the contract for categorizer.py.
Run with: python -m pytest tests/test_finance/test_categorizer.py -v
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch
import tempfile
import os
import json

from app.services.finance.categorizer import (
    categorize_transactions,
    parse_llm_response,
    build_categorization_prompt,
)
from app.services.finance.models import RawTransaction, EnrichedTransaction
from app.services.finance.db import FinanceDB


@pytest.fixture
def db():
    """Create a temporary database with seeded categories."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    database = FinanceDB(db_path)
    database.seed_categories()
    yield database
    
    database.close()
    os.unlink(db_path)


@pytest.fixture
def sample_raw_transactions():
    """Sample transactions for testing."""
    return [
        RawTransaction(
            date=datetime(2026, 1, 24, 12, 25, 6),
            amount=1000.00,
            balance=1202.14,
            raw_description="CAD 사기",
            transaction_type="deposit"
        ),
        RawTransaction(
            date=datetime(2026, 1, 23, 14, 8, 59),
            amount=-68.53,
            balance=207.90,
            raw_description="DOORDASHPRINKLECHIC",
            transaction_type="spending"
        ),
        RawTransaction(
            date=datetime(2026, 1, 17, 8, 36, 14),
            amount=-52.50,
            balance=570.55,
            raw_description="RAUM HAIR",
            transaction_type="spending"
        ),
    ]


class TestPatternCache:
    """Pattern cache lookup behavior."""
    
    @pytest.mark.asyncio
    async def test_uses_cached_pattern_when_available(self, db, sample_raw_transactions):
        """If pattern exists in DB, uses it without LLM call."""
        # Pre-populate cache
        db.create_merchant("DoorDash", "Delivery")
        db.create_pattern("DOORDASHPRINKLECHIC", "DoorDash", vendor="Prinkle Chic")
        
        # Only the DoorDash transaction
        txn = sample_raw_transactions[1]
        
        # Mock LLM to verify it's not called
        with patch("app.services.finance.categorizer.call_llm") as mock_llm:
            result = await categorize_transactions([txn], db)
        
        # LLM should not be called for cached pattern
        mock_llm.assert_not_called()
        
        # Result should use cached data
        assert len(result) == 1
        assert result[0].merchant == "DoorDash"
        assert result[0].vendor == "Prinkle Chic"
        assert result[0].category == "Delivery"
    
    @pytest.mark.asyncio
    async def test_pattern_with_category_override(self, db):
        """Pattern's category_override takes precedence over merchant default."""
        db.create_merchant("DoorDash", "Delivery")
        db.create_pattern(
            "DOORDASHNOFRILLS",
            "DoorDash",
            vendor="No Frills",
            category_override="Groceries"
        )
        
        txn = RawTransaction(
            date=datetime(2026, 1, 8, 18, 35, 33),
            amount=-83.60,
            balance=919.74,
            raw_description="DOORDASHNOFRILLS",
            transaction_type="spending"
        )
        
        with patch("app.services.finance.categorizer.call_llm"):
            result = await categorize_transactions([txn], db)
        
        assert result[0].category == "Groceries"  # Override, not default "Delivery"


class TestLLMCategorization:
    """LLM-based categorization for unknown patterns."""
    
    @pytest.mark.asyncio
    async def test_calls_llm_for_unknown_patterns(self, db, sample_raw_transactions):
        """Unknown patterns trigger LLM call."""
        # Only the RAUM HAIR transaction (not in cache)
        txn = sample_raw_transactions[2]
        
        mock_response = json.dumps([{
            "raw": "RAUM HAIR",
            "merchant": "Raum Hair",
            "vendor": None,
            "category": "Grooming"
        }])
        
        with patch("app.services.finance.categorizer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await categorize_transactions([txn], db)
        
        # LLM was called
        mock_llm.assert_called_once()
        
        # Result uses LLM output
        assert len(result) == 1
        assert result[0].merchant == "Raum Hair"
        assert result[0].category == "Grooming"
    
    @pytest.mark.asyncio
    async def test_creates_merchant_for_new_merchants(self, db):
        """New merchants from LLM are persisted to DB."""
        txn = RawTransaction(
            date=datetime(2026, 1, 16, 7, 5, 55),
            amount=-43.74,
            balance=666.79,
            raw_description="VAN VAPES",
            transaction_type="spending"
        )
        
        mock_response = json.dumps([{
            "raw": "VAN VAPES",
            "merchant": "Van Vapes",
            "vendor": None,
            "category": "Vices"
        }])
        
        with patch("app.services.finance.categorizer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            await categorize_transactions([txn], db)
        
        # Merchant should be created
        merchant = db.get_merchant("Van Vapes")
        assert merchant is not None
        assert merchant.default_category == "Vices"
    
    @pytest.mark.asyncio
    async def test_creates_pattern_for_new_raw_strings(self, db):
        """New patterns are persisted for future cache hits."""
        txn = RawTransaction(
            date=datetime(2026, 1, 11, 6, 38, 43),
            amount=-8.95,
            balance=855.37,
            raw_description="NETFLIX.COM",
            transaction_type="spending"
        )
        
        mock_response = json.dumps([{
            "raw": "NETFLIX.COM",
            "merchant": "Netflix",
            "vendor": None,
            "category": "Streaming"
        }])
        
        with patch("app.services.finance.categorizer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            await categorize_transactions([txn], db)
        
        # Pattern should be created
        pattern = db.get_pattern("NETFLIX.COM")
        assert pattern is not None
        assert pattern.merchant == "Netflix"


class TestDepositHandling:
    """Deposit transactions need special handling."""
    
    @pytest.mark.asyncio
    async def test_deposits_get_transfer_category(self, db, sample_raw_transactions):
        """Deposits are categorized as Transfer/Load."""
        deposit = sample_raw_transactions[0]
        
        with patch("app.services.finance.categorizer.call_llm"):
            result = await categorize_transactions([deposit], db)
        
        assert result[0].category == "Load"
        assert result[0].merchant == "Transfer"


class TestPromptBuilding:
    """Verify prompt construction."""
    
    def test_builds_prompt_with_raw_descriptions(self):
        """Prompt includes all raw descriptions."""
        raw_descs = ["DOORDASHPRINKLECHIC", "VAN VAPES", "RAUM HAIR"]
        
        prompt = build_categorization_prompt(raw_descs)
        
        assert "DOORDASHPRINKLECHIC" in prompt
        assert "VAN VAPES" in prompt
        assert "RAUM HAIR" in prompt
    
    def test_prompt_requests_json_format(self):
        """Prompt specifies JSON output format."""
        prompt = build_categorization_prompt(["TEST"])
        
        assert "JSON" in prompt or "json" in prompt


class TestResponseParsing:
    """LLM response parsing."""
    
    def test_parses_valid_json_array(self):
        """Parses well-formed JSON response."""
        response = json.dumps([
            {"raw": "DOORDASH1", "merchant": "DoorDash", "vendor": "Vendor1", "category": "Delivery"},
            {"raw": "NETFLIX", "merchant": "Netflix", "vendor": None, "category": "Streaming"}
        ])
        
        result = parse_llm_response(response)
        
        assert len(result) == 2
        assert result["DOORDASH1"]["merchant"] == "DoorDash"
        assert result["NETFLIX"]["category"] == "Streaming"
    
    def test_handles_json_in_markdown_code_block(self):
        """Handles LLM wrapping JSON in markdown."""
        response = """```json
[{"raw": "TEST", "merchant": "Test", "vendor": null, "category": "Shopping"}]
```"""
        
        result = parse_llm_response(response)
        
        assert "TEST" in result
        assert result["TEST"]["merchant"] == "Test"
    
    def test_returns_empty_dict_for_invalid_json(self):
        """Invalid JSON returns empty dict, doesn't crash."""
        response = "This is not JSON"
        
        result = parse_llm_response(response)
        
        assert result == {}
