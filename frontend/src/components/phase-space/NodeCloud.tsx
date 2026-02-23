/**
 * NodeCloud.tsx — InstancedMesh renderer for all proposition nodes.
 *
 * Replaces per-node DataNode components (425 React components + 425 useFrame
 * callbacks + 425 Three.js objects) with a single InstancedMesh (1 draw call,
 * 1 useFrame, 1 geometry + material).
 *
 * Per-instance visual properties (color, opacity, emissive intensity) are
 * driven by custom InstancedBufferAttributes and a lightweight Lambertian
 * ShaderMaterial that matches the scene's lighting setup.
 *
 * Architecture:
 *   Props change → compute target arrays → useFrame lerps current → targets
 *   → writes instance matrices + attribute buffers → GPU renders.
 *
 * Breathing animation runs per-instance with deterministic phase offsets
 * derived from node ID hashes (same algorithm as DataNode).
 *
 * BUG PREVENTION NOTES (Ralph review):
 *   - needsUpdate is set via mesh.geometry.attributes, NOT on the useMemo refs.
 *     The JSX <instancedBufferAttribute> creates new IBA objects from our arrays;
 *     the refs share the Float32Array backing buffer but not the IBA wrapper.
 *   - Zero allocations inside useFrame — all scratch objects pre-allocated at module scope.
 *   - frustumCulled=false: InstancedMesh's bounding sphere is the geometry's BS,
 *     not the union of all instances. Disabling avoids culling when instances spread
 *     beyond the geometry's tiny sphere.
 *   - key={n} on <instancedMesh>: forces React re-mount when node count changes
 *     (extraction adds nodes), ensuring attribute buffers and instance count stay in sync.
 */

import { useRef, useMemo, useEffect, useState, useCallback } from "react";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import {
  type PropositionNode,
  type LayoutMode,
  TYPE_COLORS,
  CLUSTER_COLORS,
  DIMENSION_COLORS,
  UNASSIGNED_COLOR,
  timeColor,
  getNodePosition,
} from "../../types/phase-space";

// ---------------------------------------------------------------------------
// Shader: Lambertian diffuse + emissive, per-instance color/opacity/emissive.
// Matches the scene's ambient + 2 point lights without paying for full PBR
// (indistinguishable on small spheres at this scale).
// ---------------------------------------------------------------------------

const VERTEX_SHADER = /* glsl */ `
  attribute vec3 aColor;
  attribute float aOpacity;
  attribute float aEmissive;

  varying vec3 vColor;
  varying float vOpacity;
  varying float vEmissive;
  varying vec3 vNormal;
  varying vec3 vWorldPos;

  void main() {
    vec4 worldPos = instanceMatrix * vec4(position, 1.0);
    vWorldPos = worldPos.xyz;

    // For uniform scaling (no rotation), mat3(instanceMatrix) is a scalar
    // multiple of identity — normalizing recovers the unit normal.
    vNormal = normalize(mat3(instanceMatrix) * normal);

    vColor = aColor;
    vOpacity = aOpacity;
    vEmissive = aEmissive;

    gl_Position = projectionMatrix * viewMatrix * worldPos;
  }
`;

const FRAGMENT_SHADER = /* glsl */ `
  uniform vec3 uAmbientColor;
  uniform float uAmbientIntensity;
  uniform vec3 uLight1Pos;
  uniform vec3 uLight1Color;
  uniform float uLight1Intensity;
  uniform vec3 uLight2Pos;
  uniform vec3 uLight2Color;
  uniform float uLight2Intensity;

  varying vec3 vColor;
  varying float vOpacity;
  varying float vEmissive;
  varying vec3 vNormal;
  varying vec3 vWorldPos;

  void main() {
    vec3 n = normalize(vNormal);

    // Ambient
    vec3 ambient = uAmbientColor * uAmbientIntensity;

    // Point light 1 — Lambertian diffuse (no specular at this scale)
    vec3 dir1 = normalize(uLight1Pos - vWorldPos);
    float diff1 = max(dot(n, dir1), 0.0);
    vec3 diffuse1 = uLight1Color * uLight1Intensity * diff1;

    // Point light 2
    vec3 dir2 = normalize(uLight2Pos - vWorldPos);
    float diff2 = max(dot(n, dir2), 0.0);
    vec3 diffuse2 = uLight2Color * uLight2Intensity * diff2;

    vec3 lit = vColor * (ambient + diffuse1 + diffuse2) + vColor * vEmissive;
    gl_FragColor = vec4(lit, vOpacity);
  }
`;

