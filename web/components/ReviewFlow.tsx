"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { mediaSrc } from "@/lib/types";

type Clip = { id: string; clip: string; keyframe: string; pet_s: number; a_cls: string; b_cls: string; intersection: string };
type V = "near_miss" | "not_near_miss" | "unsure";
const BUTTONS: [V, string, string][] = [["near_miss", "1", "Near-miss"], ["not_near_miss", "2", "Not a near-miss"], ["unsure", "3", "Unsure"]];

export function ReviewFlow({ clips }: { clips: Clip[] }) {
  const [done, setDone] = useState<Set<string>>(new Set());
  const [i, setI] = useState(0);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [finished, setFinished] = useState(false);
  const noteRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetch("/api/review").then((r) => r.json()).then((d) => {
      if (d.error) { setErr(d.error); return; }
      const s = new Set<string>(d.done);
      setDone(s);
      setFinished(d.finished);
      const next = clips.findIndex((c) => !s.has(c.id));
      setI(next === -1 ? clips.length : next);
    }).catch(() => setErr("could not reach the review API"));
  }, [clips]);

  const answer = useCallback(async (v: V) => {
    const c = clips[i];
    if (!c || busy) return;
    setBusy(true); setErr("");
    try {
      const r = await fetch("/api/review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: c.id, verdict: v, note }) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "save failed");
      const s = new Set(done); s.add(c.id); setDone(s); setNote("");
      const next = clips.findIndex((x, j) => j > i && !s.has(x.id));
      setI(next === -1 ? clips.length : next);
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  }, [clips, i, busy, note, done]);

  const finish = async () => {
    const r = await fetch("/api/review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ finish: true }) });
    if (r.ok) setFinished(true);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (document.activeElement === noteRef.current) return;
      const b = BUTTONS.find(([, k]) => k === e.key);
      if (b) { e.preventDefault(); answer(b[0]); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [answer]);

  const c = clips[i];
  return (
    <div className="wrap section" style={{ maxWidth: 900 }}>
      <div className="eyebrow">Human review · blind</div>
      <h2 style={{ marginTop: 10 }}>Is this a near-miss?</h2>
      <p className="muted" style={{ fontSize: 14 }}>
        Each clip shows two road users, A (amber) and B (cyan), who passed through the same spot within the time shown.
        The AI labels and the model votes stay hidden until you have answered every clip. Keys: <b className="mono">1</b> near-miss · <b className="mono">2</b> not · <b className="mono">3</b> unsure.
      </p>
      <div className="k" style={{ margin: "12px 0" }}>{Math.min(done.size + (c && !done.has(c.id) ? 1 : 0), clips.length)} of {clips.length}{done.size ? ` · ${done.size} answered` : ""}</div>
      <div style={{ height: 4, background: "var(--line-strong)", borderRadius: 2 }}><div style={{ height: 4, width: `${(done.size / clips.length) * 100}%`, background: "var(--amber)", borderRadius: 2 }} /></div>
      {err && <p style={{ color: "var(--red)" }}>{err}</p>}
      {c ? (
        <div className="card" style={{ marginTop: 16 }}>
          <video key={c.id} src={mediaSrc(c.clip)} poster={mediaSrc(c.keyframe)} autoPlay muted loop playsInline controls />
          <h3 style={{ marginTop: 12 }}><span style={{ color: "var(--amber)" }}>A {c.a_cls}</span> → <span style={{ color: "var(--cyan)" }}>B {c.b_cls}</span> · {c.pet_s.toFixed(2)} s apart on screen</h3>
          <div className="faint mono" style={{ fontSize: 12 }}>{c.id}</div>
          <textarea ref={noteRef} value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} placeholder="Optional note (what you saw)"
            style={{ width: "100%", marginTop: 12, minHeight: 60, borderRadius: 8, border: "1px solid var(--line-strong)", background: "var(--bg-2)", color: "var(--ink)", padding: 10, fontFamily: "var(--sans)", fontSize: 14 }} />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
            {BUTTONS.map(([v, k, label]) => (
              <button key={v} className={`btn ${v === "near_miss" ? "primary" : ""}`} disabled={busy} onClick={() => answer(v)}><span className="mono">{k}</span> {label}</button>
            ))}
          </div>
        </div>
      ) : (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>All {clips.length} clips answered.</h3>
          {finished
            ? <p className="muted">Saved and marked finished in <span className="mono">eval/human_review.json</span>. The ledger and evals now show the human column.</p>
            : <><p className="muted">Saved to <span className="mono">eval/human_review.json</span>. Mark the review finished to publish it to the other pages.</p><button className="btn primary" onClick={finish}>Mark review finished</button></>}
        </div>
      )}
    </div>
  );
}
