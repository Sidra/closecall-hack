import type { Run } from "@/lib/types";

export function StoreNotice({ run }: { run: Run }) {
  if (!run.store.standin) return <div className="chip green"><span className="dot" />Stored on {run.store.name}: {run.store.detail}</div>;
  return (
    <details className="notice-line">
      <summary><b>Stand-in storage:</b> this run uses local stand-in storage; VAST/VSS was not connected.</summary>
      <span>Clips, ledger rows and search vectors sit behind the same storage adapter ({run.store.detail}). Switching to VAST is one setting:
        <span className="mono"> CLOSECALL_STORE=vast</span> plus the VAST S3 / VSS endpoints.</span>
    </details>
  );
}