// Light uniforms matching Scene.tsx's light setup. Static — never changes.
const LIGHT_UNIFORMS = {
  uAmbientColor: { value: new THREE.Color("#c8c0d0") },
  uAmbientIntensity: { value: 0.4 },
  uLight1Pos: { value: new THREE.Vector3(8, 8, 8) },
  uLight1Color: { value: new THREE.Color("#ffe8d0") },
  uLight1Intensity: { value: 0.8 },
  uLight2Pos: { value: new THREE.Vector3(-6, -4, 4) },
  uLight2Color: { value: new THREE.Color("#d0c8e0") },
  uLight2Intensity: { value: 0.4 },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Deterministic phase offset from node ID (same hash as DataNode). */
function computePhaseOffset(id: string): number {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash + id.charCodeAt(i)) | 0;
  }
  return ((Math.abs(hash) % 1000) / 1000) * Math.PI * 2;
}

/** Resolve node color from layout mode. Returns hex string. */
function getNodeColor(node: PropositionNode, layoutMode: LayoutMode): string {
  if (layoutMode === "dimension") {
    return node.dimension
      ? DIMENSION_COLORS[node.dimension] ?? UNASSIGNED_COLOR
      : UNASSIGNED_COLOR;
  }
  if (layoutMode === "time") return timeColor(node.age);
  if (layoutMode === "cluster") {
    return node.cluster >= 0
      ? CLUSTER_COLORS[node.cluster % CLUSTER_COLORS.length]
      : "#999";
  }
  return TYPE_COLORS[node.nodeType] || "#888";
}

// Pre-allocated scratch — NEVER allocate inside useFrame.
const _matrix = new THREE.Matrix4();
const _pos = new THREE.Vector3();
const _color = new THREE.Color();

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface NodeCloudProps {
  nodes: PropositionNode[];
  relevanceMap: Map<string, number>;
  retrievalIds: string[];
  layoutMode: LayoutMode;
  hasActive: boolean;
}

