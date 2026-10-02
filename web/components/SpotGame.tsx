"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { mediaSrc } from "@/lib/types";

export type Round = {
  id: string; clip: string; keyframe: string; pet_s: number; a_cls: string; b_cls: string; intersection: string;
  label: "near_miss" | "not_near_miss"; model: "near_miss" | "not_near_miss"; votes: Record<string, boolean>; explanation: string;
};
type Pick = "near_miss" | "not_near_miss" | null;
type Result = { round: Round; pick: Pick; ms: number; points: number };
type Entry = { initials: string; score: number; agree: number; at: string };

const ROUNDS = 10;
const SECONDS = 10;
const LB_KEY = "closecall-play-leaderboard-v1";
const MODEL_NAMES: Record<string, string> = { "qwen3.6-35b": "Qwen", "minimax-m3": "MiniMax", "gemma-4-31b": "Gemma" };

/** Small seeded PRNG so a game is reproducible from its seed (shown on the end card). */
function rng(seed: number) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 2 ** 32; };
}

function deal(pool: Round[], seed: number): Round[] {
  const r = rng(seed);
  const shuffle = <T,>(a: T[]) => { const b = [...a]; for (let i = b.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [b[i], b[j]] = [b[j], b[i]]; } return b; };
  const near = shuffle(pool.filter((p) => p.label === "near_miss"));
  const flagsSafe = shuffle(pool.filter((p) => p.label !== "near_miss" && p.model === "near_miss"));
  const rest = shuffle(pool.filter((p) => p.label !== "near_miss" && p.model !== "near_miss"));
  const pick = [...near.slice(0, 3), ...flagsSafe.slice(0, 3), ...rest].slice(0, ROUNDS);
  return shuffle(pick);
}

const points = (correct: boolean, ms: number, streak: number) => {
  if (!correct) return 0;
  const speed = Math.max(0, Math.round((SECONDS * 1000 - ms) / 100)); // up to +100
  const mult = streak >= 5 ? 2 : streak >= 3 ? 1.5 : 1;
  return Math.round((100 + speed) * mult);
};

function readLB(): Entry[] {
  try { const v = JSON.parse(localStorage.getItem(LB_KEY) || "[]"); return Array.isArray(v) ? v.slice(0, 10) : []; } catch { return []; }
}
function writeLB(e: Entry[]) {
  try { localStorage.setItem(LB_KEY, JSON.stringify(e.slice(0, 10))); } catch { /* storage unavailable */ }
  window.dispatchEvent(new Event("closecall-lb"));
}
const lbSubscribe = (cb: () => void) => {
  window.addEventListener("storage", cb); window.addEventListener("closecall-lb", cb);
  return () => { window.removeEventListener("storage", cb); window.removeEventListener("closecall-lb", cb); };
};
const lbSnapshot = () => { try { return localStorage.getItem(LB_KEY) || "[]"; } catch { return "[]"; } };

const verdictText = (v: Pick) => (v === "near_miss" ? "Near-miss" : v === "not_near_miss" ? "Safe" : "No answer");

