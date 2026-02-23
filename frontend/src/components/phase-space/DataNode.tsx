import { useState, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { type FixtureNode, TYPE_COLORS, CLUSTER_COLORS } from "../../types/phase-space";

export function DataNode({ node, relevance, colorMode, hasActive }: {
  node: FixtureNode;
  relevance: number;
  colorMode: "cluster" | "type";
  hasActive: boolean;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.MeshStandardMaterial>(null);
  const [hovered, setHovered] = useState(false);

  const isActive = relevance > 0.3;
  const isResidual = relevance > 0 && relevance <= 0.3;

  let targetScale: number;
  let targetOpacity: number;
  let targetEmissive: number;

  if (isActive) {
    targetScale = 0.3 + relevance * 0.35;
    targetOpacity = 1;
    targetEmissive = 0.6 + relevance * 0.6;
  } else if (isResidual) {
    targetScale = 0.12 + relevance * 0.15;
    targetOpacity = hasActive ? 0.25 : 0.5 + relevance * 0.3;
    targetEmissive = hasActive ? 0.08 : 0.15 + relevance * 0.3;
  } else if (hasActive) {
    targetScale = 0.06;
    targetOpacity = 0.08;
    targetEmissive = 0.02;
  } else {
    targetScale = 0.18;
    targetOpacity = 0.55;
    targetEmissive = 0.25;
  }

  const showLabel = isActive || (hovered && !hasActive) || (hovered && isActive);
  const labelOpacity = isActive ? 0.8 + relevance * 0.2 : hovered ? 0.65 : 0;

  useFrame(() => {
    if (!meshRef.current || !materialRef.current) return;
    const lerp = 0.06;
    const s = meshRef.current.scale.x;
    meshRef.current.scale.setScalar(s + (targetScale - s) * lerp);
    materialRef.current.opacity += (targetOpacity - materialRef.current.opacity) * lerp;
    materialRef.current.emissiveIntensity += (targetEmissive - materialRef.current.emissiveIntensity) * lerp;
  });

  const color = colorMode === "cluster"
    ? (node.cluster >= 0 ? CLUSTER_COLORS[node.cluster % CLUSTER_COLORS.length] : "#555")
    : (TYPE_COLORS[node.nodeType] || "#888");

  return (
    <mesh ref={meshRef} position={node.position}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); }}
      onPointerOut={() => setHovered(false)}
    >
      <sphereGeometry args={[0.18, 16, 16]} />
      <meshStandardMaterial ref={materialRef} color={color} emissive={color}
        emissiveIntensity={0.05} transparent opacity={0.2} />
      {showLabel && (
        <Html position={[0, 0.3, 0]} center distanceFactor={8} style={{ pointerEvents: "none" }}>
          <div style={{
            color, fontSize: isActive ? "11px" : "10px",
            fontFamily: "'Inter', system-ui, sans-serif", fontWeight: isActive ? 500 : 400,
            opacity: labelOpacity, whiteSpace: "nowrap", maxWidth: "280px",
            overflow: "hidden", textOverflow: "ellipsis",
            textShadow: "0 1px 4px rgba(0,0,0,1), 0 0 12px rgba(0,0,0,0.8)", userSelect: "none",
          }}>
            {node.label}
            <span style={{ color: "#666", fontSize: "9px", marginLeft: "6px" }}>[{node.nodeType}]</span>
          </div>
        </Html>
      )}
    </mesh>
  );
}
