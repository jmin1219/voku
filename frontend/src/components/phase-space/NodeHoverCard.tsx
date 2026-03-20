import { Html } from "@react-three/drei";
import { animated, useSpring } from "@react-spring/web";
import type { PhaseSpaceNode, PhaseSpaceCluster, PhaseSpaceEdge } from "../../types/phase-space";

interface NodeHoverCardProps {
  node: PhaseSpaceNode;
  clusters: PhaseSpaceCluster[];
  edges: PhaseSpaceEdge[];
}

/**
 * Format date as "Feb 22" or "Mar 10"
 */
function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  const month = date.toLocaleDateString("en-US", { month: "short" });
  const day = date.getDate();
  return `${month} ${day}`;
}

/**
 * Calculate node degree (connection count) from edges.
 */
function getNodeDegree(nodeId: string, edges: PhaseSpaceEdge[]): number {
  let degree = 0;
  for (const edge of edges) {
    if (edge.source === nodeId || edge.target === nodeId) {
      degree++;
    }
  }
  return degree;
}

/**
 * Get cluster label for a node.
 */
function getClusterLabel(node: PhaseSpaceNode, clusters: PhaseSpaceCluster[]): string | null {
  if (node.cluster === -1) return null;
  const cluster = clusters.find((c) => c.id === node.cluster);
  return cluster?.label || null;
}

export function NodeHoverCard({ node, clusters, edges }: NodeHoverCardProps) {
  const [x, y, z] = node.position;
  const degree = getNodeDegree(node.id, edges);
  const clusterLabel = getClusterLabel(node, clusters);
  const truncatedContent = node.fullText.length > 120
    ? node.fullText.slice(0, 120) + "..."
    : node.fullText;

  // Spring animation for entrance
  const spring = useSpring({
    from: { opacity: 0, transform: "scale(0.95)" },
    to: { opacity: 1, transform: "scale(1)" },
    config: { tension: 300, friction: 20 },
  });

  return (
    <Html
      position={[x + 0.3, y + 0.4, z]}
      style={{
        pointerEvents: "none",
        userSelect: "none",
      }}
    >
      <animated.div
        style={{
          ...spring,
          background: "rgba(15, 12, 8, 0.85)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(201, 162, 60, 0.3)",
          borderRadius: "6px",
          boxShadow: "0 0 20px rgba(201, 162, 60, 0.15)",
          padding: "10px 12px",
          minWidth: "240px",
          maxWidth: "320px",
          fontFamily: "var(--voku-font-mono)",
          fontSize: "0.7rem",
          lineHeight: "1.5",
          color: "#e0dbd0",
        }}
      >
        {/* Date */}
        <div
          style={{
            fontSize: "0.65rem",
            color: "#c9a23c",
            marginBottom: "6px",
            fontWeight: 500,
          }}
        >
          {formatDate(node.createdAt)}
        </div>

        {/* Content */}
        <div
          style={{
            marginBottom: "8px",
            color: "#d0cbc0",
            fontSize: "0.68rem",
          }}
        >
          {truncatedContent}
        </div>

        {/* Metadata row */}
        <div
          style={{
            display: "flex",
            gap: "12px",
            fontSize: "0.62rem",
            color: "#99907f",
          }}
        >
          {clusterLabel && (
            <div>
              <span style={{ color: "#6a88b8" }}>cluster:</span> {clusterLabel}
            </div>
          )}
          <div>
            <span style={{ color: "#6a88b8" }}>connections:</span> {degree}
          </div>
        </div>
      </animated.div>
    </Html>
  );
}
