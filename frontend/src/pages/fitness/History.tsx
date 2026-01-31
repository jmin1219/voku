import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Dumbbell, Bike, Footprints, Waves, Activity, Zap, Plus, Edit, Trash2, CheckCircle2, AlertCircle, Calendar, Clock } from "lucide-react";
import { formatDate } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";
import SessionForm from "@/components/fitness/SessionForm";

interface Session {
  id: string;
  created_at: string;
  workout_date?: string;
  workout_time?: string;
  workout_type?: string;
  variables: Record<string, { value: string; unit: string | null }> | {
    workout_type: string;
    variables: Record<string, { value: string; unit: string | null }>;
  };
  updated_at?: string;
}

interface SessionPayload {
  workout_type: string;
  variables: Record<string, { value: string; unit: string }>;
  workout_date?: string;
  workout_time?: string;
}

interface RegistryVariable {
  display: string;
  unit: string;
  aliases: string[];
  count: number;
}

const workoutConfig: Record<
  string,
  { icon: LucideIcon; color: string; bg: string; border: string }
> = {
  "Indoor Cycle": {
    icon: Bike,
    color: "#e6773a",
    bg: "rgba(230, 119, 58, 0.2)",
    border: "2px solid rgba(230, 119, 58, 0.4)",
  },
  Cycling: {
    icon: Bike,
    color: "#e6773a",
    bg: "rgba(230, 119, 58, 0.2)",
    border: "2px solid rgba(230, 119, 58, 0.4)",
  },
  Running: {
    icon: Footprints,
    color: "#5a9f6e",
    bg: "rgba(90, 159, 110, 0.2)",
    border: "2px solid rgba(90, 159, 110, 0.4)",
  },
  Swimming: {
    icon: Waves,
    color: "#36b8c8",
    bg: "rgba(54, 184, 200, 0.2)",
    border: "2px solid rgba(54, 184, 200, 0.4)",
  },
  Strength: {
    icon: Dumbbell,
    color: "#9c67cc",
    bg: "rgba(156, 103, 204, 0.2)",
    border: "2px solid rgba(156, 103, 204, 0.4)",
  },
  Rowing: {
    icon: Activity,
    color: "#5d8fb0",
    bg: "rgba(93, 143, 176, 0.2)",
    border: "2px solid rgba(93, 143, 176, 0.4)",
  },
  "Upper Body": {
    icon: Dumbbell,
    color: "#9c67cc",
    bg: "rgba(156, 103, 204, 0.2)",
    border: "2px solid rgba(156, 103, 204, 0.4)",
  },
  "S&S": {
    icon: Dumbbell,
    color: "#9c67cc",
    bg: "rgba(156, 103, 204, 0.2)",
    border: "2px solid rgba(156, 103, 204, 0.4)",
  },
  "Zone 2 Row": {
    icon: Activity,
    color: "#5d8fb0",
    bg: "rgba(93, 143, 176, 0.2)",
    border: "2px solid rgba(93, 143, 176, 0.4)",
  },
  "Zone 2 Bike": {
    icon: Bike,
    color: "#e6773a",
    bg: "rgba(230, 119, 58, 0.2)",
    border: "2px solid rgba(230, 119, 58, 0.4)",
  },
};

function getWorkoutConfig(type: string) {
  return (
    workoutConfig[type] || {
      icon: Activity,
      color: "#9a9286",
      bg: "rgba(154, 146, 134, 0.15)",
      border: "1px solid rgba(154, 146, 134, 0.3)",
    }
  );
}

function getWorkoutType(session: Session): string {
  if (session.workout_type) return session.workout_type;
  if ('workout_type' in session.variables) {
    return (session.variables as any).workout_type;
  }
  return "Unknown";
}

function getVariables(session: Session): Record<string, { value: string; unit: string | null }> {
  // Handle nested format (old format)
  if ('variables' in session.variables) {
    return (session.variables as any).variables;
  }
  
  // Handle flat format (current backend format) - transform to nested
  const vars = session.variables as any;
  const transformed: Record<string, { value: string; unit: string | null }> = {};
  
  for (const [key, value] of Object.entries(vars)) {
    transformed[key] = {
      value: String(value), // Convert to string (handles numbers)
      unit: null
    };
  }
  
  return transformed;
}

