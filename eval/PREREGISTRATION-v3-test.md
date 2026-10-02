# Pre-registration: verifier v3, test run

Committed **before** any v3 model call on the test split. The labels, the split and the scoring rule are unchanged.

## Headline metric (CloseCall is a triage tool: the engineer reviews only what it flags)
1. **Primary: recall** of reviewer-confirmed near-misses (labelled `near_miss`), i.e. how many it caught.
2. **Second: review-load cut**: clips flagged for review ÷ candidate events. Footage minutes are shown next to it.
3. **Precision**, reported honestly as "flags the reviewer will reject" (FP).

## Chosen variant (picked on dev by: recall first, then the fewest flags)
- **Input:** the 8-frame storyboard (`pipeline/storyboard.py`): zoomed on the conflict point, A/B boxes and trails, times.
- **Prompt:** `verify_v3.PROMPT_V3` (six booleans + evidence), temperature 0.1.
- **Models:** `Qwen/Qwen3.6-35B-A3B` (thinking off), `MiniMaxAI/MiniMax-M3`, `google/gemma-4-31B-it`, all on W&B Inference.
- **Per-model rule `strict`:** a_on_road ∧ b_on_road ∧ same_depth ∧ paths_cross ∧ close.
- **Decision:** flag when at least 2 of the 3 models' `strict` is true.
- **Dev result:** recall 2/2, 5 flags (2 TP, 3 FP) of 22 scored dev events. See `eval/v3_dev_results.md` for every variant tried.

## Caveats, stated in advance
- **Dev has only 2 positives, and many combinations were compared on it**, so the dev numbers are optimistic (selection bias). The test number is the one to quote.
- **Test also has only 2 positives:** a recall of 2/2, 1/2 or 0/2 is a very coarse measurement.
- **Dev and test share scenes** (stratified split; see `PREREGISTRATION-v3-split.md`).

## Reporting
- **Test** is reported once, as is.
- A **separate line** reports all 51 (dev ∪ test) for this variant, labelled as including the dev events it was chosen on.
- v1 and v2 (full set) stay on `/evals`.
