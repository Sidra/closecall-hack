import { reviewClips } from "@/lib/review";
import { ReviewFlow } from "@/components/ReviewFlow";

export const metadata = { title: "Review · CloseCall" };
export const dynamic = "force-dynamic";

export default function ReviewPage() {
  // Only what a blind reviewer may see: the clip, PET and the two road-user types. No labels, no votes.
  return <ReviewFlow clips={reviewClips()} />;
}
