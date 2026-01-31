"""
Finance module CLI.

Commands:
  import <path>           Import transactions from Toss CAD PDF
  summary --month YYYY-MM Monthly spending summary
  list [--last N] [--category X] [--merchant X]  List transactions

Usage:
  python -m app.services.finance.cli import ../data/finance/imports/CAD_Toss.pdf
  python -m app.services.finance.cli summary --month 2026-01
  python -m app.services.finance.cli list --last 20
"""

import argparse
import asyncio
from pathlib import Path
from datetime import datetime

from app.services.finance.parser import parse_toss_cad_pdf
from app.services.finance.categorizer import categorize_transactions
from app.services.finance.db import FinanceDB


# Default database path (repo_root/data/voku.db)
# cli.py is at backend/app/services/finance/cli.py
# Go up 5 levels: finance -> services -> app -> backend -> repo_root
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "voku.db"


def get_db() -> FinanceDB:
    """Get database connection, creating schema if needed."""
    db = FinanceDB(DEFAULT_DB_PATH)
    db.seed_categories()  # Idempotent
    return db


async def cmd_import(args):
    """Import transactions from PDF."""
    pdf_path = Path(args.path)
    
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        return 1
    
    print(f"Parsing {pdf_path.name}...")
    raw_transactions = parse_toss_cad_pdf(pdf_path)
    print(f"Found {len(raw_transactions)} transactions")
    
    db = get_db()
    
    print("Categorizing transactions...")
    enriched = await categorize_transactions(raw_transactions, db)
    
    print("Saving to database...")
    inserted = 0
    skipped = 0
    
    for txn in enriched:
        if db.insert_transaction(txn, source="toss_cad_pdf"):
            inserted += 1
        else:
            skipped += 1
    
    db.close()
    
    print(f"\nImport complete:")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped (duplicates): {skipped}")
    
    return 0


def cmd_summary(args):
    """Show monthly spending summary."""
    month = args.month
    
    # Validate month format
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        print(f"Error: Invalid month format. Use YYYY-MM (e.g., 2026-01)")
        return 1
    
    db = get_db()
    summary = db.get_summary(month)
    
    # Get all transactions for the month to calculate deposits
    transactions = db.get_transactions()
    month_start = datetime.strptime(f"{month}-01", "%Y-%m-%d")
    next_month = month_start.month + 1
    next_year = month_start.year
    if next_month > 12:
        next_month = 1
        next_year += 1
    month_end = datetime(next_year, next_month, 1)
    
    deposits = sum(
        t.amount for t in transactions
        if t.transaction_type == "deposit"
        and month_start <= t.date < month_end
    )
    
    db.close()
    
    if not summary:
        print(f"No spending data for {month}")
        return 0
    
    # Group by parent category
    category_groups = {}
    for cat, amount in summary.items():
        # Find parent category
        parent = _get_parent_category(cat)
        if parent:
            if parent not in category_groups:
                category_groups[parent] = {}
            category_groups[parent][cat] = amount
        else:
            # Top-level category
            if cat not in category_groups:
                category_groups[cat] = {}
            category_groups[cat]["_total"] = amount
    
    # Display
    print(f"\n{_format_month(month)} Spending Summary")
    print("─" * 35)
    
    total = 0
    for parent in sorted(category_groups.keys()):
        subcats = category_groups[parent]
        
        if "_total" in subcats and len(subcats) == 1:
            # Only top-level, no subcategories
            amount = subcats["_total"]
            print(f"{parent:20} ${abs(amount):>10.2f}")
            total += amount
        else:
            # Has subcategories
            parent_total = sum(v for k, v in subcats.items() if k != "_total")
            print(f"{parent}")
            for subcat, amount in sorted(subcats.items()):
                if subcat == "_total":
                    continue
                print(f"  {subcat:18} ${abs(amount):>10.2f}")
                total += amount
    
    print("─" * 35)
    print(f"{'Total Spending':20} ${abs(total):>10.2f}")
    
    if deposits > 0:
        print(f"{'Deposits':20} ${deposits:>10.2f}")
    
    print()
    return 0


def cmd_list(args):
    """List transactions."""
    db = get_db()
    
    transactions = db.get_transactions(
        category=args.category,
        merchant=args.merchant,
        limit=args.last
    )
    
    db.close()
    
    if not transactions:
        print("No transactions found.")
        return 0
    
    # Table header
    print(f"\n{'Date':<12} {'Merchant':<15} {'Category':<12} {'Amount':>10}")
    print("─" * 55)
    
    for txn in transactions:
        date_str = txn.date.strftime("%Y-%m-%d")
        merchant = (txn.merchant or "Unknown")[:14]
        category = (txn.category or "")[:11]
        amount_str = f"${txn.amount:,.2f}"
        
        print(f"{date_str:<12} {merchant:<15} {category:<12} {amount_str:>10}")
    
    print()
    return 0


def _get_parent_category(category: str) -> str | None:
    """Get parent category for subcategories."""
    hierarchy = {
        "Delivery": "Food",
        "Groceries": "Food",
        "Eating Out": "Food",
        "Meal Prep": "Food",
        "Streaming": "Subscriptions",
        "Software": "Subscriptions",
        "Grooming": "Personal Care",
        "Clothes": "Shopping",
        "Tech": "Shopping",
        "Home": "Shopping",
        "Transit": "Transport",
        "Rideshare": "Transport",
        "Load": "Transfer",
    }
    return hierarchy.get(category)


def _format_month(month: str) -> str:
    """Format YYYY-MM as 'Month YYYY'."""
    dt = datetime.strptime(f"{month}-01", "%Y-%m-%d")
    return dt.strftime("%B %Y")


def main():
    parser = argparse.ArgumentParser(
        description="Voku Finance Module",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import from PDF")
    import_parser.add_argument("path", help="Path to Toss CAD PDF")
    
    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Monthly summary")
    summary_parser.add_argument("--month", required=True, help="Month (YYYY-MM)")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List transactions")
    list_parser.add_argument("--last", type=int, default=20, help="Number of transactions")
    list_parser.add_argument("--category", help="Filter by category")
    list_parser.add_argument("--merchant", help="Filter by merchant")
    
    args = parser.parse_args()
    
    if args.command == "import":
        return asyncio.run(cmd_import(args))
    elif args.command == "summary":
        return cmd_summary(args)
    elif args.command == "list":
        return cmd_list(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    exit(main())
