import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { type PropositionNode, type ClusterData, type LayoutMode } from "../types/phase-space";
import { scoreRelevance } from "../lib/relevance";
import { ChatPanel } from "../components/chat/ChatPanel";
import { PhaseSpace } from "../components/phase-space/PhaseSpace";
import { ActiveSummary } from "../components/chat/ActiveSummary";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  createdAt: string; // ISO timestamp
}

export interface ConversationBoundary {
  startIndex: number;
  messageCount: number;
}

const API_BASE = "http://localhost:8000/api";
// Chat width: 1/3 of viewport by default, min 420px, max 2/3 viewport
// Drag bounds recalculated dynamically in the drag handler.
const MIN_CHAT_WIDTH = 420;
const INITIAL_VISIBLE_CONVERSATIONS = 2;

export default function Workspace() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [focusStartIndex, setFocusStartIndex] = useState(0);
  const [showClusters, setShowClusters] = useState(true);
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("cluster");
  const [retrievalIds, setRetrievalIds] = useState<string[]>([]);
  const [chatWidth, setChatWidth] = useState(() =>
    Math.max(MIN_CHAT_WIDTH, Math.round(window.innerWidth / 3))
  );
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Dynamic proposition nodes (fetched from API)
  const [nodes, setNodes] = useState<PropositionNode[]>([]);
  const [clusters, setClusters] = useState<ClusterData[]>([]);

  // Conversation boundaries
  const [boundaries, setBoundaries] = useState<ConversationBoundary[]>([]);
  const [visibleFromBoundary, setVisibleFromBoundary] = useState(0);

  // --- Fetch propositions from API ---
  const fetchPropositions = useCallback(() => {
    fetch(`${API_BASE}/propositions`)
      .then((res) => res.json())
      .then((data) => {
        setNodes(data.nodes || []);
        setClusters(data.clusters || []);
        console.log(`[propositions] ${data.nodes?.length || 0} nodes, ${data.clusters?.length || 0} clusters`);
      })
      .catch((err) => console.error("Failed to load propositions:", err));
  }, []);

  // Load propositions on mount
  useEffect(() => {
    fetchPropositions();
  }, [fetchPropositions]);

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
  const visibleFromIndex = useMemo(() => {
    if (boundaries.length === 0) return 0;
    if (visibleFromBoundary >= boundaries.length) return 0;
    return boundaries[visibleFromBoundary].startIndex;
  }, [boundaries, visibleFromBoundary]);

  const hasHiddenConversations = visibleFromBoundary > 0;

  const loadPreviousConversations = () => {
    setVisibleFromBoundary((prev) => Math.max(0, prev - 2));
  };

  const conversationStartIndices = useMemo(() => {
    return new Set(boundaries.map((b) => b.startIndex));
  }, [boundaries]);

  // Has active conversation (for time mode gating)
  const hasActiveConversation = focusStartIndex < messages.length;

  // Draggable divider
  const handleMouseDown = useCallback(() => {
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;
    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const maxWidth = Math.round(rect.width * (2 / 3));
      const newWidth = Math.min(maxWidth, Math.max(MIN_CHAT_WIDTH, e.clientX - rect.left));
      setChatWidth(newWidth);
    };
    const handleMouseUp = () => setIsDragging(false);
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isDragging]);

  // Relevance scoring
  const relevanceMap = useMemo(() => {
    const map = new Map<string, number>();
    const focusedMessages = messages.slice(focusStartIndex);
    const userMessages = focusedMessages.filter((m) => m.role === "user");
    if (userMessages.length === 0) {
      nodes.forEach((n) => map.set(n.id, 0));
      return map;
    }
    nodes.forEach((node) => {
      let totalScore = 0;
      userMessages.forEach((msg, i) => {
        const distFromEnd = userMessages.length - 1 - i;
        const decay = Math.pow(0.4, distFromEnd);
        totalScore += scoreRelevance(msg.content, node) * decay;
      });
      map.set(node.id, Math.min(totalScore, 1));
    });
    return map;
  }, [messages, focusStartIndex, nodes]);

  // Layout mode cycling: cluster → type → dimension → time (if active) → cluster
  const cycleLayoutMode = () => {
    setLayoutMode((prev) => {
      if (prev === "cluster") return "type";
      if (prev === "type") return "dimension";
      if (prev === "dimension" && hasActiveConversation) return "time";
      return "cluster";
    });
  };

  const handleNewConversation = () => {
    // Fire extraction, then re-fetch propositions when done
    if (conversationId) {
      fetch(`${API_BASE}/extract/${conversationId}`, { method: "POST" })
        .then((res) => res.json())
        .then((data) => {
          console.log(
            `[extract] ${data.propositions_stored} stored, ${data.duplicates_skipped} dupes, ${data.propositions_extracted} total`
          );
          // Re-fetch propositions with new nodes
          if (data.propositions_stored > 0) {
            fetchPropositions();
          }
        })
        .catch((err) => console.warn("[extract] failed:", err));
    }

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

    // Reset to semantic layout when starting fresh
    if (layoutMode === "time") setLayoutMode("cluster");
  };

  const handleSubmit = async () => {
    if (!inputValue.trim() || isStreaming) return;

    const userMessage: ChatMessage = { role: "user", content: inputValue.trim(), createdAt: new Date().toISOString() };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInputValue("");
    setIsStreaming(true);
    setMessages([...updatedMessages, { role: "assistant", content: "", createdAt: new Date().toISOString() }]);

    const focusedMessages = updatedMessages.slice(focusStartIndex);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          messages: focusedMessages.map((m) => ({ role: m.role, content: m.content })),
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
          } catch (e) {
            console.warn("Failed to parse retrieval metadata:", e);
          }
          if (!buffer) continue;
        }

        accumulated += metadataParsed ? buffer : chunk;
        buffer = "";
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: accumulated };
          return updated;
        });
      }
    } catch (err) {
      console.error("Stream error:", err);
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", content: "[Error: Failed to get response]" };
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div
      ref={containerRef}
      style={{ display: "flex", height: "100vh", width: "100vw", background: "var(--voku-bg-deep)" }}
    >
      <div style={{ width: chatWidth, flexShrink: 0, background: "var(--voku-bg-base)" }}>
        <ChatPanel
          messages={messages}
          inputValue={inputValue}
          onInputChange={setInputValue}
          onSubmit={handleSubmit}
          onNewConversation={handleNewConversation}
          isStreaming={isStreaming}
          focusStartIndex={focusStartIndex}
          visibleFromIndex={visibleFromIndex}
          conversationStartIndices={conversationStartIndices}
          hasHiddenConversations={hasHiddenConversations}
          onLoadPrevious={loadPreviousConversations}
        />
      </div>

      <div
        onMouseDown={handleMouseDown}
        style={{
          width: 4, cursor: "col-resize", flexShrink: 0,
          background: isDragging ? "var(--voku-accent-gold-dim)" : "#2a2a32",
          transition: isDragging ? "none" : "background 0.15s ease",
        }}
        onMouseEnter={(e) => { if (!isDragging) (e.target as HTMLElement).style.background = "#3a3a44"; }}
        onMouseLeave={(e) => { if (!isDragging) (e.target as HTMLElement).style.background = "#2a2a32"; }}
      />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <ActiveSummary nodes={nodes} relevanceMap={relevanceMap} retrievalIds={retrievalIds} />
        <PhaseSpace
          nodes={nodes}
          clusters={clusters}
          relevanceMap={relevanceMap}
          showClusters={showClusters}
          layoutMode={layoutMode}
          retrievalIds={retrievalIds}
        />
      </div>
    </div>
  );
}
