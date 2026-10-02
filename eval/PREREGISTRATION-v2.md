# Pre-registration, verifier v2

Committed **before** verifier v2 made any call on the eval set.

## Why there is a v2
On v1 (whole wide-angle clip, neutral prompt), with 43 of 51 verdicts in, the verifier flagged 9 labelled
events as near-misses and none of them was labelled a near-miss; it also missed all 4 labelled
near-misses. Its explanations fail mainly on depth (far road users overlapping on screen). The labels are
**not** changed: `eval/labels.json` stays exactly as first written.

## What changes in v2 (and nothing else)
1. **Input:** the same anonymised clip, cropped around the conflict point (3x the larger actor box, at
   least 22% of frame width) and upscaled to 640x360 (`clips.export_crop`).
2. **Prompt:** asks five questions in order (on roadway, same depth, gap in car lengths, evasive action)
   and applies an explicit decision rule (`verify.PROMPT_V2`).
Same model (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`), temperature 0.2, same 51 events.

## Scoring
Exactly the rule in `eval/PREREGISTRATION.md` (unsure excluded, `unclear` = not flagged, counts reported,
every FP/FN listed). One run.

## Reporting (fixed now, whatever the outcome)
- `/evals` shows **v1 and v2 side by side**, with v1's final 51/51 result kept.
- The ledger, hero clip and search use **v2 verdicts**, whichever version scores better.
- The hero clip is chosen among events **labelled** `near_miss`; its verifier verdict is shown as it is,
  even if the verifier missed it. No event labelled `not_near_miss` is ever presented as a near-miss
  example on the landing page.
- If v2 is no better, that is reported as a null result.
