import Link from "next/link";
import { getEval, getLedger, getRun } from "@/lib/data";
import type { Eval, Metrics, Row, SplitM } from "@/lib/types";
import { Headline } from "@/components/Headline";
import { HumanLine } from "@/components/HumanLine";
import { reviewSummary } from "@/lib/review";

export const metadata = { title: "Evals · CloseCall" };

const pct = (x: number | null | undefined) => (x === null || x === undefined ? "n/a" : `${Math.round(x * 100)}%`);

function List({ ids, title, tone, byId, labels }: { ids: string[]; title: string; tone: string; byId: Record<string, Row>; labels: Eval["labels"] }) {
  return (
    <div className="card flat">
      <div className="k">{title} · {ids.length}</div>
      {ids.length === 0 && <p className="faint" style={{ margin: "8px 0 0" }}>none</p>}
      <ul style={{ paddingLeft: 18, margin: "8px 0 0", fontSize: 13.5 }}>
        {ids.map((id) => (
          <li key={id} style={{ marginBottom: 6 }}>
            <Link href={`/ledger`} className="mono" style={{ color: tone }}>{id}</Link>{" "}
            <span className="muted">{byId[id]?.pair}: model said “{byId[id]?.explanation}”</span>
            {labels[id]?.note && <div className="faint">label note: {labels[id].note}</div>}
          </li>
        ))}
      </ul>
    </div>
  );
}

function MRow({ name, set, m, reg }: { name: string; set: string; m: Metrics; reg: string }) {
  const flags = m.tp.length + m.fp.length;
  return <tr><td>{name}</td><td>{set}</td><td className="mono">{m.tp.length} / {m.tp.length + m.fn.length}</td><td className="mono">{flags} of {m.scored} scored</td><td className="mono">{m.fp.length}</td><td className="mono">{pct(m.precision)}</td><td className="mono faint">{reg}</td></tr>;
}
function SRow({ name, set, m, reg, strong }: { name: string; set: string; m: SplitM; reg: string; strong?: boolean }) {
  const st = strong ? { fontWeight: 700 } : undefined;
  return <tr style={st}><td>{name}</td><td>{set}</td><td className="mono">{m.tp} / {m.tp + m.fn}</td><td className="mono">{m.flags} of {m.candidates} candidates</td><td className="mono">{m.fp}</td><td className="mono">{pct(m.precision)}</td><td className="mono faint">{reg}</td></tr>;
}

export const dynamic = "force-dynamic";

