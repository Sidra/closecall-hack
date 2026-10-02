import type { Eval, Run } from "@/lib/types";

/** The recall-first headline, always computed from eval.json / run.json (never hard-coded). */
export function Headline({ ev, run }: { ev: Eval | null; run: Run }) {
  const h = ev?.headline;
  const t = run.totals;
  if (!h) {
    return <p className="headline muted">{Math.round(t.duration_s)} s video → {t.events} candidates → {t.verified} flagged for review → {t.confirmed_and_flagged ?? 0} of {t.confirmed ?? 0} AI-labelled near-misses among them.</p>;
  }
  return (
    <p className="headline">
      Caught <b>{h.caught} of {h.confirmed}</b> AI-labelled near-misses (blind, pre-registered labels); the engineer reviews <b>{h.flags} clips</b> instead of{" "}
      <b>{h.footage_s} s</b> of video / <b>{h.candidates}</b> candidates.{" "}
      <span className="muted">Test split: {h.test.tp} of {h.test.tp + h.test.fn} caught, {h.test.flags} flags of {h.test.candidates} (split made after v1 saw all events; v3 designed from v1/v2 failures).</span>
    </p>
  );
}
