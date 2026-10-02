import "server-only";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import path from "node:path";
import { getLedger } from "./data";

export type HumanVerdict = "near_miss" | "not_near_miss" | "unsure";
export type HumanReview = {
  reviewer: string;
  clip_list_hash: string;
  clip_ids: string[];
  started_at: string;
  finished_at: string | null;
  verdicts: Record<string, { verdict: HumanVerdict; note: string; at: string }>;
};

export const REVIEW_FILE = path.join(process.cwd(), "..", "eval", "human_review.json");
export const REVIEWER = "Sidra Miconi";

/** The 4 AI-labelled near-misses + every v3 flag, deduped, in a seeded order that hides which is which. */
export function reviewClips() {
  const rows = getLedger().filter((r) => r.label === "near_miss" || r.verdict === "near_miss");
  const key = (id: string) => createHash("sha256").update("closecall-review-2026-10-02:" + id).digest("hex");
  return [...rows].sort((a, b) => key(a.id).localeCompare(key(b.id)))
    .map((r) => ({ id: r.id, clip: r.clip, keyframe: r.keyframes[1] ?? r.keyframes[0], pet_s: r.pet_s, a_cls: r.a_cls, b_cls: r.b_cls, intersection: r.intersection }));
}

export const clipListHash = (ids: string[]) => createHash("sha256").update([...ids].sort().join("\n")).digest("hex");

export function readReview(): HumanReview | null {
  if (!existsSync(REVIEW_FILE)) return null;
  try { return JSON.parse(readFileSync(REVIEW_FILE, "utf8")) as HumanReview; } catch { return null; }
}

export function writeReview(r: HumanReview) {
  const tmp = REVIEW_FILE + ".tmp";
  writeFileSync(tmp, JSON.stringify(r, null, 1));
  renameSync(tmp, REVIEW_FILE); // atomic replace
}

/** Summary for the other pages (null until a review exists). */
export function reviewSummary() {
  const r = readReview();
  if (!r) return null;
  const rows = Object.fromEntries(getLedger().map((x) => [x.id, x]));
  const done = Object.entries(r.verdicts);
  const flagged = done.filter(([id]) => rows[id]?.verdict === "near_miss");
  const confirmedFlags = flagged.filter(([, v]) => v.verdict === "near_miss").length;
  const decided = done.filter(([id, v]) => v.verdict !== "unsure" && rows[id]?.label && rows[id].label !== "unsure");
  const agree = decided.filter(([id, v]) => rows[id].label === v.verdict).length;
  return {
    reviewer: r.reviewer, total: r.clip_ids.length, reviewed: done.length, finished: !!r.finished_at,
    flagged_reviewed: flagged.length, flagged_confirmed: confirmedFlags,
    human_near_miss: done.filter(([, v]) => v.verdict === "near_miss").length,
    agree, agree_n: decided.length,
    verdicts: Object.fromEntries(done.map(([id, v]) => [id, v.verdict])),
  };
}