export function NodeCloud({
  nodes,
  relevanceMap,
  retrievalIds,
  layoutMode,
  hasActive,
}: NodeCloudProps) {
  const n = nodes.length;
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const retrievalSet = useMemo(() => new Set(retrievalIds), [retrievalIds]);

  // -----------------------------------------------------------------------
  // Phase offsets — deterministic per node ID.
  // -----------------------------------------------------------------------
  const phaseOffsets = useMemo(() => {
    const arr = new Float32Array(n);
    for (let i = 0; i < n; i++) arr[i] = computePhaseOffset(nodes[i].id);
    return arr;
  }, [nodes, n]);

  // -----------------------------------------------------------------------
  // CPU-side state arrays for lerping. Written by useEffect (targets) and
  // useFrame (current values). Raw Float32Arrays — no React state overhead.
  // -----------------------------------------------------------------------
  const state = useMemo(() => ({
    curScale: new Float32Array(n).fill(0.2),
    curOpacity: new Float32Array(n).fill(0.5),
    curEmissive: new Float32Array(n).fill(0.1),
    curPosX: new Float32Array(n),
    curPosY: new Float32Array(n),
    curPosZ: new Float32Array(n),
    tgtScale: new Float32Array(n).fill(0.2),
    tgtOpacity: new Float32Array(n).fill(0.5),
    tgtEmissive: new Float32Array(n).fill(0.1),
    tgtPosX: new Float32Array(n),
    tgtPosY: new Float32Array(n),
    tgtPosZ: new Float32Array(n),
  }), [n]);

  // -----------------------------------------------------------------------
  // GPU attribute backing arrays. The JSX <instancedBufferAttribute> wraps
  // these in IBA objects. We write to these arrays in useFrame, then flag
  // needsUpdate on the GEOMETRY'S attributes (not these refs).
  // -----------------------------------------------------------------------
  const gpuArrays = useMemo(() => ({
    color: new Float32Array(n * 3),
    opacity: new Float32Array(n),
    emissive: new Float32Array(n),
  }), [n]);

  // -----------------------------------------------------------------------
  // Initialize current positions to actual layout positions (no lerp-from-origin).
  // -----------------------------------------------------------------------
  useEffect(() => {
    for (let i = 0; i < n; i++) {
      const pos = getNodePosition(nodes[i], layoutMode);
      state.curPosX[i] = pos[0];
      state.curPosY[i] = pos[1];
      state.curPosZ[i] = pos[2];
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [n]); // Only on mount / node-count change — layout transitions are lerped in useFrame.

  // -----------------------------------------------------------------------
  // Compute targets whenever props change.
  // -----------------------------------------------------------------------
  useEffect(() => {
    for (let i = 0; i < n; i++) {
      const node = nodes[i];
      const isRetrieved = retrievalSet.has(node.id);
      const rawRelevance = relevanceMap.get(node.id) || 0;
      const relevance = isRetrieved ? 1.0 : rawRelevance;
      const isActiveNode = relevance > 0.3;
      const isResidual = relevance > 0 && relevance <= 0.3;
      const dr = node.dimensionRelevance;

      let scale: number, opacity: number, emissive: number;

      if (isActiveNode) {
        scale = 0.45 + relevance * 0.45;
        opacity = 0.95;
        emissive = 0.3 + relevance * 0.4;
      } else if (isResidual) {
        scale = 0.22 + relevance * 0.22;
        opacity = hasActive ? 0.4 : 0.65 + relevance * 0.2;
        emissive = hasActive ? 0.08 : 0.15 + relevance * 0.2;
      } else if (hasActive) {
        scale = 0.10 + dr * 0.14;
        opacity = 0.15 + dr * 0.08;
        emissive = 0.02 + dr * 0.04;
      } else {
        scale = 0.18 + dr * 0.27;
        opacity = 0.55 + dr * 0.30;
        emissive = 0.06 + dr * 0.12;
      }

      state.tgtScale[i] = scale;
      state.tgtOpacity[i] = opacity;
      state.tgtEmissive[i] = emissive;

      const pos = getNodePosition(node, layoutMode);
      state.tgtPosX[i] = pos[0];
      state.tgtPosY[i] = pos[1];
      state.tgtPosZ[i] = pos[2];
    }
  }, [nodes, relevanceMap, retrievalSet, layoutMode, hasActive, n, state]);

  // -----------------------------------------------------------------------
  // Per-frame animation loop. ZERO allocations.
  // Lerps all per-instance values, applies breathing, writes GPU buffers.
  // -----------------------------------------------------------------------
  useFrame(({ clock }) => {
    const mesh = meshRef.current;
    if (!mesh || n === 0) return;

    const t = clock.getElapsedTime();
    const lerp = 0.08;
    const geo = mesh.geometry;

    for (let i = 0; i < n; i++) {
      const node = nodes[i];
      const dr = node.dimensionRelevance;
      const isRetrieved = retrievalSet.has(node.id);
      const rawRelevance = relevanceMap.get(node.id) || 0;
      const relevance = isRetrieved ? 1.0 : rawRelevance;
      const isActiveNode = relevance > 0.3;
      const isResidual = relevance > 0 && relevance <= 0.3;

      // --- Lerp position ---
      state.curPosX[i] += (state.tgtPosX[i] - state.curPosX[i]) * lerp;
      state.curPosY[i] += (state.tgtPosY[i] - state.curPosY[i]) * lerp;
      state.curPosZ[i] += (state.tgtPosZ[i] - state.curPosZ[i]) * lerp;

      // --- Breathing (resting/dimmed states only) ---
      const breathActive = !isActiveNode && !isResidual;
      const breathPeriod = 3.0 + dr * 3.0;
      const breathAmplitude = 0.03 + dr * 0.05;
      const emissivePulse = 0.01 + dr * 0.03;
      const breath = breathActive
        ? Math.sin((t * Math.PI * 2) / breathPeriod + phaseOffsets[i])
        : 0;

      // --- Lerp scale + breathing ---
      state.curScale[i] += (state.tgtScale[i] - state.curScale[i]) * lerp;
      let finalScale = state.curScale[i] * (1 + breath * breathAmplitude);

      // --- Lerp opacity ---
      state.curOpacity[i] += (state.tgtOpacity[i] - state.curOpacity[i]) * lerp;
      let finalOpacity = state.curOpacity[i];

      // --- Lerp emissive + breathing ---
      state.curEmissive[i] += (state.tgtEmissive[i] - state.curEmissive[i]) * lerp;
      let finalEmissive = state.curEmissive[i] + breath * emissivePulse;

      // --- Hover boost (applied on top, not baked into targets) ---
      if (hoveredIdx === i && !hasActive) {
        finalScale *= 1.3;
        finalEmissive += 0.15;
        finalOpacity = Math.min(finalOpacity + 0.15, 1);
      }

      // --- Instance matrix: position + uniform scale ---
      _pos.set(state.curPosX[i], state.curPosY[i], state.curPosZ[i]);
      _matrix.makeScale(finalScale, finalScale, finalScale);
      _matrix.setPosition(_pos);
      mesh.setMatrixAt(i, _matrix);

      // --- Color (snappy switch on layout change, no lerp) ---
      _color.set(getNodeColor(node, layoutMode));
      gpuArrays.color[i * 3] = _color.r;
      gpuArrays.color[i * 3 + 1] = _color.g;
      gpuArrays.color[i * 3 + 2] = _color.b;

      // --- Opacity + emissive ---
      gpuArrays.opacity[i] = finalOpacity;
      gpuArrays.emissive[i] = finalEmissive;
    }

    // --- Flag GPU buffers for upload ---
    mesh.instanceMatrix.needsUpdate = true;
    if (geo.attributes.aColor) (geo.attributes.aColor as THREE.BufferAttribute).needsUpdate = true;
    if (geo.attributes.aOpacity) (geo.attributes.aOpacity as THREE.BufferAttribute).needsUpdate = true;
    if (geo.attributes.aEmissive) (geo.attributes.aEmissive as THREE.BufferAttribute).needsUpdate = true;
  });

  // -----------------------------------------------------------------------
  // Hover — InstancedMesh raycasting returns instanceId in the event.
  // -----------------------------------------------------------------------
  const handlePointerMove = useCallback(
    (e: ThreeEvent<PointerEvent>) => {
      e.stopPropagation();
      const id = (e as unknown as { instanceId?: number }).instanceId;
      if (id !== undefined && id < n) {
        setHoveredIdx(id);
      }
    },
    [n],
  );

  const handlePointerOut = useCallback(() => {
    setHoveredIdx(null);
  }, []);

  // -----------------------------------------------------------------------
  // Label candidates: retrieved nodes + hovered node.
  // -----------------------------------------------------------------------
  const labelNodes = useMemo(() => {
    const labels: { node: PropositionNode; idx: number; isRetrieved: boolean }[] = [];
    const seen = new Set<number>();

    for (let i = 0; i < n; i++) {
      if (retrievalSet.has(nodes[i].id)) {
        labels.push({ node: nodes[i], idx: i, isRetrieved: true });
        seen.add(i);
      }
    }

    if (hoveredIdx !== null && !seen.has(hoveredIdx) && hoveredIdx < n) {
      labels.push({ node: nodes[hoveredIdx], idx: hoveredIdx, isRetrieved: false });
    }

    return labels;
  }, [nodes, retrievalSet, hoveredIdx, n]);

  // -----------------------------------------------------------------------
  // Material — created once, static uniforms.
  // -----------------------------------------------------------------------
  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      uniforms: { ...LIGHT_UNIFORMS },
      transparent: true,
      depthWrite: false,
    });
  }, []);

  useEffect(() => () => material.dispose(), [material]);

  if (n === 0) return null;

  return (
    <>
      {/*
        key={n}: force remount when node count changes (extraction adds nodes).
        New count requires new InstancedMesh + new attribute buffers.
      */}
      <instancedMesh
        key={n}
        ref={meshRef}
        args={[undefined, undefined, n]}
        onPointerMove={handlePointerMove}
        onPointerOut={handlePointerOut}
        material={material}
        frustumCulled={false}
      >
        <sphereGeometry args={[0.18, 20, 20]}>
          <instancedBufferAttribute attach="attributes-aColor" args={[gpuArrays.color, 3]} />
          <instancedBufferAttribute attach="attributes-aOpacity" args={[gpuArrays.opacity, 1]} />
          <instancedBufferAttribute attach="attributes-aEmissive" args={[gpuArrays.emissive, 1]} />
        </sphereGeometry>
      </instancedMesh>

      {/* Labels — HTML overlays at current lerped positions */}
      {labelNodes.map(({ node, idx, isRetrieved }) => (
        <Html
          key={node.id}
          position={[
            state.curPosX[idx] ?? 0,
            state.curPosY[idx] ?? 0,
            (state.curPosZ[idx] ?? 0) + 0.35,
          ]}
          center
          distanceFactor={8}
          style={{ pointerEvents: "none" }}
        >
          <div
            style={{
              color: "#e0dbd0",
              fontSize: isRetrieved ? "11px" : "10px",
              fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
              fontWeight: isRetrieved ? 500 : 400,
              opacity: isRetrieved ? 0.9 : 0.75,
              whiteSpace: "nowrap",
              maxWidth: "280px",
              overflow: "hidden",
              textOverflow: "ellipsis",
              textShadow:
                "0 1px 4px rgba(0,0,0,0.6), 0 0 8px rgba(0,0,0,0.4)",
              userSelect: "none",
            }}
          >
            {node.label}
            <span
              style={{
                color: "#8a8578",
                fontSize: "9px",
                marginLeft: "6px",
                fontFamily: "'IBM Plex Mono', monospace",
              }}
            >
              [{node.nodeType}]
            </span>
          </div>
        </Html>
      ))}
    </>
  );
}
