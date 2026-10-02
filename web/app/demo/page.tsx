import { getEval, getLedger, getMemos, getRun } from "@/lib/data";
import { DemoFlow } from "@/components/DemoFlow";
import { reviewSummary } from "@/lib/review";

export const metadata = { title: "Demo · CloseCall" };

export const dynamic = "force-dynamic";

export default function DemoPage() {
  const run = getRun();
  if (!run) return <div className="wrap section"><h2>No run yet</h2></div>;
  return <DemoFlow run={run} rows={getLedger()} memos={getMemos()} ev={getEval()} human={reviewSummary()} />;
}
