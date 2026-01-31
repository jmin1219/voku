"""
Toss CAD PDF parser.

Extracts raw transactions from Toss Bank CAD statement PDFs.
No enrichment — just structured data extraction.

PDF Format (Toss CAD):
- Date: "2026-JAN-24 12:25:06"
- Category: "Check Card" (spending) or "Deposit"
- Amount: "-5.76" or "1,000.00"
- Balance: "1,202.14"
- Details: Merchant name (may include Korean text)
"""

import re
from datetime import datetime
from pathlib import Path

import pdfplumber

from app.services.finance.models import RawTransaction


def parse_toss_cad_pdf(path: Path) -> list[RawTransaction]:
    """
    Parse a Toss Bank CAD statement PDF.
    
    Args:
        path: Path to the PDF file
        
    Returns:
        List of RawTransaction objects, sorted by date descending (newest first)
        
    Raises:
        FileNotFoundError: If the PDF doesn't exist
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    
    transactions = []
    
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            
            for table in tables:
                for row in table:
                    # Skip header rows and non-transaction rows
                    if not _is_transaction_row(row):
                        continue
                    
                    txn = _parse_row(row)
                    if txn:
                        transactions.append(txn)
    
    # Sort by date descending (newest first)
    transactions.sort(key=lambda t: t.date, reverse=True)
    
    return transactions


def _is_transaction_row(row: list) -> bool:
    """
    Check if a row is a transaction (not header or metadata).
    
    Transaction rows have:
    - Date in first column (format: YYYY-MMM-DD HH:MM:SS)
    - Category in second column (Check Card or Deposit)
    """
    if not row or len(row) < 5:
        return False
    
    first_cell = row[0] if row[0] else ""
    
    # Check for date pattern: 2026-JAN-24 or similar
    date_pattern = r'^\d{4}-[A-Z]{3}-\d{2}'
    return bool(re.match(date_pattern, first_cell))


def _parse_row(row: list) -> RawTransaction | None:
    """
    Parse a single transaction row.
    
    Expected columns:
    [0] Date: "2026-JAN-24 12:25:06"
    [1] Category: "Check Card" or "Deposit"
    [2] Amount: "-5.76" or "1,000.00"
    [3] Balance: "1,202.14"
    [4] Details: Merchant name
    """
    try:
        # Parse date
        date_str = row[0].strip()
        date = _parse_date(date_str)
        
        # Parse category to determine transaction type
        category = row[1].strip() if row[1] else ""
        transaction_type = "deposit" if category == "Deposit" else "spending"
        
        # Parse amount (remove commas, handle negative)
        amount_str = row[2].strip().replace(",", "")
        amount = float(amount_str)
        
        # Parse balance
        balance_str = row[3].strip().replace(",", "")
        balance = float(balance_str)
        
        # Get raw description (may span multiple lines, clean it up)
        raw_description = row[4].strip() if row[4] else ""
        # Remove any newlines or extra whitespace
        raw_description = " ".join(raw_description.split())
        
        return RawTransaction(
            date=date,
            amount=amount,
            balance=balance,
            raw_description=raw_description,
            transaction_type=transaction_type
        )
        
    except (ValueError, IndexError, AttributeError) as e:
        # Log and skip malformed rows
        print(f"Warning: Could not parse row: {row} - {e}")
        return None


def _parse_date(date_str: str) -> datetime:
    """
    Parse Toss date format: "2026-JAN-24 12:25:06" or "2026-JAN-2412:25:06"
    
    The PDF sometimes concatenates date and time without space.
    """
    # Handle concatenated format (no space between date and time)
    # "2026-JAN-2412:25:06" -> "2026-JAN-24 12:25:06"
    date_str = re.sub(r'(\d{2})(\d{2}:\d{2}:\d{2})', r'\1 \2', date_str)
    
    # Parse with month abbreviation
    return datetime.strptime(date_str, "%Y-%b-%d %H:%M:%S")
