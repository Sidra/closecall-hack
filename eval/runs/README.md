# Raw verdict files (for re-scoring without any model calls)

| File | What |
|---|---|
| `events.json` | the 51 stage-1 events (inputs to every verifier) |
| `kinematics.json` | track-based stats per event (used by the kinematic rule) |
| `v1_verdicts.json` | v1: Nemotron Omni on the whole clip; 12 of 51 came from the Llama-3.2 Vision keyframe fallback (`model` field). One event, `pieix-1066-410`, was re-run under the final v1 prompt after the batch, because its first verdict came from an earlier, leading prompt draft |
| `v2_verdicts.json` | v2: Nemotron Omni on the zoomed crop; 2 calls errored (`model: none`, scored as not flagged) |
| `v3_<split>__<model>.json` | v3 per-model answers (six booleans + evidence) on the storyboards. `@risk` = the 0–10 risk-score variant |

Re-score: `mkdir -p data/work && cp eval/runs/* data/work/ && cp data/work/v1_verdicts.json data/work/verdicts.json && cp data/work/v2_verdicts.json data/work/verdicts_v2.json && .venv/bin/python -m pipeline.score_v3 dev` (or `test`).
Labels: `eval/labels.json` (AI-made by Claude Code, blind to verdicts). Split: `eval/split.json`.
