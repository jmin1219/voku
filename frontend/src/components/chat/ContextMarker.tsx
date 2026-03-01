import { useState, useRef, useEffect } from "react";

const API_BASE = "http://localhost:8000/api";

interface TraceDetail {
  id: string;
  content: string;
  source: string;
  timestamp: string;
  conversationId: string | null;
}

// Module-level cache — persists across re-renders
const traceCache = new Map<string, TraceDetail>();

/**
 * ContextMarker — Interactive inline citation [N] that reveals trace context.
 *
 * Perplexity-style: small numbered indicator in the text.
 * Hover: trace excerpt + relative timestamp in a tooltip.
 * Click: (future) expand to full trace with connections.
 *
 * Progressive disclosure: marker → excerpt → full context.
 * Research: 1 citation = 5 for trust (AAAI 2025). Presence is the signal.
 */
export function ContextMarker({
  index,
  traceId,
}: {
  index: number;
  traceId: string | undefined;
}) {
  const [hovered, setHovered] = useState(false);
  const [trace, setTrace] = useState<TraceDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState<"above" | "below">("above");
  const markerRef = useRef<HTMLSpanElement>(null);

  // Fetch trace on first hover
  useEffect(() => {
    if (!hovered || !traceId || trace || loading) return;

    // Check cache first
    const cached = traceCache.get(traceId);
    if (cached) {
      setTrace(cached);
      return;
    }

    setLoading(true);
    fetch(`${API_BASE}/traces/${traceId}`)
      .then((res) => res.json())
      .then((data) => {
        const detail: TraceDetail = {
          id: data.id,
          content: data.content,
          source: data.source,
          timestamp: data.timestamp,
          conversationId: data.conversationId,
        };
        traceCache.set(traceId, detail);
        setTrace(detail);
      })
      .catch((err) => console.warn("Failed to fetch trace:", err))
      .finally(() => setLoading(false));
  }, [hovered, traceId, trace, loading]);

  // Determine tooltip position based on viewport
  useEffect(() => {
    if (hovered && markerRef.current) {
      const rect = markerRef.current.getBoundingClientRect();
      setTooltipPosition(rect.top < 200 ? "below" : "above");
    }
  }, [hovered]);

  return (
    <span
      ref={markerRef}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ position: "relative", display: "inline" }}
    >
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: "1.1em",
          height: "1.1em",
          fontSize: "0.7em",
          fontFamily: "var(--voku-font-mono)",
          fontWeight: 600,
          color: hovered ? "var(--voku-bg-base)" : "var(--voku-accent-gold)",
          background: hovered ? "var(--voku-accent-gold)" : "var(--voku-accent-gold)18",
          border: `1px solid var(--voku-accent-gold)40`,
          borderRadius: "3px",
          cursor: "pointer",
          transition: "all 0.15s ease",
          verticalAlign: "super",
          lineHeight: 1,
          marginLeft: "1px",
          marginRight: "1px",
        }}
      >
        {index}
      </span>

      {/* Tooltip */}
      {hovered && (
        <span
          style={{
            position: "absolute",
            [tooltipPosition === "above" ? "bottom" : "top"]: "calc(100% + 6px)",
            left: "50%",
            transform: "translateX(-50%)",
            width: "min(320px, 80vw)",
            padding: "8px 10px",
            background: "var(--voku-bg-raised)",
            border: "1px solid var(--voku-border-default)",
            borderLeft: "3px solid var(--voku-accent-gold)",
            borderRadius: "var(--voku-radius-md)",
            boxShadow: "0 4px 16px rgba(44, 38, 32, 0.12)",
            zIndex: 1000,
            fontSize: "var(--voku-text-xs)",
            lineHeight: "var(--voku-leading-normal)",
            color: "var(--voku-text-secondary)",
            fontFamily: "var(--voku-font-body)",
            fontWeight: 400,
            textAlign: "left",
            whiteSpace: "normal",
            pointerEvents: "none",
          }}
        >
          {loading && (
            <span style={{ color: "var(--voku-text-muted)", fontStyle: "italic" }}>
              loading...
            </span>
          )}
          {trace && (
            <>
              <span
                style={{
                  display: "block",
                  fontSize: "0.65rem",
                  fontFamily: "var(--voku-font-mono)",
                  color: "var(--voku-accent-gold)",
                  marginBottom: "4px",
                  fontWeight: 500,
                }}
              >
                {trace.source === "user" ? "you" : trace.source}
                {" · "}
                {formatRelativeTime(trace.timestamp)}
              </span>
              <span style={{ display: "block" }}>
                {truncateExcerpt(trace.content, 200)}
              </span>
            </>
          )}
          {!loading && !trace && !traceId && (
            <span style={{ color: "var(--voku-text-muted)", fontStyle: "italic" }}>
              trace not found
            </span>
          )}
        </span>
      )}
    </span>
  );
}

function formatRelativeTime(timestamp: string): string {
  try {
    const created = new Date(timestamp);
    const now = new Date();
    const seconds = (now.getTime() - created.getTime()) / 1000;

    if (seconds < 60) return "just now";
    if (seconds < 3600) {
      const m = Math.floor(seconds / 60);
      return `${m} min ago`;
    }
    if (seconds < 86400) {
      const h = Math.floor(seconds / 3600);
      return `${h}h ago`;
    }
    if (seconds < 604800) {
      const d = Math.floor(seconds / 86400);
      return `${d}d ago`;
    }
    if (seconds < 2592000) {
      const w = Math.floor(seconds / 604800);
      return `${w}w ago`;
    }
    const mo = Math.floor(seconds / 2592000);
    return `${mo}mo ago`;
  } catch {
    return "";
  }
}

function truncateExcerpt(text: string, maxChars: number): string {
  if (text.length <= maxChars) return text;
  const truncated = text.slice(0, maxChars);
  const lastSpace = truncated.lastIndexOf(" ");
  return (lastSpace > maxChars * 0.5 ? truncated.slice(0, lastSpace) : truncated) + "…";
}
