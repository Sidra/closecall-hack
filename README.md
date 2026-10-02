# CloseCall

**A flight recorder for intersections.** CloseCall finds possible near-misses in traffic-camera video, has vision models triage each one for an engineer to review, files the clip and a ledger row where they can be searched in plain words, and drafts the fix memo citing the AI-labelled near-miss clips. Faces and plates are pixelated before anything is stored or sent to a model. Heads and plates are pixelated in tracked boxes; untracked people may not be.

> For a city traffic engineer (or the consultancy running a safety study) who can't prove an intersection is dangerous until someone is hurt, CloseCall creates a reviewed near-miss ledger with clips and a fix memo, so they can make the case for a redesign before the crash.

## Services / ports

| Service | Port | Notes |
|---|---|---|
| Web app (Next.js 16) | **3502** | `cd web && pnpm dev`; pages `/`, `/demo`, `/ledger`, `/evals` |
| API routes | 3502 | `POST /api/search` (NVIDIA embeddings, keyword fallback, identity refusal) · `POST /api/memo` (W&B Inference, cached fallback) |
| Pipeline (Python 3.14) | — | batch CLI: `pipeline.candidates_run`, `pipeline.verify_run`, `pipeline.publish` |
| Storage | — | `CLOSECALL_STORE=local` (default stand-in: JSON under `web/public/data`) or `vast` (VAST S3 endpoint + VSS ingest) |

## Inputs → outputs → evaluation

