/**
 * EdgeMesh.tsx — Ambient connectivity mesh rendered via THREE.LineSegments.
 *
 * Renders k-NN edges as translucent lines between proposition nodes.
 * This is Layer 1 (ambient mesh) of the three-layer edge system:
 *   L1: Ambient k-NN mesh (always visible, very low opacity) — THIS FILE
 *   L2: Retrieval connections (bright, shown during chat response) — B3
 *   L3: Dimension radials (shown in dimension mode) — B3
 *
 * Architecture:
 *   - Single THREE.LineSegments with BufferGeometry
 *   - Position attribute: Float32Array, 6 floats per edge (2 vertices × xyz)
 *   - Color attribute: Float32Array, 6 floats per edge (2 vertices × rgb)
 *   - Updated each frame to track node position lerps from NodeCloud
 *
 * Performance:
 *   ~1582 edges × 2 vertices = ~3164 vertices. One draw call.
 *   Position updates are O(edges) per frame — negligible at this count.
 *
 * BUG PREVENTION NOTES (Ralph review):
 *   - Edge vertex positions MUST track NodeCloud's lerped positions, not the
 *     static node.position/positionTime from props. Otherwise edges lag behind
 *     layout transitions. Solution: NodeCloud exports its state.curPos arrays
 *     ... except it doesn't (internal state). So EdgeMesh independently lerps
 *     node positions with the same lerp factor (0.08) for visual sync.
 *   - Edges reference nodes by ID. A Map<id, index> is built once per node
 *     array change to avoid O(n) lookups per edge per frame.
 *   - key={edges.length} forces remount when edge count changes.
 */

