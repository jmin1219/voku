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

const DEFAULT_POSITION = new THREE.Vector3(0, 8, 12);
const DEFAULT_TARGET = new THREE.Vector3(0, 0, 0);
const LERP_SPEED = 0.05;

interface CameraControllerProps {
  focusPosition: [number, number, number] | null;
}

export function CameraController({ focusPosition }: CameraControllerProps) {
  const controlsRef = useRef<any>(null);
  const targetRef = useRef(DEFAULT_TARGET.clone());
  const goalTarget = useRef(DEFAULT_TARGET.clone());

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
      maxDistance={30}
      makeDefault
    />
  );
}
