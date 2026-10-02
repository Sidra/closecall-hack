export type Row = {
  id: string; source: string; intersection: string; pair: string; a_cls: string; b_cls: string;
  pet_s: number; t: number; angle_deg: number | null; vulnerable: boolean; pairs_in_event: number;
  clip: string; keyframes: string[]; verdict: "near_miss" | "not_near_miss" | "unclear";
  conflict_type: string; severity: number; evasive_action: string; explanation: string; confidence: number;
  verifier_model: string; verifier_input: string; verifier_latency_s: number; label: string | null;
  search_text: string; clip_ref: string;
  verifier_version?: string; v1_verdict?: string | null; v1_explanation?: string | null;
  v2_verdict?: string | null; v2_explanation?: string | null; votes?: Record<string, boolean>; split?: string; reviewer_note?: string;
};
export type Source = { file: string; title: string; license: string; author: string; url: string };
export type Run = {
  generated_at: string;
  funnel: Record<string, { tracks: number; naive: number; crossing: number; events: number; duration_s: number; title: string }>;
  totals: { tracks: number; naive: number; crossing: number; events: number; duration_s: number; verified: number; verifier_calls: number; fallback_verdicts: number; confirmed?: number; confirmed_and_flagged?: number };
  verifier_version?: string; verifier_label?: string;
  store: { name: string; standin: boolean; detail: string };
  models: Record<string, string>;
  thresholds: { pet_candidate_s: number; cell_frac: number; angle_deg: number[] };
  search: { mode: string; demo: Record<string, { id: string; score: number }[]> };
  weave: { enabled: boolean; url: string | null; error: string | null };
  sources: Record<string, Source>;
};
export type Memo = { intersection: string; clips: string[]; markdown?: string; model?: string; generated_at?: string; error?: string; cached?: boolean };
export type Metrics = {
  scored: number; excluded_unsure: number; tp: string[]; fp: string[]; fn: string[]; tn_count: number;
  precision: number | null; recall: number | null; baseline_precision: number | null; unsure_flagged: string[];
};
export type SplitM = { tp: number; fp: number; fn: number; n: number; precision: number | null; recall: number | null; f1: number; flags: number; candidates: number };
export type Headline = { caught: number; confirmed: number; flags: number; candidates: number; footage_s: number; test: SplitM; dev: SplitM };
export type Eval = {
  version?: string; v1?: Metrics; v1_calls?: number; v2?: Metrics | null;
  v3?: { dev: SplitM; test: SplitM; all: SplitM } | null; headline?: Headline | null; v3_label?: string;
  scored: number; excluded_unsure: number; tp: string[]; fp: string[]; fn: string[]; tn_count: number;
  precision: number | null; recall: number | null; baseline_precision: number | null; unsure_flagged: string[];
  labeller: string; labels: Record<string, { idx: number; label: string; note: string }>;
};

export const pretty = (s: string) => s.replace(/_/g, " ");

/** Only same-origin anonymised media under /clips is ever rendered; anything else becomes "". */
const MEDIA = /^clips\/[A-Za-z0-9_-]+\.(mp4|jpg)$/;
export function mediaSrc(p: string | undefined | null): string {
  if (!p || !MEDIA.test(p)) return "";
  return `/clips/${encodeURIComponent(p.slice("clips/".length))}`;
}
