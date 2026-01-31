import { useState, useEffect } from "react";
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
import { Plus, Trash2, Save, X, Calendar, Clock } from "lucide-react";

interface Variable {
  key: string;
  value: string;
  unit: string;
}

interface Session {
  id: string;
  created_at: string;
  workout_date?: string;
  workout_time?: string;
  workout_type: string;
  variables: Record<string, { value: string; unit: string }>;
  updated_at?: string;
}

interface SessionFormProps {
  mode: "create" | "edit";
  initialData?: Session;
  onSave: (data: SessionPayload) => void;
  onCancel: () => void;
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
}

export default function SessionForm({
  mode,
  initialData,
  onSave,
  onCancel,
}: SessionFormProps) {
  // Get today's date and current time as defaults
  const now = new Date();
  const todayDate = now.toISOString().split('T')[0]; // YYYY-MM-DD
  const currentTime = now.toTimeString().slice(0, 5); // HH:MM

  const [workoutType, setWorkoutType] = useState(
    initialData?.workout_type || ""
  );
  
  const [workoutDate, setWorkoutDate] = useState(
    initialData?.workout_date || todayDate
  );
  
  const [workoutTime, setWorkoutTime] = useState(
    initialData?.workout_time || currentTime
  );

  const initialVariables: Variable[] = initialData?.variables
    ? Object.entries(initialData.variables).map(([key, { value, unit }]) => ({
        key,
        value: String(value || ''), // Ensure value is always a string
        unit: unit || '',
      }))
    : [{ key: "", value: "", unit: "" }];

  const [variables, setVariables] = useState<Variable[]>(initialVariables);
  const [registry, setRegistry] = useState<Record<string, RegistryVariable>>({});
  const [suggestions, setSuggestions] = useState<string[][]>(
    variables.map(() => [])
  );

  useEffect(() => {
    fetch("http://localhost:8000/registry/variables")
      .then((res) => res.json())
      .then((data) => {
        setRegistry(data.variables || {});
      })
      .catch((err) => console.error("Failed to load registry:", err));
  }, []);

  const handleAddVariable = () => {
    setVariables([...variables, { key: "", value: "", unit: "" }]);
    setSuggestions([...suggestions, []]);
  };

  const handleRemoveVariable = (index: number) => {
    setVariables(variables.filter((_, i) => i !== index));
    setSuggestions(suggestions.filter((_, i) => i !== index));
  };

  const handleVariableChange = (
    index: number,
    field: keyof Variable,
    value: string
  ) => {
    const updated = [...variables];
    updated[index][field] = value;

    if (field === "key") {
      const newSuggestions = [...suggestions];
      if (value.trim()) {
        const matches = Object.entries(registry)
          .filter(([canonical, info]) => {
            const searchTerm = value.toLowerCase();
            return (
              canonical.toLowerCase().includes(searchTerm) ||
              info.display.toLowerCase().includes(searchTerm) ||
              info.aliases.some((alias) =>
                alias.toLowerCase().includes(searchTerm)
              )
            );
          })
          .map(([canonical]) => canonical)
          .slice(0, 5);

        newSuggestions[index] = matches;
      } else {
        newSuggestions[index] = [];
      }
      setSuggestions(newSuggestions);
    }

    setVariables(updated);
  };

  const handleSelectSuggestion = (index: number, canonical: string) => {
    const updated = [...variables];
    updated[index].key = canonical;
    
    if (registry[canonical]) {
      updated[index].unit = registry[canonical].unit;
    }

    setVariables(updated);
    
    const newSuggestions = [...suggestions];
    newSuggestions[index] = [];
    setSuggestions(newSuggestions);
  };

  const handleSubmit = () => {
    const variablesObj: Record<string, { value: string; unit: string }> = {};
    
    variables.forEach((v) => {
      if (v.key.trim()) {
        variablesObj[v.key] = {
          value: v.value,
          unit: v.unit,
        };
      }
    });

    const payload: SessionPayload = {
      workout_type: workoutType,
      variables: variablesObj,
      workout_date: workoutDate,
      workout_time: workoutTime,
    };

    onSave(payload);
  };

  const isValid = () => {
    if (!workoutType.trim()) return false;
    const hasValidVariable = variables.some(
      (v) => {
        const key = String(v.key || '').trim();
        const value = String(v.value || '').trim();
        return key && value;
      }
    );
    return hasValidVariable;
  };

  const isInRegistry = (key: string) => {
    return key in registry;
  };

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle>
          {mode === "create" ? "Log New Session" : "Edit Session"}
        </CardTitle>
        <CardDescription>
          {mode === "create"
            ? "Manually enter your training session details"
            : "Update session details"}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Date and Time Row */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="workout_date" className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Workout Date
            </Label>
            <Input
              id="workout_date"
              type="date"
              value={workoutDate}
              onChange={(e) => setWorkoutDate(e.target.value)}
              className="text-base"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="workout_time" className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Start Time
            </Label>
            <Input
              id="workout_time"
              type="time"
              value={workoutTime}
              onChange={(e) => setWorkoutTime(e.target.value)}
              className="text-base"
            />
          </div>
        </div>

        {/* Workout Type */}
        <div className="space-y-2">
          <Label htmlFor="workout_type">Workout Type</Label>
          <Input
            id="workout_type"
            placeholder="e.g., Upper Body, Zone 2 Row, S&S"
            value={workoutType}
            onChange={(e) => setWorkoutType(e.target.value)}
            className="text-base"
          />
        </div>

        {/* Variables Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label>Metrics</Label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddVariable}
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Metric
            </Button>
          </div>

          {/* Variable Rows */}
          <div className="space-y-3">
            {variables.map((variable, index) => (
              <div key={index} className="space-y-2">
                <div className="flex gap-2 items-start">
                  {/* Metric Name with Autocomplete */}
                  <div className="flex-1 relative">
                    <Input
                      placeholder="Metric name (e.g., duration)"
                      value={variable.key}
                      onChange={(e) =>
                        handleVariableChange(index, "key", e.target.value)
                      }
                      className={
                        variable.key && !isInRegistry(variable.key)
                          ? "border-yellow-500/50 bg-yellow-500/5"
                          : ""
                      }
                    />
                    {/* Autocomplete Suggestions */}
                    {suggestions[index] && suggestions[index].length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-[#1a1a24] border border-[#2a2a3a] rounded-lg shadow-lg overflow-hidden">
                        {suggestions[index].map((canonical) => (
                          <button
                            key={canonical}
                            type="button"
                            onClick={() =>
                              handleSelectSuggestion(index, canonical)
                            }
                            className="w-full px-3 py-2 text-left text-sm hover:bg-[#22222e] transition-colors flex items-center justify-between"
                          >
                            <span className="text-slate-200">
                              {registry[canonical]?.display || canonical}
                            </span>
                            <span className="text-xs text-slate-500">
                              {registry[canonical]?.unit}
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  {/* Value */}
                  <div className="flex-1">
                    <Input
                      placeholder="Value (e.g., 45)"
                      value={variable.value}
                      onChange={(e) =>
                        handleVariableChange(index, "value", e.target.value)
                      }
                      type="number"
                      step="any"
                    />
                  </div>
                  
                  {/* Unit */}
                  <div className="w-28">
                    <Input
                      placeholder="Unit"
                      value={variable.unit}
                      onChange={(e) =>
                        handleVariableChange(index, "unit", e.target.value)
                      }
                    />
                  </div>
                  
                  {/* Delete Button */}
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemoveVariable(index)}
                    disabled={variables.length === 1}
                    className="text-slate-500 hover:text-red-400 hover:bg-red-500/10"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                
                {/* Warning for unknown metrics */}
                {variable.key && !isInRegistry(variable.key) && (
                  <p className="text-xs text-yellow-500/70 ml-1">
                    New metric - will be added to registry after save
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      </CardContent>

      <CardFooter className="flex justify-end gap-2">
        <Button variant="outline" onClick={onCancel}>
          <X className="h-4 w-4 mr-1" />
          Cancel
        </Button>
        <Button onClick={handleSubmit} disabled={!isValid()}>
          <Save className="h-4 w-4 mr-1" />
          {mode === "create" ? "Create Session" : "Save Changes"}
        </Button>
      </CardFooter>
    </Card>
  );
}