export default function EvalsPage() {
  const ev = getEval();
  const run = getRun();
  const rows = getLedger();
  const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
  if (!ev || !run) return <div className="wrap section"><h2>No eval yet</h2></div>;
  return (
    <div className="wrap section">
      <div className="eyebrow">Evaluation · W&amp;B Weave</div>
      <h2 style={{ marginTop: 10 }}>Does the triage catch the near-misses, and how much review does it save?</h2>
      <p className="muted" style={{ maxWidth: 780 }}>
        The scoring rule was committed to the repo (<span className="mono">eval/PREREGISTRATION.md</span>) before any label was written, and the
        labels (<span className="mono">eval/labels.json</span>) were committed before any verifier ran on the set. Each verifier version has its own pre-registration commit and was run once; none of the numbers below was re-run to improve it.
      </p>
      <div className="card" style={{ marginTop: 20 }}><Headline ev={ev} run={run} /><HumanLine s={reviewSummary()} /></div>
      <div className="card flat scroll-x" style={{ marginTop: 16 }}>
        <div className="k">Every pre-registered run · same 51 events · same blind labels (unsure excluded)</div>
        <table className="table" style={{ marginTop: 8 }}>
          <thead><tr><th>Verifier</th><th>Set</th><th>Caught (recall)</th><th>Flags (review load)</th><th>Labelled not a near-miss (FP)</th><th>Precision</th><th>Pre-registration</th></tr></thead>
          <tbody>
            {ev.v1 && <MRow name="v1 · Nemotron Omni (39) + Llama-3.2 fallback (12), whole clip" set="all 51" m={ev.v1} reg="PREREGISTRATION.md" />}
            {ev.v2 && <MRow name="v2 · Nemotron Omni, zoomed clip + rule (2 calls errored → not flagged)" set="all 51" m={ev.v2} reg="PREREGISTRATION-v2.md" />}
            {ev.v3 && <>
              <SRow name="v3 · storyboard, 2-of-3 vote" set="dev (chosen here: optimistic)" m={ev.v3.dev} reg="PREREGISTRATION-v3-split.md" />
              <SRow name="v3 · storyboard, 2-of-3 vote" set="TEST (held out, one run)" m={ev.v3.test} reg="PREREGISTRATION-v3-test.md" strong />
              <SRow name="v3 · storyboard, 2-of-3 vote" set="all 51 (includes dev)" m={ev.v3.all} reg="PREREGISTRATION-v3-test.md" />
            </>}
          </tbody>
        </table>
        <p className="faint" style={{ fontSize: 13, margin: "8px 0 0" }}>
          Each version was written after the previous one failed and committed before it ran. v3 was chosen on the dev split (recall first, then fewest flags)
          and run once on test. Test has only {ev.v3 ? ev.v3.test.tp + ev.v3.test.fn : "?"} labelled near-misses, so its recall is a coarse measure. The split was made after v1 saw all 51 events, and v3’s design was informed by v1/v2 failures, so test is not fully held out. The labels were never changed.
          The ledger uses {run.verifier_label ?? ev.version}.
        </p>
      </div>
      <div className="grid g4" style={{ marginTop: 22 }}>
        <div className="card"><div className="k">Ledger verifier ({ev.version ?? "v1"}), all 51: precision</div><div className="big" style={{ color: "var(--green)" }}>{pct(ev.precision)}</div><div className="muted">{ev.tp.length} of {ev.tp.length + ev.fp.length} flags correct</div></div>
        <div className="card"><div className="k">Recall</div><div className="big">{pct(ev.recall)}</div><div className="muted">{ev.tp.length} of {ev.tp.length + ev.fn.length} labelled near-misses found</div></div>
        <div className="card"><div className="k">Stage 1 alone (baseline)</div><div className="big">{pct(ev.baseline_precision)}</div><div className="muted">precision if every PET flag were reported</div></div>
        <div className="card"><div className="k">Scored / excluded</div><div className="big">{ev.scored}<span className="faint" style={{ fontSize: 22 }}> / {ev.excluded_unsure}</span></div><div className="muted">events scored / labelled “unsure”</div></div>
      </div>
      <div className="grid g3" style={{ marginTop: 16 }}>
        <List ids={ev.tp} title="True positives" tone="var(--green)" byId={byId} labels={ev.labels} />
        <List ids={ev.fp} title="False positives (model said near-miss, label said no)" tone="var(--red)" byId={byId} labels={ev.labels} />
        <List ids={ev.fn} title="Missed (label said near-miss, model said no)" tone="var(--amber)" byId={byId} labels={ev.labels} />
      </div>
      {ev.unsure_flagged.length > 0 && (
        <p className="muted" style={{ fontSize: 13.5 }}>Flagged by the model but labelled “unsure” (not scored): <span className="mono">{ev.unsure_flagged.join(", ")}</span></p>
      )}
      <div className="card flat" style={{ marginTop: 22 }}>
        <h3>Limits, stated plainly</h3>
        <ul className="muted" style={{ fontSize: 14, marginBottom: 0 }}>
          <li>Small sample: {run.totals.events} events from {Math.round(run.totals.duration_s)} s of public footage. Indicative, not a benchmark.</li>
          <li>Labeller: {ev.labeller}. Not a traffic engineer, and the same agent that built the pipeline.</li>
          <li>PET is measured in screen pixels without a ground-plane calibration, which is why stage 1 alone is so noisy.</li>
          <li>v3 (the ledger): {run.totals.fallback_verdicts} of {run.totals.verifier_calls} verdicts from a fallback model. v1: 12 of 51 came from the Llama 3.2 Vision fallback on one keyframe; v2: 2 of 51 calls errored and count as not flagged.</li>
        </ul>
      </div>
      <p style={{ marginTop: 18 }}>
        {run.weave.url
          ? <a className="btn" href={run.weave.url} target="_blank" rel="noreferrer">Open traces + evaluation in Weave ↗</a>
          : <span className="faint">Weave tracing was off for this run{run.weave.error ? `: ${run.weave.error}` : ""}.</span>}
      </p>
    </div>
  );
}
