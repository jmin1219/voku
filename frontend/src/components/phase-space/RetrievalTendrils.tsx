import { useRef, useMemo, useEffect, useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import type { PhaseSpaceNode } from "../../types/phase-space";

/**
 * RetrievalTendrils — Animated luminous lines growing from retrieved nodes
 * toward the chat panel during memory retrieval.
 *
 * Creates a visual connection showing which graph nodes are being pulled
 * into the current conversation.
 */

const TENDRIL_COLOR = new THREE.Color("#C9A23C"); // Amber/gold
const GROWTH_DURATION = 600; // ms
const RETRACT_DURATION = 400; // ms

type AnimationPhase = "idle" | "growing" | "holding" | "retracting";

interface Tendril {
  nodeId: string;
  nodePosition: THREE.Vector3;
  targetPosition: THREE.Vector3;
  curve: THREE.CatmullRomCurve3;
  mesh: THREE.Mesh;
}

interface RetrievalTendrilsProps {
  nodes: PhaseSpaceNode[];
  retrievalIds: string[];
  isStreaming: boolean; // New prop to detect when streaming starts
}

export function RetrievalTendrils({
  nodes,
  retrievalIds,
  isStreaming,
}: RetrievalTendrilsProps) {
  const groupRef = useRef<THREE.Group>(null!);
  const { camera, size } = useThree();

  const [phase, setPhase] = useState<AnimationPhase>("idle");
  const [phaseStartTime, setPhaseStartTime] = useState(0);
  const tendrilsRef = useRef<Tendril[]>([]);
  const prevRetrievalIdsRef = useRef<string[]>([]);
  const prevStreamingRef = useRef(false);

  // Build node map
  const nodeMap = useMemo(() => {
    const map = new Map<string, PhaseSpaceNode>();
    for (const node of nodes) {
      map.set(node.id, node);
    }
    return map;
  }, [nodes]);

  // Calculate right edge of phase space in 3D world coordinates
  const getRightEdgePosition = (yPos: number, zPos: number): THREE.Vector3 => {
    // Project from screen space to world space
    // Right edge is at normalized device coordinates x = 1
    const vector = new THREE.Vector3(0.95, (yPos / size.height) * 2 - 1, 0.5);
    vector.unproject(camera);

    // Use the node's Z position to place the target in the same depth plane
    return new THREE.Vector3(vector.x, yPos, zPos);
  };

  // Create tendrils when retrievalIds change
  useEffect(() => {
    if (retrievalIds.length === 0) {
      // No retrieval - clean up
      if (phase !== "idle") {
        setPhase("idle");
        tendrilsRef.current = [];
        if (groupRef.current) {
          groupRef.current.clear();
        }
      }
      prevRetrievalIdsRef.current = [];
      return;
    }

    // New retrieval started
    const prevIds = prevRetrievalIdsRef.current;
    const idsChanged =
      retrievalIds.length !== prevIds.length ||
      retrievalIds.some((id, i) => id !== prevIds[i]);

    if (idsChanged && !isStreaming) {
      // Start growing animation
      setPhase("growing");
      setPhaseStartTime(Date.now());

      // Create tendrils for 2-4 random retrieved nodes
      const selectedCount = Math.min(
        Math.max(2, Math.floor(retrievalIds.length * 0.3)),
        4
      );
      const shuffled = [...retrievalIds].sort(() => Math.random() - 0.5);
      const selectedIds = shuffled.slice(0, selectedCount);

      const newTendrils: Tendril[] = [];

      for (const nodeId of selectedIds) {
        const node = nodeMap.get(nodeId);
        if (!node) continue;

        const nodePos = new THREE.Vector3(...node.position);
        const targetPos = getRightEdgePosition(nodePos.y, nodePos.z);

        // Create curve with 3 control points
        const midPoint = new THREE.Vector3()
          .addVectors(nodePos, targetPos)
          .multiplyScalar(0.5);

        // Add some perpendicular displacement for organic curve
        const direction = new THREE.Vector3().subVectors(targetPos, nodePos);
        const perpendicular = new THREE.Vector3(-direction.y, direction.x, 0).normalize();
        midPoint.addScaledVector(perpendicular, direction.length() * 0.15);

        const curve = new THREE.CatmullRomCurve3([nodePos, midPoint, targetPos]);

        // Create tube geometry
        const geometry = new THREE.TubeGeometry(curve, 32, 0.015, 8, false);
        const material = new THREE.MeshBasicMaterial({
          color: TENDRIL_COLOR,
          transparent: true,
          opacity: 0.7,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        });
        const mesh = new THREE.Mesh(geometry, material);

        newTendrils.push({
          nodeId,
          nodePosition: nodePos,
          targetPosition: targetPos,
          curve,
          mesh,
        });

        if (groupRef.current) {
          groupRef.current.add(mesh);
        }
      }

      tendrilsRef.current = newTendrils;
    }

    prevRetrievalIdsRef.current = retrievalIds;
  }, [retrievalIds, nodeMap, camera, size, phase, isStreaming]);

  // Detect streaming start to trigger retraction
  useEffect(() => {
    if (isStreaming && !prevStreamingRef.current && phase === "holding") {
      setPhase("retracting");
      setPhaseStartTime(Date.now());
    }
    prevStreamingRef.current = isStreaming;
  }, [isStreaming, phase]);

  // Animate tendrils
  useFrame(() => {
    if (phase === "idle" || tendrilsRef.current.length === 0) return;

    const now = Date.now();
    const elapsed = now - phaseStartTime;

    let t = 0;

    switch (phase) {
      case "growing":
        t = Math.min(elapsed / GROWTH_DURATION, 1.0);
        if (t >= 1.0) {
          setPhase("holding");
          setPhaseStartTime(now);
          t = 1.0;
        }
        break;

      case "holding":
        // Gentle pulsing effect
        const pulseFreq = 2.0; // Hz
        const pulse = Math.sin(elapsed * 0.001 * Math.PI * 2 * pulseFreq);
        const pulseMagnitude = 0.05;
        t = 1.0 + pulse * pulseMagnitude;
        break;

      case "retracting":
        t = 1.0 - Math.min(elapsed / RETRACT_DURATION, 1.0);
        if (t <= 0) {
          setPhase("idle");
          tendrilsRef.current = [];
          if (groupRef.current) {
            groupRef.current.clear();
          }
          return;
        }
        break;
    }

    // Update each tendril
    for (const tendril of tendrilsRef.current) {
      // Create partial curve based on t
      const points = tendril.curve.getPoints(32);
      const visiblePoints = Math.max(2, Math.floor(points.length * t));
      const partialPoints = points.slice(0, visiblePoints);

      // Recreate geometry with partial curve
      const partialCurve = new THREE.CatmullRomCurve3(partialPoints);
      const newGeometry = new THREE.TubeGeometry(partialCurve, 32, 0.015, 8, false);

      // Update mesh
      tendril.mesh.geometry.dispose();
      tendril.mesh.geometry = newGeometry;

      // Pulse opacity during holding phase
      if (phase === "holding") {
        const material = tendril.mesh.material as THREE.MeshBasicMaterial;
        const basePulse = Math.sin(elapsed * 0.001 * Math.PI * 2 * 2.0);
        material.opacity = 0.6 + basePulse * 0.15;
      }
    }
  });

  return <group ref={groupRef} />;
}
