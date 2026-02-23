import { useRef, useEffect } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { type PropositionNode, getNodePosition, type LayoutMode } from "../../types/phase-space";

export function CameraController({ nodes, relevanceMap, layoutMode }: {
  nodes: PropositionNode[];
  relevanceMap: Map<string, number>;
  layoutMode?: LayoutMode;
}) {
  const { camera } = useThree();
  const controlsRef = useRef<any>(null);
  const targetPos = useRef(new THREE.Vector3(0, 0, 14));
  const targetLookAt = useRef(new THREE.Vector3(0, 0, 0));
  const isAnimating = useRef(false);
  const layout = layoutMode || "cluster";

  useEffect(() => {
    const activeNodes = nodes.filter((n) => (relevanceMap.get(n.id) || 0) > 0.3);

    if (activeNodes.length === 0) {
      targetPos.current.set(0, 0, 14);
      targetLookAt.current.set(0, 0, 0);
    } else {
      const positions = activeNodes.map((n) => getNodePosition(n, layout));
      const min = [Infinity, Infinity, Infinity];
      const max = [-Infinity, -Infinity, -Infinity];
      for (const p of positions) {
        for (let i = 0; i < 3; i++) {
          min[i] = Math.min(min[i], p[i]);
          max[i] = Math.max(max[i], p[i]);
        }
      }

      const center = new THREE.Vector3(
        (min[0] + max[0]) / 2,
        (min[1] + max[1]) / 2,
        (min[2] + max[2]) / 2,
      );

      const spread = Math.max(
        max[0] - min[0],
        max[1] - min[1],
        max[2] - min[2],
        2,
      );
      const distance = spread * 1.8 + 2;

      targetPos.current.set(center.x, center.y, center.z + distance);
      targetLookAt.current.copy(center);
    }

    isAnimating.current = true;
  }, [relevanceMap, nodes, layout]);

  useFrame(() => {
    if (!isAnimating.current) return;

    camera.position.lerp(targetPos.current, 0.04);
    if (controlsRef.current) {
      controlsRef.current.target.lerp(targetLookAt.current, 0.04);
      controlsRef.current.update();
    }

    const posDist = camera.position.distanceTo(targetPos.current);
    const lookDist = controlsRef.current
      ? controlsRef.current.target.distanceTo(targetLookAt.current)
      : 0;
    if (posDist < 0.01 && lookDist < 0.01) {
      isAnimating.current = false;
    }
  });

  return <OrbitControls ref={controlsRef} enableDamping dampingFactor={0.05} minDistance={2} maxDistance={30} />;
}
