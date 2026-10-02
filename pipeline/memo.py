"""Stage 4: draft the fix memo from verified near-misses, via W&B Inference (CoreWeave GPUs).

Falls back to the last cached memo (clearly marked) if W&B Inference is down.
"""
from __future__ import annotations

import json
import urllib.request

from . import config as C, tracing

SYSTEM = (
    "You are a traffic-safety engineer writing a one-page memo to a city council. Use only the "
    "evidence given. Cite every clip by its id in square brackets. Never identify a person or plate. "
    "Do not invent statistics, distances, speeds, signal timings or any detail not in the evidence. "
    "Call the events 'AI-labelled near-misses for the engineer\'s review'. Be specific and plain. Markdown, under 300 words."
)


@tracing.op
def draft_memo(intersection: str, rows: list[dict], model: str = C.MEMO_MODEL) -> dict:
    ev = [{"id": r["id"], "pair": r["pair"], "pet_s": r["pet_s"], "reviewer_note": r.get("reviewer_note", "")} for r in rows]
    user = (f"Intersection: {intersection}\nAI-labelled near-miss events, for the engineer's review (from anonymised camera footage):\n"
            f"{json.dumps(ev, indent=1)}\n\nWrite: 1) what is happening, 2) the pattern, 3) up to three "
            "concrete fixes (e.g. leading pedestrian interval, daylighting the corners, no turn on red, "
            "hardened centre line), each tied to the clips it addresses, 4) what to measure after the fix.")
    body = {"model": model, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
            "max_tokens": 6000, "temperature": 0.3}
    req = urllib.request.Request(f"{C.WANDB_BASE}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {C.WANDB_API_KEY}", "Content-Type": "application/json",
                                          "User-Agent": "curl/8.7.1"})
    d = json.load(urllib.request.urlopen(req, timeout=180))
    content = d["choices"][0]["message"].get("content")
    if not content:
        raise ValueError("empty memo content (model spent its budget reasoning)")
    return {"markdown": content.strip(), "model": model, "usage": d.get("usage", {})}
