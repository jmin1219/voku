import type { FixtureNode } from "../types/phase-space";

export function scoreRelevance(message: string, node: FixtureNode): number {
  const lower = message.toLowerCase();
  const words = lower.split(/\s+/).filter((w) => w.length > 2);
  let score = 0;
  for (const kw of node.keywords) {
    if (lower.includes(kw)) {
      score += 1;
    } else {
      for (const word of words) {
        if (word.length > 3 && (kw.startsWith(word) || word.startsWith(kw))) {
          score += 0.4;
          break;
        }
      }
    }
  }
  const textLower = node.fullText.toLowerCase();
  for (const word of words) {
    if (word.length > 4 && textLower.includes(word)) score += 0.3;
  }
  return Math.min(score / 3.0, 1);
}
