import { limited } from "@/lib/ratelimit";
import { getLedger, getMemos } from "@/lib/data";

const MODEL = "nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B";
const SYSTEM =
  "You are a traffic-safety engineer writing a one-page memo to a city council. Use only the evidence given. Cite every clip by its id in square brackets. Never identify a person or plate. Do not invent statistics, distances, speeds, signal timings or any detail not in the evidence. Call the events \'AI-labelled near-misses for the engineer\'s review\'. Be specific and plain. Markdown, under 300 words.";

/** Regenerate the fix memo live on W&B Inference; on any failure return the cached memo, marked. */
export async function POST(req: Request) {
  if (limited(req, 5)) return Response.json({ error: "rate limited, try again in a minute" }, { status: 429 });
  let intersection = "";
  try { intersection = String((await req.json())?.intersection ?? ""); } catch { /* bad body */ }
  const cached = getMemos().find((m) => m.intersection === intersection);
  const rows = getLedger().filter((r) => r.label === "near_miss" && r.intersection === intersection);
  if (!rows.length) return Response.json({ error: "unknown intersection" }, { status: 404 });
  const key = process.env.VIDEO_HACK_WANDB_API_KEY;
  const evidence = rows.map(({ id, pair, pet_s, reviewer_note }) => ({ id, pair, pet_s, reviewer_note }));
  try {
    if (!key) throw new Error("no W&B key");
    const r = await fetch("https://api.inference.wandb.ai/v1/chat/completions", {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json", "User-Agent": "curl/8.7.1" },
      body: JSON.stringify({
        model: MODEL, temperature: 0.3, max_tokens: 6000,
        messages: [
          { role: "system", content: SYSTEM },
          { role: "user", content: `Intersection: ${intersection}\nAI-labelled near-miss events, for the engineer's review (from anonymised camera footage):\n${JSON.stringify(evidence, null, 1)}\n\nWrite: 1) what is happening, 2) the pattern, 3) up to three concrete fixes (e.g. leading pedestrian interval, daylighting the corners, no turn on red, hardened centre line), each tied to the clips it addresses, 4) what to measure after the fix.` },
        ],
      }),
      signal: AbortSignal.timeout(30000),
    });
    if (!r.ok) throw new Error(`W&B ${r.status}`);
    const d = await r.json();
    if (!d.choices?.[0]?.message?.content) throw new Error("empty memo content");
    return Response.json({ intersection, clips: rows.map((x) => x.id), markdown: d.choices[0].message.content.trim(), model: MODEL, generated_at: new Date().toISOString(), cached: false });
  } catch (e) {
    if (cached) return Response.json({ ...cached, cached: true, fallback_reason: String(e).slice(0, 120) });
    return Response.json({ error: String(e).slice(0, 160) }, { status: 502 });
  }
}
