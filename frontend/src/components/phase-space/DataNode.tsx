import { useState, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import {
  type PropositionNode, type LayoutMode,
  TYPE_COLORS, CLUSTER_COLORS, DIMENSION_COLORS, UNASSIGNED_COLOR,
  timeColor, getNodePosition,
} from "../../types/phase-space";

export function DataNode({ node, relevance, layoutMode, hasActive }: {
  node: PropositionNode;
  relevance: number;
  layoutMode: LayoutMode;
  hasActive: boolean;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.MeshStandardMaterial>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const isActive = relevance > 0.3;
  const isResidual = relevance > 0 && relevance <= 0.3;

  let targetScale: number;
  let targetOpacity: number;
  let targetEmissive: number;
  let targetGlowScale: number;
  let targetGlowOpacity: number;

  if (isActive) {
    targetScale = 0.25 + relevance * 0.25;
    targetOpacity = 0.95;
    targetEmissive = 0.3 + relevance * 0.4;
    targetGlowScale = targetScale * 2.2;
    targetGlowOpacity = 0.12 + relevance * 0.08;
  } else if (isResidual) {
    targetScale = 0.12 + relevance * 0.12;
    targetOpacity = hasActive ? 0.4 : 0.65 + relevance * 0.2;
    targetEmissive = hasActive ? 0.08 : 0.15 + relevance * 0.2;
    targetGlowScale = 0;
    targetGlowOpacity = 0;
  } else if (hasActive) {
    targetScale = 0.07;
    targetOpacity = 0.18;
    targetEmissive = 0.03;
    targetGlowScale = 0;
    targetGlowOpacity = 0;
  } else {
    targetScale = 0.15;
    targetOpacity = 0.75;
    targetEmissive = 0.12;
    targetGlowScale = 0;
    targetGlowOpacity = 0;
  }

  // Hover boost
  if (hovered && !hasActive) {
    targetScale *= 1.3;
    targetEmissive += 0.15;
    targetOpacity = Math.min(targetOpacity + 0.15, 1);
  }

  const showLabel = isActive || (hovered && !hasActive) || (hovered && isActive);
  const labelOpacity = isActive ? 0.85 + relevance * 0.15 : hovered ? 0.75 : 0;

  useFrame(() => {
    if (!meshRef.current || !materialRef.current) return;
    const lerp = 0.08;
    const s = meshRef.current.scale.x;
    meshRef.current.scale.setScalar(s + (targetScale - s) * lerp);
    materialRef.current.opacity += (targetOpacity - materialRef.current.opacity) * lerp;
    materialRef.current.emissiveIntensity += (targetEmissive - materialRef.current.emissiveIntensity) * lerp;

    // Glow ring animation
    if (glowRef.current) {
      const gs = glowRef.current.scale.x;
      const gMat = (glowRef.current as THREE.Mesh).material as THREE.MeshBasicMaterial;
      glowRef.current.scale.setScalar(gs + (targetGlowScale - gs) * lerp);
      gMat.opacity += (targetGlowOpacity - gMat.opacity) * lerp;
    }

    // Animate position transitions between layouts
    if (groupRef.current) {
      const target = getNodePosition(node, layoutMode);
      groupRef.current.position.x += (target[0] - groupRef.current.position.x) * lerp;
      groupRef.current.position.y += (target[1] - groupRef.current.position.y) * lerp;
      groupRef.current.position.z += (target[2] - groupRef.current.position.z) * lerp;
    }
  });

  const color = layoutMode === "dimension"
    ? (node.dimension ? DIMENSION_COLORS[node.dimension] ?? UNASSIGNED_COLOR : UNASSIGNED_COLOR)
    : layoutMode === "time"
      ? timeColor(node.age)
      : layoutMode === "cluster"
        ? (node.cluster >= 0 ? CLUSTER_COLORS[node.cluster % CLUSTER_COLORS.length] : "#999")
        : (TYPE_COLORS[node.nodeType] || "#888");

  const initialPos = getNodePosition(node, layoutMode);

  return (
    <group ref={groupRef} position={initialPos}>
      {/* Glow aura for active/retrieved nodes */}
      <mesh ref={glowRef} scale={0}>
        <sphereGeometry args={[0.18, 16, 16]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0}
          depthWrite={false}
        />
      </mesh>

      {/* Main sphere — 3D material */}
      <mesh
        ref={meshRef}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); }}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[0.18, 24, 24]} />
        <meshStandardMaterial
          ref={materialRef}
          color={color}
          emissive={color}
          emissiveIntensity={0.05}
          transparent
          opacity={0.2}
          roughness={0.35}
          metalness={0.15}
        />
      </mesh>

      {/* Label */}
      {showLabel && (
        <Html position={[0, 0.35, 0]} center distanceFactor={8} style={{ pointerEvents: "none" }}>
          <div style={{
            color: "#2c2620",
            fontSize: isActive ? "11px" : "10px",
            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
            fontWeight: isActive ? 500 : 400,
            opacity: labelOpacity,
            whiteSpace: "nowrap",
            maxWidth: "280px",
            overflow: "hidden",
            textOverflow: "ellipsis",
            textShadow: "0 1px 4px rgba(245,240,232,0.9), 0 0 8px rgba(245,240,232,0.7)",
            userSelect: "none",
          }}>
            {node.label}
            <span style={{
              color: "#99907f",
              fontSize: "9px",
              marginLeft: "6px",
              fontFamily: "'IBM Plex Mono', monospace",
            }}>
              [{node.nodeType}]
            </span>
          </div>
        </Html>
      )}
    </group>
  );
}
