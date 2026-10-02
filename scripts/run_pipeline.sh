#!/usr/bin/env bash
# Full pipeline, end to end. Needs .env.local with VIDEO_HACK_NVIDIA_API_KEY and VIDEO_HACK_WANDB_API_KEY.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
bash scripts/fetch_footage.sh
.venv/bin/python -m pipeline.candidates_run   # stages 0-1: track, PET, physics filter, anonymised clips
.venv/bin/python -m pipeline.verify_run       # stage 2: Nemotron Omni verdict per clip (Weave-traced, cached)
.venv/bin/python -m pipeline.publish          # stages 3-5: store, search index, memo, Weave eval
