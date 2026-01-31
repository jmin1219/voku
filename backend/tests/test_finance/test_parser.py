"""
Tests for Toss CAD PDF parser.

TDD: These tests define the contract for parser.py.
Run with: python -m pytest tests/test_finance/test_parser.py -v
"""

import pytest
from datetime import datetime
from pathlib import Path

from app.services.finance.parser import parse_toss_cad_pdf
from app.services.finance.models import RawTransaction


# Sample data extracted from actual CAD_Toss.pdf (Jan 8-24, 2026)
# Using this for test validation
EXPECTED_FIRST_ROW = {
    "date": datetime(2026, 1, 24, 12, 25, 6),
    "amount": 1000.00,  # Deposit (positive)
    "balance": 1202.14,
    "raw_description": "CAD 사기",
    "transaction_type": "deposit"
}

EXPECTED_SECOND_ROW = {
    "date": datetime(2026, 1, 24, 4, 25, 6),
    "amount": -5.76,  # Spending (negative)
    "balance": 202.14,
    "raw_description": "BLENZ ON ROBSON & CARD",
    "transaction_type": "spending"
}


class TestParserOutput:
    """Verify parser returns correct structure."""
    
    @pytest.fixture
    def pdf_path(self):
        """Path to test PDF."""
        # Adjust this path based on where the PDF is stored
        path = Path(__file__).parent.parent.parent.parent / "data" / "finance" / "imports" / "CAD_Toss.pdf"
        if not path.exists():
            pytest.skip(f"Test PDF not found at {path}")
        return path
    
    def test_returns_list_of_raw_transactions(self, pdf_path):
        """Parser returns a list of RawTransaction objects."""
        result = parse_toss_cad_pdf(pdf_path)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(t, RawTransaction) for t in result)
    
    def test_extracts_correct_count(self, pdf_path):
        """Parser extracts all 20 transactions from the sample PDF."""
        result = parse_toss_cad_pdf(pdf_path)
        
        # The PDF has 20 rows (19 Check Card + 1 Deposit)
        assert len(result) == 20
    
    def test_first_transaction_is_deposit(self, pdf_path):
        """First row is the deposit (most recent by date)."""
        result = parse_toss_cad_pdf(pdf_path)
        
        # Sorted by date descending, first should be Jan 24 deposit
        first = result[0]
        assert first.transaction_type == "deposit"
        assert first.amount == 1000.00
        assert first.raw_description == "CAD 사기"
    
    def test_spending_amounts_are_negative(self, pdf_path):
        """Spending transactions have negative amounts."""
        result = parse_toss_cad_pdf(pdf_path)
        
        spending = [t for t in result if t.transaction_type == "spending"]
        assert len(spending) == 19  # All except the deposit
        assert all(t.amount < 0 for t in spending)
    
    def test_parses_datetime_correctly(self, pdf_path):
        """Datetime includes both date and time components."""
        result = parse_toss_cad_pdf(pdf_path)
        
        # Check the deposit row specifically
        deposit = next(t for t in result if t.amount > 0)
        assert deposit.date.year == 2026
        assert deposit.date.month == 1
        assert deposit.date.day == 24
        assert deposit.date.hour == 12
        assert deposit.date.minute == 25
    
    def test_preserves_raw_description(self, pdf_path):
        """Raw description is preserved exactly as in PDF."""
        result = parse_toss_cad_pdf(pdf_path)
        
        # Find the Blenz transaction
        blenz = next((t for t in result if "BLENZ" in t.raw_description), None)
        assert blenz is not None
        assert blenz.raw_description == "BLENZ ON ROBSON & CARD"
    
    def test_extracts_balance(self, pdf_path):
        """Balance column is extracted."""
        result = parse_toss_cad_pdf(pdf_path)
        
        # All transactions should have balance
        assert all(t.balance is not None for t in result)
        
        # First transaction (deposit) should have balance 1202.14
        deposit = next(t for t in result if t.amount > 0)
        assert deposit.balance == 1202.14


class TestParserEdgeCases:
    """Edge case handling."""
    
    def test_handles_missing_file(self):
        """Raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            parse_toss_cad_pdf(Path("/nonexistent/path.pdf"))
    
    def test_handles_korean_text_in_description(self, pdf_path=None):
        """Korean characters in description are preserved."""
        # Skip if no PDF
        path = Path(__file__).parent.parent.parent.parent / "data" / "finance" / "imports" / "CAD_Toss.pdf"
        if not path.exists():
            pytest.skip("Test PDF not found")
        
        result = parse_toss_cad_pdf(path)
        
        # Find the deposit which has Korean description
        deposit = next(t for t in result if t.amount > 0)
        assert "사기" in deposit.raw_description  # Korean characters preserved
