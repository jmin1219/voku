import { useMemo, useRef, useEffect } from "react";
import * as THREE from "three";
import type { PhaseSpaceNode, PhaseSpaceEdge } from "../../types/phase-space";

/**
 * EdgeMesh — k-NN edges as LineSegments.
 *
 * Renders all edges in a single draw call using BufferGeometry.
 * Edges connecting retrieved nodes brighten subtly.
 */

const EDGE_COLOR = new THREE.Color("#8a9ab0");
const EDGE_GLOW = new THREE.Color("#e8c84a");
const BASE_OPACITY = 0.25;
const GLOW_OPACITY = 0.5;

interface EdgeMeshProps {
  nodes: PhaseSpaceNode[];
  edges: PhaseSpaceEdge[];
  retrievalIds: string[];
}

export function EdgeMesh({ nodes, edges, retrievalIds }: EdgeMeshProps) {
  const lineRef = useRef<THREE.LineSegments>(null!);

  const nodePositions = useMemo(() => {
    const map = new Map<string, [number, number, number]>();
    for (const node of nodes) {
      map.set(node.id, node.position);
    }
    return map;
  }, [nodes]);

  const retrievalSet = useMemo(() => new Set(retrievalIds), [retrievalIds]);

  // Build geometry
  useEffect(() => {
    if (!lineRef.current || edges.length === 0) return;

    const positions = new Float32Array(edges.length * 6); // 2 vertices × 3 coords
    const colors = new Float32Array(edges.length * 6); // 2 vertices × 3 color channels
    let idx = 0;
    let cidx = 0;

    for (const edge of edges) {
      const posA = nodePositions.get(edge.source);
      const posB = nodePositions.get(edge.target);
      if (!posA || !posB) continue;

      positions[idx++] = posA[0];
      positions[idx++] = posA[1];
      positions[idx++] = posA[2];
      positions[idx++] = posB[0];
      positions[idx++] = posB[1];
      positions[idx++] = posB[2];

      // Color: glow if either endpoint is retrieved
      const isGlow =
        retrievalSet.has(edge.source) || retrievalSet.has(edge.target);
      const color = isGlow ? EDGE_GLOW : EDGE_COLOR;

      colors[cidx++] = color.r;
      colors[cidx++] = color.g;
      colors[cidx++] = color.b;
      colors[cidx++] = color.r;
      colors[cidx++] = color.g;
      colors[cidx++] = color.b;
    }

    const geom = lineRef.current.geometry as THREE.BufferGeometry;
    geom.setAttribute("position", new THREE.BufferAttribute(positions.slice(0, idx), 3));
    geom.setAttribute("color", new THREE.BufferAttribute(colors.slice(0, cidx), 3));
    geom.computeBoundingSphere();
  }, [edges, nodePositions, retrievalSet]);

  const opacity = retrievalIds.length > 0 ? GLOW_OPACITY : BASE_OPACITY;

  if (edges.length === 0) return null;

  return (
    <lineSegments ref={lineRef}>
      <bufferGeometry />
      <lineBasicMaterial
        vertexColors
        transparent
        opacity={opacity}
        depthWrite={false}
      />
    </lineSegments>
  );
}
