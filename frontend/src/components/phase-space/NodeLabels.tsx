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
  // Only render labels for hovered or focused nodes — at 200+ nodes,
  // rendering all labels creates visual chaos and DOM overhead.
  const activeNodes = nodes.filter(
    (node) => node.id === focusedId || node.id === hoveredId
  );

  if (activeNodes.length === 0) return null;

  return (
    <>
      {activeNodes.map((node) => {
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
                fontSize: "11px",
                fontFamily: "var(--voku-font-body)",
                color: "rgba(224, 219, 208, 0.9)",
                textShadow: "0 1px 4px rgba(0, 0, 0, 0.8)",
                maxWidth: "220px",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {truncateLabel(node.label, 10)}
            </div>
          </Html>
        );
      })}
    </>
  );
}
