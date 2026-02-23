/**
 * ChatHeader — Brand label + new conversation button.
 *
 * Stripped to minimum. Phase-space controls (layout mode, clusters)
 * moved to PhaseSpaceOverlay (B3). This header is purely conversational.
 */
export function ChatHeader({
  onNewConversation,
  isStreaming,
}: {
  onNewConversation: () => void;
  isStreaming: boolean;
}) {
  return (
    <header
      style={{
        height: "var(--voku-header-h)",
        padding: "0 var(--voku-space-4)",
        borderBottom: "1px solid var(--voku-border-subtle)",
        display: "flex",
        alignItems: "center",
        gap: "var(--voku-space-3)",
        flexShrink: 0,
      }}
    >
      <span
        style={{
          color: "var(--voku-accent-gold)",
          fontWeight: 500,
          fontSize: "var(--voku-text-sm)",
          letterSpacing: "0.05em",
        }}
      >
        Voku
      </span>
      <button
        onClick={onNewConversation}
        disabled={isStreaming}
        style={{
          background: "transparent",
          border: "1px solid var(--voku-border-default)",
          borderRadius: "var(--voku-radius-sm)",
          padding: "var(--voku-space-1) var(--voku-space-3)",
          color: "var(--voku-text-tertiary)",
          fontSize: "var(--voku-text-xs)",
          opacity: isStreaming ? 0.3 : 1,
          transition: "all 0.15s ease",
        }}
      >
        + new
      </button>
    </header>
  );
}
