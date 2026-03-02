import { useRef, useEffect } from "react";
import { Markdown } from "./Markdown";
import type { ChatMessage } from "../../pages/Workspace";

/** Format ISO timestamp to "5:42 PM" */
function formatTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

/** Format ISO timestamp to "Sun, Feb 22" */
function formatDate(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
}

/**
 * ChatMessages — Scrollable message list with conversation boundaries.
 *
 * v2: Accepts retrievalIds to show context indicator on assistant messages.
 * Full ContextMarker component (progressive disclosure) is a separate step.
 */
export function ChatMessages({
  messages,
  focusStartIndex,
  visibleFromIndex,
  conversationStartIndices,
  hasHiddenConversations,
  onLoadPrevious,
  retrievalIds,
}: {
  messages: ChatMessage[];
  focusStartIndex: number;
  visibleFromIndex: number;
  conversationStartIndices: Set<number>;
  hasHiddenConversations: boolean;
  onLoadPrevious: () => void;
  retrievalIds: string[];
}) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div
      className="scrollbar-fade"
      style={{
        flex: 1,
        overflowY: "auto",
        overflowX: "hidden",
        padding: "var(--voku-space-4) var(--voku-space-6)",
      }}
    >
      {/* Load earlier conversations */}
      {hasHiddenConversations && (
        <button
          onClick={onLoadPrevious}
          style={{
            display: "block",
            width: "100%",
            padding: "var(--voku-space-2)",
            marginBottom: "var(--voku-space-3)",
            background: "none",
            border: "1px dashed var(--voku-border-default)",
            borderRadius: "var(--voku-radius-md)",
            color: "var(--voku-text-tertiary)",
            fontSize: "var(--voku-text-xs)",
            fontFamily: "var(--voku-font-mono)",
            cursor: "pointer",
            transition: "all 0.15s ease",
            opacity: 0.5,
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

      {/* Empty state */}
      {messages.length === 0 && (
        <div
          style={{
            color: "var(--voku-text-muted)",
            fontSize: "var(--voku-text-base)",
            lineHeight: "var(--voku-leading-relaxed)",
            padding: "var(--voku-space-8) var(--voku-space-2)",
          }}
        >
          Start a conversation.
          <br />
          <span style={{ fontSize: "var(--voku-text-sm)", color: "var(--voku-text-tertiary)" }}>
            Every message becomes a trace in your thinking graph.
          </span>
        </div>
      )}

      {/* Message list */}
      {messages.map((msg, i) => {
        if (i < visibleFromIndex) return null;

        const isUser = msg.role === "user";
        const isFocused = i >= focusStartIndex;
        const isLatest = i === messages.length - 1;
        const isConversationStart =
          conversationStartIndices.has(i) && i > visibleFromIndex;

        // Show retrieval indicator on the latest assistant message
        const showRetrieval = !isUser && isLatest && isFocused && retrievalIds.length > 0;

        return (
          <div key={i}>
            {/* Conversation separator */}
            {isConversationStart && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--voku-space-2)",
                  margin: "var(--voku-space-4) 0 var(--voku-space-3)",
                  padding: "0 var(--voku-space-1)",
                }}
              >
                <div
                  style={{
                    flex: 1,
                    height: "1px",
                    background: isFocused
                      ? "var(--voku-accent-gold-dim)"
                      : "var(--voku-border-subtle)",
                  }}
                />
                <span
                  style={{
                    fontSize: "var(--voku-text-xs)",
                    fontFamily: "var(--voku-font-mono)",
                    color: isFocused
                      ? "var(--voku-accent-gold)"
                      : "var(--voku-text-muted)",
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    whiteSpace: "nowrap",
                  }}
                >
                  {isFocused ? `current · ${formatDate(msg.createdAt)}` : formatDate(msg.createdAt)}
                </span>
                <div
                  style={{
                    flex: 1,
                    height: "1px",
                    background: isFocused
                      ? "var(--voku-accent-gold-dim)"
                      : "var(--voku-border-subtle)",
                  }}
                />
              </div>
            )}

            {/* Message bubble */}
            <div
              style={{
                display: "flex",
                justifyContent: isUser ? "flex-end" : "flex-start",
                marginBottom: "var(--voku-space-3)",
              }}
            >
            <div
              style={{
                maxWidth: "var(--voku-msg-max-w)",
                fontSize: "var(--voku-text-base)",
                lineHeight: "var(--voku-leading-normal)",
                padding: "var(--voku-space-3) var(--voku-space-4)",
                background: isFocused
                  ? isUser
                    ? "var(--voku-user-bg)"
                    : "var(--voku-assistant-bg)"
                  : "var(--voku-bg-deep)",
                borderRadius: isUser
                  ? "var(--voku-radius-lg) var(--voku-radius-lg) var(--voku-radius-sm) var(--voku-radius-lg)"
                  : "var(--voku-radius-lg) var(--voku-radius-lg) var(--voku-radius-lg) var(--voku-radius-sm)",
                borderLeft: !isUser
                  ? `3px solid ${isFocused ? "var(--voku-assistant-accent)" : "var(--voku-border-subtle)"}`
                  : "none",
                textAlign: isUser ? "right" : "left",
                opacity: isFocused ? (isLatest ? 1 : 0.9) : 0.5,
                whiteSpace: isUser ? "pre-wrap" : "normal",
                transition: "opacity 0.3s ease",
              }}
            >
              {/* Retrieval indicator — only on assistant messages with context */}
              {showRetrieval && (
                <div
                  style={{
                    fontSize: "var(--voku-text-xs)",
                    color: "var(--voku-accent-gold)",
                    marginBottom: "var(--voku-space-2)",
                    fontWeight: 500,
                    letterSpacing: "0.04em",
                    opacity: 0.7,
                  }}
                  title={`${retrievalIds.length} trace${retrievalIds.length > 1 ? "s" : ""} informed this response`}
                >
                  ◆ {retrievalIds.length} trace{retrievalIds.length > 1 ? "s" : ""}
                </div>
              )}
              {isUser ? (
                msg.content
              ) : msg.content ? (
                <Markdown
                  content={msg.content}
                  retrievalIds={showRetrieval ? retrievalIds : undefined}
                />
              ) : (
                <span style={{ color: "var(--voku-accent-gold-dim)" }}>▊</span>
              )}
            </div>
            </div>
          </div>
        );
      })}
      <div ref={messagesEndRef} />
    </div>
  );
}
