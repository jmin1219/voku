import { Canvas } from "@react-three/fiber";
import { type PropositionNode, type ClusterData, type LayoutMode } from "../../types/phase-space";
import { Scene } from "./Scene";

export function PhaseSpace({ nodes, clusters, relevanceMap, showClusters, layoutMode, retrievalIds }: {
  nodes: PropositionNode[];
  clusters: ClusterData[];
  relevanceMap: Map<string, number>;
  showClusters: boolean;
  layoutMode: LayoutMode;
  retrievalIds: string[];
}) {
  return (
    <div style={{ flex: 1, background: "var(--voku-phase-bg)" }}>
      <Canvas
        camera={{ position: [0, 0, 14], fov: 50 }}
        gl={{ alpha: true }}
        style={{ background: "transparent" }}
      >
        <color attach="background" args={["#eae4da"]} />
        <Scene nodes={nodes} clusters={clusters} relevanceMap={relevanceMap}
          showClusters={showClusters} layoutMode={layoutMode} retrievalIds={retrievalIds} />
      </Canvas>
    </div>
  );
}
