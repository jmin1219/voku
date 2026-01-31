import os
import tempfile
from pathlib import Path

from app.services.finance.categorizer import categorize_transactions
from app.services.finance.db import FinanceDB
from app.services.finance.parser import parse_toss_cad_pdf
from fastapi import APIRouter, File, UploadFile

router = APIRouter()

# Database path (same as CLI)
DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "voku.db"


def get_db() -> FinanceDB:
    """Get database connection"""
    db = FinanceDB(DB_PATH)
    db.seed_categories()
    return db


@router.post("/import")
async def import_transactions(file: UploadFile = File(...)):
    """Import transactions from a PDF file"""
    # 1. Save uploaded PDF to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    # 2. Parse with parse_toss_cad_pdf()
    transactions = parse_toss_cad_pdf(tmp_path)
    os.remove(tmp_path)

    # 3. Categorize with categorize_transactions()
    db = get_db()
    categorized = await categorize_transactions(transactions, db)
    inserted = 0
    skipped = 0
    for tx in categorized:
        success = db.insert_transaction(tx, source="toss_cad_pdf")
        if success:
            inserted += 1
        else:
            skipped += 1

    # Close DB connection
    db.close()

    # 4. Insert each transaction, count inserted vs skipped
    total = len(categorized)

    # 5. Return {"inserted": N, "skipped": N, "total": N}
    return {"inserted": inserted, "skipped": skipped, "total": total}


@router.get("/transactions")
def get_transactions(
    category: str | None = None, merchant: str | None = None, limit: int = 50
):
    """Get transactions with optional filters."""
    db = get_db()
    transactions = db.get_transactions(
        category=category, merchant=merchant, limit=limit
    )
    db.close()

    # Convert to JSON-serializable format
    return [
        {
            "id": t.id,
            "date": t.date.isoformat(),
            "amount": t.amount,
            "merchant": t.merchant,
            "category": t.category,
            "transaction_type": t.transaction_type,
        }
        for t in transactions
    ]


@router.get("/summary")
def get_summary(month: str):
    """
    Get spending summary by category for a month.

    Args:
        month: Format "YYYY-MM" (e.g., "2026-01")
    """
    db = get_db()
    summary = db.get_summary(month)
    db.close()

    return {"month": month, "categories": summary}
