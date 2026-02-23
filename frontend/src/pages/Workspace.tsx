import { useState, useMemo } from "react";
import { NODES } from "../types/phase-space";
import { scoreRelevance } from "../lib/relevance";
import { ChatPanel } from "../components/chat/ChatPanel";
import { PhaseSpace } from "../components/phase-space/PhaseSpace";

export default function Workspace() {
  const [messages, setMessages] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [showClusters, setShowClusters] = useState(true);
  const [colorMode, setColorMode] = useState<"cluster" | "type">("cluster");

  const relevanceMap = useMemo(() => {
    const map = new Map<string, number>();
    if (messages.length === 0) {
      NODES.forEach((n) => map.set(n.id, 0));
      return map;
    }
    NODES.forEach((node) => {
      let totalScore = 0;
      messages.forEach((msg, i) => {
        const distFromEnd = messages.length - 1 - i;
        const decay = Math.pow(0.4, distFromEnd);
        totalScore += scoreRelevance(msg, node) * decay;
      });
      map.set(node.id, Math.min(totalScore, 1));
    });
    return map;
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;
    setMessages((prev) => [...prev, inputValue.trim()]);
    setInputValue("");
  };

  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw" }}>
      <ChatPanel
        messages={messages}
        inputValue={inputValue}
        onInputChange={setInputValue}
        onSubmit={handleSubmit}
        showClusters={showClusters}
        onToggleClusters={() => setShowClusters(!showClusters)}
        colorMode={colorMode}
        onToggleColorMode={() => setColorMode(colorMode === "cluster" ? "type" : "cluster")}
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
