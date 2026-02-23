import { useRef, useEffect } from "react";
import { type LayoutMode } from "../../types/phase-space";
import { Markdown } from "./Markdown";
import type { ChatMessage } from "../../pages/Workspace";

export function ChatPanel({
  messages,
  inputValue,
  onInputChange,
  onSubmit,
  onNewConversation,
  isStreaming,
  focusStartIndex,
  visibleFromIndex,
  conversationStartIndices,
  hasHiddenConversations,
  onLoadPrevious,
  showClusters,
  onToggleClusters,
  layoutMode,
  onCycleLayout,
  nodeCount,
  clusterCount,
  relevanceMap,
}: {
  messages: ChatMessage[];
  inputValue: string;
  onInputChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onNewConversation: () => void;
  isStreaming: boolean;
  focusStartIndex: number;
  visibleFromIndex: number;
  conversationStartIndices: Set<number>;
  hasHiddenConversations: boolean;
  onLoadPrevious: () => void;
  showClusters: boolean;
  onToggleClusters: () => void;
  layoutMode: LayoutMode;
  onCycleLayout: () => void;
  nodeCount: number;
  clusterCount: number;
  relevanceMap: Map<string, number>;
}) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div style={{
      width: "100%", height: "100%",
      display: "flex", flexDirection: "column",
      background: "var(--voku-bg-base)", color: "var(--voku-text-primary)",
    }}>
      {/* Header */}
      <div style={{
        padding: "0.6rem 1rem", borderBottom: `1px solid var(--voku-border-subtle)`,
        fontSize: "0.8rem", color: "var(--voku-text-tertiary)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ color: "var(--voku-accent-gold)", fontWeight: 500, letterSpacing: "0.05em" }}>
            Voku
          </span>
          <button onClick={onNewConversation} disabled={isStreaming}
            style={{
              background: "transparent",
              border: `1px solid var(--voku-border-default)`,
              borderRadius: "var(--voku-radius-sm)",
              padding: "2px 10px",
              color: "var(--voku-text-tertiary)",
              fontSize: "11px",
              opacity: isStreaming ? 0.3 : 1,
              transition: "all 0.15s ease",
            }}>
            + new
          </button>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button onClick={onToggleClusters}
            style={{
              background: showClusters ? "var(--voku-bg-hover)" : "transparent",
              border: `1px solid var(--voku-border-default)`,
              borderRadius: "var(--voku-radius-sm)",
              padding: "2px 10px",
              color: showClusters ? "var(--voku-text-secondary)" : "var(--voku-text-tertiary)",
              fontSize: "11px",
            }}>
            clusters
          </button>
          <button onClick={onCycleLayout}
            style={{
              background: "var(--voku-bg-raised)",
              border: `1px solid var(--voku-border-default)`,
              borderRadius: "var(--voku-radius-sm)",
              padding: "2px 10px",
              color: layoutMode === "time" ? "var(--voku-accent-gold)" : "var(--voku-text-secondary)",
              fontSize: "11px",
            }}>
            {layoutMode === "cluster" ? "by cluster" : layoutMode === "type" ? "by type" : "by time"}
          </button>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", overflowX: "hidden", padding: "0.75rem" }}>
        {/* Load earlier conversations */}
        {hasHiddenConversations && (
          <button
            onClick={onLoadPrevious}
            style={{
              display: "block",
              width: "100%",
              padding: "0.5rem",
              marginBottom: "0.75rem",
              background: "none",
              border: `1px dashed var(--voku-border-default)`,
              borderRadius: "var(--voku-radius-md)",
              color: "var(--voku-text-tertiary)",
              fontSize: "0.75rem",
              fontFamily: "var(--voku-font-mono)",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              (e.target as HTMLElement).style.borderColor = "var(--voku-accent-gold-dim)";
              (e.target as HTMLElement).style.color = "var(--voku-accent-gold)";
            }}
            onMouseLeave={(e) => {
              (e.target as HTMLElement).style.borderColor = "var(--voku-border-default)";
              (e.target as HTMLElement).style.color = "var(--voku-text-tertiary)";
            }}
          >
            load earlier conversations
          </button>
        )}

        {messages.length === 0 && (
          <div style={{
            color: "var(--voku-text-muted)", fontSize: "0.95rem", lineHeight: 1.8,
            padding: "2rem 0.5rem",
          }}>
            Start a conversation with Claude.<br />
            Your messages will light up related propositions in the phase space.
          </div>
        )}
        {messages.map((msg, i) => {
          // Skip messages before visible window
          if (i < visibleFromIndex) return null;

          const isUser = msg.role === "user";
          const isFocused = i >= focusStartIndex;
          const isLatest = i === messages.length - 1;
          const isConversationStart = conversationStartIndices.has(i) && i > visibleFromIndex;

          return (
            <div key={i}>
              {/* Conversation separator */}
              {isConversationStart && (
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  margin: "1rem 0 0.75rem",
                  padding: "0 0.25rem",
                }}>
                  <div style={{
                    flex: 1,
                    height: "1px",
                    background: isFocused
                      ? "var(--voku-accent-gold-dim)"
                      : "var(--voku-border-subtle)",
                  }} />
                  <span style={{
                    fontSize: "0.62rem",
                    fontFamily: "var(--voku-font-mono)",
                    color: isFocused
                      ? "var(--voku-accent-gold)"
                      : "var(--voku-text-muted)",
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    whiteSpace: "nowrap",
                  }}>
                    {isFocused ? "current" : "previous"}
                  </span>
                  <div style={{
                    flex: 1,
                    height: "1px",
                    background: isFocused
                      ? "var(--voku-accent-gold-dim)"
                      : "var(--voku-border-subtle)",
                  }} />
                </div>
              )}

              {/* Message bubble */}
              <div style={{
                marginBottom: "0.5rem",
                fontSize: "0.95rem",
                padding: "0.6rem 0.85rem",
                background: isFocused
                  ? (isUser ? "var(--voku-user-bg)" : "var(--voku-assistant-bg)")
                  : "var(--voku-bg-deep)",
                borderRadius: "var(--voku-radius-md)",
                borderLeft: !isUser ? `2px solid ${isFocused ? "var(--voku-assistant-accent)" : "var(--voku-border-subtle)"}` : "none",
                borderRight: isUser ? `2px solid ${isFocused ? "var(--voku-user-accent)" : "var(--voku-border-subtle)"}` : "none",
                marginLeft: isUser ? "1.5rem" : "0",
                marginRight: isUser ? "0" : "1.5rem",
                textAlign: isUser ? "right" : "left",
                opacity: isFocused ? (isLatest ? 1 : 0.7) : 0.2,
                lineHeight: 1.6,
                whiteSpace: isUser ? "pre-wrap" : "normal",
                transition: "opacity 0.3s ease",
              }}>
                {isFocused && (
                  <div style={{
                    fontSize: "0.7rem",
                    color: isUser ? "var(--voku-user-accent)" : "var(--voku-assistant-accent)",
                    marginBottom: "0.25rem",
                    fontWeight: 500,
                    letterSpacing: "0.04em",
                    textTransform: "lowercase",
                  }}>
                    {isUser ? "you" : "claude"}
                  </div>
                )}
                {isUser ? (
                  msg.content
                ) : (
                  msg.content ? <Markdown content={msg.content} /> : (
                    <span style={{ color: "var(--voku-accent-gold-dim)" }}>▊</span>
                  )
                )}
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Footer — type legend */}
      <div style={{
        padding: "0.5rem 1rem", borderTop: `1px solid var(--voku-border-subtle)`,
        fontSize: "0.75rem", color: "var(--voku-text-muted)", display: "flex", gap: "14px",
        fontFamily: "var(--voku-font-mono)",
      }}>
        {layoutMode === "type" ? (
          <>
            <span><span style={{ color: "var(--voku-type-stance)" }}>●</span> stance</span>
            <span><span style={{ color: "var(--voku-type-event)" }}>●</span> event</span>
            <span><span style={{ color: "var(--voku-type-intention)" }}>●</span> intention</span>
          </>
        ) : layoutMode === "time" ? (
          <>
            <span><span style={{ color: "#4a78a8" }}>●</span> oldest</span>
            <span>→</span>
            <span><span style={{ color: "#9a7b3c" }}>●</span> newest</span>
            <span style={{ marginLeft: "auto" }}>{nodeCount} nodes</span>
          </>
        ) : (
          <span>{clusterCount} clusters · {nodeCount} nodes</span>
        )}
      </div>

      {/* Input */}
      <form onSubmit={onSubmit} style={{
        padding: "0.75rem", borderTop: `1px solid var(--voku-border-subtle)`,
      }}>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => onInputChange(e.target.value)}
          disabled={isStreaming}
          placeholder={isStreaming ? "Claude is thinking..." : "Type a message..."}
          style={{
            width: "100%",
            padding: "0.6rem 0.85rem",
            background: "var(--voku-bg-raised)",
            border: `1px solid ${isStreaming ? "var(--voku-border-subtle)" : "var(--voku-border-default)"}`,
            borderRadius: "var(--voku-radius-md)",
            color: "var(--voku-text-primary)",
            fontSize: "0.95rem",
            fontFamily: "var(--voku-font-body)",
            outline: "none",
            opacity: isStreaming ? 0.5 : 1,
            transition: "border-color 0.15s ease",
          }}
          onFocus={(e) => { if (!isStreaming) e.target.style.borderColor = "var(--voku-border-focus)"; }}
          onBlur={(e) => { e.target.style.borderColor = "var(--voku-border-default)"; }}
        />
      </form>
    </div>
  );
}
