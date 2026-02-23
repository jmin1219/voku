import fixtureData from "../data/fixtures.json";

// --- Interfaces ---

export interface FixtureNode {
  id: string;
  label: string;
  fullText: string;
  nodeType: string;
  confidence: number;
  sourceFile: string;
  eventTimeframe: string | null;
  position: [number, number, number];
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

// --- Color Constants ---

export const TYPE_COLORS: Record<string, string> = {
  stance: "#60a5fa",
  event: "#4ade80",
  intention: "#fbbf24",
};

export const CLUSTER_COLORS = [
  "#f87171",
  "#fb923c",
  "#fbbf24",
  "#a3e635",
  "#34d399",
  "#22d3ee",
  "#60a5fa",
  "#a78bfa",
  "#e879f9",
  "#fb7185",
  "#fdba74",
  "#bef264",
  "#6ee7b7",
  "#67e8f9",
  "#93c5fd",
  "#c4b5fd",
];

// --- Loaded Fixture Data ---

interface FixtureFile {
  nodes: FixtureNode[];
  clusters: ClusterData[];
}

export const NODES: FixtureNode[] = (fixtureData as FixtureFile).nodes;
export const CLUSTERS: ClusterData[] = (fixtureData as FixtureFile).clusters;
