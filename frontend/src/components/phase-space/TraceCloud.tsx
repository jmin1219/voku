import { useRef, useMemo, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { PhaseSpaceNode } from "../../types/phase-space";

/**
 * TraceCloud — InstancedMesh rendering for all trace nodes.
 *
 * Single draw call for all nodes. Per-instance:
 *   - Position from UMAP
 *   - Color from recency (gold → slate)
 *   - Scale from source type (user=sphere implicit, all same geometry)
 *   - Emissive boost for retrieved traces (glow)
 *
 * Performance: 500 nodes = 1 draw call, 60fps.
 */

const WARM = new THREE.Color("#e8c84a"); // bright gold — recent
const COOL = new THREE.Color("#8a9ab0"); // light slate — old
const GLOW = new THREE.Color("#ffe066"); // vivid gold — retrieved
const BASE_SIZE = 0.22;

interface TraceCloudProps {
  nodes: PhaseSpaceNode[];
  retrievalIds: string[];
  focusedId: string | null;
  onNodeClick?: (id: string) => void;
  onNodeHover?: (id: string | null) => void;
}

export function TraceCloud({
  nodes,
  retrievalIds,
  focusedId,
  onNodeClick,
  onNodeHover,
}: TraceCloudProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null!);
  const glowRef = useRef<Float32Array>(null!);
  const targetGlowRef = useRef<Float32Array>(null!);

  const retrievalSet = useMemo(() => new Set(retrievalIds), [retrievalIds]);

  // Initialize glow arrays
  useMemo(() => {
    glowRef.current = new Float32Array(nodes.length).fill(0);
    targetGlowRef.current = new Float32Array(nodes.length).fill(0);
  }, [nodes.length]);

  // Set instance matrices + colors
  useEffect(() => {
    if (!meshRef.current || nodes.length === 0) return;

    const dummy = new THREE.Object3D();
    const color = new THREE.Color();

    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      const [x, y, z] = node.position;

      // Size: assistant slightly smaller
      const size = node.source === "assistant" ? BASE_SIZE * 0.8 : BASE_SIZE;
      dummy.position.set(x, y, z);
      dummy.scale.setScalar(size);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);

      // Color: lerp warm→cool based on age (1=newest=warm, 0=oldest=cool)
      color.copy(COOL).lerp(WARM, node.age);
      meshRef.current.setColorAt(i, color);
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true;
    }
  }, [nodes]);

  // Update glow targets when retrieval changes
  useEffect(() => {
    if (!targetGlowRef.current) return;
    for (let i = 0; i < nodes.length; i++) {
      targetGlowRef.current[i] = retrievalSet.has(nodes[i].id) ? 1.0 : 0.0;
    }
  }, [nodes, retrievalSet]);

  // Animate glow fade per frame
  useFrame(() => {
    if (!meshRef.current || !glowRef.current || !targetGlowRef.current) return;
    if (nodes.length === 0) return;

    const color = new THREE.Color();
    let needsUpdate = false;

    for (let i = 0; i < nodes.length; i++) {
      const target = targetGlowRef.current[i];
      const current = glowRef.current[i];

      // Lerp toward target (fast attack, slow decay)
      const speed = target > current ? 0.15 : 0.02;
      const next = current + (target - current) * speed;
      if (Math.abs(next - current) > 0.001) {
        glowRef.current[i] = next;
        needsUpdate = true;
      }

      // Focus dimming
      const focusDim =
        focusedId && focusedId !== nodes[i].id ? 0.25 : 1.0;

      // Base color from age
      color.copy(COOL).lerp(WARM, nodes[i].age);

      // Add glow
      if (next > 0.01) {
        color.lerp(GLOW, next * 0.6);
      }

      // Apply focus dimming
      color.multiplyScalar(focusDim);

      meshRef.current.setColorAt(i, color);
    }

    if (needsUpdate && meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true;
    }
  });

  // Raycasting for hover/click
  const handlePointerMove = (e: THREE.Event) => {
    // @ts-expect-error — R3F event typing
    const instanceId = e.instanceId;
    if (instanceId !== undefined && instanceId < nodes.length) {
      onNodeHover?.(nodes[instanceId].id);
    }
    // @ts-expect-error
    e.stopPropagation?.();
  };

  const handlePointerOut = () => {
    onNodeHover?.(null);
  };

  const handleClick = (e: THREE.Event) => {
    // @ts-expect-error
    const instanceId = e.instanceId;
    if (instanceId !== undefined && instanceId < nodes.length) {
      onNodeClick?.(nodes[instanceId].id);
    }
    // @ts-expect-error
    e.stopPropagation?.();
  };

  if (nodes.length === 0) return null;

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, nodes.length]}
      onPointerMove={handlePointerMove}
      onPointerOut={handlePointerOut}
      onClick={handleClick}
    >
      <sphereGeometry args={[1, 12, 8]} />
      <meshStandardMaterial
        vertexColors
        roughness={0.4}
        metalness={0.2}
        emissive="#c9a23c"
        emissiveIntensity={0.6}
      />
    </instancedMesh>
  );
}
