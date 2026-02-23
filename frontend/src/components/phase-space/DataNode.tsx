import { useState, useRef, useMemo } from "react";
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

  // dimensionRelevance: 0.0 (unassigned/peripheral) → ~1.0 (core belief)
  // Smooth lerp creates visual hierarchy: dust → body → anchor
  const dr = node.dimensionRelevance;

  // Breathing: deterministic phase offset from node ID so nodes don't pulse in sync
  const phaseOffset = useMemo(() => {
    let hash = 0;
    for (let i = 0; i < node.id.length; i++) {
      hash = ((hash << 5) - hash + node.id.charCodeAt(i)) | 0;
    }
    return (Math.abs(hash) % 1000) / 1000 * Math.PI * 2;
  }, [node.id]);

  // Breathing parameters driven by confidence (dimensionRelevance as proxy)
  // High confidence → slow deep breath; low → fast shallow
  const breathPeriod = 3.0 + dr * 3.0;       // 3s (low) → 6s (high)
  const breathAmplitude = 0.03 + dr * 0.05;   // ±3% (low) → ±8% (high)
  const emissivePulse = 0.01 + dr * 0.03;     // subtle luminance sync


  let targetScale: number;
  let targetOpacity: number;
  let targetEmissive: number;
  let targetGlowScale: number;
  let targetGlowOpacity: number;

  if (isActive) {
    targetScale = 0.45 + relevance * 0.45;
    targetOpacity = 0.95;
    targetEmissive = 0.3 + relevance * 0.4;
    targetGlowScale = targetScale * 2.2;
    targetGlowOpacity = 0.12 + relevance * 0.08;
  } else if (isResidual) {
    targetScale = 0.22 + relevance * 0.22;
    targetOpacity = hasActive ? 0.4 : 0.65 + relevance * 0.2;
    targetEmissive = hasActive ? 0.08 : 0.15 + relevance * 0.2;
    targetGlowScale = 0;
    targetGlowOpacity = 0;
  } else if (hasActive) {
    // Dimmed during active retrieval — but preserve size hierarchy
    targetScale = 0.10 + dr * 0.14;        // 0.10 (dust) → 0.24 (anchor)
    targetOpacity = 0.15 + dr * 0.08;      // 0.15 → 0.23
    targetEmissive = 0.02 + dr * 0.04;     // 0.02 → 0.06
    targetGlowScale = 0;
    targetGlowOpacity = 0;
  } else {
    // Resting state — size communicates importance to user model
    targetScale = 0.18 + dr * 0.27;        // 0.18 (dust) → 0.45 (anchor)
    targetOpacity = 0.55 + dr * 0.30;      // 0.55 → 0.85
    targetEmissive = 0.06 + dr * 0.12;     // 0.06 → 0.18
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

  useFrame(({ clock }) => {
    if (!meshRef.current || !materialRef.current) return;
    const lerp = 0.08;
    const t = clock.getElapsedTime();

    // Breathing: sine wave modulates scale and emissive around their targets
    // Only breathe in resting/dimmed states — retrieved nodes stay solid
    const breathActive = !isActive && !isResidual;
    const breath = breathActive
      ? Math.sin((t * Math.PI * 2) / breathPeriod + phaseOffset)
      : 0;
    const scaleWithBreath = targetScale * (1 + breath * breathAmplitude);
    const emissiveWithBreath = targetEmissive + breath * emissivePulse;

    const s = meshRef.current.scale.x;
    meshRef.current.scale.setScalar(s + (scaleWithBreath - s) * lerp);
    materialRef.current.opacity += (targetOpacity - materialRef.current.opacity) * lerp;
    materialRef.current.emissiveIntensity += (emissiveWithBreath - materialRef.current.emissiveIntensity) * lerp;

    // Glow ring animation
    if (glowRef.current) {
      const gs = glowRef.current.scale.x;
      const gMat = (glowRef.current as THREE.Mesh).material as THREE.MeshBasicMaterial;
      glowRef.current.scale.setScalar(gs + (targetGlowScale - gs) * lerp);
      gMat.opacity += (targetGlowOpacity - gMat.opacity) * lerp;
    }

    // Animate position transitions between layouts + float
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
          emissiveIntensity={0.15}
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
            color: "#e0dbd0",
            fontSize: isActive ? "11px" : "10px",
            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
            fontWeight: isActive ? 500 : 400,
            opacity: labelOpacity,
            whiteSpace: "nowrap",
            maxWidth: "280px",
            overflow: "hidden",
            textOverflow: "ellipsis",
            textShadow: "0 1px 4px rgba(0,0,0,0.6), 0 0 8px rgba(0,0,0,0.4)",
            userSelect: "none",
          }}>
            {node.label}
            <span style={{
              color: "#8a8578",
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
