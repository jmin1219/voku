import { useMemo, useRef, useEffect } from "react";
import * as THREE from "three";
import type { PhaseSpaceNode, PhaseSpaceEdge } from "../../types/phase-space";

/**
 * EdgeMesh — k-NN edges as curved bezier arcs.
 *
 * Each edge is a quadratic bezier curve (5 points = 4 segments per edge),
 * all assembled into a single LineSegments draw call.
 * The midpoint is displaced perpendicular to the edge, creating soft arcs
 * that feel organic rather than a rigid wire grid.
 *
 * Retrieved edges glow gold. Non-retrieved edges are dim blue-grey.
 */

// Base edge colors by connection type
const EDGE_TEMPORAL     = new THREE.Color("#c9a23c"); // warm amber — conversation flow
const EDGE_TEMPORAL_MID = new THREE.Color("#e8c84a"); // brighter amber at arc peak
const EDGE_SEMANTIC     = new THREE.Color("#2a3a50"); // cool blue — similarity (default k-NN)
const EDGE_SEMANTIC_MID = new THREE.Color("#1a2535"); // darker at midpoint
const EDGE_GLOW         = new THREE.Color("#ffe066"); // vivid gold — retrieved (brightest)
const EDGE_GLOW_MID     = new THREE.Color("#fff4b3"); // brightest gold at arc peak

// Only render edges above this weight threshold — eliminates weak noise connections
const WEIGHT_THRESHOLD = 0.45;

const CURVE_SEGMENTS = 4; // points per bezier = 5, segments = 4

// Adaptive opacity — tuned for dark background
function getEdgeOpacity(edgeCount: number, hasRetrieval: boolean): number {
  const base = edgeCount <= 50  ? 0.55
    : edgeCount <= 200  ? 0.40
    : edgeCount <= 1000 ? 0.28
    : 0.20;
  return hasRetrieval ? Math.min(base * 2.0, 0.75) : base;
}

// Detect edge type based on node metadata (heuristic until backend provides type field)
type EdgeType = "temporal" | "semantic";

function detectEdgeType(
  sourceNode: PhaseSpaceNode | undefined,
  targetNode: PhaseSpaceNode | undefined,
): EdgeType {
  if (!sourceNode || !targetNode) return "semantic";

  // Temporal: same conversation AND created within 10 minutes
  if (
    sourceNode.conversationId &&
    sourceNode.conversationId === targetNode.conversationId
  ) {
    const timeDiff = Math.abs(
      new Date(sourceNode.createdAt).getTime() -
      new Date(targetNode.createdAt).getTime()
    );
    if (timeDiff < 1000 * 60 * 10) {
      return "temporal";
    }
  }

  return "semantic"; // default: k-NN similarity edges
}

// Build a quadratic bezier curve between two points.
// Midpoint is displaced perpendicular to the edge to create an arc.
function buildCurvePoints(
  aVec: THREE.Vector3,
  bVec: THREE.Vector3,
): THREE.Vector3[] {
  const mid = new THREE.Vector3().addVectors(aVec, bVec).multiplyScalar(0.5);
  const edge = new THREE.Vector3().subVectors(bVec, aVec);
  const edgeLen = edge.length();

  // Perpendicular to edge: cross with up vector
  const up = new THREE.Vector3(0, 1, 0);
  const perp = new THREE.Vector3().crossVectors(edge, up);
  if (perp.lengthSq() < 0.0001) {
    // Edge is nearly vertical — use X as reference
    perp.crossVectors(edge, new THREE.Vector3(1, 0, 0));
  }
  perp.normalize();

  // Displace midpoint by 10% of edge length, alternating direction per edge
  // (using dot product of midpoint with a fixed vector for determinism)
  const sign = mid.dot(new THREE.Vector3(1, 0.5, 0.3)) >= 0 ? 1 : -1;
  mid.addScaledVector(perp, edgeLen * 0.10 * sign);

  // Sample quadratic bezier at CURVE_SEGMENTS+1 points
  const curve = new THREE.QuadraticBezierCurve3(aVec, mid, bVec);
  return curve.getPoints(CURVE_SEGMENTS);
}

interface EdgeMeshProps {
  nodes: PhaseSpaceNode[];
  edges: PhaseSpaceEdge[];
  retrievalIds: string[];
}

