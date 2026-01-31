import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dumbbell,
  Wallet,
  Upload,
  History,
  ArrowRight,
  Activity,
  PieChart,
  Zap,
} from "lucide-react";

export default function Home() {
  return (
    <div className="h-full flex flex-col gap-8 max-w-5xl">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold tracking-tight" style={{ color: 'var(--text-dark-primary)' }}>
            Welcome to{" "}
            <span className="gradient-text-finance">
              Voku
            </span>
          </h1>
          <Zap className="w-6 h-6" style={{ color: 'var(--finance-primary)' }} />
        </div>
        <p style={{ color: 'var(--text-dark-muted)' }}>
          Your cognitive prosthetic for fitness and finance tracking
        </p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-4">
        <Link to="/fitness/log" className="group">
          <Card 
            className="h-full cursor-pointer card-dark transition-all"
            style={{
              borderColor: 'var(--border-dark)'
            }}
          >
            <CardContent className="p-5 flex items-start justify-between">
              <div className="flex-1">
                <div 
                  className="w-10 h-10 rounded-lg flex items-center justify-center mb-4" 
                  style={{ 
                    background: 'rgba(230, 119, 58, 0.2)', 
                    border: '1px solid rgba(230, 119, 58, 0.3)' 
                  }}
                >
                  <Dumbbell className="w-5 h-5" style={{ color: 'var(--fitness-primary)' }} />
                </div>
                <h3 className="font-semibold mb-1" style={{ color: 'var(--text-dark-primary)' }}>
                  Log Workout
                </h3>
                <p className="text-sm" style={{ color: 'var(--text-dark-muted)' }}>
                  Upload a screenshot to extract training data
                </p>
              </div>
              <ArrowRight 
                className="w-5 h-5 group-hover:translate-x-1 transition-all" 
                style={{ color: 'var(--text-dark-muted)' }}
              />
            </CardContent>
          </Card>
        </Link>

        <Link to="/finance/import" className="group">
          <Card 
            className="h-full cursor-pointer card-dark transition-all"
            style={{
              borderColor: 'var(--border-dark)'
            }}
          >
            <CardContent className="p-5 flex items-start justify-between">
              <div className="flex-1">
                <div 
                  className="w-10 h-10 rounded-lg flex items-center justify-center mb-4" 
                  style={{ 
                    background: 'rgba(54, 184, 200, 0.2)', 
                    border: '1px solid rgba(54, 184, 200, 0.3)' 
                  }}
                >
                  <Upload className="w-5 h-5" style={{ color: 'var(--finance-primary)' }} />
                </div>
                <h3 className="font-semibold mb-1" style={{ color: 'var(--text-dark-primary)' }}>
                  Import Transactions
                </h3>
                <p className="text-sm" style={{ color: 'var(--text-dark-muted)' }}>
                  Upload a bank statement PDF
                </p>
              </div>
              <ArrowRight 
                className="w-5 h-5 group-hover:translate-x-1 transition-all" 
                style={{ color: 'var(--text-dark-muted)' }}
              />
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Domain Cards */}
      <div className="grid grid-cols-2 gap-6">
        {/* Fitness */}
        <Card className="card-dark">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div 
                className="w-8 h-8 rounded-lg flex items-center justify-center" 
                style={{ 
                  background: 'rgba(230, 119, 58, 0.2)', 
                  border: '1px solid rgba(230, 119, 58, 0.3)' 
                }}
              >
                <Activity className="w-4 h-4" style={{ color: 'var(--fitness-primary)' }} />
              </div>
              <h2 className="text-lg font-semibold" style={{ color: 'var(--text-dark-primary)' }}>
                Fitness
              </h2>
            </div>
            <p className="text-sm mb-6" style={{ color: 'var(--text-dark-muted)' }}>
              Track workouts, monitor trends, optimize training.
            </p>
            <div className="flex gap-3">
              <Link to="/fitness/log">
                <Button variant="outline" size="sm">
                  <Upload className="w-4 h-4" />
                  Log
                </Button>
              </Link>
              <Link to="/fitness/history">
                <Button variant="outline" size="sm">
                  <History className="w-4 h-4" />
                  History
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Finance */}
        <Card className="card-dark">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div 
                className="w-8 h-8 rounded-lg flex items-center justify-center" 
                style={{ 
                  background: 'rgba(54, 184, 200, 0.2)', 
                  border: '1px solid rgba(54, 184, 200, 0.3)' 
                }}
              >
                <Wallet className="w-4 h-4" style={{ color: 'var(--finance-primary)' }} />
              </div>
              <h2 className="text-lg font-semibold" style={{ color: 'var(--text-dark-primary)' }}>
                Finance
              </h2>
            </div>
            <p className="text-sm mb-6" style={{ color: 'var(--text-dark-muted)' }}>
              Import transactions, categorize spending, see summaries.
            </p>
            <div className="flex gap-3">
              <Link to="/finance/import">
                <Button variant="outline" size="sm">
                  <Upload className="w-4 h-4" />
                  Import
                </Button>
              </Link>
              <Link to="/finance/summary">
                <Button variant="outline" size="sm">
                  <PieChart className="w-4 h-4" />
                  Summary
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
