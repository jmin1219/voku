import { Html } from "@react-three/drei";
import type { PhaseSpaceNode } from "../../types/phase-space";

/**
 * NodeLabels — Billboard text labels floating near each trace node.
 *
 * Shows first ~6 words of the trace content. Uses drei's Html
 * component for CSS-rendered text that always faces the camera.
 */

function truncateLabel(text: string, maxWords: number = 6): string {
  const words = text.split(/\s+/);
  if (words.length <= maxWords) return text;
  return words.slice(0, maxWords).join(" ") + "…";
}

interface NodeLabelsProps {
  nodes: PhaseSpaceNode[];
  focusedId: string | null;
  hoveredId: string | null;
}

export function NodeLabels({ nodes, focusedId, hoveredId }: NodeLabelsProps) {
  return (
    <>
      {nodes.map((node) => {
        const isActive = node.id === focusedId || node.id === hoveredId;
        const [x, y, z] = node.position;

        return (
          <Html
            key={node.id}
            position={[x, y + 0.35, z]}
            center
            style={{
              pointerEvents: "none",
              whiteSpace: "nowrap",
              userSelect: "none",
            }}
          >
            <div
              style={{
                fontSize: isActive ? "11px" : "9px",
                fontFamily: "var(--voku-font-body)",
                color: isActive
                  ? "rgba(224, 219, 208, 0.9)"
                  : "rgba(224, 219, 208, 0.45)",
                textShadow: "0 1px 4px rgba(0, 0, 0, 0.8)",
                transition: "all 0.2s ease",
                maxWidth: isActive ? "200px" : "120px",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {truncateLabel(node.label, isActive ? 10 : 5)}
            </div>
          </Html>
        );
      })}
    </>
  );
}
