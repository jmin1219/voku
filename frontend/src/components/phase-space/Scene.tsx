import { useMemo } from "react";
import { type PropositionNode, type ClusterData, type EdgeData, type LayoutMode } from "../../types/phase-space";
import { CameraController } from "./CameraController";
import { ClusterShell } from "./ClusterShell";
import { EdgeMesh } from "./EdgeMesh";
import { NodeCloud } from "./NodeCloud";
import { TimeAxis } from "./TimeAxis";

export function Scene({ nodes, clusters, edges, relevanceMap, showClusters, layoutMode, retrievalIds }: {
  nodes: PropositionNode[];
  clusters: ClusterData[];
  edges: EdgeData[];
  relevanceMap: Map<string, number>;
  showClusters: boolean;
  layoutMode: LayoutMode;
  retrievalIds: string[];
}) {
  const retrievalSet = useMemo(() => new Set(retrievalIds), [retrievalIds]);

  const hasActive = useMemo(() => {
    if (retrievalSet.size > 0) return true;
    for (const v of relevanceMap.values()) {
      if (v > 0.3) return true;
    }
    return false;
  }, [relevanceMap, retrievalSet]);

  // Only show cluster shells in semantic layouts (not time view)
  // Hide cluster shells in time and dimension modes — geometric clusters
  // don't correspond to temporal or semantic-dimension groupings
  const showClusterShells = showClusters && layoutMode !== "time" && layoutMode !== "dimension";

  return (
    <>
      <ambientLight intensity={0.4} color="#c8c0d0" />
      <pointLight position={[8, 8, 8]} intensity={0.8} color="#ffe8d0" />
      <pointLight position={[-6, -4, 4]} intensity={0.4} color="#d0c8e0" />
      <CameraController nodes={nodes} relevanceMap={relevanceMap} />
      {showClusterShells && clusters.map((c) => (
        <ClusterShell key={c.id} cluster={c} layoutMode={layoutMode} hasActive={hasActive} />
      ))}
      {layoutMode === "time" && <TimeAxis />}
      <EdgeMesh
        nodes={nodes}
        edges={edges}
        layoutMode={layoutMode}
        retrievalIds={retrievalIds}
        hasActive={hasActive}
      />
      <NodeCloud
        nodes={nodes}
        relevanceMap={relevanceMap}
        retrievalIds={retrievalIds}
        layoutMode={layoutMode}
        hasActive={hasActive}
      />
    </>
  );
}
