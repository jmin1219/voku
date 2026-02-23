// --- Layout modes ---

export type LayoutMode = "cluster" | "type" | "time";

// --- Interfaces ---

export interface PropositionNode {
  id: string;
  label: string;
  fullText: string;
  nodeType: string;
  confidence: number;
  sourceFile: string;
  eventTimeframe: string | null;
  createdAt: string;
  age: number; // 0 = oldest, 1 = newest
  position: [number, number, number];       // 3D UMAP (semantic)
  positionTime: [number, number, number];   // 2D UMAP + time Z axis (developmental)
  keywords: string[];
  cluster: number;
}

export interface ClusterData {
  id: number;
  center: [number, number, number];
  radius: number;
  count: number;
  label: string;
}

// --- Position helper ---

export function getNodePosition(node: PropositionNode, layout: LayoutMode): [number, number, number] {
  if (layout === "time") return node.positionTime;
  return node.position;
}

// --- Color Constants ---

export const TYPE_COLORS: Record<string, string> = {
  stance: "#4a78a8",     // Medium blue
  event: "#4a8a5e",      // Medium green
  intention: "#a07830",  // Warm amber
};

export const CLUSTER_COLORS = [
  "#b05555",   // brick
  "#b07840",   // sienna
  "#9a8530",   // olive gold
  "#5a8a40",   // fern
  "#3a8a6a",   // jade
  "#3a7a8a",   // ocean
  "#4a6a9a",   // denim
  "#6a5a9a",   // iris
  "#8a5080",   // plum
  "#b05a5a",   // coral
  "#8a7050",   // umber
  "#5a8a50",   // clover
  "#3a8a7a",   // teal
  "#4a7a9a",   // cadet
  "#6a6a9a",   // indigo
  "#7a5a8a",   // grape
];

// --- Time gradient ---
// age: 0 = oldest (cool slate) → 1 = newest (warm gold)

export function timeColor(age: number): string {
  const r = Math.round(100 + age * 54);  // 100 → 154
  const g = Math.round(120 + age * 3);   // 120 → 123
  const b = Math.round(160 - age * 100); // 160 → 60
  return `rgb(${r}, ${g}, ${b})`;
}
