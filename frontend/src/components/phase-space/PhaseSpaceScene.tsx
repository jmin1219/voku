import { useState, useMemo, useCallback } from "react";
import { Canvas } from "@react-three/fiber";
import type { PhaseSpaceData, PhaseSpaceNode } from "../../types/phase-space";
import { TraceCloud } from "./TraceCloud";
import { EdgeMesh } from "./EdgeMesh";
import { ClusterCloud } from "./ClusterCloud";
import { CameraController } from "./CameraController";
import { NodeLabels } from "./NodeLabels";
import { NodeHoverCard } from "./NodeHoverCard";

/**
 * PhaseSpaceScene — R3F Canvas with all phase space layers.
 *
 * Composes: TraceCloud (nodes), EdgeMesh (k-NN), ClusterCloud (shells),
 * CameraController (orbit + focus). Dark background.
 */

interface PhaseSpaceSceneProps {
  data: PhaseSpaceData;
  retrievalIds: string[];
  currentConversationId: string | null;
}

export function PhaseSpaceScene({
  data,
  retrievalIds,
  currentConversationId,
}: PhaseSpaceSceneProps) {
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const nodeMap = useMemo(() => {
    const map = new Map<string, PhaseSpaceNode>();
    for (const node of data.nodes) {
      map.set(node.id, node);
    }
    return map;
  }, [data.nodes]);

  const focusPosition = useMemo<[number, number, number] | null>(() => {
    if (!focusedId) return null;
    const node = nodeMap.get(focusedId);
    return node ? node.position : null;
  }, [focusedId, nodeMap]);

  // Bounding radius: max distance from origin across all nodes
  const dataRadius = useMemo(() => {
    if (data.nodes.length === 0) return 0;
    let maxDist = 0;
    for (const node of data.nodes) {
      const [x, y, z] = node.position;
      const dist = Math.sqrt(x * x + y * y + z * z);
      if (dist > maxDist) maxDist = dist;
    }
    return maxDist;
  }, [data.nodes]);

  const handleNodeClick = useCallback(
    (id: string) => {
      setFocusedId((prev) => (prev === id ? null : id));
    },
    []
  );

  const handleBgClick = useCallback(() => {
    setFocusedId(null);
  }, []);

  // Hovered node tooltip
  const hoveredNode = hoveredId ? nodeMap.get(hoveredId) : null;

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <Canvas
        camera={{ position: [0, 8, 12], fov: 50 }}
        style={{ background: "#080810" }}
        onPointerMissed={handleBgClick}
      >
        {/* meshBasicMaterial — no lights needed, vertex colors render directly */}

        <CameraController focusPosition={focusPosition} dataRadius={dataRadius} />

        <TraceCloud
          nodes={data.nodes}
          edges={data.edges}
          retrievalIds={retrievalIds}
          currentConversationId={currentConversationId}
          focusedId={focusedId}
          hoveredId={hoveredId}
          onNodeClick={handleNodeClick}
          onNodeHover={setHoveredId}
        />

        <EdgeMesh
          nodes={data.nodes}
          edges={data.edges}
          retrievalIds={retrievalIds}
        />

        <ClusterCloud clusters={data.clusters} />

        <NodeLabels
          nodes={data.nodes}
          focusedId={focusedId}
          hoveredId={hoveredId}
        />

        {/* Floating hover card */}
        {hoveredNode && (
          <NodeHoverCard
            node={hoveredNode}
            clusters={data.clusters}
            edges={data.edges}
          />
        )}
      </Canvas>

      {/* Meta overlay */}
      <div
        style={{
          position: "absolute",
          top: 8,
          right: 12,
          fontSize: "0.6rem",
          fontFamily: "var(--voku-font-mono)",
          color: "rgba(224, 219, 208, 0.4)",
          textAlign: "right",
        }}
      >
        {data.meta.count} traces · {data.meta.n_clusters} clusters · {data.meta.n_edges} edges
        {data.meta.count < 20 && (
          <div style={{ marginTop: 4, color: "rgba(201, 162, 60, 0.4)" }}>
            structure emerges with more conversations
          </div>
        )}
      </div>
    </div>
  );
}