export function SpotGame({ pool }: { pool: Round[] }) {
  const [seed, setSeed] = useState<number | null>(null);
  const [i, setI] = useState(0);
  const [results, setResults] = useState<Result[]>([]);
  const [revealed, setRevealed] = useState<Result | null>(null);
  const [left, setLeft] = useState(SECONDS * 1000);
  const lbRaw = useSyncExternalStore(lbSubscribe, lbSnapshot, () => "[]");
  const lb = useMemo<Entry[]>(() => { try { const v = JSON.parse(lbRaw); return Array.isArray(v) ? v.slice(0, 10) : []; } catch { return []; } }, [lbRaw]);
  const [initials, setInitials] = useState("");
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);
  const started = useRef(0);

  const rounds = useMemo(() => (seed === null ? [] : deal(pool, seed)), [pool, seed]);
  const round = rounds[i];
  const done = seed !== null && i >= rounds.length;
  const streak = (() => { let s = 0; for (let k = results.length - 1; k >= 0 && results[k].points > 0; k--) s++; return s; })();
  const score = results.reduce((a, r) => a + r.points, 0);

  const start = () => { setSeed(Math.floor(Math.random() * 1e9)); setI(0); setResults([]); setRevealed(null); setSaved(false); setCopied(false); };

  const answer = useCallback((pick: Pick) => {
    if (!round || revealed) return;
    const ms = Math.min(SECONDS * 1000, Date.now() - started.current);
    const correct = pick === round.label;
    const res = { round, pick, ms, points: points(correct, ms, correct ? streak + 1 : 0) };
    setResults((r) => [...r, res]);
    setRevealed(res);
  }, [round, revealed, streak]);

  const next = useCallback(() => { setRevealed(null); setI((x) => x + 1); }, []);

  // round timer
  useEffect(() => {
    if (!round || revealed) return;
    started.current = Date.now();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset the visible countdown when a new round starts
    setLeft(SECONDS * 1000);
    const id = window.setInterval(() => {
      const l = SECONDS * 1000 - (Date.now() - started.current);
      setLeft(Math.max(0, l));
      if (l <= 0) { window.clearInterval(id); answer(null); }
    }, 100);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- restart only when the round changes
  }, [round?.id, revealed === null]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName === "INPUT") return;
      if (!revealed && round && (e.key === "1" || e.key === "2")) { e.preventDefault(); answer(e.key === "1" ? "near_miss" : "not_near_miss"); }
      else if (revealed && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); next(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [answer, next, revealed, round]);

  const playerAgree = results.filter((r) => r.pick === r.round.label).length;
  const modelAgree = results.filter((r) => r.round.model === r.round.label).length;

  const shareText = `CloseCall · Spot the Near-Miss: ${score} pts · I matched the label on ${playerAgree}/${results.length}; the 3-model vote matched ${modelAgree}/${results.length}. (Labels are AI-made and blind; it's a game.)`;

  const save = () => {
    const ini = initials.toUpperCase().replace(/[^A-Z]/g, "").slice(0, 3);
    if (!ini) return;
    const e = [...readLB(), { initials: ini, score, agree: playerAgree, at: new Date().toISOString().slice(0, 10) }].sort((a, b) => b.score - a.score).slice(0, 10);
    writeLB(e); setSaved(true);
  };

  return (
    <div className="wrap section" style={{ maxWidth: 860 }}>
      <div className="eyebrow">Play · Spot the Near-Miss</div>
      <h2 style={{ marginTop: 10 }}>Near-miss or safe? You have {SECONDS} seconds.</h2>
      <p className="muted" style={{ fontSize: 14, maxWidth: 680 }}>
        Each round loops one anonymised intersection clip. A (amber) and B (cyan) passed the same spot moments apart. Call it, then see
        what the 3-model vote and the label said. <b>The labels are AI-made and blind; this is a game, not an evaluation.</b> Your answers stay in this browser and are never written to any eval file.
      </p>

      {seed === null && (
        <div className="card" style={{ marginTop: 18 }}>
          <h3>{ROUNDS} rounds · +100 for matching the label · speed bonus · streak ×1.5 at 3, ×2 at 5</h3>
          <p className="muted" style={{ fontSize: 14 }}>Keys: <b className="mono">1</b> near-miss · <b className="mono">2</b> safe · <b className="mono">Enter</b> next.</p>
          <button className="btn primary" onClick={start}>▶ Start</button>
          {lb.length > 0 && <Leaderboard lb={lb} />}
        </div>
      )}

      {round && (
        <div className="card fade" style={{ marginTop: 18 }} key={round.id}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
            <div className="k">Round {i + 1} of {rounds.length} · score <span className="mono" style={{ color: "var(--ink)" }}>{score}</span>{streak >= 2 && <> · streak {streak}🔥</>}</div>
            {!revealed && <div className="mono" style={{ color: left < 3000 ? "var(--red)" : "var(--amber)" }}>{(left / 1000).toFixed(1)} s</div>}
          </div>
          {!revealed && <div style={{ height: 4, background: "var(--line-strong)", borderRadius: 2, margin: "8px 0 10px" }}><div style={{ height: 4, width: `${(left / (SECONDS * 1000)) * 100}%`, background: left < 3000 ? "var(--red)" : "var(--amber)", borderRadius: 2 }} /></div>}
          <video src={mediaSrc(round.clip)} poster={mediaSrc(round.keyframe)} autoPlay muted loop playsInline />
          <h3 style={{ marginTop: 10 }}><span style={{ color: "var(--amber)" }}>A {round.a_cls}</span> → <span style={{ color: "var(--cyan)" }}>B {round.b_cls}</span></h3>
          {!revealed ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 12 }}>
              <button className="btn primary" style={{ height: 56, justifyContent: "center" }} onClick={() => answer("near_miss")}><span className="mono">1</span> Near-miss</button>
              <button className="btn" style={{ height: 56, justifyContent: "center" }} onClick={() => answer("not_near_miss")}><span className="mono">2</span> Safe</button>
            </div>
          ) : (
            <Reveal r={revealed} onNext={next} last={i === rounds.length - 1} />
          )}
        </div>
      )}

      {done && (
        <div className="card fade" style={{ marginTop: 18 }}>
          <div className="k">Final</div>
          <div className="big">{score} pts</div>
          <div className="grid g3" style={{ marginTop: 12 }}>
            <div className="card flat"><div className="k">You</div><div className="big" style={{ fontSize: 30 }}>{playerAgree}/{results.length}</div><div className="muted">matched the label</div></div>
            <div className="card flat"><div className="k">3-model vote</div><div className="big" style={{ fontSize: 30 }}>{modelAgree}/{results.length}</div><div className="muted">matched the label</div></div>
            <div className="card flat"><div className="k">The label</div><div className="big" style={{ fontSize: 30 }}>AI</div><div className="muted">blind, pre-registered; not ground truth</div></div>
          </div>
          <pre className="mono" style={{ whiteSpace: "pre-wrap", background: "var(--bg-2)", border: "1px solid var(--line)", borderRadius: 8, padding: 12, fontSize: 13, marginTop: 14 }}>{shareText}</pre>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button className="btn" onClick={() => { navigator.clipboard?.writeText(shareText).then(() => setCopied(true)).catch(() => setCopied(false)); }}>{copied ? "Copied ✓" : "Copy score card"}</button>
            <button className="btn primary" onClick={start}>↻ Play again</button>
            <Link className="btn" href="/evals">How the real eval works →</Link>
          </div>
          {!saved ? (
            <form onSubmit={(e) => { e.preventDefault(); save(); }} style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap", alignItems: "center" }}>
              <label className="muted" style={{ fontSize: 14 }}>Initials for this browser&apos;s leaderboard:</label>
              <input className="search" style={{ width: 90, height: 40, textTransform: "uppercase" }} maxLength={3} value={initials} onChange={(e) => setInitials(e.target.value)} aria-label="Initials (letters only)" />
              <button className="btn" type="submit">Save</button>
            </form>
          ) : <p className="muted" style={{ fontSize: 13 }}>Saved in this browser only.</p>}
          {lb.length > 0 && <Leaderboard lb={lb} />}
        </div>
      )}
    </div>
  );
}

