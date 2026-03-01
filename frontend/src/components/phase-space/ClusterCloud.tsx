import { useMemo } from "react";
import * as THREE from "three";
import type { PhaseSpaceCluster } from "../../types/phase-space";

/**
 * ClusterCloud — Translucent shells around cluster boundaries.
 *
 * Soft spheres at cluster centers, radius from API.
 * Hover shows label + count. Visual grouping without hard borders.
 */

const CLUSTER_COLORS = [
  "#6b8cae", "#8a7b6b", "#7a9a6b", "#9a7b8a", "#8a9a6b",
  "#6b7a9a", "#9a8a6b", "#6b9a8a", "#8a6b9a", "#6b8a6b",
];

interface ClusterCloudProps {
  clusters: PhaseSpaceCluster[];
  onClusterHover?: (id: number | null) => void;
  onClusterClick?: (id: number) => void;
}

export function ClusterCloud({
  clusters,
  onClusterHover,
  onClusterClick,
}: ClusterCloudProps) {
  const shells = useMemo(
    () =>
      clusters.map((cluster) => ({
        ...cluster,
        color: new THREE.Color(
          CLUSTER_COLORS[cluster.id % CLUSTER_COLORS.length]
        ),
      })),
    [clusters]
  );

  return (
    <group>
      {shells.map((shell) => (
        <mesh
          key={shell.id}
          position={shell.center}
          onPointerEnter={() => onClusterHover?.(shell.id)}
          onPointerLeave={() => onClusterHover?.(null)}
          onClick={() => onClusterClick?.(shell.id)}
        >
          <sphereGeometry args={[shell.radius, 16, 12]} />
          <meshStandardMaterial
            color={shell.color}
            transparent
            opacity={0.1}
            roughness={1}
            depthWrite={false}
            side={THREE.BackSide}
          />
        </mesh>
      ))}
    </group>
  );
}
