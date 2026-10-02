"""Stage 2 (model): a video-reasoning model checks each candidate clip.

Primary: NVIDIA Nemotron-3 Nano Omni (reasoning) on build.nvidia.com, given the whole clip.
Fallback: Llama-3.2-11B-Vision on three keyframes, when Nemotron is down or rate-limited.
The verdict records which model produced it, so the ledger never hides a fallback.
"""
from __future__ import annotations

import base64
import json
import re
import time
import urllib.error
import urllib.request

from . import config as C

PROMPT = """You are a traffic-safety analyst reviewing a short intersection clip for a city near-miss study.
Faces and licence plates are pixelated on purpose. Never try to identify any person or vehicle.

Two road users are outlined: A (amber box) is a {a_cls}, B (cyan box) is a {b_cls}.
A cheap tracker flagged this pair because, on screen, B reached the spot A had just left (red circle)
{pet:.2f} s later. Most such flags are false alarms: the tracker works in screen pixels, so
road users at different distances from the camera often overlap on screen without ever being close.
First work out where each one actually is on the road and how they move, then decide.

Decide whether A and B had a genuine traffic conflict: their paths actually crossed or merged on
the road surface close in time, so a small change in timing or speed could have caused a collision.
It is NOT a near-miss if: they are in different depth planes that only overlap on screen, one is
parked, they are on the sidewalk vs the road with no crossing, it is ordinary queued traffic, or the
boxes are a tracking error.

Answer with ONLY a JSON object:
{{"verdict": "near_miss" | "not_near_miss" | "unclear",
  "conflict_type": one of "left_turn_vs_through", "right_turn_vs_crossing", "turn_vs_pedestrian",
     "turn_vs_cyclist", "crossing_path", "merge", "other", "none",
  "severity": 1-5 (5 = evasive braking or swerving),
  "evasive_action": short phrase or "none",
  "explanation": one or two plain sentences a city council member would understand,
  "confidence": 0.0-1.0}}"""


def _post(model: str, content: list, max_tokens: int = 2500, timeout: int = 120) -> str:
    body = {"model": model, "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens, "temperature": 0.2}
    req = urllib.request.Request(
        f"{C.NVIDIA_BASE}/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {C.NVIDIA_API_KEY}", "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=timeout))
    return r["choices"][0]["message"].get("content") or ""


def parse_verdict(text: str) -> dict:
    """Pull the last JSON object out of a model reply; tolerate code fences and prose."""
    m = re.findall(r"\{[^{}]*\"verdict\"[^{}]*\}", text, re.S)
    if not m:
        raise ValueError(f"no verdict JSON in reply: {text[:200]!r}")
    v = json.loads(m[-1])
    if v.get("verdict") not in ("near_miss", "not_near_miss", "unclear"):
        raise ValueError(f"bad verdict value: {v.get('verdict')!r}")
    v["severity"] = int(v.get("severity") or 1)
    v["confidence"] = float(v.get("confidence") or 0.0)
    return v


def verify(event: dict, clip_path: str, keyframe_paths: list[str], retries: int = 5) -> dict:
    prompt = PROMPT.format(a_cls=event["a_cls"], b_cls=event["b_cls"], pet=event["pet_s"])
    video_b64 = base64.b64encode(open(clip_path, "rb").read()).decode()
    t = time.time()
    err = ""
    for attempt in range(retries):
        try:
            text = _post(C.VERIFY_MODEL, [{"type": "text", "text": prompt},
                                          {"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{video_b64}"}}])
            return {**parse_verdict(text), "model": C.VERIFY_MODEL, "input": "clip",
                    "latency_s": round(time.time() - t, 1), "attempts": attempt + 1}
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
            time.sleep(4 + 4 * attempt)
        except (ValueError, json.JSONDecodeError, urllib.error.URLError, TimeoutError) as e:
            err = str(e)[:160]
            time.sleep(2)
    # Fallback: Llama vision on keyframes (the 11B model takes one image per request)
    content: list = [{"type": "text", "text": prompt + "\nThe image is the moment B reaches the conflict point."}]
    mid = keyframe_paths[min(1, len(keyframe_paths) - 1)]
    content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(open(mid, "rb").read()).decode()}})
    for attempt in range(3):
        try:
            text = _post(C.VERIFY_FALLBACK, content, max_tokens=600)
            return {**parse_verdict(text), "model": C.VERIFY_FALLBACK, "input": "keyframe",
                    "latency_s": round(time.time() - t, 1), "fallback_reason": err}
        except Exception as e:  # noqa: BLE001 - every failure is recorded on the row
            err = f"{err}; fallback: {str(e)[:120]}"
            time.sleep(3)
    return {"verdict": "unclear", "conflict_type": "none", "severity": 0, "evasive_action": "none",
            "explanation": "Both verifiers were unavailable; this candidate stays unverified.",
            "confidence": 0.0, "model": "none", "input": "none", "error": err,
            "latency_s": round(time.time() - t, 1)}


