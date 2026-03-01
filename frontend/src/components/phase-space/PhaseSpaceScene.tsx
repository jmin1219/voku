import { useState, useMemo, useCallback } from "react";
import { Canvas } from "@react-three/fiber";
import type { PhaseSpaceData, PhaseSpaceNode } from "../../types/phase-space";
import { TraceCloud } from "./TraceCloud";
import { EdgeMesh } from "./EdgeMesh";
import { ClusterCloud } from "./ClusterCloud";
import { CameraController } from "./CameraController";

/**
 * PhaseSpaceScene — R3F Canvas with all phase space layers.
 *
 * Composes: TraceCloud (nodes), EdgeMesh (k-NN), ClusterCloud (shells),
 * CameraController (orbit + focus). Dark background.
 */

interface PhaseSpaceSceneProps {
  data: PhaseSpaceData;
  retrievalIds: string[];
}

export function PhaseSpaceScene({ data, retrievalIds }: PhaseSpaceSceneProps) {
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
        style={{ background: "var(--voku-phase-bg, #1a1a22)" }}
        onPointerMissed={handleBgClick}
      >
        {/* Lighting — warm/cool split, bright enough for dark bg */}
        <ambientLight intensity={0.4} />
        <pointLight position={[10, 10, 10]} intensity={1.2} color="#ffeedd" />
        <pointLight position={[-10, -5, -10]} intensity={0.6} color="#aabbdd" />
        <pointLight position={[0, -10, 5]} intensity={0.4} color="#ddccaa" />

        <CameraController focusPosition={focusPosition} />

        <TraceCloud
          nodes={data.nodes}
          retrievalIds={retrievalIds}
          focusedId={focusedId}
          onNodeClick={handleNodeClick}
          onNodeHover={setHoveredId}
        />

        <EdgeMesh
          nodes={data.nodes}
          edges={data.edges}
          retrievalIds={retrievalIds}
        />

        <ClusterCloud clusters={data.clusters} />
      </Canvas>

      {/* Tooltip overlay */}
      {hoveredNode && (
        <div
          style={{
            position: "absolute",
            bottom: 12,
            left: 12,
            maxWidth: 320,
            padding: "8px 12px",
            background: "rgba(26, 26, 34, 0.92)",
            border: "1px solid rgba(201, 162, 60, 0.3)",
            borderRadius: 6,
            color: "#e0dbd0",
            fontSize: "0.75rem",
            fontFamily: "var(--voku-font-body)",
            lineHeight: 1.5,
            pointerEvents: "none",
          }}
        >
          <div
            style={{
              fontSize: "0.65rem",
              fontFamily: "var(--voku-font-mono)",
              color: "#c9a23c",
              marginBottom: 4,
            }}
          >
            {hoveredNode.source} · {hoveredNode.createdAt.slice(0, 10)}
          </div>
          <div>{hoveredNode.label}</div>
          {hoveredNode.annotations.length > 0 && (
            <div
              style={{
                marginTop: 4,
                fontSize: "0.65rem",
                color: "#99907f",
              }}
            >
              {hoveredNode.annotations
                .slice(0, 2)
                .map((a) => `${a.type}: ${a.key}`)
                .join(" · ")}
            </div>
          )}
        </div>
      )}

      {/* Meta overlay */}
      <div
        style={{
          position: "absolute",
          top: 8,
          right: 12,
          fontSize: "0.6rem",
          fontFamily: "var(--voku-font-mono)",
          color: "rgba(224, 219, 208, 0.4)",
        }}
      >
        {data.meta.count} traces · {data.meta.n_clusters} clusters · {data.meta.n_edges} edges
      </div>
    </div>
  );
}
