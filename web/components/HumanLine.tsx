type S = { reviewer: string; flagged_reviewed: number; flagged_confirmed: number; human_near_miss: number; agree: number; agree_n: number; finished: boolean; reviewed: number; total: number } | null;

/** One line about the human review; renders nothing until eval/human_review.json exists and is finished. */
export function HumanLine({ s }: { s: S }) {
  if (!s || !s.finished) return null;
  return (
    <p className="headline" style={{ fontSize: 15.5, marginTop: 8 }}>
      <span className="chip green" style={{ marginRight: 8 }}>human review</span>
      A person ({s.reviewer}) reviewed {s.flagged_reviewed} flagged clips blind: confirmed <b>{s.flagged_confirmed}</b> near-misses.{" "}
      <span className="muted">Agrees with the AI labels on {s.agree} of {s.agree_n}.</span>
    </p>
  );
}
