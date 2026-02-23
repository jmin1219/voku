import { useRef, useEffect } from "react";
import { NODES, CLUSTERS, TYPE_COLORS } from "../../types/phase-space";
import { ActiveSummary } from "./ActiveSummary";
import type { ChatMessage } from "../../pages/Workspace";

export function ChatPanel({
  messages,
  inputValue,
  onInputChange,
  onSubmit,
  onNewConversation,
  isStreaming,
  focusStartIndex,
  showClusters,
  onToggleClusters,
  colorMode,
  onToggleColorMode,
  relevanceMap,
}: {
  messages: ChatMessage[];
  inputValue: string;
  onInputChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onNewConversation: () => void;
  isStreaming: boolean;
  focusStartIndex: number;
  showClusters: boolean;
  onToggleClusters: () => void;
  colorMode: "cluster" | "type";
  onToggleColorMode: () => void;
  relevanceMap: Map<string, number>;
}) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div style={{
      width: "30%", minWidth: 320, display: "flex", flexDirection: "column",
      borderRight: "1px solid #1a1a1a", background: "#080808", color: "#e0e0e0",
    }}>
      <div style={{
        padding: "0.6rem 1rem", borderBottom: "1px solid #1a1a1a",
        fontSize: "0.75rem", color: "#555", display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span>Voku</span>
          <button onClick={onNewConversation} disabled={isStreaming}
            style={{ background: "transparent", border: "1px solid #333",
              borderRadius: "4px", padding: "2px 8px", color: "#666",
              fontSize: "10px", cursor: isStreaming ? "default" : "pointer",
              opacity: isStreaming ? 0.3 : 1 }}>
            + new
          </button>
        </div>
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
          <div style={{ color: "#3a3a3a", fontSize: "0.85rem", lineHeight: 1.8 }}>
            Start a conversation with Claude.<br />
            Your messages will light up related propositions in the phase space.
          </div>
        )}
        {messages.map((msg, i) => {
          const isUser = msg.role === "user";
          const isFocused = i >= focusStartIndex;
          const isLatest = i === messages.length - 1;
          return (
            <div key={i} style={{
              marginBottom: "0.5rem",
              fontSize: "0.9rem",
              padding: "0.5rem 0.7rem",
              background: isFocused
                ? (isUser ? "#111118" : "#0d100d")
                : "#0a0a0a",
              borderRadius: "0.3rem",
              borderLeft: !isUser ? (isFocused ? "2px solid #2d8a4e" : "2px solid #1a1a1a") : "none",
              borderRight: isUser ? (isFocused ? "2px solid #3b82f6" : "2px solid #1a1a1a") : "none",
              marginLeft: isUser ? "2rem" : "0",
              marginRight: isUser ? "0" : "2rem",
              textAlign: isUser ? "right" : "left",
              opacity: isFocused ? (isLatest ? 1 : 0.7) : 0.25,
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
              transition: "opacity 0.3s ease",
            }}>
              {isFocused && (
                <div style={{
                  fontSize: "0.65rem",
                  color: isUser ? "#3b82f6" : "#2d8a4e",
                  marginBottom: "0.2rem",
                  fontWeight: 600,
                }}>
                  {isUser ? "you" : "claude"}
                </div>
              )}
              {msg.content}
              {isLatest && !isUser && msg.content === "" && (
                <span style={{ color: "#555" }}>▊</span>
              )}
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      <div style={{ padding: "0.5rem 1rem", borderTop: "1px solid #1a1a1a",
        fontSize: "0.7rem", color: "#444", display: "flex", gap: "12px" }}>
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
        <input
          type="text"
          value={inputValue}
          onChange={(e) => onInputChange(e.target.value)}
          disabled={isStreaming}
          placeholder={isStreaming ? "Claude is thinking..." : "Type a message..."}
          style={{
            width: "100%",
            padding: "0.5rem 0.65rem",
            background: "#0d0d0d",
            border: `1px solid ${isStreaming ? "#1a1a1a" : "#222"}`,
            borderRadius: "0.3rem",
            color: "#d0d0d0",
            fontSize: "0.9rem",
            outline: "none",
            opacity: isStreaming ? 0.5 : 1,
          }}
        />
      </form>
    </div>
  );
}
