/**
 * Phase space data types — matches backend /api/phase-space response.
 */

export interface PhaseSpaceNode {
  id: string;
  label: string;
  fullText: string;
  source: "user" | "assistant" | "resource" | "system";
  conversationId: string | null;
  parentTraceId: string | null;
  createdAt: string;
  annotations: { type: string; key: string | null; value: string | null }[];
  age: number; // 0 (oldest) to 1 (newest)
  position: [number, number, number]; // UMAP 3D
  positionTime: [number, number, number]; // UMAP 2D + temporal Z
  keywords: string[];
  cluster: number; // -1 = noise
  orientation: number; // -1 = noise
}

export interface PhaseSpaceCluster {
  id: number;
  center: [number, number, number];
  radius: number;
  count: number;
  label: string;
  trace_ids: string[];
  orientation_id: number;
}

export interface PhaseSpaceOrientation {
  id: number;
  label: string;
  cluster_ids: number[];
  center: [number, number, number];
  trace_count: number;
}

export interface PhaseSpaceEdge {
  source: string;
  target: string;
  weight: number;
}

export interface PhaseSpaceMeta {
  count: number;
  n_clusters: number;
  n_orientations: number;
  n_edges: number;
  knn_k: number;
}

export interface PhaseSpaceData {
  nodes: PhaseSpaceNode[];
  clusters: PhaseSpaceCluster[];
  orientations: PhaseSpaceOrientation[];
  edges: PhaseSpaceEdge[];
  meta: PhaseSpaceMeta;
}
