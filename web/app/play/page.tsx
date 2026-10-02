import { getLedger } from "@/lib/data";
import { SpotGame, type Round } from "@/components/SpotGame";

export const metadata = { title: "Play · Spot the Near-Miss · CloseCall" };

export default function PlayPage() {
  // Only labelled (near-miss / not) events are playable; "unsure" ones have no answer to score against.
  const pool: Round[] = getLedger()
    .filter((r) => r.label === "near_miss" || r.label === "not_near_miss")
    .map((r) => ({
      id: r.id, clip: r.clip, keyframe: r.keyframes[1] ?? r.keyframes[0], pet_s: r.pet_s,
      a_cls: r.a_cls, b_cls: r.b_cls, intersection: r.intersection,
      label: r.label as Round["label"], model: r.verdict === "near_miss" ? "near_miss" : "not_near_miss",
      votes: r.votes ?? {}, explanation: r.explanation,
    }));
  return <SpotGame pool={pool} />;
}
