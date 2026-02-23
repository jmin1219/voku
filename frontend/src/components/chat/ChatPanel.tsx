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
 * Phase-space controls (layout mode, clusters, legend) are no longer
 * part of this component. They move to a PhaseSpaceOverlay in B3.
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
