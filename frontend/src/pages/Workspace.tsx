import { useState, useEffect } from "react";
import { ChatPanel } from "../components/chat/ChatPanel";
import { PhaseSpaceContainer } from "../components/phase-space/PhaseSpaceContainer";
import { usePhaseSpace } from "../hooks/usePhaseSpace";
import { API_BASE } from "../config";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}

export interface ConversationBoundary {
  startIndex: number;
  messageCount: number;
}

const INITIAL_VISIBLE_CONVERSATIONS = 2;

export default function Workspace() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [focusStartIndex, setFocusStartIndex] = useState(0);
  const [retrievalIds, setRetrievalIds] = useState<string[]>([]);
  const [phaseSpaceOpen, setPhaseSpaceOpen] = useState(false);
  const phaseSpace = usePhaseSpace();

  // Keyboard shortcut: ⌘+Space / Ctrl+Space = toggle phase space, Escape = close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.code === "Space" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setPhaseSpaceOpen((prev) => !prev);
      }
      if (e.code === "Escape" && phaseSpaceOpen) {
        setPhaseSpaceOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [phaseSpaceOpen]);

  // Conversation boundaries
  const [boundaries, setBoundaries] = useState<ConversationBoundary[]>([]);
  const [visibleFromBoundary, setVisibleFromBoundary] = useState(0);

  // Load conversations on mount
  useEffect(() => {
    fetch(`${API_BASE}/history`)
      .then((res) => res.json())
      .then((conversations) => {
        if (conversations.length > 0) {
          const allMessages: ChatMessage[] = [];
          const allBoundaries: ConversationBoundary[] = [];
          const chronological = [...conversations].reverse();

          for (const conv of chronological) {
            allBoundaries.push({
              startIndex: allMessages.length,
              messageCount: conv.messages.length,
            });
            for (const m of conv.messages) {
              allMessages.push({
                role: m.role as "user" | "assistant",
                content: m.content,
                createdAt: m.created_at,
              });
            }
          }

          setMessages(allMessages);
          setBoundaries(allBoundaries);

          const latestConv = conversations[0];
          setConversationId(latestConv.id);
          setFocusStartIndex(allMessages.length - latestConv.messages.length);

          const startBoundary = Math.max(0, allBoundaries.length - INITIAL_VISIBLE_CONVERSATIONS);
          setVisibleFromBoundary(startBoundary);
        }
      })
      .catch((err) => console.error("Failed to load history:", err));
  }, []);

  // Conversation boundary helpers
  const visibleFromIndex = boundaries.length === 0 || visibleFromBoundary >= boundaries.length
    ? 0
    : boundaries[visibleFromBoundary].startIndex;

  const hasHiddenConversations = visibleFromBoundary > 0;

  const loadPreviousConversations = () => {
    setVisibleFromBoundary((prev) => Math.max(0, prev - 2));
  };

  const conversationStartIndices = new Set(boundaries.map((b) => b.startIndex));

  const handleNewConversation = () => {
    // Create empty conversation in DB
    fetch(`${API_BASE}/conversations`, { method: "POST" })
      .then((res) => res.json())
      .then((data) => setConversationId(data.id))
      .catch((err) => console.warn("[new conversation] failed:", err));

    const newBoundary: ConversationBoundary = {
      startIndex: messages.length,
      messageCount: 0,
    };
    setBoundaries((prev) => [...prev, newBoundary]);
    setVisibleFromBoundary((prev) => {
      const newLen = boundaries.length + 1;
      return Math.max(prev, newLen - INITIAL_VISIBLE_CONVERSATIONS);
    });

    setFocusStartIndex(messages.length);
    setInputValue("");
    setRetrievalIds([]);
  };

  // --- Digest handler: /digest [days] or button trigger ---
  const handleDigest = async (days: number = 30) => {
    if (isStreaming) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: `Summarize my thinking over the last ${days} days`,
      createdAt: new Date().toISOString(),
    };
    const updatedMessages = [...messages, userMessage];
    setMessages([
      ...updatedMessages,
      { role: "assistant", content: "Generating digest...", createdAt: new Date().toISOString() },
    ]);
    setInputValue("");
    setIsStreaming(true);

    try {
      const response = await fetch(`${API_BASE}/digest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ days }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || `Digest failed: ${response.status}`);
      }

      const data = await response.json();
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: data.narrative,
          createdAt: data.timestamp || new Date().toISOString(),
        };
        return updated;
      });
    } catch (err: any) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: err.message || "[Error: Failed to generate digest]",
          createdAt: new Date().toISOString(),
        };
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  const handleSubmit = async () => {
    if (!inputValue.trim() || isStreaming) return;

    // Detect /digest slash command
    const digestMatch = inputValue.trim().match(/^\/digest(?:\s+(\d+))?$/i);
    if (digestMatch) {
      const days = digestMatch[1] ? parseInt(digestMatch[1], 10) : 30;
      handleDigest(days);
      return;
    }

    const userMessage: ChatMessage = {
      role: "user",
      content: inputValue.trim(),
      createdAt: new Date().toISOString(),
    };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInputValue("");
    setIsStreaming(true);
    setMessages([
      ...updatedMessages,
      { role: "assistant", content: "", createdAt: new Date().toISOString() },
    ]);

    const focusedMessages = updatedMessages.slice(focusStartIndex);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          messages: focusedMessages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });

      if (!response.ok) throw new Error(`Chat failed: ${response.status}`);

      const newConversationId = response.headers.get("X-Conversation-Id");
      if (newConversationId) setConversationId(newConversationId);

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";
      let metadataParsed = false;
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        if (!metadataParsed) {
          const newlineIdx = buffer.indexOf("\n");
          if (newlineIdx === -1) continue;
          const metadataLine = buffer.slice(0, newlineIdx);
          buffer = buffer.slice(newlineIdx + 1);
          metadataParsed = true;
          try {
            const metadata = JSON.parse(metadataLine);
            if (metadata.retrieval_ids) setRetrievalIds(metadata.retrieval_ids);
            if (metadata.conversation_id) setConversationId(metadata.conversation_id);
          } catch (e) {
            console.warn("Failed to parse retrieval metadata:", e);
          }
          if (!buffer) continue;
        }

        accumulated += metadataParsed ? buffer : chunk;
        buffer = "";
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: accumulated,
            createdAt: new Date().toISOString(),
          };
          return updated;
        });
      }
    } catch (err) {
      console.error("Stream error:", err);
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: "[Error: Failed to get response]",
          createdAt: new Date().toISOString(),
        };
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        width: "100vw",
        background: "var(--voku-bg-base)",
      }}
    >
      {/* Chat panel — compresses when phase space is open */}
      <div
        style={{
          flex: 1,
          display: "flex",
          justifyContent: "center",
          height: "100%",
          minWidth: 0,
          transition: "flex 0.2s ease-out",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: phaseSpaceOpen ? "100%" : 720,
            height: "100%",
          }}
        >
          <ChatPanel
            messages={messages}
            inputValue={inputValue}
            onInputChange={setInputValue}
            onSubmit={handleSubmit}
            onNewConversation={handleNewConversation}
            onDigest={() => handleDigest(30)}
            isStreaming={isStreaming}
            focusStartIndex={focusStartIndex}
            visibleFromIndex={visibleFromIndex}
            conversationStartIndices={conversationStartIndices}
            hasHiddenConversations={hasHiddenConversations}
            onLoadPrevious={loadPreviousConversations}
            retrievalIds={retrievalIds}
          />
        </div>
      </div>

      {/* Phase space — slides in from right */}
      <PhaseSpaceContainer
        isOpen={phaseSpaceOpen}
        data={phaseSpace.data}
        loading={phaseSpace.loading}
        error={phaseSpace.error}
        retrievalIds={retrievalIds}
        currentConversationId={conversationId}
        onFetchData={phaseSpace.fetch}
      />
    </div>
  );
}
