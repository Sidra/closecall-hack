import { LiveView } from "@/components/LiveView";

export const metadata = { title: "Live · CloseCall" };

export default function LivePage() {
  return <LiveView workerUrl={process.env.NEXT_PUBLIC_CLOSECALL_LIVE_URL || "http://localhost:3503"} />;
}
