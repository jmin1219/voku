import { Html } from "@react-three/drei";
import * as THREE from "three";
import { useMemo } from "react";

/**
 * Vertical time axis for the developmental arc view.
 * Y axis runs from -5 (oldest) to +5 (newest).
 */
export function TimeAxis() {
  const axisX = -6.5;

  const lineGeo = useMemo(() => {
    return new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(axisX, -5.2, 0),
      new THREE.Vector3(axisX, 5.2, 0),
    ]);
  }, []);

  const ticks = [-5, -3, -1, 1, 3, 5];

  return (
    <group>
      {/* Vertical line */}
      <line geometry={lineGeo}>
        <lineBasicMaterial color="#b8a88a" transparent opacity={0.4} />
      </line>

      {/* Tick marks */}
      {ticks.map((y) => {
        const geo = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(axisX - 0.15, y, 0),
          new THREE.Vector3(axisX + 0.15, y, 0),
        ]);
        return (
          <line key={y} geometry={geo}>
            <lineBasicMaterial color="#9a8a70" transparent opacity={0.3} />
          </line>
        );
      })}

      {/* Arrow tip */}
      <mesh position={[axisX, 5.3, 0]}>
        <coneGeometry args={[0.08, 0.25, 6]} />
        <meshBasicMaterial color="#b8a88a" transparent opacity={0.4} />
      </mesh>

      {/* Labels */}
      <Html position={[axisX, -5.6, 0]} center distanceFactor={14} style={{ pointerEvents: "none" }}>
        <div style={{
          color: "#9a8a70",
          fontSize: "9px",
          fontFamily: "'IBM Plex Mono', monospace",
          fontWeight: 500,
          opacity: 0.65,
          userSelect: "none",
        }}>
          oldest
        </div>
      </Html>

      <Html position={[axisX, 5.6, 0]} center distanceFactor={14} style={{ pointerEvents: "none" }}>
        <div style={{
          color: "#9a7b3c",
          fontSize: "9px",
          fontFamily: "'IBM Plex Mono', monospace",
          fontWeight: 600,
          opacity: 0.75,
          userSelect: "none",
        }}>
          newest
        </div>
      </Html>
    </group>
  );
}
