import type { Row } from "./types";

/** Requests to identify people or vehicles are refused before any search runs. */
const IDENTITY = /\b(who|whose|driver'?s? name|identify|identity|face|faces|plate|plates|licen[cs]e|number plate|registration|owner|name of)\b/i;
export const isIdentityQuery = (q: string) => IDENTITY.test(q);
export const REFUSAL =
  "CloseCall does not identify people or vehicles. Heads and plates are pixelated in tracked boxes, and no identity is ever extracted. Ask about what happened instead, e.g. \"turning cars cutting across pedestrians\".";

export function cosine(a: number[], b: number[]) {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
  return na && nb ? dot / Math.sqrt(na * nb) : 0;
}

/** Fallback when the embedding service is down: token overlap on the row's text. */
export function keywordScore(q: string, r: Row) {
  const terms = q.toLowerCase().split(/[^a-z]+/).filter((w) => w.length > 2);
  const text = r.search_text.toLowerCase();
  if (!terms.length) return 0;
  return terms.filter((w) => text.includes(w.replace(/s$/, ""))).length / terms.length;
}
