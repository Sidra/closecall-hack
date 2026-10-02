import type { Row } from "@/lib/types";
import { mediaSrc, pretty } from "@/lib/types";

export function VerdictChip({ v }: { v: Row["verdict"] }) {
  if (v === "near_miss") return <span className="chip red"><span className="dot" />model: near-miss</span>;
  if (v === "unclear") return <span className="chip amber"><span className="dot" />unclear</span>;
  return <span className="chip"><span className="dot" />model: rejected</span>;
}

export function LabelChip({ l }: { l: string | null }) {
  if (l === "near_miss") return <span className="chip green" title="AI label (Claude Code, blind to verdicts, pre-registered)">label: near-miss</span>;
  if (l === "not_near_miss") return <span className="chip" title="AI label (Claude Code, blind to verdicts, pre-registered)">label: not a near-miss</span>;
  if (l === "unsure") return <span className="chip" title="AI label (Claude Code, blind to verdicts, pre-registered)">label: unsure</span>;
  return null;
}

export function ClipCard({ r, weaveUrl, compact = false }: { r: Row; weaveUrl?: string | null; compact?: boolean }) {
  return (
    <div className="card fade" id={r.id} style={{ padding: 12 }}>
      <video src={mediaSrc(r.clip)} poster={mediaSrc(r.keyframes[1] ?? r.keyframes[0])} controls muted loop playsInline preload="none" />
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
        <VerdictChip v={r.verdict} />
        <LabelChip l={r.label} />
        <span className="chip amber mono">PET {r.pet_s.toFixed(2)} s</span>
        {r.severity > 0 && <span className="chip">severity {r.severity}/5</span>}
        {r.verifier_input === "keyframe" && <span className="chip violet">fallback: Llama vision on keyframe</span>}
      </div>
      <h3 style={{ marginTop: 10, fontSize: 15 }}>
        <span style={{ color: "var(--amber)" }}>A {r.a_cls}</span> → <span style={{ color: "var(--cyan)" }}>B {r.b_cls}</span>
        <span className="faint" style={{ fontWeight: 500 }}> · {pretty(r.conflict_type)}</span>
      </h3>
      {!compact && <p style={{ margin: "6px 0 0", fontSize: 14 }}>{r.explanation}</p>}
      <div className="faint mono" style={{ fontSize: 11.5, marginTop: 8 }}>
        {r.id} · t={r.t.toFixed(1)}s · {r.intersection}
        {weaveUrl && <> · <a href={weaveUrl} target="_blank" rel="noreferrer">trace ↗</a></>}
      </div>
    </div>
  );
}
