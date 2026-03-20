import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { PhaseSpaceNode } from "../../types/phase-space";

/**
 * AnnotationBadges — small icon badges above nodes showing top annotation type.
 *
 * Only visible when camera is close (distance < 15 units).
 * Uses instanced rendering for performance.
 * Billboard rendering (always faces camera).
 */

// Annotation type colors
const BADGE_COLORS: Record<string, string> = {
  decision: "#c9a23c",     // gold
  commitment: "#4a9eff",   // cyan
  question: "#ff9a4a",     // orange
  emotion: "#ff6b6b",      // red
  belief: "#b8a0d8",       // purple
  topic: "#8a9ab0",        // gray
  default: "#8a9ab0",      // gray fallback
};

// Get top annotation by confidence (backend returns sorted)
function getTopAnnotation(node: PhaseSpaceNode) {
  if (node.annotations.length === 0) return null;
  return node.annotations[0];
}

// Get badge color for annotation type
function getBadgeColor(type: string): THREE.Color {
  const colorHex = BADGE_COLORS[type.toLowerCase()] || BADGE_COLORS.default;
  return new THREE.Color(colorHex);
}

interface AnnotationBadgesProps {
  nodes: PhaseSpaceNode[];
  cameraDistance: number;
}

export function AnnotationBadges({ nodes, cameraDistance }: AnnotationBadgesProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null!);
  const visibleRef = useRef(false);

  // Filter nodes that have annotations
  const annotatedNodes = useMemo(() => {
    return nodes.filter((node) => node.annotations.length > 0);
  }, [nodes]);

  // Badge visibility threshold
  const VISIBILITY_DISTANCE = 15;
  const isVisible = cameraDistance < VISIBILITY_DISTANCE;

  // Update instance matrices and colors
  useMemo(() => {
    if (!meshRef.current || annotatedNodes.length === 0) return;

    const dummy = new THREE.Object3D();
    const color = new THREE.Color();

    for (let i = 0; i < annotatedNodes.length; i++) {
      const node = annotatedNodes[i];
      const annotation = getTopAnnotation(node);
      if (!annotation) continue;

      const [x, y, z] = node.position;

      // Position badge above node (offset by 0.4 units)
      dummy.position.set(x, y + 0.4, z);
      dummy.scale.setScalar(0.2); // Small badge size
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);

      // Color by annotation type
      color.copy(getBadgeColor(annotation.type));
      meshRef.current.setColorAt(i, color);
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true;
    }
  }, [annotatedNodes]);

  // Billboard effect: make badges face camera
  useFrame(({ camera }) => {
    if (!meshRef.current || !isVisible) return;
    if (annotatedNodes.length === 0) return;

    const dummy = new THREE.Object3D();
    const cameraDir = new THREE.Vector3();

    for (let i = 0; i < annotatedNodes.length; i++) {
      const node = annotatedNodes[i];
      const [x, y, z] = node.position;

      dummy.position.set(x, y + 0.4, z);
      dummy.scale.setScalar(0.2);

      // Look at camera for billboard effect
      cameraDir.subVectors(camera.position, dummy.position).normalize();
      dummy.lookAt(camera.position);

      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  // Update visibility ref
  visibleRef.current = isVisible;

  if (annotatedNodes.length === 0 || !isVisible) return null;

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, annotatedNodes.length]}
      frustumCulled={false}
    >
      {/* Simple circle geometry for badges */}
      <circleGeometry args={[1, 16]} />
      <meshBasicMaterial
        vertexColors
        transparent
        opacity={0.9}
        depthWrite={false}
        side={THREE.DoubleSide}
      />
    </instancedMesh>
  );
}
