import { useMemo } from "react";
import { type PropositionNode, type ClusterData, type LayoutMode } from "../../types/phase-space";
import { CameraController } from "./CameraController";
import { ClusterShell } from "./ClusterShell";
import { DataNode } from "./DataNode";
import { TimeAxis } from "./TimeAxis";

export function Scene({ nodes, clusters, relevanceMap, showClusters, layoutMode, retrievalIds }: {
  nodes: PropositionNode[];
  clusters: ClusterData[];
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
  const showClusterShells = showClusters && layoutMode !== "time";

  return (
    <>
      <ambientLight intensity={1.2} color="#fff8f0" />
      <pointLight position={[8, 8, 8]} intensity={0.6} color="#fffaf0" />
      <pointLight position={[-6, -4, 4]} intensity={0.3} color="#f0e8d8" />
      <CameraController nodes={nodes} relevanceMap={relevanceMap} />
      {showClusterShells && clusters.map((c) => (
        <ClusterShell key={c.id} cluster={c} layoutMode={layoutMode} hasActive={hasActive} />
      ))}
      {layoutMode === "time" && <TimeAxis />}
      {nodes.map((node) => (
        <DataNode key={node.id} node={node}
          relevance={retrievalSet.has(node.id) ? 1.0 : (relevanceMap.get(node.id) || 0)}
          layoutMode={layoutMode} hasActive={hasActive} />
      ))}
    </>
  );
}
