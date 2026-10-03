"use client";
import { useEffect, useRef, useState } from "react";

type Source = { id: string; kind: "live" | "simulated"; title: string; license: string; label: string };
type Stats = { source: string | null; running: boolean; fps: number | null; frames: number; dropped: number; detect_ms_p50: number | null;
  events: number; flag_ms_p50: number | null; flag_ms_p95: number | null; vote_ms_p50: number | null; vote_ms_p95: number | null; votes_done: number; vote_on: boolean; uptime_s: number };
type Ev = { id: string; a_cls: string; b_cls: string; pet_s: number; pairs?: number; t: number; flag_ms: number; vulnerable: boolean;
  vote: string; votes?: Record<string, boolean>; evidence?: string; vote_ms?: number | null };

const NAMES: Record<string, string> = { "qwen3.6-35b": "Qwen", "minimax-m3": "MiniMax", "gemma-4-31b": "Gemma" };
const ms = (v: number | null | undefined) => (v == null ? "–" : v >= 1000 ? `${(v / 1000).toFixed(1)} s` : `${v} ms`);

function voteChip(e: Ev) {
  if (e.vote === "pending") return <span className="chip amber">vote pending…</span>;
  if (e.vote === "near_miss") return <span className="chip red"><span className="dot" />vote: near-miss flag</span>;
  if (e.vote === "not_near_miss") return <span className="chip">vote: no conflict</span>;
  if (e.vote === "low_priority") return <span className="chip">not voted (low priority)</span>;
  if (e.vote === "skipped") return <span className="chip">not voted (queue full)</span>;
  if (e.vote === "off") return <span className="chip">vote off (no W&amp;B key)</span>;
  return <span className="chip">vote unavailable</span>;
}

