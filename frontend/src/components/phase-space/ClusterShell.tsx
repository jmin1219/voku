import { Html } from "@react-three/drei";
import * as THREE from "three";
import { type ClusterData, CLUSTER_COLORS } from "../../types/phase-space";

export function ClusterShell({ cluster, colorMode, hasActive }: {
  cluster: ClusterData;
  colorMode: "cluster" | "type";
  hasActive: boolean;
}) {
  const color = CLUSTER_COLORS[cluster.id % CLUSTER_COLORS.length];
  const padding = 0.3;
  const baseOpacity = hasActive ? 0.015 : (colorMode === "cluster" ? 0.06 : 0.03);

  return (
    <group position={cluster.center}>
      <mesh>
        <sphereGeometry args={[cluster.radius + padding, 24, 24]} />
        <meshStandardMaterial color={color} transparent opacity={baseOpacity} side={THREE.BackSide} depthWrite={false} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[cluster.radius + padding - 0.02, cluster.radius + padding, 48]} />
        <meshBasicMaterial color={color} transparent opacity={hasActive ? 0.04 : 0.15} side={THREE.DoubleSide} />
      </mesh>
      <Html position={[0, cluster.radius + padding + 0.4, 0]} center distanceFactor={10} style={{ pointerEvents: "none" }}>
        <div style={{
          color, fontSize: "9px", fontFamily: "'Inter', system-ui, sans-serif",
          fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em",
          opacity: hasActive ? 0.25 : 0.7, whiteSpace: "nowrap",
          textShadow: "0 1px 6px rgba(0,0,0,1)", userSelect: "none",
        }}>
          {cluster.label} ({cluster.count})
        </div>
      </Html>
    </group>
  );
}
