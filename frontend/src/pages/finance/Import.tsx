import { useState, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, FileText, CheckCircle, AlertCircle, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface ImportResponse {
  inserted: number;
  skipped: number;
  total: number;
}

export default function Import() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (selected: File | null) => {
    if (selected && selected.type === "application/pdf") {
      setFile(selected);
      setResult(null);
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
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/finance/import", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }

      const data: ImportResponse = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col gap-6 max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-dark-primary)' }}>
          Import Transactions
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-dark-muted)' }}>
          Upload a bank statement PDF to import transactions
        </p>
      </div>

      {/* Drop Zone */}
      <Card
        className={cn("cursor-pointer transition-all duration-300 card-dark")}
        style={{
          borderColor: dragOver 
            ? 'rgba(54, 184, 200, 0.5)'
            : file
            ? 'rgba(90, 159, 110, 0.5)'
            : 'var(--border-dark)',
          boxShadow: dragOver
            ? '0 0 30px -10px rgba(54, 184, 200, 0.3)'
            : file
            ? '0 0 30px -10px rgba(90, 159, 110, 0.3)'
            : 'none'
        }}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <CardContent className="flex flex-col items-center justify-center gap-4 py-16">
          {file ? (
            <>
              <div 
                className="w-16 h-16 rounded-2xl flex items-center justify-center shadow-medium" 
                style={{ 
                  background: 'rgba(90, 159, 110, 0.2)', 
                  border: '1px solid rgba(90, 159, 110, 0.3)' 
                }}
              >
                <FileText className="w-8 h-8" style={{ color: 'var(--color-success)' }} />
              </div>
              <div className="text-center">
                <p className="font-semibold" style={{ color: 'var(--text-dark-primary)' }}>
                  {file.name}
                </p>
                <p className="text-sm mt-1" style={{ color: 'var(--text-dark-muted)' }}>
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
            </>
          ) : (
            <>
              <div 
                className={cn("w-16 h-16 rounded-2xl border flex items-center justify-center transition-all duration-300")}
                style={{
                  background: dragOver ? 'rgba(54, 184, 200, 0.2)' : 'var(--level-3)',
                  borderColor: dragOver ? 'rgba(54, 184, 200, 0.3)' : 'var(--border-dark)',
                  boxShadow: dragOver ? '0 0 20px -8px rgba(54, 184, 200, 0.3)' : 'none'
                }}
              >
                <Upload className="w-8 h-8" 
                        style={{ color: dragOver ? 'var(--finance-primary)' : 'var(--text-dark-muted)' }} />
              </div>
              <div className="text-center">
                <p className="font-medium" style={{ color: 'var(--text-dark-primary)' }}>
                  Drop PDF here or click to browse
                </p>
                <p className="text-sm mt-1" style={{ color: 'var(--text-dark-muted)' }}>
                  Supports Toss Bank CAD statements
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
      />

      {/* Actions */}
      <div className="flex items-center gap-4">
        <Button onClick={handleUpload} disabled={!file || loading}>
          {loading ? (
            <>
              <Sparkles className="w-4 h-4 animate-pulse" />
              Importing...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" />
              Import
            </>
          )}
        </Button>
        {file && !loading && (
          <Button
            variant="outline"
            onClick={() => {
              setFile(null);
              setResult(null);
              setError(null);
            }}
          >
            Clear
          </Button>
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

      {/* Result */}
      {result && (
        <Card 
          className="shadow-medium"
          style={{ 
            background: 'rgba(90, 159, 110, 0.1)', 
            border: '1px solid rgba(90, 159, 110, 0.3)' 
          }}
        >
          <CardContent className="py-6">
            <div className="flex items-center gap-3 mb-6">
              <div 
                className="w-10 h-10 rounded-xl flex items-center justify-center" 
                style={{ 
                  background: 'rgba(90, 159, 110, 0.2)', 
                  border: '1px solid rgba(90, 159, 110, 0.4)' 
                }}
              >
                <CheckCircle className="w-5 h-5" style={{ color: 'var(--color-success)' }} />
              </div>
              <span className="font-semibold text-lg" style={{ color: 'var(--color-success)' }}>
                Import complete
              </span>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 rounded-xl card-dark">
                <p className="text-3xl font-bold font-mono" style={{ color: 'var(--finance-primary)' }}>
                  {result.inserted}
                </p>
                <p className="text-xs mt-1 uppercase tracking-wider" style={{ color: 'var(--text-dark-muted)' }}>
                  Inserted
                </p>
              </div>
              <div className="p-4 rounded-xl card-dark">
                <p className="text-3xl font-bold font-mono" style={{ color: 'var(--text-dark-secondary)' }}>
                  {result.skipped}
                </p>
                <p className="text-xs mt-1 uppercase tracking-wider" style={{ color: 'var(--text-dark-muted)' }}>
                  Skipped
                </p>
              </div>
              <div className="p-4 rounded-xl card-dark">
                <p className="text-3xl font-bold font-mono" style={{ color: 'var(--text-dark-primary)' }}>
                  {result.total}
                </p>
                <p className="text-xs mt-1 uppercase tracking-wider" style={{ color: 'var(--text-dark-muted)' }}>
                  Total
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
