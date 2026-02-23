import { Html } from "@react-three/drei";
import * as THREE from "three";
import { type ClusterData, type LayoutMode, CLUSTER_COLORS } from "../../types/phase-space";

export function ClusterShell({ cluster, layoutMode, hasActive }: {
  cluster: ClusterData;
  layoutMode: LayoutMode;
  hasActive: boolean;
}) {
  const color = CLUSTER_COLORS[cluster.id % CLUSTER_COLORS.length];
  const padding = 0.3;
  const maxRadius = 3.0; // Cap so no single cluster shell dominates the scene
  const radius = Math.min(cluster.radius + padding, maxRadius);
  const baseOpacity = hasActive ? 0.03 : (layoutMode === "cluster" ? 0.08 : 0.04);

  return (
    <group position={cluster.center}>
      <mesh>
        <sphereGeometry args={[radius, 24, 24]} />
        <meshStandardMaterial color={color} transparent opacity={baseOpacity} side={THREE.BackSide} depthWrite={false} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[radius - 0.02, radius, 48]} />
        <meshBasicMaterial color={color} transparent opacity={hasActive ? 0.04 : 0.15} side={THREE.DoubleSide} />
      </mesh>
      <Html position={[0, radius + 0.4, 0]} center distanceFactor={10} style={{ pointerEvents: "none" }}>
        <div style={{
          color, fontSize: "9px", fontFamily: "'IBM Plex Mono', monospace",
          fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.08em",
          opacity: hasActive ? 0.3 : 0.65, whiteSpace: "nowrap",
          textShadow: "0 1px 4px rgba(245,240,232,0.8)", userSelect: "none",
        }}>
          {cluster.label} ({cluster.count})
        </div>
      </Html>
    </group>
  );
}
