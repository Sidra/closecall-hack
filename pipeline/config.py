"""Shared paths, thresholds and source metadata for the CloseCall pipeline."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")

RAW = ROOT / "data" / "raw"
WORK = ROOT / "data" / "work"
OUT = ROOT / "web" / "public" / "data"  # what the UI reads (pre-cached run)
CLIPS_OUT = ROOT / "web" / "public" / "clips"

# Stage 1 (cheap): a pair of road users is a candidate when PET < this many seconds.
PET_CANDIDATE_S = 4.0
# Grid cell for the conflict-zone footprint, as a fraction of frame width.
CELL_FRAC = 0.025
# Tracks shorter than this are tracker noise.
MIN_TRACK_S = 0.6
# Analysis width; frames are downscaled before YOLO.
ANALYSIS_W = 960

YOLO_WEIGHTS = os.getenv("CLOSECALL_YOLO", str(ROOT / "yolo26s.pt"))
ROAD_USER_CLASSES = {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
VULNERABLE = {"person", "bicycle", "motorcycle"}

NVIDIA_API_KEY = os.getenv("VIDEO_HACK_NVIDIA_API_KEY", "")
NVIDIA_BASE = "https://integrate.api.nvidia.com/v1"
VERIFY_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
VERIFY_FALLBACK = "meta/llama-3.2-11b-vision-instruct"
EMBED_MODEL = os.getenv("CLOSECALL_EMBED", "nvidia/nemotron-3-embed-1b")

WANDB_API_KEY = os.getenv("VIDEO_HACK_WANDB_API_KEY", "")
WANDB_BASE = "https://api.inference.wandb.ai/v1"
MEMO_MODEL = os.getenv("CLOSECALL_MEMO_MODEL", "nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B")
WEAVE_PROJECT = os.getenv("CLOSECALL_WEAVE_PROJECT", "closecall")

# Every clip the pipeline ingests, with its licence, so the UI can credit it.
SOURCES = {
    "pieix": {
        "file": "pieix.webm",
        "title": "Pie-IX / Sherbrooke, Montréal",
        "license": "CC BY-SA 4.0",
        "author": "Thomas1313 (Wikimedia Commons)",
        "url": "https://commons.wikimedia.org/wiki/File:Intersection_Pie-IX-Sherbrooke.webm",
    },
    "tyumen-prof": {
        "file": "tyumen-prof.webm",
        "title": "Respubliki / Profsoyuznaya, Tyumen",
        "license": "CC BY-SA 4.0",
        "author": "RG72 (Wikimedia Commons)",
        "url": "https://commons.wikimedia.org/wiki/File:Kruci%C4%9Do_de_stratoj_Respubliko_kaj_Profsojuznaja_(Tjumeno).webm",
    },
    "tyumen-vodo": {
        "file": "tyumen-vodo.webm",
        "title": "Respubliki / Vodoprovodnaya, Tyumen",
        "license": "CC BY-SA 4.0",
        "author": "RG72 (Wikimedia Commons)",
        "url": "https://commons.wikimedia.org/wiki/File:Kruci%C4%9Do_de_stratoj_Respubliko_kaj_Vodoprovodnaja_(Tjumeno).webm",
    },
    "chiangmai": {
        "file": "chiangmai.ogv",
        "title": "Intersection in Chiang Mai, Thailand",
        "license": "CC BY-SA 4.0",
        "author": "Amada44 (Wikimedia Commons)",
        "url": "https://commons.wikimedia.org/wiki/File:A_intersection_with_traffic_in_Chiang_Mai,_Thailand.ogv",
    },
}
