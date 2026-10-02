# Evaluation pre-registration: CloseCall near-miss verifier

Committed **before** any hand label was written and **before** the verifier ran on the eval set.

## Question
Of the events the verifier calls `near_miss`, what fraction are real traffic conflicts?
(precision). Secondary questions: recall, and how much stage 2 improves on stage 1 alone.

## Eval set
- Every event produced by stages 0-1 (`pipeline/candidates_run.py`) from the four CC-licensed
  intersection clips listed in the README: 51 events, fixed before labelling.
- **Labeller:** the builder (Claude Code, reviewing for Sidra Miconi), looking at the three
  anonymised keyframes per event, cropped around the conflict point. Not a traffic engineer.
  The labeller has not seen any verifier verdict on these events.
- **Label values:** `near_miss` (paths really cross or merge on the road surface close in time,
  so a small timing change could cause contact), `not_near_miss`, `unsure`.
- Labels are written to `eval/labels.json` and committed **before** the verifier is run on the set.

## Scoring rule (fixed now)
- Positive = label `near_miss`. Events labelled `unsure` are **excluded** from every metric and
  their count is reported next to the result.
- Verifier "flags" an event when its verdict is `near_miss`. `unclear` and `not_near_miss` = not flagged.
- **Precision** = flagged ∩ positive / flagged. **Recall** = flagged ∩ positive / positive.
- **Stage-1 baseline precision** = positive / all scored events (that is: precision if every
  stage-1 event were reported, with no model).
- Report counts (TP, FP, FN, TN), not only ratios, and list every false positive and false
  negative by event id in the UI.
- One run, temperature 0.2, no re-running to improve the number. If the verifier is replaced
  or its prompt changes after this, the result is reported as a new, separately labelled run.

## Known limits (stated in advance)
- 51 events from ~2.3 minutes of footage: a small sample, so the result is indicative only.
- One labeller, the same agent that built the pipeline: a conflict of interest, mitigated
  only by labelling blind to verdicts and committing labels first.
- Image-plane PET without ground-plane calibration.
