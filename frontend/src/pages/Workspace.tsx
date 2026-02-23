import { useState, useMemo, useEffect } from "react";
import { NODES } from "../types/phase-space";
import { scoreRelevance } from "../lib/relevance";
import { ChatPanel } from "../components/chat/ChatPanel";
import { PhaseSpace } from "../components/phase-space/PhaseSpace";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const API_BASE = "http://localhost:8000/api";

export default function Workspace() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [focusStartIndex, setFocusStartIndex] = useState(0);
  const [showClusters, setShowClusters] = useState(true);
  const [colorMode, setColorMode] = useState<"cluster" | "type">("cluster");

  // Load all conversations on mount into one continuous stream
  useEffect(() => {
    fetch(`${API_BASE}/history`)
      .then((res) => res.json())
      .then((conversations) => {
        if (conversations.length > 0) {
          // Flatten all conversations into one stream (oldest first)
          const allMessages: ChatMessage[] = [];
          // History returns most recent first — reverse to get chronological
          const chronological = [...conversations].reverse();
          for (const conv of chronological) {
            for (const m of conv.messages) {
              allMessages.push({
                role: m.role as "user" | "assistant",
                content: m.content,
              });
            }
          }
          setMessages(allMessages);
          // Focus only on the most recent conversation
          const latestConv = conversations[0];
          setConversationId(latestConv.id);
          setFocusStartIndex(allMessages.length - latestConv.messages.length);
        }
      })
      .catch((err) => console.error("Failed to load history:", err));
  }, []);

  // Relevance scoring only uses messages from focusStartIndex onward
  const relevanceMap = useMemo(() => {
    const map = new Map<string, number>();
    const focusedMessages = messages.slice(focusStartIndex);
    const userMessages = focusedMessages.filter((m) => m.role === "user");
    if (userMessages.length === 0) {
      NODES.forEach((n) => map.set(n.id, 0));
      return map;
    }
    NODES.forEach((node) => {
      let totalScore = 0;
      userMessages.forEach((msg, i) => {
        const distFromEnd = userMessages.length - 1 - i;
        const decay = Math.pow(0.4, distFromEnd);
        totalScore += scoreRelevance(msg.content, node) * decay;
      });
      map.set(node.id, Math.min(totalScore, 1));
    });
    return map;
  }, [messages, focusStartIndex]);

  const handleNewConversation = () => {
    // Don't clear messages — just move the focus window forward
    setFocusStartIndex(messages.length);
    setConversationId(null);
    setInputValue("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isStreaming) return;

    const userMessage: ChatMessage = { role: "user", content: inputValue.trim() };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInputValue("");
    setIsStreaming(true);

    // Add empty assistant message for streaming into
    setMessages([...updatedMessages, { role: "assistant", content: "" }]);

    // Only send messages from current focus window to the API
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

      if (!response.ok) {
        throw new Error(`Chat failed: ${response.status}`);
      }

      const newConversationId = response.headers.get("X-Conversation-Id");
      if (newConversationId) {
        setConversationId(newConversationId);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        accumulated += chunk;

        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: accumulated,
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
        };
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw" }}>
      <ChatPanel
        messages={messages}
        inputValue={inputValue}
        onInputChange={setInputValue}
        onSubmit={handleSubmit}
        onNewConversation={handleNewConversation}
        isStreaming={isStreaming}
        focusStartIndex={focusStartIndex}
        showClusters={showClusters}
        onToggleClusters={() => setShowClusters(!showClusters)}
        colorMode={colorMode}
        onToggleColorMode={() =>
          setColorMode(colorMode === "cluster" ? "type" : "cluster")
        }
        relevanceMap={relevanceMap}
      />
      <PhaseSpace
        relevanceMap={relevanceMap}
        showClusters={showClusters}
        colorMode={colorMode}
      />
    </div>
  );
}
