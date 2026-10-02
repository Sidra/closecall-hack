import { limited } from "@/lib/ratelimit";
import { getLedger, getVectors } from "@/lib/data";
import { cosine, isIdentityQuery, keywordScore, REFUSAL } from "@/lib/search";

const EMBED_MODEL = "nvidia/nemotron-3-embed-1b";

export async function POST(req: Request) {
  if (limited(req, 30)) return Response.json({ error: "rate limited, try again in a minute" }, { status: 429 });
  let q = "";
  try { q = String((await req.json())?.q ?? "").slice(0, 300).trim(); } catch { /* bad body */ }
  if (!q) return Response.json({ error: "empty query" }, { status: 400 });
  if (isIdentityQuery(q)) return Response.json({ refused: true, message: REFUSAL, results: [] });

  const ledger = getLedger().filter((r) => r.verdict === "near_miss" || r.label === "near_miss");
  const vectors = getVectors();
  const key = process.env.VIDEO_HACK_NVIDIA_API_KEY;
  if (key && Object.keys(vectors).length) {
    try {
      const r = await fetch("https://integrate.api.nvidia.com/v1/embeddings", {
        method: "POST",
        headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
        body: JSON.stringify({ model: EMBED_MODEL, input: [q], input_type: "query" }),
        signal: AbortSignal.timeout(12000),
      });
      if (!r.ok) throw new Error(`embed ${r.status}`);
      const qv: number[] = (await r.json()).data[0].embedding;
      const results = ledger
        .filter((row) => vectors[row.id])
        .map((row) => ({ id: row.id, score: Number(cosine(qv, vectors[row.id]).toFixed(4)) }))
        .sort((a, b) => b.score - a.score)
        .slice(0, 5);
      return Response.json({ mode: "nvidia-embeddings", model: EMBED_MODEL, results });
    } catch (e) {
      const results = ledger.map((row) => ({ id: row.id, score: Number(keywordScore(q, row).toFixed(3)) }))
        .filter((x) => x.score > 0).sort((a, b) => b.score - a.score).slice(0, 5);
      return Response.json({ mode: "keyword-fallback", reason: String(e).slice(0, 120), results });
    }
  }
  const results = ledger.map((row) => ({ id: row.id, score: Number(keywordScore(q, row).toFixed(3)) }))
    .filter((x) => x.score > 0).sort((a, b) => b.score - a.score).slice(0, 5);
  return Response.json({ mode: "keyword-fallback", reason: "no embedding key or index", results });
}