function Reveal({ r, onNext, last }: { r: Result; onNext: () => void; last: boolean }) {
  const correct = r.pick === r.round.label;
  const closeness = Math.max(4, Math.min(100, ((4 - r.round.pet_s) / 4) * 100));
  return (
    <div className="fade" style={{ marginTop: 12 }}>
      <div className="grid reveal3">
        <div className="card flat"><div className="k">You</div><div style={{ fontWeight: 700, marginTop: 4 }}>{verdictText(r.pick)}</div>
          <div className={`chip ${correct ? "green" : "red"}`} style={{ marginTop: 6 }}>{correct ? `+${r.points}` : r.pick ? "missed" : "time up"}</div></div>
        <div className="card flat"><div className="k">3-model vote</div><div style={{ fontWeight: 700, marginTop: 4 }}>{verdictText(r.round.model)}</div>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 6 }}>
            {Object.entries(r.round.votes).map(([m, v]) => <span key={m} className={`chip ${v ? "red" : ""}`}>{MODEL_NAMES[m] ?? m}: {v ? "yes" : "no"}</span>)}
          </div></div>
        <div className="card flat"><div className="k">AI label (blind)</div><div style={{ fontWeight: 700, marginTop: 4 }}>{verdictText(r.round.label)}</div></div>
      </div>
      <div style={{ marginTop: 12 }}>
        <div className="k">How close was it · PET {r.round.pet_s.toFixed(2)} s (on screen)</div>
        <div style={{ height: 10, background: "var(--line-strong)", borderRadius: 5, marginTop: 6 }}><div style={{ height: 10, width: `${closeness}%`, background: "var(--red)", borderRadius: 5 }} /></div>
        <div className="faint" style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}><span>4 s apart</span><span>same moment</span></div>
      </div>
      <p className="muted" style={{ fontSize: 14, margin: "10px 0" }}>Model: “{r.round.explanation}”</p>
      <button className="btn primary" onClick={onNext}>{last ? "See results" : "Next round"} <span className="mono">↵</span></button>
    </div>
  );
}

function Leaderboard({ lb }: { lb: Entry[] }) {
  return (
    <div style={{ marginTop: 16 }}>
      <div className="k">Leaderboard · this browser only</div>
      <ol style={{ paddingLeft: 20, margin: "6px 0 0", fontSize: 14 }}>
        {lb.map((e, k) => <li key={k} className="mono">{e.initials} · {e.score} pts · {e.agree} matched · {e.at}</li>)}
      </ol>
    </div>
  );
}