# ---- v2 (pre-registered in eval/PREREGISTRATION-v2.md before it was run) -----------------
PROMPT_V2 = """You are a traffic-safety analyst. This clip is ZOOMED IN around one spot at an intersection
(the original camera is wide; this is a crop). Faces and plates are pixelated on purpose; never
try to identify anyone.

Road user A (amber box) is a {a_cls}. Road user B (cyan box) is a {b_cls}.
A pixel tracker flagged them because on screen B reached the spot A had just left {pet:.2f} s later.
Most such flags are false: things at different distances from the camera overlap on screen.

Answer these in order, briefly, then give the JSON:
1. Is A on the roadway (not sidewalk, not parked)? 2. Is B on the roadway?
3. Are A and B at the same distance from the camera (same depth), judged by their size and
   where they touch the ground?
4. At their closest, how far apart are they on the ground, in car lengths?
5. Did either brake hard, stop suddenly, or swerve?

Decision rule: verdict is "near_miss" ONLY IF answers 1-3 are all yes AND (closest gap is under
about one car length OR answer 5 is yes). If you cannot see well enough to answer 1-3, verdict is
"unclear". Otherwise "not_near_miss".

End with ONLY this JSON object on the last line:
{{"verdict": "near_miss" | "not_near_miss" | "unclear",
  "conflict_type": one of "left_turn_vs_through", "right_turn_vs_crossing", "turn_vs_pedestrian",
     "turn_vs_cyclist", "crossing_path", "merge", "other", "none",
  "severity": 1-5, "evasive_action": short phrase or "none",
  "explanation": one or two plain sentences a city council member would understand,
  "confidence": 0.0-1.0}}"""


def verify_v2(event: dict, crop_path: str, retries: int = 5) -> dict:
    prompt = PROMPT_V2.format(a_cls=event["a_cls"], b_cls=event["b_cls"], pet=event["pet_s"])
    video_b64 = base64.b64encode(open(crop_path, "rb").read()).decode()
    t = time.time()
    err = ""
    for attempt in range(retries):
        try:
            text = _post(C.VERIFY_MODEL, [{"type": "text", "text": prompt},
                                          {"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{video_b64}"}}],
                         max_tokens=3000)
            return {**parse_verdict(text), "model": C.VERIFY_MODEL, "input": "zoomed clip", "version": "v2",
                    "latency_s": round(time.time() - t, 1), "attempts": attempt + 1}
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
            time.sleep(4 + 4 * attempt)
        except (ValueError, json.JSONDecodeError, urllib.error.URLError, TimeoutError) as e:
            err = str(e)[:160]
            time.sleep(2)
    return {"verdict": "unclear", "conflict_type": "none", "severity": 0, "evasive_action": "none",
            "explanation": "The verifier was unavailable; this candidate stays unverified.",
            "confidence": 0.0, "model": "none", "input": "none", "version": "v2", "error": err,
            "latency_s": round(time.time() - t, 1)}
