import { useState } from "react";
import { type PropositionNode } from "../../types/phase-space";

const TYPE_BADGE: Record<string, { label: string; color: string }> = {
  stance: { label: "stance", color: "var(--voku-type-stance)" },
  event: { label: "event", color: "var(--voku-type-event)" },
  intention: { label: "intent", color: "var(--voku-type-intention)" },
};

interface ActiveSummaryProps {
  nodes: PropositionNode[];
  relevanceMap: Map<string, number>;
  retrievalIds: string[];
}

export function ActiveSummary({ nodes, relevanceMap, retrievalIds }: ActiveSummaryProps) {
  const [expanded, setExpanded] = useState(false);

  const retrieved = nodes.filter((n) => retrievalIds.includes(n.id));
  const relevant = nodes
    .filter((n) => !retrievalIds.includes(n.id) && (relevanceMap.get(n.id) || 0) > 0.3)
    .sort((a, b) => (relevanceMap.get(b.id) || 0) - (relevanceMap.get(a.id) || 0))
    .slice(0, 10);

  const totalCount = retrieved.length + relevant.length;
  if (totalCount === 0) return null;

  return (
    <div style={{ position: "relative", zIndex: 10 }}>
      {/* Header — always in flow, thin bar */}
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          width: "100%",
          padding: "0.4rem 1rem",
          background: "var(--voku-phase-bg)",
          border: "none",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          cursor: "pointer",
          fontFamily: "var(--voku-font-mono)",
          fontSize: "0.72rem",
          color: "var(--voku-phase-label)",
          textAlign: "left",
        }}
      >
        <span style={{
          display: "inline-block",
          transform: expanded ? "rotate(90deg)" : "rotate(0deg)",
          transition: "transform 0.15s ease",
          fontSize: "0.6rem",
          color: "var(--voku-accent-gold-dim)",
        }}>
          ▶
        </span>
        {retrieved.length > 0 && (
          <span style={{ color: "var(--voku-accent-gold)", fontWeight: 600 }}>
            {retrieved.length} retrieved
          </span>
        )}
        {retrieved.length > 0 && relevant.length > 0 && (
          <span style={{ color: "var(--voku-border-default)" }}>·</span>
        )}
        {relevant.length > 0 && (
          <span style={{ color: "#8a8578" }}>
            {relevant.length} related
          </span>
        )}
        {!expanded && retrieved.length > 0 && (
          <span style={{
            color: "#8a8578",
            marginLeft: "auto",
            maxWidth: "50%",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}>
            {retrieved[0]?.label.slice(0, 60)}
          </span>
        )}
      </button>

      {/* Expanded table — overlays the phase space */}
      {expanded && (
        <div style={{
          position: "absolute",
          top: "100%",
          left: 0,
          right: 0,
          zIndex: 100,
          maxHeight: "45vh",
          overflowY: "auto",
          background: "#ece6db",
          borderBottom: "2px solid var(--voku-border-default)",
          boxShadow: "0 6px 24px rgba(44, 38, 32, 0.2)",
          padding: "0.25rem 0.75rem 0.5rem",
        }}>
          <table style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "0.75rem",
            lineHeight: 1.5,
          }}>
            <thead>
              <tr style={{
                borderBottom: "1px solid var(--voku-border-subtle)",
                color: "var(--voku-text-tertiary)",
                fontFamily: "var(--voku-font-mono)",
                fontSize: "0.65rem",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                position: "sticky",
                top: 0,
                background: "#ece6db",
              }}>
                <th style={{ textAlign: "left", padding: "0.3rem 0.5rem", fontWeight: 500 }}>proposition</th>
                <th style={{ textAlign: "center", padding: "0.3rem 0.5rem", fontWeight: 500, width: "60px" }}>type</th>
                <th style={{ textAlign: "center", padding: "0.3rem 0.5rem", fontWeight: 500, width: "45px" }}>conf</th>
                <th style={{ textAlign: "center", padding: "0.3rem 0.5rem", fontWeight: 500, width: "45px" }}>src</th>
              </tr>
            </thead>
            <tbody>
              {retrieved.map((node) => (
                <Row key={node.id} node={node} source="retrieved" />
              ))}
              {retrieved.length > 0 && relevant.length > 0 && (
                <tr>
                  <td colSpan={4} style={{ padding: "0.15rem 0", borderBottom: "1px dashed var(--voku-border-subtle)" }} />
                </tr>
              )}
              {relevant.map((node) => (
                <Row key={node.id} node={node} source="related" relevance={relevanceMap.get(node.id)} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Row({ node, source, relevance }: {
  node: { id: string; label: string; fullText: string; nodeType: string; confidence: number; sourceFile: string };
  source: "retrieved" | "related";
  relevance?: number;
}) {
  const [hovered, setHovered] = useState(false);
  const badge = TYPE_BADGE[node.nodeType] || { label: node.nodeType, color: "var(--voku-text-muted)" };

  return (
    <tr
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        borderLeft: source === "retrieved" ? "2px solid var(--voku-accent-gold)" : "2px solid transparent",
        background: hovered ? "var(--voku-bg-hover)" : "transparent",
        transition: "background 0.1s ease",
        cursor: "default",
      }}
    >
      <td style={{
        padding: "0.3rem 0.5rem",
        color: "var(--voku-text-primary)",
        maxWidth: "0",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: hovered ? "normal" : "nowrap",
      }}
        title={node.fullText}
      >
        {hovered ? node.fullText : node.label}
      </td>
      <td style={{ textAlign: "center", padding: "0.3rem 0.5rem" }}>
        <span style={{
          display: "inline-block",
          padding: "1px 6px",
          borderRadius: "3px",
          fontSize: "0.62rem",
          fontFamily: "var(--voku-font-mono)",
          color: badge.color,
          background: `${badge.color}12`,
          border: `1px solid ${badge.color}25`,
        }}>
          {badge.label}
        </span>
      </td>
      <td style={{
        textAlign: "center",
        padding: "0.3rem 0.5rem",
        fontFamily: "var(--voku-font-mono)",
        fontSize: "0.68rem",
        color: "var(--voku-text-tertiary)",
      }}>
        {node.confidence.toFixed(1)}
      </td>
      <td style={{
        textAlign: "center",
        padding: "0.3rem 0.5rem",
        fontFamily: "var(--voku-font-mono)",
        fontSize: "0.62rem",
        color: "var(--voku-text-muted)",
      }}>
        {source === "retrieved" ? "⬡" : `${((relevance || 0) * 100).toFixed(0)}%`}
      </td>
    </tr>
  );
}
