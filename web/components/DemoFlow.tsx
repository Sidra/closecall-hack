"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { Eval, Memo, Row, Run } from "@/lib/types";
import { ClipCard, LabelChip, VerdictChip } from "./ClipCard";
import { Headline } from "./Headline";
import { HumanLine } from "./HumanLine";
import { mediaSrc } from "@/lib/types";
import { Markdown } from "./Markdown";
import { StoreNotice } from "./StoreNotice";

type Hit = { id: string; score: number };
type SearchState = { q: string; mode: string; results: Hit[]; refused?: string; cached?: boolean } | null;

const REFUSE_Q = "Who was driving the white car? Read me its plate.";

export function DemoFlow({ run, rows, memos, ev, human }: { run: Run; rows: Row[]; memos: Memo[]; ev: Eval | null; human: Parameters<typeof HumanLine>[0]["s"] }) {
  const [step, setStep] = useState(0);
  const [search, setSearch] = useState<SearchState>(null);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [memo, setMemo] = useState<Memo | null>(memos[0] ?? null);
  const [memoNote, setMemoNote] = useState("pre-cached from the pipeline run");
  const timers = useRef<number[]>([]);
  const t = run.totals;
  const verified = rows.filter((r) => r.verdict === "near_miss");
  const confirmed = rows.filter((r) => r.label === "near_miss")
    .sort((a, b) => Number(b.verdict === "near_miss") - Number(a.verdict === "near_miss") || a.pet_s - b.pet_s);
  const lead = confirmed[0];
  const vname = run.verifier_version === "v3" ? "2-of-3 vision-model vote (W&B Inference)" : "Nemotron Omni verifier";
  const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
  const demoQs = Object.keys(run.search.demo);

  const runSearch = async (query: string, instant = false) => {
    setQ(query);
    if (instant && run.search.demo[query]) {
      setSearch({ q: query, mode: run.search.mode, results: run.search.demo[query], cached: true });
      return;
    }
    setBusy(true);
    try {
      const r = await fetch("/api/search", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ q: query }) });
      const d = await r.json();
      setSearch({ q: query, mode: d.mode ?? "refused", results: d.results ?? [], refused: d.refused ? d.message : undefined });
    } catch {
      setSearch({ q: query, mode: "error", results: [] });
    } finally { setBusy(false); }
  };

  const regenerate = async () => {
    if (!memo) return;
    setBusy(true);
    try {
      const r = await fetch("/api/memo", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ intersection: memo.intersection }) });
      const d = await r.json();
      if (d.markdown) { setMemo(d); setMemoNote(d.cached ? `W&B unavailable (${d.fallback_reason}); showing cached memo` : `generated live just now on W&B Inference · ${d.model}`); }
    } finally { setBusy(false); }
  };

  const instant = () => {
    timers.current.forEach(clearTimeout);
    setStep(1);
    const plan: [number, () => void][] = [
      [1600, () => setStep(2)],
      [3600, () => { setStep(3); if (demoQs[0]) runSearch(demoQs[0], true); }],
      [6200, () => setStep(4)],
      [8200, () => setStep(5)],
    ];
    timers.current = plan.map(([ms, fn]) => window.setTimeout(fn, ms));
  };

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("instant") !== "1") return;
    const id = window.setTimeout(instant, 400);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once on mount
  }, []);

  const S = (n: number, title: string, body: React.ReactNode) => (
    <div className={`step ${step >= n ? "on" : ""}`} style={{ opacity: step >= n || step === 0 ? 1 : 0.45 }}>
      <div className="n">{n}</div>
      <div><h3 style={{ marginTop: 4 }}>{title}</h3>{step >= n && <div className="fade" style={{ marginTop: 10 }}>{body}</div>}</div>
    </div>
  );

  return (
    <div className="wrap section">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap", alignItems: "end" }}>
        <div>
          <div className="eyebrow">Guided run</div>
          <h2 style={{ marginTop: 10 }}>From footage nobody watched to a filed fix memo.</h2>
          <p className="muted" style={{ maxWidth: 720 }}>Instant Demo replays the pre-cached pipeline run (every number below was measured on it). Search and memo can also run live.</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn primary" onClick={instant}>⚡ Instant Demo</button>
          <button className="btn" onClick={() => setStep((s) => Math.min(5, s + 1))}>Next step →</button>
        </div>
      </div>
      {step >= 1 && lead && (
        <div className="card evidence fade" style={{ marginTop: 18 }}>
          <video src={mediaSrc(lead.clip)} poster={mediaSrc(lead.keyframes[1] ?? lead.keyframes[0])} autoPlay muted loop playsInline />
          <div>
            <div className="k">Evidence · {lead.intersection}</div>
            <h3 style={{ marginTop: 6 }}><span style={{ color: "var(--amber)" }}>A {lead.a_cls}</span> → <span style={{ color: "var(--cyan)" }}>B {lead.b_cls}</span>, {lead.pet_s.toFixed(2)} s apart</h3>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "10px 0" }}><VerdictChip v={lead.verdict} /><LabelChip l={lead.label} /></div>
            <p style={{ margin: 0, fontSize: 14 }}>“{lead.explanation}”</p>
            <div style={{ marginTop: 12 }}><Headline ev={ev} run={run} /><HumanLine s={human} /></div>
          </div>
        </div>
      )}
      <div style={{ margin: "14px 0 24px" }}><StoreNotice run={run} /></div>

      <div className="steps" style={{ gap: 26 }}>
        {S(1, `Ingest: ${Math.round(t.duration_s)} s of intersection footage, ${t.tracks} tracks`, (
          <div className="grid g4">
            {Object.entries(run.funnel).map(([id, f]) => (
              <div className="card flat" key={id} style={{ padding: 12 }}>
                <div className="k">{f.title}</div>
                <div className="mono" style={{ marginTop: 6 }}>{f.duration_s}s · {f.tracks} tracks</div>
                <div className="faint" style={{ fontSize: 12 }}>{run.sources[id]?.license} · {run.sources[id]?.author}</div>
              </div>
            ))}
          </div>
        ))}
        {S(2, "Stage 1 (cheap): YOLO26 tracking + post-encroachment time", (
          <div className="funnel">
            {[["Naive flags, PET < 4 s", t.naive, "pixel overlap alone"], ["Crossing paths, both moving", t.crossing, "physics filter"], ["Distinct events", t.events, "sent to the model"], ["Flagged for review", t.verified, `${vname}; ${t.confirmed_and_flagged ?? 0} of the ${t.confirmed ?? 0} labelled near-misses among them`]].map(([k, v, s], i) => (
              <div key={String(k)}>
                <div className="k">{k}</div>
                <div className="big" style={i === 3 ? { color: "var(--red)" } : undefined}>{v}</div>
                <div className="muted" style={{ fontSize: 13 }}>{s}</div>
                <div className="bar"><i style={{ width: `${Math.max(2, (Number(v) / t.naive) * 100)}%` }} /></div>
              </div>
            ))}
          </div>
        ))}
        {S(3, `Stage 2 (models): the ${vname} triaged ${t.verifier_calls} anonymised clips and flagged ${t.verified} for review; the AI labels mark ${t.confirmed ?? 0} near-misses`, (
          <>
            <p className="muted" style={{ marginTop: 0, fontSize: 14 }}>
              The models triage; an engineer reviews each flag before anything is filed. The labels here are AI-made (Claude Code, blind to the verdicts, pre-registered), not a human review. Below: the labelled near-misses, each with
              the model&apos;s own verdict ({run.verifier_version ?? "v1"}), agreement or not.
            </p>
            <div className="grid g3">{confirmed.slice(0, 6).map((r) => <ClipCard key={r.id} r={r} weaveUrl={run.weave.url} />)}</div>
            <p className="muted" style={{ fontSize: 14 }}>
              {verified.length} model flags in total, {verified.filter((r) => r.label === "near_miss").length} confirmed. <Link href="/ledger">See every flag and rejection in the ledger →</Link> · <Link href="/evals">precision →</Link>
            </p>
          </>
        ))}
        {S(4, "Ask in plain words", (
          <div>
            <form onSubmit={(e) => { e.preventDefault(); if (q.trim()) runSearch(q.trim()); }}>
              <input className="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. turning car cutting across a pedestrian" aria-label="Search the near-miss ledger" />
            </form>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
              {demoQs.map((x) => <button key={x} className="chip" style={{ cursor: "pointer", background: "none" }} onClick={() => runSearch(x)}>{x}</button>)}
              <button className="chip violet" style={{ cursor: "pointer", background: "none" }} onClick={() => runSearch(REFUSE_Q)}>{REFUSE_Q}</button>
            </div>
            {busy && <p className="muted mono">searching…</p>}
            {search && !busy && (
              <div style={{ marginTop: 14 }}>
                {search.refused
                  ? <div className="notice"><b>Refused.</b> {search.refused}</div>
                  : <>
                      <div className="faint mono" style={{ fontSize: 12, marginBottom: 8 }}>
                        “{search.q}” · {search.mode}{search.cached ? " · pre-cached result" : " · live"} · {search.results.length} hits
                      </div>
                      <div className="grid g3">{search.results.slice(0, 3).map((h) => byId[h.id] && (
                        <div key={h.id}><ClipCard r={byId[h.id]} /><div className="faint mono" style={{ fontSize: 11, marginTop: 4 }}>similarity {h.score}</div></div>
                      ))}</div>
                    </>}
              </div>
            )}
          </div>
        ))}
        {S(5, "The fix memo: cites the AI-labelled near-misses for the engineer’s review", memo?.markdown ? (
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
              <div><div className="k">Memo · {memo.intersection}</div><div className="faint mono" style={{ fontSize: 11.5 }}>{memoNote} · {memo.model}</div></div>
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", minWidth: 0 }}>
                {memos.length > 1 && (
                  <select className="theme-btn" value={memo.intersection} onChange={(e) => { const m = memos.find((x) => x.intersection === e.target.value); if (m) { setMemo(m); setMemoNote("pre-cached from the pipeline run"); } }} aria-label="Choose intersection">
                    {memos.filter((m) => m.markdown).map((m) => <option key={m.intersection}>{m.intersection}</option>)}
                  </select>
                )}
                <button className="btn" disabled={busy} onClick={regenerate}>{busy ? "Drafting…" : "↻ Regenerate live (W&B)"}</button>
              </div>
            </div>
            <div className="stripe" style={{ margin: "12px 0" }} />
            <Markdown text={memo.markdown} />
            <div className="faint mono" style={{ fontSize: 11.5, marginTop: 10 }}>Attached clips: {memo.clips.join(", ")}</div>
            <div style={{ marginTop: 14 }}><span className="chip green"><span className="dot" />Memo filed ✅ with {memo.clips.length} clips</span></div>
          </div>
        ) : <p className="muted">No memo in this run.</p>)}
      </div>
      {ev && ev.precision !== null && (
        <p className="muted" style={{ marginTop: 30 }}>Verifier precision on this run: <b className="mono">{Math.round(ev.precision * 100)}%</b> (against blind, pre-registered AI labels; {ev.scored} events scored). <Link href="/evals">Evals →</Link></p>
      )}
    </div>
  );
}
