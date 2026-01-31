import { useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Image, CheckCircle, AlertCircle, Zap, Sparkles, Upload, Save } from "lucide-react";
import { cn } from "@/lib/utils";
import ReviewUnknownsModal from "@/components/ReviewUnknownsModal";

interface ParsedSession {
  workout_type: string;
  variables: Record<string, { value: string; unit?: string }>;
}

interface LogResponse {
  filename: string;
  parsed: ParsedSession;
  id: string | null;
  logged_to: string | null;
  provider: string;
  unknown_variables: string[];
  stats: Record<string, number>;
}

interface UnknownVariable {
  name: string;
  value: string;
  unit?: string;
}

interface ReviewDecision {
  action: "add_new" | "map_existing" | "skip";
  canonical?: string;
  display?: string;
  unit?: string;
}

export default function Log() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [extractedData, setExtractedData] = useState<LogResponse | null>(null);
  const [savedResult, setSavedResult] = useState<LogResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (selected: File | null) => {
    if (selected && selected.type.startsWith("image/")) {
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
      setExtractedData(null);
      setSavedResult(null);
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    handleFileSelect(dropped);
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("image", file);

    try {
      const response = await fetch(
        "http://localhost:8000/log/training/session",
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }

      const data: LogResponse = await response.json();
      setExtractedData(data);
      
      // If unknowns exist, show review modal
      if (data.unknown_variables && data.unknown_variables.length > 0) {
        setShowReviewModal(true);
      } else {
        // No unknowns - already saved by backend
        setSavedResult(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  const handleReviewComplete = async (decisions: Map<string, ReviewDecision>) => {
    if (!extractedData) return;
    
    setSaving(true);
    setError(null);
    
    try {
      // Process each decision
      for (const [varName, decision] of decisions.entries()) {
        if (decision.action === "add_new") {
          // Create new variable
          await fetch("http://localhost:8000/registry/variables", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              canonical: decision.canonical,
              display: decision.display,
              unit: decision.unit,
              aliases: [varName],
            }),
          });
        } else if (decision.action === "map_existing") {
          // Add alias to existing variable
          await fetch(
            `http://localhost:8000/registry/variables/${decision.canonical}/aliases`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ alias: varName }),
            }
          );
        }
        // "skip" action = do nothing
      }
      
      // Now save the session (backend auto-saves, so we mark as complete)
      setSavedResult(extractedData);
      setShowReviewModal(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save decisions");
    } finally {
      setSaving(false);
    }
  };

  const handleReviewCancel = () => {
    setShowReviewModal(false);
    setExtractedData(null);
  };

  const handleClear = () => {
    setFile(null);
    setPreview(null);
    setExtractedData(null);
    setSavedResult(null);
    setError(null);
  };

  // Prepare unknowns for modal
  const unknowns: UnknownVariable[] = extractedData
    ? extractedData.unknown_variables.map((name) => ({
        name,
        value: extractedData.parsed.variables[name]?.value || "",
        unit: extractedData.parsed.variables[name]?.unit,
      }))
    : [];

  const result = savedResult || extractedData;

  return (
    <div className="h-full flex flex-col gap-6">
      {/* Review Modal */}
      {showReviewModal && (
        <ReviewUnknownsModal
          unknowns={unknowns}
          onComplete={handleReviewComplete}
          onCancel={handleReviewCancel}
        />
      )}

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-dark-primary)' }}>
          Log Workout
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-dark-muted)' }}>
          Upload a screenshot from Apple Fitness to extract workout data
        </p>
      </div>

      {/* Main Content */}
      <div
        className={cn(
          "flex-1 min-h-0 grid gap-6",
          result ? "grid-cols-2" : "grid-cols-1 max-w-2xl"
        )}
      >
        {/* Drop Zone / Preview */}
        <Card
          className={cn(
            "cursor-pointer transition-all duration-300 overflow-hidden card-dark",
            !result && "max-h-80"
          )}
          style={{
            borderColor: dragOver 
              ? 'rgba(54, 184, 200, 0.5)'
              : file && !result
              ? 'rgba(230, 119, 58, 0.5)'
              : 'var(--border-dark)',
            boxShadow: dragOver
              ? '0 0 30px -10px rgba(54, 184, 200, 0.3)'
              : file && !result
              ? '0 0 30px -10px rgba(230, 119, 58, 0.3)'
              : 'none'
          }}
          onClick={() => !result && inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <CardContent className="h-full flex flex-col items-center justify-center gap-4 p-6">
            {preview ? (
              <img
                src={preview}
                alt="Preview"
                className="max-h-full max-w-full object-contain rounded-lg"
              />
            ) : (
              <>
                <div className={cn(
                  "w-16 h-16 rounded-2xl border flex items-center justify-center transition-all duration-300"
                )}
                style={{
                  background: dragOver ? 'rgba(54, 184, 200, 0.2)' : 'var(--level-3)',
                  borderColor: dragOver ? 'rgba(54, 184, 200, 0.3)' : 'var(--border-dark)'
                }}>
                  <Image className="w-8 h-8" 
                         style={{ color: dragOver ? 'var(--finance-primary)' : 'var(--text-dark-muted)' }} />
                </div>
                <div className="text-center">
                  <p className="font-medium" style={{ color: 'var(--text-dark-primary)' }}>
                    Drop image here or click to browse
                  </p>
                  <p className="text-sm mt-1" style={{ color: 'var(--text-dark-muted)' }}>
                    PNG, JPG from Apple Fitness
                  </p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
        />

        {/* Extracted Data - Light surface for readability */}
        {result && (
          <Card className="flex flex-col min-h-0 card-light shadow-medium">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <div 
                    className="w-8 h-8 rounded-lg flex items-center justify-center" 
                    style={{ 
                      background: savedResult 
                        ? 'rgba(90, 159, 110, 0.15)' 
                        : 'rgba(212, 161, 52, 0.15)', 
                      border: savedResult 
                        ? '1px solid rgba(90, 159, 110, 0.3)'
                        : '1px solid rgba(212, 161, 52, 0.3)'
                    }}
                  >
                    {savedResult ? (
                      <CheckCircle className="w-4 h-4" style={{ color: 'var(--color-success)' }} />
                    ) : (
                      <AlertCircle className="w-4 h-4" style={{ color: 'var(--color-warning)' }} />
                    )}
                  </div>
                  <span style={{ color: 'var(--text-light-primary)' }}>
                    {result.parsed.workout_type}
                  </span>
                </CardTitle>
                <Badge variant="secondary" className="font-mono text-xs badge-warning-light flex items-center gap-1">
                  <Zap className="w-3 h-3" />
                  {result.provider}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto p-0">
              <Table>
                <TableHeader>
                  <TableRow style={{ borderColor: 'var(--border-light)' }}>
                    <TableHead style={{ color: 'var(--text-light-secondary)' }}>Metric</TableHead>
                    <TableHead className="text-right" style={{ color: 'var(--text-light-secondary)' }}>Value</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(result.parsed.variables).map(
                    ([name, data]) => (
                      <TableRow 
                        key={name}
                        className="hover:bg-[var(--level-6)]"
                        style={{ borderColor: 'var(--border-light)' }}
                      >
                        <TableCell style={{ color: 'var(--text-light-secondary)' }}>
                          {name}
                        </TableCell>
                        <TableCell className="text-right font-mono" style={{ color: 'var(--fitness-primary)' }}>
                          {data.value}
                          {data.unit && (
                            <span className="ml-1" style={{ color: 'var(--text-light-muted)' }}>
                              {data.unit}
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    )
                  )}
                </TableBody>
              </Table>

              {extractedData && !savedResult && extractedData.unknown_variables.length > 0 && (
                <div 
                  className="m-4 p-3 rounded-lg" 
                  style={{ 
                    background: 'rgba(212, 161, 52, 0.1)', 
                    border: '1px solid rgba(212, 161, 52, 0.3)' 
                  }}
                >
                  <p className="text-sm font-medium" style={{ color: 'var(--color-warning)' }}>
                    {extractedData.unknown_variables.length} unknown variable{extractedData.unknown_variables.length > 1 ? 's' : ''} detected
                  </p>
                  <p className="text-sm mt-1" style={{ color: 'var(--text-light-muted)' }}>
                    Click "Review & Save" to teach Voku these variables
                  </p>
                </div>
              )}

              {savedResult && (
                <div 
                  className="m-4 p-3 rounded-lg" 
                  style={{ 
                    background: 'rgba(90, 159, 110, 0.1)', 
                    border: '1px solid rgba(90, 159, 110, 0.3)' 
                  }}
                >
                  <p className="text-sm font-medium" style={{ color: 'var(--color-success)' }}>
                    Session saved successfully!
                  </p>
                  <p className="text-sm mt-1 font-mono" style={{ color: 'var(--text-light-muted)' }}>
                    {savedResult.id}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Error */}
      {error && (
        <Card 
          className="shadow-medium"
          style={{ 
            background: 'rgba(200, 85, 78, 0.1)', 
            border: '1px solid rgba(200, 85, 78, 0.3)' 
          }}
        >
          <CardContent className="flex items-center gap-3 py-4">
            <AlertCircle className="w-5 h-5" style={{ color: 'var(--color-error)' }} />
            <span style={{ color: 'var(--color-error)' }}>{error}</span>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      {file && !savedResult && (
        <div className="flex items-center gap-4">
          {!extractedData ? (
            <Button onClick={handleUpload} disabled={loading}>
              {loading ? (
                <>
                  <Sparkles className="w-4 h-4 animate-pulse" />
                  Extracting...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Extract Data
                </>
              )}
            </Button>
          ) : (
            <Button onClick={() => setShowReviewModal(true)} disabled={saving}>
              {saving ? (
                <>
                  <Sparkles className="w-4 h-4 animate-pulse" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Review & Save
                </>
              )}
            </Button>
          )}
          <Button variant="outline" onClick={handleClear}>
            Clear
          </Button>
        </div>
      )}

      {savedResult && (
        <div className="flex items-center gap-4">
          <Button onClick={handleClear}>
            Log Another Workout
          </Button>
        </div>
      )}
    </div>
  );
}
