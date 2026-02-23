import { useMemo } from "react";
import { NODES, CLUSTERS } from "../../types/phase-space";
import { CameraController } from "./CameraController";
import { ClusterShell } from "./ClusterShell";
import { DataNode } from "./DataNode";

export function Scene({ relevanceMap, showClusters, colorMode }: {
  relevanceMap: Map<string, number>;
  showClusters: boolean;
  colorMode: "cluster" | "type";
}) {
  const hasActive = useMemo(() => {
    for (const v of relevanceMap.values()) {
      if (v > 0.3) return true;
    }
    return false;
  }, [relevanceMap]);

  return (
    <>
      <ambientLight intensity={0.8} />
      <pointLight position={[8, 8, 8]} intensity={1.0} />
      <pointLight position={[-6, -4, 4]} intensity={0.6} />
      <CameraController relevanceMap={relevanceMap} />
      {showClusters && CLUSTERS.map((c) => (
        <ClusterShell key={c.id} cluster={c} colorMode={colorMode} hasActive={hasActive} />
      ))}
      {NODES.map((node) => (
        <DataNode key={node.id} node={node} relevance={relevanceMap.get(node.id) || 0}
          colorMode={colorMode} hasActive={hasActive} />
      ))}
    </>
  );
}
