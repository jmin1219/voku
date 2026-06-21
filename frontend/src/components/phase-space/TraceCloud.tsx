import { useRef, useMemo, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { PhaseSpaceNode, PhaseSpaceEdge } from "../../types/phase-space";

/**
 * TraceCloud — InstancedMesh rendering for all trace nodes.
 *
 * meshBasicMaterial: ignores lighting, vertex colors render at full value.
 * Color = cluster membership. Brightness = age (older = dimmer). Glow = retrieval.
 * Static at rest — no ambient animation.
 */

// Cluster-based colors — BRIGHT, designed for dark background
// These need to be light enough to read against #080810
const CLUSTER_COLORS = [
  "#7eb8d4", // bright sky blue
  "#e8934a", // vivid orange
  "#72c47a", // bright green
  "#c47ab0", // bright rose
  "#a8b85a", // bright olive
  "#6aaed4", // cornflower blue
  "#d4944a", // amber
  "#5ac8c8", // bright teal
  "#a87ad4", // bright violet
  "#88c460", // lime green
  "#d45880", // hot rose
  "#60a880", // seafoam
].map(hex => new THREE.Color(hex));

const NOISE_COLOR = new THREE.Color("#6a6a7a"); // ungrouped — medium grey
const GLOW = new THREE.Color("#ffe066"); // vivid gold — retrieved

function getClusterColor(cluster: number): THREE.Color {
  if (cluster === -1) return NOISE_COLOR;
  return CLUSTER_COLORS[cluster % CLUSTER_COLORS.length];
}

function getBaseSize(count: number): number {
  if (count <= 10) return 0.45;
  if (count <= 50) return 0.35;
  if (count <= 150) return 0.28;
  if (count <= 300) return 0.22;
  return 0.18; // 800+ nodes — still clearly visible
}

function getSphereDetail(count: number): [number, number] {
  // High detail is trivially cheap up to a few hundred instances; only drop to
  // low-poly for very large graphs where the per-node screen size is tiny.
  if (count <= 300) return [32, 24];
  if (count <= 800) return [16, 12];
  return [8, 6];
}

interface TraceCloudProps {
  nodes: PhaseSpaceNode[];
  edges: PhaseSpaceEdge[];
  retrievalIds: string[];
  currentConversationId: string | null;
  focusedId: string | null;
  hoveredId: string | null;
  onNodeClick?: (id: string) => void;
  onNodeHover?: (id: string | null) => void;
}

export function TraceCloud({
  nodes,
  edges: _edges, // accepted but not used at rest — reserved for hover ripple
  retrievalIds,
  currentConversationId,
  focusedId,
  hoveredId: _hoveredId, // accepted but not used at rest
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

  const baseSize = useMemo(() => getBaseSize(nodes.length), [nodes.length]);
  const sphereDetail = useMemo(() => getSphereDetail(nodes.length), [nodes.length]);

  // Set instance matrices + colors
  useEffect(() => {
    if (!meshRef.current || nodes.length === 0) return;

    const dummy = new THREE.Object3D();
    const color = new THREE.Color();

    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      const [x, y, z] = node.position;
      const isCurrentSession = node.conversationId === currentConversationId;

      // Current session nodes are 1.3x bigger
      const sizeMult = isCurrentSession ? 1.3 : 1.0;
      // Deterministic per-node jitter (hash of index → stable, no flicker) so
      // co-located same-cluster traces separate into distinct, countable spheres
      // instead of merging into one mushy blob.
      const hsh = (i * 2654435761) >>> 0;
      const jit = baseSize * 2.6;
      const jx = ((hsh & 0xff) / 255 - 0.5) * jit;
      const jy = (((hsh >> 8) & 0xff) / 255 - 0.5) * jit;
      const jz = (((hsh >> 16) & 0xff) / 255 - 0.5) * jit;
      dummy.position.set(x + jx, y + jy, z + jz);
      dummy.scale.setScalar(baseSize * sizeMult * 0.62);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);

      // Color by cluster — same brightness for all, current session is larger
      color.copy(getClusterColor(node.cluster));
      meshRef.current.setColorAt(i, color);
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true;
    }
  }, [nodes, baseSize, currentConversationId]);

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
    for (let i = 0; i < nodes.length; i++) {
      const target = targetGlowRef.current[i];
      const current = glowRef.current[i];

      // Lerp toward target (fast attack, slow decay)
      const speed = target > current ? 0.15 : 0.02;
      const next = current + (target - current) * speed;
      if (Math.abs(next - current) > 0.001) {
        glowRef.current[i] = next;
      }

      const node = nodes[i];
      // Selected node emphasis: dim the rest, but keep them clearly readable
      // (0.25 blacked out bright cluster colours on the dark background).
      const focusDim = focusedId && focusedId !== node.id ? 0.6 : 1.0;

      // Color by cluster — flat brightness, size differentiates current session
      color.copy(getClusterColor(node.cluster));

      // Retrieval glow overrides base color toward gold
      if (next > 0.01) {
        color.lerp(GLOW, next * 0.7);
      }

      color.multiplyScalar(focusDim);

      meshRef.current.setColorAt(i, color);
    }

    if (meshRef.current.instanceColor) {
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
      key={`traces-${sphereDetail[0]}-${nodes.length}`}
      ref={meshRef}
      args={[undefined, undefined, nodes.length]}
      onPointerMove={handlePointerMove}
      onPointerOut={handlePointerOut}
      onClick={handleClick}
    >
      <sphereGeometry args={[1, sphereDetail[0], sphereDetail[1]]} />
      {/* No `vertexColors`: InstancedMesh per-instance colour comes from
          `instanceColor` (setColorAt). With `vertexColors` the shader reads the
          geometry's (absent) colour attribute and multiplies every node to black. */}
      <meshBasicMaterial />
    </instancedMesh>
  );
}
