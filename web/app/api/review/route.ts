import { clipListHash, readReview, REVIEWER, reviewClips, writeReview, type HumanReview, type HumanVerdict } from "@/lib/review";

const VERDICTS: HumanVerdict[] = ["near_miss", "not_near_miss", "unsure"];

/** Local-only: the review writes into the repo, so it refuses anything not addressed to localhost. */
function local(req: Request) {
  if (process.env.NODE_ENV === "production" && process.env.CLOSECALL_REVIEW !== "1") return false;
  const host = (req.headers.get("host") || "").split(":")[0];
  return host === "localhost" || host === "127.0.0.1";
}

export async function GET(req: Request) {
  if (!local(req)) return Response.json({ error: "review is local-only" }, { status: 403 });
  const clips = reviewClips();
  const r = readReview();
  return Response.json({ clips, done: r ? Object.keys(r.verdicts) : [], finished: !!r?.finished_at });
}

export async function POST(req: Request) {
  if (!local(req)) return Response.json({ error: "review is local-only" }, { status: 403 });
  let body: { id?: string; verdict?: string; note?: string; finish?: boolean } = {};
  try { body = await req.json(); } catch { return Response.json({ error: "bad json" }, { status: 400 }); }
  const clips = reviewClips();
  const ids = clips.map((c) => c.id);
  const hash = clipListHash(ids);
  const now = new Date().toISOString();
  const existing = readReview();
  const r: HumanReview = existing && existing.clip_list_hash === hash
    ? existing
    : { reviewer: REVIEWER, clip_list_hash: hash, clip_ids: ids, started_at: now, finished_at: null, verdicts: {} };
  if (body.finish) {
    r.finished_at = now;
  } else {
    if (!body.id || !ids.includes(body.id)) return Response.json({ error: "unknown clip" }, { status: 400 });
    if (!VERDICTS.includes(body.verdict as HumanVerdict)) return Response.json({ error: "bad verdict" }, { status: 400 });
    r.verdicts[body.id] = { verdict: body.verdict as HumanVerdict, note: String(body.note ?? "").slice(0, 500), at: now };
  }
  writeReview(r);
  return Response.json({ ok: true, reviewed: Object.keys(r.verdicts).length, total: ids.length, finished: !!r.finished_at });
}
