import { useRef, useMemo, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { PhaseSpaceNode, PhaseSpaceEdge } from "../../types/phase-space";

/**
 * ParticleFlow — Animated particles traveling along edges.
 *
 * Creates a neural impulse / signal flow effect where particles move
 * along edge curves continuously. Particle count is proportional to
 * edge weight, color matches source node age.
 */

interface Particle {
  edgeIndex: number;
  t: number; // position along curve (0→1)
  speed: number; // units per second
  direction: 1 | -1; // 1 = forward, -1 = backward
  curve: THREE.QuadraticBezierCurve3;
  sourceColor: THREE.Color;
}

// Build curve same way as EdgeMesh for consistency
function buildCurveForEdge(
  posA: [number, number, number],
  posB: [number, number, number]
): THREE.QuadraticBezierCurve3 {
  const aVec = new THREE.Vector3(...posA);
  const bVec = new THREE.Vector3(...posB);
  const mid = new THREE.Vector3().addVectors(aVec, bVec).multiplyScalar(0.5);
  const edge = new THREE.Vector3().subVectors(bVec, aVec);
  const edgeLen = edge.length();

  const up = new THREE.Vector3(0, 1, 0);
  const perp = new THREE.Vector3().crossVectors(edge, up);
  if (perp.lengthSq() < 0.0001) {
    perp.crossVectors(edge, new THREE.Vector3(1, 0, 0));
  }
  perp.normalize();

  const sign = mid.dot(new THREE.Vector3(1, 0.5, 0.3)) >= 0 ? 1 : -1;
  mid.addScaledVector(perp, edgeLen * 0.10 * sign);

  return new THREE.QuadraticBezierCurve3(aVec, mid, bVec);
}

// Get color for node based on age (same as TraceCloud)
function getColorForAge(age: number): THREE.Color {
  const COLOR_0_7 = new THREE.Color("#C9A23C");
  const COLOR_8_30 = new THREE.Color("#8B7355");
  const COLOR_31_60 = new THREE.Color("#6a88b8");
  const COLOR_60_PLUS = new THREE.Color("#3d5a80");

  const color = new THREE.Color();
  if (age <= 7) {
    color.copy(COLOR_0_7);
  } else if (age <= 30) {
    const t = (age - 7) / (30 - 7);
    color.lerpColors(COLOR_0_7, COLOR_8_30, t);
  } else if (age <= 60) {
    const t = (age - 30) / (60 - 30);
    color.lerpColors(COLOR_8_30, COLOR_31_60, t);
  } else {
    const t = Math.min((age - 60) / 60, 1.0);
    color.lerpColors(COLOR_31_60, COLOR_60_PLUS, t);
  }
  return color;
}

function getAgeInDays(createdAt: string): number {
  const created = new Date(createdAt);
  const now = new Date();
  const diffMs = now.getTime() - created.getTime();
  return diffMs / (1000 * 60 * 60 * 24);
}

interface ParticleFlowProps {
  nodes: PhaseSpaceNode[];
  edges: PhaseSpaceEdge[];
}

export function ParticleFlow({ nodes, edges }: ParticleFlowProps) {
  const pointsRef = useRef<THREE.Points>(null!);
  const particlesRef = useRef<Particle[]>([]);

  const nodeMap = useMemo(() => {
    const map = new Map<string, PhaseSpaceNode>();
    for (const node of nodes) {
      map.set(node.id, node);
    }
    return map;
  }, [nodes]);

  // Initialize particles
  useEffect(() => {
    if (edges.length === 0) return;

    const particles: Particle[] = [];

    // Performance cap: limit total particles to maintain 30+ fps
    const MAX_PARTICLES = 8000;
    const particlesPerEdge = Math.max(1, Math.floor(MAX_PARTICLES / edges.length / 2));
    const maxParticlesPerEdge = Math.min(3, particlesPerEdge);

    for (let i = 0; i < edges.length; i++) {
      const edge = edges[i];
      const sourceNode = nodeMap.get(edge.source);
      const targetNode = nodeMap.get(edge.target);
      if (!sourceNode || !targetNode) continue;

      const curve = buildCurveForEdge(sourceNode.position, targetNode.position);

      // Particle count based on edge weight (1-maxParticlesPerEdge)
      const normalizedWeight = Math.min(Math.max(edge.weight, 0), 1);
      const particleCount = Math.floor(1 + normalizedWeight * (maxParticlesPerEdge - 1));

      const sourceAge = getAgeInDays(sourceNode.createdAt);
      const sourceColor = getColorForAge(sourceAge);

      // Create particles for this edge - bidirectional flow
      for (let p = 0; p < particleCount; p++) {
        // Forward direction
        particles.push({
          edgeIndex: i,
          t: p / particleCount, // Stagger starting positions
          speed: 0.3, // units per second
          direction: 1,
          curve,
          sourceColor: sourceColor.clone(),
        });

        // Backward direction (offset by half cycle for variety)
        particles.push({
          edgeIndex: i,
          t: (p + 0.5) / particleCount,
          speed: 0.3,
          direction: -1,
          curve,
          sourceColor: sourceColor.clone(),
        });
      }
    }

    particlesRef.current = particles;

    // Initialize geometry
    if (pointsRef.current) {
      const positions = new Float32Array(particles.length * 3);
      const colors = new Float32Array(particles.length * 3);

      for (let i = 0; i < particles.length; i++) {
        const particle = particles[i];
        const pos = particle.curve.getPoint(particle.t);
        positions[i * 3] = pos.x;
        positions[i * 3 + 1] = pos.y;
        positions[i * 3 + 2] = pos.z;

        colors[i * 3] = particle.sourceColor.r;
        colors[i * 3 + 1] = particle.sourceColor.g;
        colors[i * 3 + 2] = particle.sourceColor.b;
      }

      const geom = pointsRef.current.geometry as THREE.BufferGeometry;
      geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      geom.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    }
  }, [edges, nodeMap]);

  // Animate particles
  useFrame((_, delta) => {
    if (!pointsRef.current || particlesRef.current.length === 0) return;

    const particles = particlesRef.current;
    const geom = pointsRef.current.geometry as THREE.BufferGeometry;
    const positions = geom.attributes.position.array as Float32Array;

    for (let i = 0; i < particles.length; i++) {
      const particle = particles[i];

      // Advance t along curve
      particle.t += (particle.speed * delta * particle.direction);

      // Wrap around when reaching end
      if (particle.t > 1) particle.t = 0;
      if (particle.t < 0) particle.t = 1;

      // Update position
      const pos = particle.curve.getPoint(particle.t);
      positions[i * 3] = pos.x;
      positions[i * 3 + 1] = pos.y;
      positions[i * 3 + 2] = pos.z;
    }

    geom.attributes.position.needsUpdate = true;
  });

  if (edges.length === 0) return null;

  return (
    <points ref={pointsRef}>
      <bufferGeometry />
      <pointsMaterial
        size={3}
        sizeAttenuation
        vertexColors
        transparent
        opacity={0.8}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}
