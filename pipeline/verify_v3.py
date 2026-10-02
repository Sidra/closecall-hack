"""Verifier v3: storyboard image (8 zoomed frames, tracks + trajectories drawn) + narrow questions.

The model returns facts as booleans; the verdict is then computed by a *rule* over those facts
and the track kinematics, so rules can be compared on dev without new model calls.
Models run on W&B Inference (CoreWeave) and build.nvidia.com in parallel.
"""
from __future__ import annotations

import base64
import json
import re
import time
import urllib.error
import urllib.request

from . import config as C

PROMPT_V3 = """These 8 frames (left to right, top row then bottom row) are zoomed in on one spot at an intersection,
from about 1 s before to 1 s after the moment of interest. Times are shown top-left. Faces and plates are
pixelated on purpose; never try to identify anyone.

Road user A (amber box and amber trail) is a {a_cls}. Road user B (cyan box and cyan trail) is a {b_cls}.
The trails show where each one has travelled on the ground. The red circle is where their paths cross on screen.
On screen, B reached the red circle {pet:.2f} s after A left it. Road users at different distances from the
camera often overlap on screen without ever being close, so judge real positions on the ground.

Answer each question with true or false, judged only from what you can see:
- a_on_road: A is on the roadway or a crossing (not on the sidewalk, not parked)
- b_on_road: B is on the roadway or a crossing (not on the sidewalk, not parked)
- same_depth: A and B are at about the same distance from the camera
- paths_cross: their ground paths actually cross or merge
- close: at some moment they are within about one car length of each other on the ground
- evasive: either one brakes, stops, swerves or yields abruptly because of the other

Reply with ONLY this JSON:
{{"a_on_road": bool, "b_on_road": bool, "same_depth": bool, "paths_cross": bool, "close": bool,
  "evasive": bool, "evidence": "one or two plain sentences about what you saw",
  "conflict_type": one of "left_turn_vs_through", "right_turn_vs_crossing", "turn_vs_pedestrian",
     "turn_vs_cyclist", "crossing_path", "merge", "other", "none"}}"""

PROMPT_RISK = """These 8 frames (left to right, top row then bottom row) are zoomed in on one spot at an intersection,
about 1 s before to 1 s after the moment of interest; times are top-left. Faces and plates are pixelated.
Road user A (amber box, amber trail) is a {a_cls}; road user B (cyan box, cyan trail) is a {b_cls}.
On screen B reached the red circle {pet:.2f} s after A left it, but things at different distances from the
camera often overlap on screen without being close.

How likely is it that A and B had a genuine near-miss on the ground (both in the roadway or crossing, at
the same place, close enough in time and space that a small change would have caused contact)?
Reply with ONLY JSON: {{"risk": integer 0-10, "evidence": "one plain sentence"}}"""

KEYS = ("a_on_road", "b_on_road", "same_depth", "paths_cross", "close", "evasive")

ENDPOINTS = {
    "wandb": (C.WANDB_BASE, lambda: C.WANDB_API_KEY),
    "nvidia": (C.NVIDIA_BASE, lambda: C.NVIDIA_API_KEY),
}
MODELS = {  # name -> (endpoint, model id)
    "gemma-4-31b": ("wandb", "google/gemma-4-31B-it"),
    "gemma-4-26b": ("wandb", "google/gemma-4-26B-A4B-it"),
    "qwen3.6-35b": ("wandb", "Qwen/Qwen3.6-35B-A3B"),
    "qwen3.8-27b": ("wandb", "Qwen/Qwen3.8-27B"),
    "kimi-k2.6": ("wandb", "moonshotai/Kimi-K2.6"),
    "glm-5.3-flash": ("wandb", "zai-org/GLM-5.3-Flash"),
    "minimax-m3": ("wandb", "MiniMaxAI/MiniMax-M3"),
    "nemotron-omni": ("nvidia", C.VERIFY_MODEL),
    "llama-3.2-11b-vision": ("nvidia", C.VERIFY_FALLBACK),
}


