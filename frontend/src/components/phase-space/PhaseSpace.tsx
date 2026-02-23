import { Canvas } from "@react-three/fiber";
import { Scene } from "./Scene";

export function PhaseSpace({ relevanceMap, showClusters, colorMode }: {
  relevanceMap: Map<string, number>;
  showClusters: boolean;
  colorMode: "cluster" | "type";
}) {
  return (
    <div style={{ width: "70%", background: "#020202" }}>
      <Canvas camera={{ position: [0, 0, 14], fov: 50 }}>
        <Scene relevanceMap={relevanceMap} showClusters={showClusters} colorMode={colorMode} />
      </Canvas>
    </div>
  );
}