import { useRef, useMemo, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import {
  type PropositionNode,
  type EdgeData,
  type LayoutMode,
  getNodePosition,
  DIMENSION_COLORS,
  UNASSIGNED_COLOR,
  CLUSTER_COLORS,
  TYPE_COLORS,
  timeColor,
} from "../../types/phase-space";

// Pre-allocated scratch
const _color = new THREE.Color();

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface EdgeMeshProps {
  nodes: PropositionNode[];
  edges: EdgeData[];
  layoutMode: LayoutMode;
  retrievalIds: string[];
  hasActive: boolean;
}

export function EdgeMesh({
  nodes,
  edges,
  layoutMode,
  retrievalIds,
  hasActive,
}: EdgeMeshProps) {
  const lineRef = useRef<THREE.LineSegments>(null);
  const edgeCount = edges.length;

  // Node ID → array index for O(1) lookups in the frame loop.
  const idToIndex = useMemo(() => {
    const map = new Map<string, number>();
    for (let i = 0; i < nodes.length; i++) map.set(nodes[i].id, i);
    return map;
  }, [nodes]);

  const retrievalSet = useMemo(() => new Set(retrievalIds), [retrievalIds]);

  // -----------------------------------------------------------------------
  // Resolved edge pairs: [sourceIdx, targetIdx, weight] using node indices.
  // Computed once when edges or nodes change. Filters out edges with
  // unresolvable IDs (shouldn't happen, but defensive).
  // -----------------------------------------------------------------------
  const resolvedEdges = useMemo(() => {
    const result: { si: number; ti: number; w: number }[] = [];
    for (const e of edges) {
      const si = idToIndex.get(e.source);
      const ti = idToIndex.get(e.target);
      if (si !== undefined && ti !== undefined) {
        result.push({ si, ti, w: e.weight });
      }
    }
    return result;
  }, [edges, idToIndex]);

  const resolvedCount = resolvedEdges.length;

  // -----------------------------------------------------------------------
  // GPU buffers: position + color. 2 vertices per edge, 3 components each.
  // -----------------------------------------------------------------------
  const positionArray = useMemo(
    () => new Float32Array(resolvedCount * 6),
    [resolvedCount],
  );
  const colorArray = useMemo(
    () => new Float32Array(resolvedCount * 6),
    [resolvedCount],
  );

  // -----------------------------------------------------------------------
  // Position lerp state — mirrors NodeCloud's lerp for visual sync.
  // -----------------------------------------------------------------------
  const posState = useMemo(() => ({
    curX: new Float32Array(nodes.length),
    curY: new Float32Array(nodes.length),
    curZ: new Float32Array(nodes.length),
    tgtX: new Float32Array(nodes.length),
    tgtY: new Float32Array(nodes.length),
    tgtZ: new Float32Array(nodes.length),
  }), [nodes.length]);

  // Initialize positions
  useEffect(() => {
    for (let i = 0; i < nodes.length; i++) {
      const pos = getNodePosition(nodes[i], layoutMode);
      posState.curX[i] = pos[0];
      posState.curY[i] = pos[1];
      posState.curZ[i] = pos[2];
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes.length]);

  // Update targets when layout changes
  useEffect(() => {
    for (let i = 0; i < nodes.length; i++) {
      const pos = getNodePosition(nodes[i], layoutMode);
      posState.tgtX[i] = pos[0];
      posState.tgtY[i] = pos[1];
      posState.tgtZ[i] = pos[2];
    }
  }, [nodes, layoutMode, posState]);

  // -----------------------------------------------------------------------
  // Per-frame: lerp positions, write edge vertices + colors.
  // -----------------------------------------------------------------------
  useFrame(() => {
    const line = lineRef.current;
    if (!line || resolvedCount === 0) return;

    const lerp = 0.08;
    const geo = line.geometry;

    // Lerp node positions (same rate as NodeCloud)
    for (let i = 0; i < nodes.length; i++) {
      posState.curX[i] += (posState.tgtX[i] - posState.curX[i]) * lerp;
      posState.curY[i] += (posState.tgtY[i] - posState.curY[i]) * lerp;
      posState.curZ[i] += (posState.tgtZ[i] - posState.curZ[i]) * lerp;
    }

    // Write edge vertices + colors
    for (let e = 0; e < resolvedCount; e++) {
      const { si, ti, w } = resolvedEdges[e];
      const base = e * 6;

      // Vertex positions (source, target)
      positionArray[base] = posState.curX[si];
      positionArray[base + 1] = posState.curY[si];
      positionArray[base + 2] = posState.curZ[si];
      positionArray[base + 3] = posState.curX[ti];
      positionArray[base + 4] = posState.curY[ti];
      positionArray[base + 5] = posState.curZ[ti];

      // Edge color: blend of the two endpoint colors.
      // Use source node color for both vertices (simpler, nearly identical
      // for k-NN neighbors which tend to be same cluster/dimension).
      const node = nodes[si];
      let hex: string;
      if (layoutMode === "dimension") {
        hex = node.dimension
          ? DIMENSION_COLORS[node.dimension] ?? UNASSIGNED_COLOR
          : UNASSIGNED_COLOR;
      } else if (layoutMode === "time") {
        hex = timeColor(node.age);
      } else if (layoutMode === "cluster") {
        hex = node.cluster >= 0
          ? CLUSTER_COLORS[node.cluster % CLUSTER_COLORS.length]
          : "#999";
      } else {
        hex = TYPE_COLORS[node.nodeType] || "#888";
      }
      _color.set(hex);

      // Apply weight to alpha via color brightness (LineBasicMaterial
      // opacity is uniform, not per-vertex). Dim low-weight edges by
      // darkening the color. Weight range is ~[0.5, 0.95].
      // Remap to visual intensity: weight 0.5 → 0.5, weight 0.95 → 1.0
      let intensity = 0.5 + (w - 0.5) * (0.5 / 0.45);
      intensity = Math.max(0.45, Math.min(1.0, intensity));

      // When retrieval is active, dim ambient mesh but keep as context
      if (hasActive) intensity *= 0.5;

      const r = _color.r * intensity;
      const g = _color.g * intensity;
      const b = _color.b * intensity;

      colorArray[base] = r;
      colorArray[base + 1] = g;
      colorArray[base + 2] = b;
      colorArray[base + 3] = r;
      colorArray[base + 4] = g;
      colorArray[base + 5] = b;
    }

    // Flag for GPU upload
    const posAttr = geo.attributes.position as THREE.BufferAttribute;
    const colAttr = geo.attributes.color as THREE.BufferAttribute;
    posAttr.needsUpdate = true;
    colAttr.needsUpdate = true;
  });

  if (resolvedCount === 0) return null;

  return (
    <lineSegments key={resolvedCount} ref={lineRef} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positionArray, 3]}
          count={resolvedCount * 2}
        />
        <bufferAttribute
          attach="attributes-color"
          args={[colorArray, 3]}
          count={resolvedCount * 2}
        />
      </bufferGeometry>
      <lineBasicMaterial
        vertexColors
        transparent
        opacity={0.20}
        depthWrite={false}
      />
    </lineSegments>
  );
}
