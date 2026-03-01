import { ChatHeader } from "./ChatHeader";
import { ChatMessages } from "./ChatMessages";
import { ChatInput } from "./ChatInput";
import type { ChatMessage } from "../../pages/Workspace";

/**
 * ChatPanel — Thin composition shell.
 *
 * Stacks ChatHeader, ChatMessages, ChatInput in a flex column.
 * No logic of its own — just layout and prop routing.
 *
 * v2: Accepts retrievalIds for context marker rendering in messages.
 * Phase-space controls removed — graph is a separate summonable surface.
 */
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
  retrievalIds,
}: {
  messages: ChatMessage[];
  inputValue: string;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  onNewConversation: () => void;
  isStreaming: boolean;
  focusStartIndex: number;
  visibleFromIndex: number;
  conversationStartIndices: Set<number>;
  hasHiddenConversations: boolean;
  onLoadPrevious: () => void;
  retrievalIds: string[];
}) {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        background: "var(--voku-bg-base)",
        color: "var(--voku-text-primary)",
      }}
    >
      <ChatHeader
        onNewConversation={onNewConversation}
        isStreaming={isStreaming}
      />
      <ChatMessages
        messages={messages}
        focusStartIndex={focusStartIndex}
        visibleFromIndex={visibleFromIndex}
        conversationStartIndices={conversationStartIndices}
        hasHiddenConversations={hasHiddenConversations}
        onLoadPrevious={onLoadPrevious}
        retrievalIds={retrievalIds}
      />
      <ChatInput
        value={inputValue}
        onChange={onInputChange}
        onSubmit={onSubmit}
        isStreaming={isStreaming}
      />
    </div>
  );
}
