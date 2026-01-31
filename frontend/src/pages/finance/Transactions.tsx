import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDate } from "@/lib/utils";

interface Transaction {
  id: string;
  date: string;
  amount: number;
  merchant: string;
  category: string;
  transaction_type: string;
}

// Category badge mapping for light surfaces
const categoryBadgeClass: Record<string, string> = {
  // Food → orange
  Delivery: "badge-category-food-light",
  "Meal Prep": "badge-category-food-light",
  "Eating Out": "badge-category-food-light",
  Groceries: "badge-category-food-light",
  // Transport → blue
  Transport: "badge-category-transport-light",
  // Shopping → pink
  Shopping: "badge-category-shopping-light",
  // Health → green
  Health: "badge-category-health-light",
  Grooming: "badge-category-health-light",
  // Entertainment → violet
  Entertainment: "badge-category-entertainment-light",
  Streaming: "badge-category-entertainment-light",
  // Vices → amber
  Vices: "badge-category-vices-light",
  // Bills/Load → slate/cyan
  Bills: "badge-category-bills-light",
  Load: "badge-category-load-light",
};

function getCategoryBadgeClass(category: string): string {
  return categoryBadgeClass[category] || "badge-category-bills-light";
}

export default function Transactions() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/finance/transactions")
      .then((res) => {
        if (!res.ok) throw new Error(`Failed: ${res.status}`);
        return res.json();
      })
      .then((data) => setTransactions(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-pulse" style={{ color: 'var(--finance-primary)' }}>
          Loading...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full" style={{ color: 'var(--color-error)' }}>
        {error}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-dark-primary)' }}>
          Transactions
        </h1>
        <div className="badge-finance-dark">
          {transactions.length} total
        </div>
      </div>

      {/* Table Card - Light surface for text-heavy content */}
      <Card className="flex-1 flex flex-col min-h-0 card-light">
        <CardHeader>
          <CardTitle className="text-sm font-medium" style={{ color: 'var(--text-light-secondary)' }}>
            All Transactions
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 overflow-auto p-0">
          <Table>
            <TableHeader>
              <TableRow style={{ borderColor: 'var(--border-light)' }}>
                <TableHead className="w-32" style={{ color: 'var(--text-light-secondary)' }}>Date</TableHead>
                <TableHead style={{ color: 'var(--text-light-secondary)' }}>Merchant</TableHead>
                <TableHead className="w-36" style={{ color: 'var(--text-light-secondary)' }}>Category</TableHead>
                <TableHead className="text-right w-32" style={{ color: 'var(--text-light-secondary)' }}>Amount</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {transactions.map((t) => (
                <TableRow 
                  key={t.id}
                  className="hover:bg-[var(--level-6)]"
                  style={{ borderColor: 'var(--border-light)' }}
                >
                  <TableCell className="font-mono text-sm" style={{ color: 'var(--text-light-muted)' }}>
                    {formatDate(t.date)}
                  </TableCell>
                  <TableCell className="font-medium" style={{ color: 'var(--text-light-primary)' }}>
                    {t.merchant}
                  </TableCell>
                  <TableCell>
                    <span className={getCategoryBadgeClass(t.category)}>
                      {t.category}
                    </span>
                  </TableCell>
                  <TableCell
                    className="text-right font-mono text-sm font-semibold"
                    style={{ color: t.amount < 0 ? 'var(--color-error)' : 'var(--color-success)' }}
                  >
                    {t.amount < 0 ? "-" : "+"}${Math.abs(t.amount).toFixed(2)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
