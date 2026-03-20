import { Html } from "@react-three/drei";
import type { PhaseSpaceCluster } from "../../types/phase-space";

/**
 * ClusterLabels — Floating text labels at each cluster center.
 *
 * Replaces translucent sphere shells. Labels float in 3D space,
 * always face the camera, show the cluster keyword summary + count.
 * Only renders clusters with a real LLM-generated label (not noise).
 */

interface ClusterCloudProps {
  clusters: PhaseSpaceCluster[];
}

export function ClusterCloud({ clusters }: ClusterCloudProps) {
  // Only show clusters with a meaningful label and enough members
  const labeled = clusters.filter(
    (c) => c.label && c.label.trim().length > 0 && c.count >= 3
  );

  return (
    <group>
      {labeled.map((cluster) => (
        <Html
          key={cluster.id}
          position={[
            cluster.center[0],
            cluster.center[1] + cluster.radius + 0.4,
            cluster.center[2],
          ]}
          center
          style={{ pointerEvents: "none" }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 2,
              userSelect: "none",
            }}
          >
            <div
              style={{
                fontSize: "10px",
                fontFamily: "var(--voku-font-mono, monospace)",
                color: "rgba(201, 162, 60, 0.7)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                whiteSpace: "nowrap",
                textShadow: "0 0 8px rgba(201, 162, 60, 0.4)",
              }}
            >
              {cluster.label}
            </div>
            <div
              style={{
                fontSize: "9px",
                fontFamily: "var(--voku-font-mono, monospace)",
                color: "rgba(201, 162, 60, 0.35)",
                letterSpacing: "0.05em",
              }}
            >
              {cluster.count}
            </div>
          </div>
        </Html>
      ))}
    </group>
  );
}
