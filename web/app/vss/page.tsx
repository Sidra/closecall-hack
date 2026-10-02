import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import Link from "next/link";
import { mediaSrc } from "@/lib/types";

export const metadata = { title: "Track B · VAST VSS · CloseCall" };
export const dynamic = "force-dynamic";

type Item = {
  id: string; query: string; similarity: number; vss_reasoning: string; original_video?: string | null;
  start_sec?: number | null; end_sec?: number | null; clip: string; keyframe: string;
  verdict: "near_miss" | "not_near_miss"; votes: Record<string, boolean>; evidence: string; conflict_type: string; models_answered: number;
};
type TrackB = { mode: string; base: string; generated_at: string; indexed_videos: number | null; queries: string[]; hits_found: number; items: Item[]; verifier: string; evaluated: boolean };

function load(): TrackB | null {
  const p = path.join(process.cwd(), "public", "data", "track_b.json");
  if (!existsSync(p)) return null;
  try { return JSON.parse(readFileSync(p, "utf8")) as TrackB; } catch { return null; }
}

export default function VssPage() {
  const d = load();
  return (
    <div className="wrap section">
      <div className="eyebrow">Track B · CloseCall on VAST VSS</div>
      <h2 style={{ marginTop: 10 }}>Track B: CloseCall over the provided footage in the team&apos;s VAST VSS index.</h2>
      <p className="muted" style={{ maxWidth: 820 }}>
        Track A (the rest of this app) runs our YOLO26 + PET pipeline on public CC clips. Track B starts from the event&apos;s own
        footage, already ingested by NVIDIA VSS on VAST (Cosmos Reason captions + Cosmos Embed vectors in VAST DataBase):
        CloseCall asks VSS for near-miss moments in plain words, downloads each hit, pixelates heads and plates in tracked
        boxes with our YOLO26 pass, and sends an 8-frame storyboard to the same 3-model vote on W&amp;B Inference.
        <b> Not evaluated:</b> there are no labels for this footage, so these are flags for an engineer to review, not measured results.
      </p>
      {!d ? (
        <div className="card flat" style={{ marginTop: 18 }}>
          <div className="chip violet">not connected</div>
          <h3 style={{ marginTop: 10 }}>VAST VSS client built and tested against the team API&apos;s public route; not connected (no credentials today).</h3>
          <ul className="muted" style={{ fontSize: 14, marginBottom: 0 }}>
            <li><span className="mono">pipeline/vss.py</span>: JWT login, semantic search, explore, segment metadata and stream download, synthesize, and re-ingest with a custom prompt, all against the documented VSS API.</li>
            <li>Tested live against the team instance&apos;s public <span className="mono">/api/v1/metadata/ingest-config</span> route (it returned the real capture types and scenarios). The authenticated routes need the team login, which wasn&apos;t available today.</li>
            <li><span className="mono">pipeline/track_b.py</span> is the Track B run: VSS search → download → YOLO26 pixelation → storyboard → the same 3-model W&amp;B vote. Its anonymise → storyboard → vote path was dry-run on a local clip. No VSS results are shown, because none were fetched.</li>
            <li>No footage from the internet is ever ingested into VSS.</li>
          </ul>
        </div>
      ) : (
        <>
          <div className="grid g4" style={{ marginTop: 18 }}>
            <div className="card flat"><div className="k">VSS index</div><div className="big">{d.indexed_videos ?? "?"}</div><div className="muted">indexed videos (team instance)</div></div>
            <div className="card flat"><div className="k">Plain-language queries</div><div className="big">{d.queries.length}</div><div className="muted">{d.hits_found} distinct segments returned</div></div>
            <div className="card flat"><div className="k">Triaged</div><div className="big">{d.items.length}</div><div className="muted">top hits by VSS similarity</div></div>
            <div className="card flat"><div className="k">Flagged for review</div><div className="big" style={{ color: "var(--red)" }}>{d.items.filter((i) => i.verdict === "near_miss").length}</div><div className="muted">2-of-3 vote · not evaluated</div></div>
          </div>
          <p className="faint mono" style={{ fontSize: 12 }}>Live run {d.generated_at} against {d.base.replace(/^https?:\/\//, "")} · {d.verifier}</p>
          <div className="grid g3" style={{ marginTop: 14 }}>
            {d.items.map((it) => (
              <div className="card" key={it.id} style={{ padding: 12 }}>
                <video src={mediaSrc(it.clip)} poster={mediaSrc(it.keyframe)} controls muted loop playsInline preload="none" />
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
                  <span className={`chip ${it.verdict === "near_miss" ? "red" : ""}`}><span className="dot" />model: {it.verdict === "near_miss" ? "near-miss flag" : "no conflict"}</span>
                  <span className="chip">VSS similarity {it.similarity}</span>
                  <span className="chip violet">not evaluated</span>
                </div>
                <p style={{ margin: "8px 0 0", fontSize: 13.5 }}><b>Query:</b> “{it.query}”</p>
                <p className="muted clamp2" style={{ margin: "6px 0 0", fontSize: 13.5 }} title={it.vss_reasoning}><b>Cosmos (VSS) caption:</b> {it.vss_reasoning}</p>
                <p style={{ margin: "6px 0 0", fontSize: 13.5 }}><b>Vote:</b> {it.evidence}</p>
              </div>
            ))}
          </div>
        </>
      )}
      <p style={{ marginTop: 24 }}><Link href="/demo">← Track A guided demo</Link></p>
    </div>
  );
}
