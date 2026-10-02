import { getLedger, getRun } from "@/lib/data";
import { LedgerTable } from "@/components/LedgerTable";
import { StoreNotice } from "@/components/StoreNotice";
import { reviewSummary } from "@/lib/review";

export const metadata = { title: "Ledger · CloseCall" };

export const dynamic = "force-dynamic";

export default function LedgerPage() {
  const run = getRun();
  const rows = getLedger();
  if (!run) return <div className="wrap section"><h2>No run yet</h2><p className="muted">Run the pipeline (see README).</p></div>;
  return (
    <div className="wrap section">
      <div className="eyebrow">The near-miss ledger</div>
      <h2 style={{ marginTop: 10 }}>Candidate close calls: what the model flagged, and how each was labelled.</h2>
      <p className="muted" style={{ maxWidth: 760 }}>
        Each row is one candidate event: two road users who passed through the same spot within the post-encroachment time
        (PET) shown. Drag the threshold to tighten the definition; tick the box to see every candidate the model rejected, with its reason.
      </p>
      <div style={{ margin: "16px 0" }}><StoreNotice run={run} /></div>
      <LedgerTable rows={rows} weaveUrl={run.weave.url} human={reviewSummary()?.finished ? reviewSummary()!.verdicts : null} />
      <div id="sources" style={{ marginTop: 40 }}>
        <h3>Footage sources</h3>
        <p className="muted" style={{ fontSize: 14 }}>Public, CC-licensed intersection clips (not a live city camera). Redistributed here anonymised, under the same licence.</p>
        <ul style={{ fontSize: 14 }}>
          {Object.values(run.sources).map((s) => (
            <li key={s.url}><a href={s.url} target="_blank" rel="noreferrer">{s.title}</a> · {s.author} · {s.license}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
