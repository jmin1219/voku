import { NODES, TYPE_COLORS } from "../../types/phase-space";

export function ActiveSummary({ relevanceMap }: { relevanceMap: Map<string, number> }) {
  const active = NODES
    .filter((n) => (relevanceMap.get(n.id) || 0) > 0.3)
    .sort((a, b) => (relevanceMap.get(b.id) || 0) - (relevanceMap.get(a.id) || 0));
  if (active.length === 0) return null;
  return (
    <div style={{ padding: "0.5rem 1rem", borderBottom: "1px solid #1a1a1a", fontSize: "0.7rem", lineHeight: 1.6 }}>
      <span style={{ color: "#666" }}>Active ({active.length}) </span>
      {active.slice(0, 5).map((n, i) => (
        <span key={n.id}>
          <span style={{ color: TYPE_COLORS[n.nodeType] || "#888" }}>{n.label.slice(0, 50)}</span>
          {i < Math.min(active.length, 5) - 1 && <span style={{ color: "#333" }}> · </span>}
        </span>
      ))}
      {active.length > 5 && <span style={{ color: "#444" }}> +{active.length - 5} more</span>}
    </div>
  );
}