NO_THINK = {"qwen3.6-35b", "qwen3.8-27b", "kimi-k2.6", "glm-5.3-flash"}


def parse(text: str) -> dict:
    m = re.findall(r"\{[^{}]*\"a_on_road\"[^{}]*\}", text, re.S)
    if not m:
        raise ValueError(f"no JSON: {text[:160]!r}")
    d = json.loads(m[-1])
    for k in KEYS:
        v = d.get(k)
        d[k] = v if isinstance(v, bool) else str(v).lower() == "true"
    return d


def ask(model: str, event: dict, story_path: str, retries: int = 4) -> dict:
    risk_mode = model.endswith("@risk")
    model = model.removesuffix("@risk")
    ep, mid = MODELS[model]
    base, key = ENDPOINTS[ep]
    img = base64.b64encode(open(story_path, "rb").read()).decode()
    body = {"model": mid, "temperature": 0.1, "max_tokens": 4000, "messages": [{"role": "user", "content": [
        {"type": "text", "text": (PROMPT_RISK if risk_mode else PROMPT_V3).format(a_cls=event["a_cls"], b_cls=event["b_cls"], pet=event["pet_s"])},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}]}]}
    if model in NO_THINK:  # these spend the whole budget thinking and return empty content otherwise
        body["chat_template_kwargs"] = {"enable_thinking": False}
    t = time.time()
    err = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(f"{base}/chat/completions", data=json.dumps(body).encode(), headers={
                "Authorization": f"Bearer {key()}", "Content-Type": "application/json", "User-Agent": "curl/8.7.1"})
            r = json.load(urllib.request.urlopen(req, timeout=150))
            text = r["choices"][0]["message"].get("content") or ""
            if risk_mode:
                mm = re.findall(r"\{[^{}]*\"risk\"[^{}]*\}", text, re.S)
                if not mm:
                    raise ValueError(f"no risk JSON: {text[:120]!r}")
                d = json.loads(mm[-1])
                return {"risk": int(d["risk"]), "evidence": d.get("evidence", ""), "model": mid, "ok": True,
                        "latency_s": round(time.time() - t, 1)}
            return {**parse(text), "model": mid, "ok": True, "latency_s": round(time.time() - t, 1)}
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}: {e.read()[:120]!r}"
            if e.code in (400, 404, 422):
                break
            time.sleep(3 + 3 * attempt)
        except Exception as e:  # noqa: BLE001 - recorded on the result
            err = str(e)[:160]
            time.sleep(2)
    return {"model": mid, "ok": False, "error": err, "latency_s": round(time.time() - t, 1)}


def load(split: str) -> dict:
    """Merge the per-model cache files for a split."""
    out = {}
    for p in C.WORK.glob(f"v3_{split}__*.json"):
        out[p.stem.split("__", 1)[1]] = json.loads(p.read_text())
    return out


def run(split: str, models: list[str], workers: int = 12) -> dict:
    """Ask every model about every event in `split`; cache per (model, event) in v3_<split>.json."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from . import tracing

    tracing.init()
    traced_ask = tracing.op(ask)
    ids = json.loads((C.ROOT / "eval" / "split.json").read_text())[split]
    evs = {e["id"]: e for e in json.loads((C.WORK / "events.json").read_text())["events"]}
    cache = load(split)
    jobs = [(m, i) for m in models for i in ids if not cache.get(m, {}).get(i, {}).get("ok")]
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(traced_ask, m, evs[i], str(C.WORK / evs[i]["source"] / f"{i}.story.jpg")): (m, i) for m, i in jobs}
        for f in as_completed(futs):
            m, i = futs[f]
            cache.setdefault(m, {})[i] = f.result()
            (C.WORK / f"v3_{split}__{m}.json").write_text(json.dumps(cache[m], indent=1))  # one file per model
    return cache


if __name__ == "__main__":
    import sys

    split = sys.argv[1]
    models = sys.argv[2].split(",") if len(sys.argv) > 2 else list(MODELS)
    c = run(split, models)
    for m, r in c.items():
        print(m, sum(v.get("ok", False) for v in r.values()), "/", len(r))
