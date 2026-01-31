import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TrendingDown, Layers, Award } from "lucide-react";

interface SummaryResponse {
  month: string;
  categories: Record<string, number>;
}

// Category badge mapping
const categoryBadgeMap: Record<string, string> = {
  Delivery: "badge-category-food-light",
  "Meal Prep": "badge-category-food-light",
  "Eating Out": "badge-category-food-light",
  Groceries: "badge-category-food-light",
  Transport: "badge-category-transport-light",
  Shopping: "badge-category-shopping-light",
  Health: "badge-category-health-light",
  Grooming: "badge-category-health-light",
  Entertainment: "badge-category-entertainment-light",
  Streaming: "badge-category-entertainment-light",
  Vices: "badge-category-vices-light",
  Bills: "badge-category-bills-light",
  Load: "badge-category-load-light",
};

// Color dots for categories
const categoryDots: Record<string, string> = {
  Delivery: "#e6773a",
  "Meal Prep": "#e6773a",
  "Eating Out": "#e6773a",
  Groceries: "#e6773a",
  Transport: "#5d8fb0",
  Shopping: "#d66288",
  Health: "#5a9f6e",
  Grooming: "#5a9f6e",
  Entertainment: "#9c67cc",
  Streaming: "#9c67cc",
  Vices: "#d4a134",
  Bills: "#9a9286",
  Load: "#36b8c8",
};

export default function Summary() {
  const [data, setData] = useState<SummaryResponse | null>(null);
  const [month, setMonth] = useState("2026-01");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetch(`http://localhost:8000/finance/summary?month=${month}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed: ${res.status}`);
        return res.json();
      })
      .then((data) => setData(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [month]);

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

  if (!data) return null;

  const sortedCategories = Object.entries(data.categories).sort(
    (a, b) => a[1] - b[1]
  );
  const total = Object.values(data.categories).reduce((a, b) => a + b, 0);
  const topCategory = sortedCategories[0];

  return (
    <div className="h-full flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight gradient-text-finance">
          Spending Summary
        </h1>
        <div className="flex items-center gap-3">
          <Label htmlFor="month" className="text-sm" style={{ color: 'var(--text-dark-muted)' }}>
            Month
          </Label>
          <Input
            id="month"
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="w-40"
          />
        </div>
      </div>

      {/* Metrics Row - Stay on dark surfaces (glanceable data) */}
      <div className="grid grid-cols-3 gap-4">
        {/* Total Card */}
        <Card className="gradient-border-finance accent-finance card-dark">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" 
                   style={{ 
                     background: 'rgba(200, 85, 78, 0.25)', 
                     border: '2px solid rgba(200, 85, 78, 0.5)' 
                   }}>
                <TrendingDown className="w-4 h-4" style={{ color: 'var(--color-error)' }} />
              </div>
              <span className="text-[10px] font-semibold uppercase tracking-wider" 
                    style={{ color: 'var(--text-dark-secondary)' }}>
                Total Spent
              </span>
            </div>
            <div className="text-4xl font-bold font-mono tracking-tight" 
                 style={{ color: 'var(--finance-primary)' }}>
              ${Math.abs(total).toFixed(2)}
            </div>
            <p className="text-sm mt-1" style={{ color: 'var(--text-dark-muted)' }}>
              across {sortedCategories.length} categories
            </p>
          </CardContent>
        </Card>

        {/* Top Category Card */}
        <Card className="gradient-border-finance accent-finance card-dark">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" 
                   style={{ 
                     background: 'rgba(212, 161, 52, 0.25)', 
                     border: '2px solid rgba(212, 161, 52, 0.5)' 
                   }}>
                <Award className="w-4 h-4" style={{ color: 'var(--color-warning)' }} />
              </div>
              <span className="text-[10px] font-semibold uppercase tracking-wider" 
                    style={{ color: 'var(--text-dark-secondary)' }}>
                Top Category
              </span>
            </div>
            {topCategory && (
              <>
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: categoryDots[topCategory[0]] || '#9a9286' }}
                  />
                  <span className="text-lg font-semibold" style={{ color: 'var(--text-dark-primary)' }}>
                    {topCategory[0]}
                  </span>
                </div>
                <p className="text-3xl font-bold font-mono mt-1" 
                   style={{ color: 'var(--finance-primary)' }}>
                  ${Math.abs(topCategory[1]).toFixed(2)}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Categories Count */}
        <Card className="gradient-border-finance accent-finance card-dark">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" 
                   style={{ 
                     background: 'rgba(156, 103, 204, 0.25)', 
                     border: '2px solid rgba(156, 103, 204, 0.5)' 
                   }}>
                <Layers className="w-4 h-4" style={{ color: '#9c67cc' }} />
              </div>
              <span className="text-[10px] font-semibold uppercase tracking-wider" 
                    style={{ color: 'var(--text-dark-secondary)' }}>
                Categories
              </span>
            </div>
            <div className="text-4xl font-bold" style={{ color: 'var(--finance-secondary)' }}>
              {sortedCategories.length}
            </div>
            <p className="text-sm mt-1" style={{ color: 'var(--text-dark-muted)' }}>
              active this month
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Category Table - Light surface for text-heavy content */}
      <Card className="flex-1 flex flex-col min-h-0 card-light">
        <CardHeader>
          <CardTitle className="text-sm font-medium" style={{ color: 'var(--text-light-secondary)' }}>
            Spending by Category
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 overflow-auto p-0">
          <Table>
            <TableHeader>
              <TableRow style={{ borderColor: 'var(--border-light)' }}>
                <TableHead style={{ color: 'var(--text-light-secondary)' }}>Category</TableHead>
                <TableHead className="w-32 text-right" style={{ color: 'var(--text-light-secondary)' }}>Amount</TableHead>
                <TableHead className="w-24 text-right" style={{ color: 'var(--text-light-secondary)' }}>Share</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedCategories.map(([category, amount]) => {
                const percentage = ((Math.abs(amount) / Math.abs(total)) * 100).toFixed(1);
                return (
                  <TableRow 
                    key={category}
                    className="hover:bg-[var(--level-6)]"
                    style={{ borderColor: 'var(--border-light)' }}
                  >
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ backgroundColor: categoryDots[category] || '#9a9286' }}
                        />
                        <span className={categoryBadgeMap[category] || "badge-category-bills-light"}>
                          {category}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm font-medium" 
                               style={{ color: 'var(--text-light-primary)' }}>
                      ${Math.abs(amount).toFixed(2)}
                    </TableCell>
                    <TableCell className="text-right text-sm" style={{ color: 'var(--text-light-muted)' }}>
                      {percentage}%
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
            <TableFooter style={{ background: 'var(--level-6)', borderColor: 'var(--border-light)' }}>
              <TableRow>
                <TableCell className="font-semibold" style={{ color: 'var(--text-light-primary)' }}>
                  Total
                </TableCell>
                <TableCell className="text-right font-mono font-bold" style={{ color: 'var(--finance-primary)' }}>
                  ${Math.abs(total).toFixed(2)}
                </TableCell>
                <TableCell className="text-right font-semibold" style={{ color: 'var(--text-light-secondary)' }}>
                  100%
                </TableCell>
              </TableRow>
            </TableFooter>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
