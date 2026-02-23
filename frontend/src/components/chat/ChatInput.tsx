import { useRef, useEffect } from "react";

/**
 * ChatInput — Auto-growing textarea with Enter-to-submit.
 *
 * Controlled component: parent owns the value.
 * Grows from 1 line to ~6 lines, then scrolls internally.
 * Enter submits. Shift+Enter inserts newline.
 */
export function ChatInput({
  value,
  onChange,
  onSubmit,
  isStreaming,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isStreaming: boolean;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-grow: reset height to auto, then expand to scrollHeight.
  // Runs on every value change. The CSS max-height caps expansion.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  // Focus textarea on mount and after streaming ends
  useEffect(() => {
    if (!isStreaming) {
      textareaRef.current?.focus();
    }
  }, [isStreaming]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter without Shift = submit
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !isStreaming) {
        onSubmit();
      }
    }
    // Shift+Enter falls through — textarea inserts newline naturally
  };

  return (
    <div
      style={{
        padding: "var(--voku-space-3) var(--voku-space-4) var(--voku-space-4)",
        borderTop: "1px solid var(--voku-border-subtle)",
        background: "var(--voku-bg-base)",
      }}
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isStreaming}
        placeholder={isStreaming ? "Claude is thinking..." : "Type a message..."}
        rows={1}
        style={{
          width: "100%",
          minHeight: "var(--voku-input-min-h)",
          maxHeight: "var(--voku-input-max-h)",
          padding: "var(--voku-space-2) var(--voku-space-3)",
          background: "var(--voku-bg-raised)",
          border: `1px solid ${isStreaming ? "var(--voku-border-subtle)" : "var(--voku-border-default)"}`,
          borderRadius: "var(--voku-radius-lg)",
          color: "var(--voku-text-primary)",
          fontSize: "var(--voku-text-base)",
          fontFamily: "var(--voku-font-body)",
          lineHeight: "var(--voku-leading-normal)",
          resize: "none",
          outline: "none",
          opacity: isStreaming ? 0.5 : 1,
          transition: "border-color 0.15s ease, opacity 0.15s ease, box-shadow 0.15s ease",
          overflowY: "auto",
        }}
        onFocus={(e) => {
          if (!isStreaming) {
            e.target.style.borderColor = "var(--voku-border-focus)";
            e.target.style.boxShadow = "0 0 0 3px rgba(154, 123, 60, 0.1)";
          }
        }}
        onBlur={(e) => {
          e.target.style.borderColor = "var(--voku-border-default)";
          e.target.style.boxShadow = "none";
        }}
      />
    </div>
  );
}