export function EdgeMesh({ nodes, edges, retrievalIds }: EdgeMeshProps) {
  const lineRef = useRef<THREE.LineSegments>(null!);

  const nodePositions = useMemo(() => {
    const map = new Map<string, [number, number, number]>();
    for (const node of nodes) map.set(node.id, node.position);
    return map;
  }, [nodes]);

  const nodeMap = useMemo(() => {
    const map = new Map<string, PhaseSpaceNode>();
    for (const node of nodes) map.set(node.id, node);
    return map;
  }, [nodes]);

  const retrievalSet = useMemo(() => new Set(retrievalIds), [retrievalIds]);

  useEffect(() => {
    if (!lineRef.current || edges.length === 0) return;

    // Each edge: CURVE_SEGMENTS segments = CURVE_SEGMENTS*2 vertices
    // (LineSegments uses pairs: [p0,p1], [p1,p2], [p2,p3], [p3,p4])
    const vertsPerEdge = CURVE_SEGMENTS * 2; // 8
    const positions = new Float32Array(edges.length * vertsPerEdge * 3);
    const colors    = new Float32Array(edges.length * vertsPerEdge * 3);
    let pidx = 0;
    let cidx = 0;

    const aVec = new THREE.Vector3();
    const bVec = new THREE.Vector3();
    const color = new THREE.Color();

    for (const edge of edges) {
      // Skip weak edges — reduces visual noise
      if (edge.weight < WEIGHT_THRESHOLD) continue;

      const posA = nodePositions.get(edge.source);
      const posB = nodePositions.get(edge.target);
      if (!posA || !posB) continue;

      aVec.set(...posA);
      bVec.set(...posB);

      const pts = buildCurvePoints(aVec, bVec);
      const isGlow = retrievalSet.has(edge.source) || retrievalSet.has(edge.target);

      // Detect edge type (temporal vs semantic)
      const sourceNode = nodeMap.get(edge.source);
      const targetNode = nodeMap.get(edge.target);
      const edgeType = detectEdgeType(sourceNode, targetNode);

      // Output as segment pairs: [pts[0],pts[1]], [pts[1],pts[2]], ...
      for (let s = 0; s < CURVE_SEGMENTS; s++) {
        const p0 = pts[s];
        const p1 = pts[s + 1];

        positions[pidx++] = p0.x; positions[pidx++] = p0.y; positions[pidx++] = p0.z;
        positions[pidx++] = p1.x; positions[pidx++] = p1.y; positions[pidx++] = p1.z;

        // Interpolate color along arc: endpoints darker, midpoint brighter
        const t = (s + 0.5) / CURVE_SEGMENTS; // 0…1
        const midT = 1 - Math.abs(t * 2 - 1); // 0→1→0 (peaks at center)

        if (isGlow) {
          // Retrieved edges: brightest gold
          color.copy(EDGE_GLOW).lerp(EDGE_GLOW_MID, midT * 0.6);
        } else if (edgeType === "temporal") {
          // Temporal edges: warm amber (conversation flow)
          color.copy(EDGE_TEMPORAL).lerp(EDGE_TEMPORAL_MID, midT * 0.5);
        } else {
          // Semantic edges: cool blue (similarity)
          color.copy(EDGE_SEMANTIC).lerp(EDGE_SEMANTIC_MID, midT * 0.5);
        }

        // Vertex 0
        colors[cidx++] = color.r; colors[cidx++] = color.g; colors[cidx++] = color.b;
        // Vertex 1
        colors[cidx++] = color.r; colors[cidx++] = color.g; colors[cidx++] = color.b;
      }
    }

    const geom = lineRef.current.geometry as THREE.BufferGeometry;
    geom.setAttribute("position", new THREE.BufferAttribute(positions.slice(0, pidx), 3));
    geom.setAttribute("color",    new THREE.BufferAttribute(colors.slice(0, cidx), 3));
    geom.computeBoundingSphere();
  }, [edges, nodePositions, nodeMap, retrievalSet]);

  const opacity = getEdgeOpacity(edges.length, retrievalIds.length > 0);

  if (edges.length === 0) return null;

  return (
    <lineSegments ref={lineRef}>
      <bufferGeometry />
      <lineBasicMaterial
        vertexColors
        transparent
        opacity={opacity}
        depthWrite={false}
        blending={THREE.NormalBlending}
      />
    </lineSegments>
  );
}