| Step | Input | What runs | Output | How to evaluate it |
|---|---|---|---|---|
| 0 Track | 4 CC BY-SA intersection clips (141 s total), `scripts/fetch_footage.sh` | Ultralytics **YOLO26s** + ByteTrack at 960 px / 15 fps | `data/work/<clip>/tracks.json` (592 tracks) | Watch any clip in `/ledger`: boxes are drawn from these tracks |
| 1a PET | tracks | Image-plane post-encroachment time on a 2.5%-width grid; pair flagged if PET < 4 s | 1,165 naive flags | Shown as the "naive" bar in the funnel |
| 1b Physics filter | naive flags | Crossing headings 35–145°, both users moving, riders merged with their bike, pedestrian-only pairs dropped, events clustered (2 s, 6 cells) | 51 events | Rule-based; see `pipeline/pet.py` |
| 1c Anonymise + clip | events | Pixelate the head of every person/cyclist box and the plate band of every vehicle box, outline actor A (amber) and B (cyan) | `web/public/clips/<event>.mp4` + 3 keyframes | Look at any clip: no readable faces or plates |
| 2 Triage (verifier) | anonymised clip → zoomed crop → 8-frame storyboard with both trails drawn (`pipeline/storyboard.py`) | **v3 (ledger):** 2-of-3 vote of `Qwen3.6-35B-A3B`, `MiniMax-M3`, `gemma-4-31B-it` on **W&B Inference**, each answering six yes/no facts, combined by the `strict` rule. **v1/v2:** NVIDIA `nemotron-3-nano-omni-30b-a3b-reasoning` on the clip (v2: zoomed + decision rule). Fallback: `llama-3.2-11b-vision-instruct` | verdict, evidence, votes, model, latency (`data/work/verdicts*.json`, `v3_*`) | Weave trace per call; `/evals` |
| 2b Review | flagged clips | In production an engineer confirms or rejects each flag. In this repo the labels are AI-made (Claude Code, blind to verdicts, pre-registered) in `eval/labels.json`, not a human review | AI-labelled set | the "reviewer" chip on every card and row |
| 3 Store + index | verdicts | `pipeline/store.py` adapter → VAST S3 + VSS ingest, or the labelled local stand-in; `nemotron-3-embed-1b` vectors | `ledger.json`, `vectors.json` | Ask `/demo` step 4 a question; the identity question is refused |
| 4 Memo | AI-labelled near-miss clips per intersection (+ the labeller's notes) | **W&B Inference** `NVIDIA-Nemotron-3.5-Lightning-30B-A3B` | `memo.json`, live regenerate in `/demo` | Every claim cites a clip id |
| 5 Eval | `eval/labels.json` (blind, pre-registered AI labels (Claude Code)), `eval/split.json` (seeded dev/test) | **W&B Weave** `Evaluation` + the same rule in `publish.py` / `score_v3.py` | `eval.json`, `/evals`, `eval/v3_dev_results.md` | Pre-registrations: `eval/PREREGISTRATION*.md`, each committed before its run |

### Results (measured; small sample, see caveats on `/evals`)

| Verifier | Set | Caught (recall) | Flags to review | Labelled not a near-miss (FP) | Precision |
|---|---|---|---|---|---|
| v1 Nemotron Omni (39) + Llama-3.2 fallback (12), whole clip | all 51 | 0 / 4 | 9 of 44 scored | 9 | 0% |
| v2 Nemotron Omni, zoomed + rule (2 calls errored → not flagged) | all 51 | 2 / 4 | 10 of 44 scored | 8 | 20% |
| v3 storyboard + 2-of-3 vote | dev (chosen here) | 2 / 2 | 6 of 26 | 3 | 40% |
| **v3 storyboard + 2-of-3 vote** | **test (held out, one run)** | **1 / 2** | **6 of 25** | **3** | **25%** |
| v3 storyboard + 2-of-3 vote | all 51 | 3 / 4 | 12 of 51 | 6 | 33% |

Stage 1 alone (report every PET flag): 9% precision. Caveats: only 4 labelled near-misses in total (2 per split); the labels are AI-made (Claude Code, blind to verdicts, from keyframes, pre-registered), not a human review; the split was made after v1 saw all 51 events, and v3's design was informed by v1/v2 failures; dev and test share scenes; v3 was picked from many dev variants.

**Reproduce:**
1. `cp .env.example .env.local` and add the NVIDIA (build.nvidia.com) and W&B keys.
2. `bash scripts/run_pipeline.sh`: footage → tracks → events → v1 verdicts → publish.
3. For v2/v3: `.venv/bin/python -m pipeline.verify_run_v2`, then `python -m pipeline.storyboard`, then `python -m pipeline.verify_v3 dev` and `... test qwen3.6-35b,minimax-m3,gemma-4-31b`, then `python -m pipeline.score_v3 dev`, then `python -m pipeline.publish`.
4. `cd web && pnpm i && pnpm dev`, then open http://localhost:3502/demo.

**No-key practice mode:** the web app runs with no keys at all. Instant Demo replays the cached run, search falls back to keyword matching (shown under the results), and the memo falls back to the cached W&B memo (marked).

## Sponsor tools (each load-bearing)

| Sponsor | Used for | Where |
|---|---|---|
| **NVIDIA** | Nemotron-3 Nano Omni video verifier (v1, v2) and Llama-3.2 Vision fallback on build.nvidia.com; `nemotron-3-embed-1b` powers plain-language search; the Nemotron-3.5 Lightning memo model is NVIDIA's (served on W&B) | `pipeline/verify.py`, `pipeline/store.py`, `web/app/api/search` |
| **VAST Data (+ NVIDIA VSS)** | Storage adapter for clips, ledger rows and vectors on the VAST S3 endpoint, and VSS ingest with a near-miss prompt. **Currently the labelled local stand-in**: the `VastStore` adapter is written but not yet run against VAST | `pipeline/store.py` |
| **Weights & Biases / CoreWeave** | W&B Inference (CoreWeave GPUs) runs the v3 triage vote (Qwen3.6, MiniMax-M3, Gemma-4) and drafts the fix memo; Weave traces every model call and holds the v1/v2/v3 evaluations | `pipeline/memo.py`, `pipeline/tracing.py`, `pipeline/publish.py` |
| **Ultralytics YOLO** | YOLO26 detection + tracking: the cheap first stage | `pipeline/track.py` |
| **Cursor (SpaceXAI)** | Build tool: Cursor's agent (model Grok 4.7, SpaceXAI) built the council-packet CSV export (`web/lib/councilPacket.ts`), reviewed and hardened afterwards. Not in the runtime path | `web/lib/councilPacket.ts` |

## Honesty notes
- **Footage is public CC BY-SA 4.0 video from Wikimedia Commons**, not a live city camera. Credits: Pie-IX / Sherbrooke, Montréal (Thomas1313); Respubliki / Profsoyuznaya and Respubliki / Vodoprovodnaya, Tyumen (RG72); an intersection in Chiang Mai (Amada44). The anonymised derived clips in `web/public/clips` are shared under the same licence.
- **Storage is a stand-in** unless the UI shows a green "Stored on VAST Data" chip.
- **PET is approximate:** measured in screen pixels without a ground-plane calibration. That is why stage 2 exists.
- **The eval is small and single-labeller** (the builder, blind to verdicts). See `/evals` for every miss and false flag.
- **Human review:** a `/review` page lets a traffic engineer confirm flags blind; not yet used on this set (no human verdicts exist, and none are shown).
- **Model output is a flag, not a verdict:** nothing is filed until a engineer reviews it; the memo cites only AI-labelled near-miss clips.
- **No identification:** redaction is geometric and applies to every detection; identity questions are refused in search.

## Repo map
`pipeline/` Python stages · `eval/` pre-registration + labels · `web/` Next.js app.