export function LiveView({ workerUrl }: { workerUrl: string }) {
  const [sources, setSources] = useState<Source[] | null>(null);
  const [err, setErr] = useState("");
  const [sel, setSel] = useState("caltrans-capistrano");
  const [stats, setStats] = useState<Stats | null>(null);
  const [events, setEvents] = useState<Ev[]>([]);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<string[] | null>(null);
  const [frameKey, setFrameKey] = useState(0);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    fetch(`${workerUrl}/sources`).then((r) => r.json()).then(setSources).catch(() => setErr("offline"));
  }, [workerUrl]);

  useEffect(() => {
    if (!sources) return;
    const es = new EventSource(`${workerUrl}/events`);
    esRef.current = es;
    es.addEventListener("stats", (m) => setStats(JSON.parse((m as MessageEvent).data)));
    es.addEventListener("reset", () => { setEvents([]); setHits(null); setFrameKey((k) => k + 1); });
    es.addEventListener("near_miss", (m) => { const e = JSON.parse((m as MessageEvent).data) as Ev; setEvents((x) => [e, ...x].slice(0, 60)); });
    es.addEventListener("update", (m) => { const u = JSON.parse((m as MessageEvent).data); setEvents((x) => x.map((e) => (e.id === u.id ? { ...e, ...u } : e))); });
    es.addEventListener("vote", (m) => { const u = JSON.parse((m as MessageEvent).data); setEvents((x) => x.map((e) => (e.id === u.id ? { ...e, ...u } : e))); });
    es.addEventListener("error", () => { /* EventSource retries on its own */ });
    return () => es.close();
  }, [sources, workerUrl]);

  const start = async () => {
    await fetch(`${workerUrl}/start`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source: sel }) });
    setFrameKey((k) => k + 1);
  };
  const stop = () => fetch(`${workerUrl}/stop`, { method: "POST" });
  const search = async () => {
    if (!q.trim()) { setHits(null); return; }
    const r = await fetch(`${workerUrl}/search?q=${encodeURIComponent(q.trim())}`).then((x) => x.json()).catch(() => null);
    setHits(r ? r.results.map((h: { id: string }) => h.id) : []);
  };

  const cur = sources?.find((s) => s.id === (stats?.source ?? sel));
  const shown = hits ? events.filter((e) => hits.includes(e.id)) : events;
  const flagged = events.filter((e) => e.vote === "near_miss").length;

  return (
    <div className="wrap section">
      <div className="eyebrow">Live · real-time near-miss detection</div>
      <h2 style={{ marginTop: 10 }}>Watch a camera, flag close calls as they happen.</h2>
      <p className="muted" style={{ maxWidth: 820, fontSize: 14.5 }}>
        Every frame: YOLO26 + ByteTrack → post-encroachment time computed incrementally as road users cross → an event the moment PET &lt; 4 s
        (same physics filter as the batch pipeline). Frames are pixelated before display. Each priority event (vulnerable road user, or PET &lt; 1.5 s)
        goes asynchronously to the same 3-model vote on W&amp;B Inference and its card updates when the vote returns. All numbers below are measured live on this machine.
      </p>

      {err === "offline" ? (
        <div className="card flat" style={{ marginTop: 16 }}>
          <div className="chip violet">worker not running</div>
          <h3 style={{ marginTop: 10 }}>The live worker runs locally.</h3>
          <p className="muted" style={{ fontSize: 14 }}>Start it with <span className="mono">.venv/bin/python -m pipeline.live</span> (port 3503), then reload. The public deployment shows the pre-cached batch demo; live mode needs a local machine with the model weights.</p>
        </div>
      ) : (
        <>
          <div className="card flat" style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginTop: 14 }}>
            <select className="theme-btn" style={{ height: 40 }} value={sel} onChange={(e) => setSel(e.target.value)} aria-label="Video source">
              {sources?.map((s) => <option key={s.id} value={s.id}>{s.kind === "live" ? "● LIVE · " : "▶ simulated · "}{s.title}</option>)}
            </select>
            <button className="btn primary" onClick={start}>Start</button>
            <button className="btn" onClick={stop}>Stop</button>
            {cur && <span className={`chip ${cur.kind === "live" ? "red" : "violet"}`}><span className="dot" />{cur.label}</span>}
          </div>
          {cur && <p className="faint" style={{ fontSize: 12.5, margin: "6px 0 0" }}>{cur.license}</p>}

          <div className="evidence" style={{ marginTop: 14, alignItems: "start" }}>
            <div className="card" style={{ padding: 10 }}>
              {/* eslint-disable-next-line @next/next/no-img-element -- MJPEG stream from the local worker */}
              <img key={frameKey} src={`${workerUrl}/stream.mjpg`} alt="Live pixelated camera frame with tracked road users" style={{ width: "100%", borderRadius: 8, background: "#000", minHeight: 200 }} />
            </div>
            <div className="grid g2" style={{ gap: 10 }}>
              {[
                ["Processed fps", stats?.fps ?? "–", "rolling 10 s"],
                ["Frame → flag", `${ms(stats?.flag_ms_p50)} / ${ms(stats?.flag_ms_p95)}`, "p50 / p95, from frame arrival"],
                ["Events", stats?.events ?? 0, `${flagged} vote-flagged`],
                ["Vote latency", `${ms(stats?.vote_ms_p50)} / ${ms(stats?.vote_ms_p95)}`, stats?.vote_on ? `p50 / p95 · ${stats?.votes_done ?? 0} votes` : "vote off (no W&B key)"],
                ["Detect + track", ms(stats?.detect_ms_p50), "per frame, p50"],
                ["Frames", stats?.frames ?? 0, `${stats?.dropped ?? 0} dropped`],
              ].map(([k, v, s]) => (
                <div className="card flat" key={String(k)} style={{ padding: 12 }}><div className="k">{k}</div><div className="mono" style={{ fontSize: 22, fontWeight: 700 }}>{v}</div><div className="faint" style={{ fontSize: 12 }}>{s}</div></div>
              ))}
            </div>
          </div>
          <p className="faint" style={{ fontSize: 12.5 }}>Latency is measured from the moment a frame reaches this machine. For the live camera, the stream&apos;s own delivery delay (HLS) is not included.</p>

          <form onSubmit={(e) => { e.preventDefault(); search(); }} style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <input className="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search live events, e.g. pedestrian, truck, turning" aria-label="Search live events" />
            <button className="btn" type="submit">Search</button>
          </form>
          {hits && <p className="faint mono" style={{ fontSize: 12 }}>keyword search over the live index · {hits.length} hits · <button className="chip" style={{ cursor: "pointer", background: "none" }} onClick={() => { setQ(""); setHits(null); }}>clear</button></p>}

          <div className="grid g3" style={{ marginTop: 12 }}>
            {shown.map((e) => (
              <div className="card fade" key={e.id} style={{ padding: 10 }}>
                {/* eslint-disable-next-line @next/next/no-img-element -- pixelated thumbnail from the local worker */}
                <img src={`${workerUrl}/thumb/${encodeURIComponent(e.id)}.jpg`} alt="Pixelated crop around the conflict point" style={{ width: "100%", borderRadius: 6, aspectRatio: "16/10", objectFit: "cover", background: "#000" }} />
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
                  <span className="chip amber mono">PET {e.pet_s.toFixed(2)} s</span>
                  <span className="chip mono">flag {ms(e.flag_ms)}</span>
                  {voteChip(e)}
                </div>
                <div style={{ fontSize: 14, marginTop: 6 }}><b>{e.a_cls}</b> → <b>{e.b_cls}</b>{(e.pairs ?? 1) > 1 && <span className="faint"> · {e.pairs} pairs</span>} <span className="faint mono">· {e.id} · t={e.t.toFixed(1)}s</span></div>
                {e.votes && Object.keys(e.votes).length > 0 && (
                  <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 6 }}>
                    {Object.entries(e.votes).map(([m, v]) => <span key={m} className={`chip ${v ? "red" : ""}`}>{NAMES[m] ?? m}: {v ? "yes" : "no"}</span>)}
                    {e.vote_ms != null && <span className="chip mono">vote {ms(e.vote_ms)}</span>}
                  </div>
                )}
                {e.evidence && <p className="muted clamp2" style={{ fontSize: 13, margin: "6px 0 0" }} title={e.evidence}>{e.evidence}</p>}
              </div>
            ))}
          </div>
          {events.length === 0 && <p className="muted" style={{ marginTop: 12 }}>No events yet. Pick a source and press Start; live cameras can be quiet.</p>}
        </>
      )}
    </div>
  );
}
