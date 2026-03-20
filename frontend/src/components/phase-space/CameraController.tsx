import { useRef, useEffect } from "react";
import { useThree, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";

/**
 * CameraController — OrbitControls + focus-on-click animation.
 *
 * Default: looks at origin from slight elevation.
 * Focus: smoothly orbits to center on a target position.
 * Reset: click empty space returns to default view.
 */

const DEFAULT_TARGET = new THREE.Vector3(0, 0, 0);
const LERP_SPEED = 0.05;
const MIN_DISTANCE = 4;
const FRAMING_MARGIN = 2.2; // multiplier on bounding radius — pull back to show full cloud

interface CameraControllerProps {
  focusPosition: [number, number, number] | null;
  dataRadius?: number; // bounding radius of all nodes
}

export function CameraController({ focusPosition, dataRadius }: CameraControllerProps) {
  const { camera } = useThree();
  const controlsRef = useRef<any>(null);
  const targetRef = useRef(DEFAULT_TARGET.clone());
  const goalTarget = useRef(DEFAULT_TARGET.clone());
  const hasFramed = useRef(false);

  // Auto-frame camera to data extent on first meaningful data
  useEffect(() => {
    if (hasFramed.current || !dataRadius || dataRadius <= 0) return;
    const dist = Math.max(MIN_DISTANCE, dataRadius * FRAMING_MARGIN);
    // Position: elevated, looking slightly down at the data
    camera.position.set(0, dist * 0.55, dist * 0.85);
    camera.lookAt(0, 0, 0);
    if (controlsRef.current) {
      controlsRef.current.target.set(0, 0, 0);
      controlsRef.current.update();
    }
    hasFramed.current = true;
  }, [dataRadius, camera]);

  useEffect(() => {
    if (focusPosition) {
      goalTarget.current.set(...focusPosition);
    } else {
      goalTarget.current.copy(DEFAULT_TARGET);
    }
  }, [focusPosition]);

  // Smooth target interpolation
  useFrame(() => {
    if (!controlsRef.current) return;

    targetRef.current.lerp(goalTarget.current, LERP_SPEED);
    controlsRef.current.target.copy(targetRef.current);
    controlsRef.current.update();
  });

  return (
    <OrbitControls
      ref={controlsRef}
      enableDamping
      dampingFactor={0.08}
      minDistance={2}
      maxDistance={dataRadius ? Math.max(30, dataRadius * 3) : 30}
      makeDefault
    />
  );
}
