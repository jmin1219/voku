import { useRef, useEffect } from "react";
import { Markdown } from "./Markdown";
import type { ChatMessage } from "../../pages/Workspace";

/**
 * ChatMessages — Scrollable message list with conversation boundaries.
 *
 * Lift-and-shift from ChatPanel. Owns the scroll container and auto-scroll ref.
 * Renders conversation separators, role labels, and message bubbles.
 * No behavioral changes from the original — just isolation.
 */
export function ChatMessages({
  messages,
  focusStartIndex,
  visibleFromIndex,
  conversationStartIndices,
  hasHiddenConversations,
  onLoadPrevious,
}: {
  messages: ChatMessage[];
  focusStartIndex: number;
  visibleFromIndex: number;
  conversationStartIndices: Set<number>;
  hasHiddenConversations: boolean;
  onLoadPrevious: () => void;
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
        padding: "var(--voku-space-3) var(--voku-space-4)",
      }}
    >
      {/* Load earlier conversations — dashed button at top of scroll */}
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
          Start a conversation with Claude.
          <br />
          Your messages will light up related propositions in the phase space.
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
                  {isFocused ? "current" : "previous"}
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
                marginBottom: "var(--voku-space-2)",
                fontSize: "var(--voku-text-base)",
                lineHeight: "var(--voku-leading-normal)",
                padding: "var(--voku-space-2) var(--voku-space-3)",
                background: isFocused
                  ? isUser
                    ? "var(--voku-user-bg)"
                    : "var(--voku-assistant-bg)"
                  : "var(--voku-bg-deep)",
                borderRadius: "var(--voku-radius-md)",
                borderLeft: !isUser
                  ? `3px solid ${isFocused ? "var(--voku-assistant-accent)" : "var(--voku-border-subtle)"}`
                  : "none",
                borderRight: isUser
                  ? `3px solid ${isFocused ? "var(--voku-user-accent)" : "var(--voku-border-subtle)"}`
                  : "none",
                marginLeft: isUser ? "var(--voku-msg-indent)" : "0",
                marginRight: isUser ? "0" : "var(--voku-msg-indent)",
                textAlign: isUser ? "right" : "left",
                opacity: isFocused ? (isLatest ? 1 : 0.85) : 0.5,
                whiteSpace: isUser ? "pre-wrap" : "normal",
                transition: "opacity 0.3s ease",
              }}
            >
              {isFocused && (
                <div
                  style={{
                    fontSize: "var(--voku-text-xs)",
                    color: isUser
                      ? "var(--voku-user-accent)"
                      : "var(--voku-assistant-accent)",
                    marginBottom: "var(--voku-space-1)",
                    fontWeight: 500,
                    letterSpacing: "0.04em",
                    textTransform: "lowercase",
                  }}
                >
                  {isUser ? "you" : "claude"}
                </div>
              )}
              {isUser ? (
                msg.content
              ) : msg.content ? (
                <Markdown content={msg.content} />
              ) : (
                <span style={{ color: "var(--voku-accent-gold-dim)" }}>▊</span>
              )}
            </div>
          </div>
        );
      })}
      <div ref={messagesEndRef} />
    </div>
  );
}
