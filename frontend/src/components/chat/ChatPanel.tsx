import { NODES, CLUSTERS, TYPE_COLORS } from "../../types/phase-space";
import { ActiveSummary } from "./ActiveSummary";

export function ChatPanel({
  messages,
  inputValue,
  onInputChange,
  onSubmit,
  showClusters,
  onToggleClusters,
  colorMode,
  onToggleColorMode,
  relevanceMap,
}: {
  messages: string[];
  inputValue: string;
  onInputChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  showClusters: boolean;
  onToggleClusters: () => void;
  colorMode: "cluster" | "type";
  onToggleColorMode: () => void;
  relevanceMap: Map<string, number>;
}) {
  return (
    <div style={{
      width: "30%", minWidth: 280, display: "flex", flexDirection: "column",
      borderRight: "1px solid #1a1a1a", background: "#080808", color: "#e0e0e0",
    }}>
      <div style={{
        padding: "0.6rem 1rem", borderBottom: "1px solid #1a1a1a",
        fontSize: "0.7rem", color: "#555", display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <span>Voku — {NODES.length} propositions · {CLUSTERS.length} clusters</span>
        <div style={{ display: "flex", gap: "8px" }}>
          <button onClick={onToggleClusters}
            style={{ background: showClusters ? "#222" : "transparent", border: "1px solid #333",
              borderRadius: "4px", padding: "2px 8px", color: showClusters ? "#aaa" : "#555",
              fontSize: "10px", cursor: "pointer" }}>
            clusters
          </button>
          <button onClick={onToggleColorMode}
            style={{ background: "#111", border: "1px solid #333", borderRadius: "4px",
              padding: "2px 8px", color: "#aaa", fontSize: "10px", cursor: "pointer" }}>
            {colorMode === "cluster" ? "by cluster" : "by type"}
          </button>
        </div>
      </div>

      <ActiveSummary relevanceMap={relevanceMap} />

      <div style={{ flex: 1, overflowY: "auto", padding: "0.75rem" }}>
        {messages.length === 0 && (
          <div style={{ color: "#3a3a3a", fontSize: "0.8rem", lineHeight: 1.8 }}>
            Try with your real data:<br />
            1. "training breathing rowing"<br />
            2. "I keep procrastinating and scrolling"<br />
            3. "finance tracker budget spending"<br />
            4. "interest based nervous system energy"<br />
            5. "Billy Voku ATLAS architecture"
          </div>
        )}
        {messages.map((msg, i) => {
          const isCurrent = i === messages.length - 1;
          return (
            <div key={i} style={{
              marginBottom: "0.4rem", fontSize: "0.85rem", padding: "0.4rem 0.6rem",
              background: isCurrent ? "#111118" : "#0d0d0d", borderRadius: "0.3rem",
              borderLeft: isCurrent ? "2px solid #3b82f6" : "2px solid transparent",
              opacity: isCurrent ? 1 : 0.45,
            }}>
              {msg}
            </div>
          );
        })}
      </div>

      <div style={{ padding: "0.5rem 1rem", borderTop: "1px solid #1a1a1a",
        fontSize: "0.65rem", color: "#444", display: "flex", gap: "12px" }}>
        {colorMode === "type" ? (
          <>
            <span><span style={{ color: TYPE_COLORS.stance }}>●</span> stance</span>
            <span><span style={{ color: TYPE_COLORS.event }}>●</span> event</span>
            <span><span style={{ color: TYPE_COLORS.intention }}>●</span> intention</span>
          </>
        ) : (
          <span>{CLUSTERS.length} clusters · {NODES.filter(n => n.cluster === -1).length} unclustered</span>
        )}
      </div>

      <form onSubmit={onSubmit} style={{ padding: "0.75rem", borderTop: "1px solid #1a1a1a" }}>
        <input type="text" value={inputValue} onChange={(e) => onInputChange(e.target.value)}
          placeholder="Type a message..."
          style={{ width: "100%", padding: "0.5rem 0.65rem", background: "#0d0d0d",
            border: "1px solid #222", borderRadius: "0.3rem", color: "#d0d0d0",
            fontSize: "0.85rem", outline: "none" }} />
      </form>
    </div>
  );
}
