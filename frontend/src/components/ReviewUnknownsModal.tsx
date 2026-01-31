import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, Check, X, GitMerge, Plus } from "lucide-react";

interface UnknownVariable {
  name: string;
  value: string;
  unit?: string;
}

interface ExistingVariable {
  canonical: string;
  display: string;
  unit: string;
  aliases: string[];
  count: number;
}

interface ReviewDecision {
  action: "add_new" | "map_existing" | "skip";
  canonical?: string;
  display?: string;
  unit?: string;
}

interface ReviewUnknownsModalProps {
  unknowns: UnknownVariable[];
  onComplete: (decisions: Map<string, ReviewDecision>) => void;
  onCancel: () => void;
}

export default function ReviewUnknownsModal({
  unknowns,
  onComplete,
  onCancel,
}: ReviewUnknownsModalProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [decisions, setDecisions] = useState<Map<string, ReviewDecision>>(
    new Map()
  );
  const [action, setAction] = useState<"add_new" | "map_existing" | "skip" | null>(
    null
  );
  
  // Form state for "add new"
  const [displayName, setDisplayName] = useState("");
  const [unit, setUnit] = useState("");
  
  // Form state for "map existing"
  const [selectedCanonical, setSelectedCanonical] = useState("");
  const [existingVariables, setExistingVariables] = useState<ExistingVariable[]>([]);
  const [loadingVariables, setLoadingVariables] = useState(false);
  
  const currentUnknown = unknowns[currentIndex];
  const isLastUnknown = currentIndex === unknowns.length - 1;
  const progress = `${currentIndex + 1} / ${unknowns.length}`;

  // Load existing variables when "map existing" is selected
  const loadExistingVariables = async () => {
    setLoadingVariables(true);
    try {
      const response = await fetch("http://localhost:8000/registry/variables");
      const data = await response.json();
      
      // Convert variables object to array
      const vars: ExistingVariable[] = Object.entries(data.variables).map(
        ([canonical, info]: [string, any]) => ({
          canonical,
          display: info.display,
          unit: info.unit,
          aliases: info.aliases || [],
          count: info.count || 0,
        })
      );
      
      setExistingVariables(vars);
    } catch (error) {
      console.error("Failed to load existing variables:", error);
    } finally {
      setLoadingVariables(false);
    }
  };

  const handleActionSelect = (selectedAction: "add_new" | "map_existing" | "skip") => {
    setAction(selectedAction);
    
    // Reset form state
    setDisplayName(currentUnknown.name);
    setUnit(currentUnknown.unit || "");
    setSelectedCanonical("");
    
    // Load variables if mapping
    if (selectedAction === "map_existing") {
      loadExistingVariables();
    }
  };

  const handleNext = () => {
    if (!action) return;
    
    // Save decision
    const decision: ReviewDecision = { action };
    
    if (action === "add_new") {
      const canonical = displayName.toLowerCase().replace(/\s+/g, "_");
      decision.canonical = canonical;
      decision.display = displayName;
      decision.unit = unit;
    } else if (action === "map_existing") {
      decision.canonical = selectedCanonical;
    }
    
    const newDecisions = new Map(decisions);
    newDecisions.set(currentUnknown.name, decision);
    setDecisions(newDecisions);
    
    // Move to next or complete
    if (isLastUnknown) {
      onComplete(newDecisions);
    } else {
      setCurrentIndex(currentIndex + 1);
      setAction(null);
    }
  };

  const handleBack = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setAction(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <Card 
        className="w-full max-w-2xl max-h-[90vh] flex flex-col card-light shadow-high"
      >
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2" style={{ color: 'var(--text-light-primary)' }}>
                <div 
                  className="w-8 h-8 rounded-lg flex items-center justify-center" 
                  style={{ 
                    background: 'rgba(212, 161, 52, 0.15)', 
                    border: '1px solid rgba(212, 161, 52, 0.3)' 
                  }}
                >
                  <AlertCircle className="w-4 h-4" style={{ color: 'var(--color-warning)' }} />
                </div>
                Review Unknown Variables
              </CardTitle>
              <CardDescription style={{ color: 'var(--text-light-secondary)' }}>
                Help Voku learn new variables for better tracking
              </CardDescription>
            </div>
            <Badge variant="secondary" className="badge-warning-light">
              {progress}
            </Badge>
          </div>
        </CardHeader>

        <CardContent className="flex-1 overflow-auto space-y-6">
          {/* Current Unknown */}
          <div 
            className="p-4 rounded-lg" 
            style={{ 
              background: 'rgba(212, 161, 52, 0.08)', 
              border: '1px solid rgba(212, 161, 52, 0.2)' 
            }}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium" style={{ color: 'var(--text-light-secondary)' }}>
                Unknown Variable
              </span>
              <Badge variant="secondary" className="badge-warning-light font-mono text-xs">
                {currentUnknown.name}
              </Badge>
            </div>
            <div className="text-2xl font-bold font-mono" style={{ color: 'var(--fitness-primary)' }}>
              {currentUnknown.value}
              {currentUnknown.unit && (
                <span className="ml-2 text-base" style={{ color: 'var(--text-light-muted)' }}>
                  {currentUnknown.unit}
                </span>
              )}
            </div>
          </div>

          {/* Action Selection */}
          {!action && (
            <div className="space-y-3">
              <Label style={{ color: 'var(--text-light-primary)' }}>
                What should Voku do with this variable?
              </Label>
              
              <button
                onClick={() => handleActionSelect("add_new")}
                className="w-full p-4 rounded-lg border-2 transition-all hover:scale-[1.02] text-left"
                style={{
                  borderColor: 'rgba(90, 159, 110, 0.3)',
                  background: 'rgba(90, 159, 110, 0.05)',
                }}
              >
                <div className="flex items-start gap-3">
                  <Plus className="w-5 h-5 mt-0.5" style={{ color: 'var(--color-success)' }} />
                  <div>
                    <div className="font-medium" style={{ color: 'var(--color-success)' }}>
                      Add as New Variable
                    </div>
                    <div className="text-sm" style={{ color: 'var(--text-light-muted)' }}>
                      Create a new canonical variable in the registry
                    </div>
                  </div>
                </div>
              </button>

              <button
                onClick={() => handleActionSelect("map_existing")}
                className="w-full p-4 rounded-lg border-2 transition-all hover:scale-[1.02] text-left"
                style={{
                  borderColor: 'rgba(54, 184, 200, 0.3)',
                  background: 'rgba(54, 184, 200, 0.05)',
                }}
              >
                <div className="flex items-start gap-3">
                  <GitMerge className="w-5 h-5 mt-0.5" style={{ color: 'var(--finance-primary)' }} />
                  <div>
                    <div className="font-medium" style={{ color: 'var(--finance-primary)' }}>
                      Map to Existing Variable
                    </div>
                    <div className="text-sm" style={{ color: 'var(--text-light-muted)' }}>
                      Link this to an existing canonical variable as an alias
                    </div>
                  </div>
                </div>
              </button>

              <button
                onClick={() => handleActionSelect("skip")}
                className="w-full p-4 rounded-lg border-2 transition-all hover:scale-[1.02] text-left"
                style={{
                  borderColor: 'var(--border-light)',
                  background: 'var(--level-6)',
                }}
              >
                <div className="flex items-start gap-3">
                  <X className="w-5 h-5 mt-0.5" style={{ color: 'var(--text-light-muted)' }} />
                  <div>
                    <div className="font-medium" style={{ color: 'var(--text-light-secondary)' }}>
                      Skip for Now
                    </div>
                    <div className="text-sm" style={{ color: 'var(--text-light-muted)' }}>
                      Don't track this variable (won't be saved)
                    </div>
                  </div>
                </div>
              </button>
            </div>
          )}

          {/* Add New Form */}
          {action === "add_new" && (
            <div className="space-y-4">
              <div>
                <Label htmlFor="display" style={{ color: 'var(--text-light-primary)' }}>
                  Display Name
                </Label>
                <Input
                  id="display"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="e.g., Average Heart Rate"
                  className="mt-1"
                />
                <p className="text-xs mt-1" style={{ color: 'var(--text-light-muted)' }}>
                  Canonical: {displayName.toLowerCase().replace(/\s+/g, "_")}
                </p>
              </div>
              
              <div>
                <Label htmlFor="unit" style={{ color: 'var(--text-light-primary)' }}>
                  Unit
                </Label>
                <Input
                  id="unit"
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  placeholder="e.g., bpm, km, watts"
                  className="mt-1"
                />
              </div>
            </div>
          )}

          {/* Map Existing Form */}
          {action === "map_existing" && (
            <div className="space-y-3">
              <Label style={{ color: 'var(--text-light-primary)' }}>
                Select Existing Variable
              </Label>
              
              {loadingVariables ? (
                <div className="text-center py-8" style={{ color: 'var(--text-light-muted)' }}>
                  Loading variables...
                </div>
              ) : existingVariables.length === 0 ? (
                <div className="text-center py-8" style={{ color: 'var(--text-light-muted)' }}>
                  No existing variables found. Consider adding as new instead.
                </div>
              ) : (
                <div className="space-y-2 max-h-64 overflow-auto">
                  {existingVariables.map((variable) => (
                    <button
                      key={variable.canonical}
                      onClick={() => setSelectedCanonical(variable.canonical)}
                      className="w-full p-3 rounded-lg border text-left transition-all"
                      style={{
                        borderColor:
                          selectedCanonical === variable.canonical
                            ? 'var(--finance-primary)'
                            : 'var(--border-light)',
                        background:
                          selectedCanonical === variable.canonical
                            ? 'rgba(54, 184, 200, 0.1)'
                            : 'transparent',
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium" style={{ color: 'var(--text-light-primary)' }}>
                            {variable.display}
                          </div>
                          <div className="text-sm font-mono" style={{ color: 'var(--text-light-muted)' }}>
                            {variable.canonical}
                          </div>
                        </div>
                        <Badge variant="secondary" className="badge-finance-light text-xs">
                          {variable.unit}
                        </Badge>
                      </div>
                      {variable.aliases.length > 0 && (
                        <div className="text-xs mt-1" style={{ color: 'var(--text-light-muted)' }}>
                          Aliases: {variable.aliases.join(", ")}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Skip Confirmation */}
          {action === "skip" && (
            <div 
              className="p-4 rounded-lg" 
              style={{ 
                background: 'rgba(154, 146, 134, 0.08)', 
                border: '1px solid rgba(154, 146, 134, 0.2)' 
              }}
            >
              <p style={{ color: 'var(--text-light-secondary)' }}>
                This variable will not be saved. You can always add it later from the settings.
              </p>
            </div>
          )}
        </CardContent>

        <CardFooter className="flex justify-between pt-4 border-t" style={{ borderColor: 'var(--border-light)' }}>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            {currentIndex > 0 && (
              <Button variant="outline" onClick={handleBack}>
                Back
              </Button>
            )}
          </div>
          
          <Button
            onClick={handleNext}
            disabled={
              !action ||
              (action === "add_new" && (!displayName || !unit)) ||
              (action === "map_existing" && !selectedCanonical)
            }
          >
            <Check className="w-4 h-4 mr-2" />
            {isLastUnknown ? "Complete" : "Next"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
