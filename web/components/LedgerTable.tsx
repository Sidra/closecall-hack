"use client";
import { useMemo, useState } from "react";
import type { Row } from "@/lib/types";
import { mediaSrc, pretty } from "@/lib/types";
import { councilPacketCsv, type CouncilPacketRow } from "@/lib/councilPacket";
import { LabelChip, VerdictChip } from "./ClipCard";

function packetRow(r: Row): CouncilPacketRow {
  const path = mediaSrc(r.clip);
  const clip_url = path && typeof window !== "undefined" ? `${window.location.origin}${path}` : path;
  return {
    id: r.id,
    intersection: r.intersection,
    PET_s: r.pet_s.toFixed(2),
    road_users: r.pair,
    model_flag: r.verdict,
    ai_label_blind: r.label ?? "",
    explanation: r.explanation,
    clip_url,
  };
}

function downloadCouncilPacket(rows: Row[]) {
  const csv = councilPacketCsv(rows.map(packetRow));
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "closecall-council-packet.csv";
  a.click(); // a detached anchor downloads in current browsers; nothing is inserted into the DOM
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function LedgerTable({ rows, weaveUrl, human = null }: { rows: Row[]; weaveUrl: string | null; human?: Record<string, string> | null }) {
  const [pet, setPet] = useState(4);
  const [all, setAll] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  // Rows are always rendered from props (sorted once); the filters only toggle visibility.
  // That keeps UI state out of every media src.
  const sorted = useMemo(() => [...rows].sort((a, b) => a.pet_s - b.pet_s), [rows]);
  const shown = useMemo(
    () => sorted.filter((r) => r.pet_s <= pet && (all || r.verdict === "near_miss" || r.label === "near_miss")),
    [sorted, pet, all],
  );
  const shownIds = useMemo(() => new Set(shown.map((r) => r.id)), [shown]);
  return (
    <div>
      <div className="card flat" style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}>
        <label style={{ flex: "1 1 280px" }}>
          <div className="k">PET threshold: <span className="mono" style={{ color: "var(--amber)" }}>{pet.toFixed(1)} s</span></div>
          <input type="range" min={0.5} max={4} step={0.1} value={pet} onChange={(e) => setPet(Number(e.target.value))} style={{ width: "100%", accentColor: "var(--amber)" }} aria-label="Post-encroachment time threshold in seconds" />
        </label>
        <button type="button" className="btn" onClick={() => downloadCouncilPacket(shown)}>Export council packet (CSV)</button>
        <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer" }}>
          <input type="checkbox" checked={all} onChange={(e) => setAll(e.target.checked)} /> show every candidate (default: model flags + labelled near-misses)
        </label>
        <div className="mono"><span className="big" style={{ fontSize: 28 }}>{shown.length}</span> <span className="muted">candidates shown</span></div>
      </div>
      <div className="scroll-x" style={{ marginTop: 14 }}>
        <table className="table">
          <thead><tr><th>Clip</th><th>Pair</th><th>Verdict</th><th>PET</th><th>Model’s reason</th><th>Verifier</th><th>Trace</th></tr></thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.id} hidden={!shownIds.has(r.id)}>
                <td style={{ width: 150 }}>
                  {open === r.id
                    ? <video src={mediaSrc(r.clip)} autoPlay controls muted loop playsInline style={{ width: 260 }} />
                    : <button onClick={() => setOpen(r.id)} style={{ all: "unset", cursor: "pointer" }} aria-label={`Play clip ${r.id}`}>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img className="frame" src={mediaSrc(r.keyframes[1] ?? r.keyframes[0])} alt={`Anonymised keyframe of ${r.pair}`} style={{ width: 140 }} />
                      </button>}
                  <div className="faint mono" style={{ fontSize: 10.5, marginTop: 4 }}>{r.id}</div>
                </td>
                <td><span style={{ color: "var(--amber)" }}>{r.a_cls}</span> → <span style={{ color: "var(--cyan)" }}>{r.b_cls}</span><div className="faint" style={{ fontSize: 12 }}>{r.intersection}</div></td>
                <td className="verdict"><div style={{ display: "grid", gap: 4, justifyItems: "start" }}><VerdictChip v={r.verdict} /><LabelChip l={r.label} />{human?.[r.id] && <span className={`chip ${human[r.id] === "near_miss" ? "green" : ""}`} title="Blind human review">human: {human[r.id].replace(/_/g, " ")}</span>}</div>
                  {(r.v2_verdict || r.v1_verdict) && <div className="faint" style={{ fontSize: 12, marginTop: 4 }}>{r.v2_verdict && <>v2: {r.v2_verdict.replace(/_/g, " ")} · </>}{r.v1_verdict && <>v1: {r.v1_verdict.replace(/_/g, " ")}</>}</div>}</td>
                <td className="mono">{r.pet_s.toFixed(2)}s</td>
                <td style={{ maxWidth: 380 }}><div className="clamp2" title={r.explanation}>{r.explanation}</div><div className="faint" style={{ fontSize: 12 }}>{pretty(r.conflict_type)}</div></td>
                <td className="faint mono" style={{ fontSize: 11 }}>{r.verifier_model?.split("/").pop()}<div>{r.verifier_input} · {r.verifier_latency_s}s</div></td>
                <td>{weaveUrl ? <a href={weaveUrl} target="_blank" rel="noreferrer">Weave ↗</a> : <span className="faint">off</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!shown.length && <p className="muted">No rows at this threshold.</p>}
      </div>
    </div>
  );
}