// Format workout datetime for display
function formatWorkoutDatetime(session: Session): string {
  if (session.workout_date && session.workout_time) {
    const date = new Date(session.workout_date + 'T' + session.workout_time);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  }
  // Fallback to created_at
  return formatDate(session.created_at);
}

export default function History() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selected, setSelected] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [showForm, setShowForm] = useState(false);
  const [formMode, setFormMode] = useState<"create" | "edit">("create");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  
  const [registry, setRegistry] = useState<Record<string, RegistryVariable>>({});

  const fetchSessions = () => {
    setLoading(true);
    fetch("http://localhost:8000/fitness/sessions")
      .then((res) => {
        if (!res.ok) throw new Error(`Failed: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setSessions(data);
        if (data.length > 0 && !selected) {
          setSelected(data[0]);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  const fetchRegistry = () => {
    fetch("http://localhost:8000/registry/variables")
      .then((res) => res.json())
      .then((data) => {
        setRegistry(data.variables || {});
      })
      .catch((err) => console.error("Failed to load registry:", err));
  };

  useEffect(() => {
    fetchSessions();
    fetchRegistry();
  }, []);

  const getDisplayName = (key: string): string => {
    if (registry[key]) {
      return registry[key].display;
    }
    
    for (const [canonical, info] of Object.entries(registry)) {
      if (info.aliases.includes(key)) {
        return info.display;
      }
    }
    
    return key
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const isInRegistry = (key: string): boolean => {
    if (registry[key]) return true;
    
    for (const info of Object.values(registry)) {
      if (info.aliases.includes(key)) return true;
    }
    
    return false;
  };

  const handleCreateSession = async (payload: SessionPayload) => {
    try {
      // Transform nested format to flat format for backend
      const flatVariables: Record<string, any> = {};
      for (const [key, { value }] of Object.entries(payload.variables)) {
        // Try to parse as number, otherwise keep as string
        const numValue = parseFloat(value);
        flatVariables[key] = isNaN(numValue) ? value : numValue;
      }
      
      const backendPayload = {
        workout_type: payload.workout_type,
        variables: flatVariables,
        workout_date: payload.workout_date,
        workout_time: payload.workout_time,
      };
      
      const response = await fetch("http://localhost:8000/fitness/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(backendPayload),
      });
      
      if (!response.ok) throw new Error("Failed to create session");
      
      const newSession = await response.json();
      setShowForm(false);
      fetchSessions();
      setSelected(newSession);
    } catch (err) {
      alert("Error creating session: " + (err as Error).message);
    }
  };

  const handleUpdateSession = async (payload: SessionPayload) => {
    if (!selected) return;
    
    try {
      // Transform nested format to flat format for backend
      const flatVariables: Record<string, any> = {};
      for (const [key, { value }] of Object.entries(payload.variables)) {
        // Try to parse as number, otherwise keep as string
        const numValue = parseFloat(value);
        flatVariables[key] = isNaN(numValue) ? value : numValue;
      }
      
      const backendPayload = {
        workout_type: payload.workout_type,
        variables: flatVariables,
        workout_date: payload.workout_date,
        workout_time: payload.workout_time,
      };
      
      const response = await fetch(
        `http://localhost:8000/fitness/sessions/${selected.id}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(backendPayload),
        }
      );
      
      if (!response.ok) throw new Error("Failed to update session");
      
      const updated = await response.json();
      setShowForm(false);
      fetchSessions();
      setSelected(updated);
    } catch (err) {
      alert("Error updating session: " + (err as Error).message);
    }
  };

  const handleDeleteSession = async () => {
    if (!selected) return;
    
    try {
      const response = await fetch(
        `http://localhost:8000/fitness/sessions/${selected.id}`,
        {
          method: "DELETE",
        }
      );
      
      if (!response.ok) throw new Error("Failed to delete session");
      
      setShowDeleteConfirm(false);
      setSelected(null);
      fetchSessions();
    } catch (err) {
      alert("Error deleting session: " + (err as Error).message);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-pulse" style={{ color: 'var(--fitness-primary)' }}>
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

  if (sessions.length === 0 && !showForm) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="w-16 h-16 rounded-2xl flex items-center justify-center card-dark">
          <Activity className="w-8 h-8" style={{ color: 'var(--text-dark-muted)' }} />
        </div>
        <div className="text-center">
          <p className="font-medium" style={{ color: 'var(--text-dark-primary)' }}>
            No sessions logged yet
          </p>
          <p className="text-sm mt-1" style={{ color: 'var(--text-dark-muted)' }}>
            Upload a workout screenshot or log manually
          </p>
        </div>
        <Button 
          onClick={() => {
            setFormMode("create");
            setShowForm(true);
          }}
          className="mt-4"
        >
          <Plus className="w-4 h-4 mr-2" />
          Log New Session
        </Button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight gradient-text-fitness">
          Fitness History
        </h1>
        <div className="flex items-center gap-3">
          <div className="px-4 py-2 rounded-lg text-sm font-mono font-bold badge-fitness-dark">
            {sessions.length} sessions
          </div>
          <Button 
            onClick={() => {
              setFormMode("create");
              setShowForm(true);
            }}
          >
            <Plus className="w-4 h-4 mr-2" />
            New Session
          </Button>
        </div>
      </div>

      {/* Content - Master-Detail Pattern */}
      <div className="flex-1 min-h-0 grid grid-cols-3 gap-6">
        {/* Session List */}
        <Card className="col-span-1 flex flex-col min-h-0 card-dark">
          <CardHeader>
            <CardTitle className="text-sm font-medium" style={{ color: 'var(--text-dark-secondary)' }}>
              Sessions
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-auto p-3 space-y-2">
            {sessions.map((session) => {
              const workoutType = getWorkoutType(session);
              const config = getWorkoutConfig(workoutType);
              const Icon = config.icon;
              const isSelected = selected?.id === session.id;

              return (
                <div
                  key={session.id}
                  onClick={() => setSelected(session)}
                  className="p-3 rounded-xl cursor-pointer transition-all duration-200 hover:scale-[1.02]"
                  style={{
                    background: isSelected 
                      ? 'linear-gradient(to right, rgba(230, 119, 58, 0.15), rgba(212, 98, 42, 0.1))'
                      : 'transparent',
                    border: isSelected 
                      ? '2px solid rgba(230, 119, 58, 0.5)'
                      : '2px solid transparent',
                    boxShadow: isSelected
                      ? '0 0 20px -8px rgba(230, 119, 58, 0.4)'
                      : 'none'
                  }}
                >
                  <div className="flex items-center gap-3">
                    <div 
                      className="p-2.5 rounded-lg" 
                      style={{ 
                        background: config.bg, 
                        border: config.border 
                      }}
                    >
                      <Icon className="w-4 h-4" style={{ color: config.color }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm truncate" 
                         style={{ color: 'var(--text-dark-primary)' }}>
                        {workoutType}
                      </p>
                      <p className="text-xs font-mono" style={{ color: 'var(--text-dark-muted)' }}>
                        {formatWorkoutDatetime(session)}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Session Detail */}
        <Card className="col-span-2 flex flex-col min-h-0 card-light">
          {selected ? (
            <>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-3">
                    {(() => {
                      const workoutType = getWorkoutType(selected);
                      const config = getWorkoutConfig(workoutType);
                      const Icon = config.icon;
                      return (
                        <div 
                          className="p-3 rounded-lg" 
                          style={{ 
                            background: config.bg, 
                            border: config.border 
                          }}
                        >
                          <Icon className="w-6 h-6" style={{ color: config.color }} />
                        </div>
                      );
                    })()}
                    <div className="flex flex-col">
                      <span className="text-xl" style={{ color: 'var(--text-light-primary)' }}>
                        {getWorkoutType(selected)}
                      </span>
                      {selected.workout_date && selected.workout_time && (
                        <span className="text-sm flex items-center gap-2 mt-1" style={{ color: 'var(--text-light-muted)' }}>
                          <Calendar className="w-3 h-3" />
                          {selected.workout_date}
                          <Clock className="w-3 h-3 ml-2" />
                          {selected.workout_time}
                        </span>
                      )}
                    </div>
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="font-mono text-xs px-3 py-1.5 badge-fitness-light flex items-center gap-1">
                      <Zap className="w-3 h-3" />
                      {formatWorkoutDatetime(selected)}
                    </Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setFormMode("edit");
                        setShowForm(true);
                      }}
                      className="text-slate-300 hover:text-slate-100 hover:border-slate-400"
                    >
                      <Edit className="w-4 h-4 mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowDeleteConfirm(true)}
                      className="text-red-400/70 hover:text-red-400 hover:bg-red-500/10"
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      Delete
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex-1 overflow-auto p-6">
                <div className="space-y-4">
                  {Object.entries(getVariables(selected)).map(
                    ([rawKey, data]) => {
                      const displayName = getDisplayName(rawKey);
                      const inRegistry = isInRegistry(rawKey);
                      const isLongText = ['notes', 'zone_breakdown', 'pacing', 'breakthrough'].includes(rawKey);
                      
                      return (
                        <div 
                          key={rawKey}
                          className={`grid gap-2 p-4 rounded-lg transition-colors ${
                            isLongText ? 'grid-cols-1' : 'grid-cols-[200px_1fr]'
                          }`}
                          style={{ 
                            backgroundColor: 'rgba(0,0,0,0.02)',
                            border: '1px solid rgba(0,0,0,0.05)'
                          }}
                        >
                          {/* Metric Label */}
                          <div className="flex items-center gap-2">
                            {inRegistry ? (
                              <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                            ) : (
                              <AlertCircle className="w-4 h-4 text-yellow-500 flex-shrink-0" />
                            )}
                            <span className="font-medium text-sm text-slate-700">
                              {displayName}
                            </span>
                            {!inRegistry && (
                              <Badge variant="outline" className="text-xs px-1.5 py-0 border-yellow-500/30 text-yellow-600">
                                Unknown
                              </Badge>
                            )}
                          </div>
                          
                          {/* Value */}
                          <div className={isLongText ? "mt-2" : ""}>
                            {isLongText ? (
                              <p className="text-sm leading-relaxed text-slate-600 whitespace-pre-wrap break-words">
                                {data.value}
                              </p>
                            ) : (
                              <div className="flex items-baseline justify-end">
                                <span 
                                  className="font-mono text-2xl font-bold"
                                  style={{ color: 'var(--fitness-primary)' }}
                                >
                                  {data.value}
                                </span>
                                {data.unit && (
                                  <span className="ml-2 text-sm font-normal text-slate-500">
                                    {data.unit}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    }
                  )}
                </div>
              </CardContent>
            </>
          ) : (
            <CardContent className="flex items-center justify-center h-full" 
                         style={{ color: 'var(--text-light-muted)' }}>
              Select a session to view details
            </CardContent>
          )}
        </Card>
      </div>

      {/* Session Form Dialog */}
      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <SessionForm
            mode={formMode}
            initialData={formMode === "edit" && selected ? {
              id: selected.id,
              created_at: selected.created_at,
              workout_date: selected.workout_date,
              workout_time: selected.workout_time,
              workout_type: getWorkoutType(selected),
              variables: getVariables(selected),
            } : undefined}
            onSave={formMode === "create" ? handleCreateSession : handleUpdateSession}
            onCancel={() => setShowForm(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent className="bg-[#1a1a24] border-red-500/30">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-slate-100">Delete Session?</AlertDialogTitle>
            <AlertDialogDescription className="text-slate-400">
              This will permanently delete <span className="text-red-400 font-semibold">"{selected && getWorkoutType(selected)}"</span> from <span className="font-mono">{selected && formatWorkoutDatetime(selected)}</span>.
              <br />
              <span className="text-red-400/80">This action cannot be undone.</span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-[#22222e] border-[#2a2a3a] text-slate-300 hover:bg-[#2a2a36] hover:text-slate-100">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteSession} 
              className="bg-red-600 hover:bg-red-700 text-white shadow-[0_0_20px_-5px_rgba(220,38,38,0.5)] hover:shadow-[0_0_30px_-5px_rgba(220,38,38,0.7)]"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete Session
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
