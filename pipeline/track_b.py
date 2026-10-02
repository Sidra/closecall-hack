"""Track B: CloseCall over the team's VAST VSS index (the provided intersection / dashcam footage).

1. Semantic search in VSS (Cosmos captions + Cosmos Embed vectors on VAST) for near-miss moments.
2. Download each hit segment through the VSS stream API; anonymise it with our YOLO26 redaction
   (geometric pixelation of heads + plates in tracked boxes) before anything is stored or shown.
3. Build an 8-frame storyboard and ask the same pre-registered 3-model vote (W&B Inference) a
   dashcam-specific question. Not evaluated: there are no labels for this footage.
Writes web/public/data/track_b.json for the UI. Nothing from the internet is ingested into VSS.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

from . import clips, config as C, tracing, verify_v3
from .vss import VssClient, VssError

QUERIES = [
    "near miss between a vehicle and a pedestrian at a crosswalk",
    "car braking hard or swerving to avoid a collision at an intersection",
    "pedestrian crossing in front of a turning vehicle",
    "vehicle running a red light or cutting across traffic at an intersection",
    "cyclist or scooter close call with a car",
]

PROMPT_B = """These 8 frames (left to right, top row then bottom row) come from one short traffic clip, possibly
filmed from a moving vehicle (dashcam). Faces and plates are pixelated on purpose; never identify anyone.

Answer each with true or false, judged only from what you can see:
- conflict_present: two road users (the camera vehicle counts) come close to colliding
- evasive: someone brakes hard, stops suddenly, swerves or yields abruptly because of another road user
- vulnerable_user: a pedestrian, cyclist or motorcyclist is involved in that conflict
- close: at their closest they are within about one car length

Reply with ONLY this JSON:
{"conflict_present": bool, "evasive": bool, "vulnerable_user": bool, "close": bool,
 "evidence": "one or two plain sentences about what you saw",
 "conflict_type": one of "turn_vs_pedestrian", "turn_vs_cyclist", "crossing_path", "rear_end_risk", "merge", "other", "none"}"""

KEYS_B = ("conflict_present", "evasive", "vulnerable_user", "close")
TRIO = ["qwen3.6-35b", "minimax-m3", "gemma-4-31b"]
OUT_DIR = C.WORK / "vss"


def rule_b(f: dict) -> bool:
    return bool(f["conflict_present"] and (f["close"] or f["evasive"]))


def _hid(source: str) -> str:
    return "vss-" + hashlib.sha256(source.encode()).hexdigest()[:12]


def anonymise(src: str, hid: str) -> tuple[str, str, str]:
    """Track with YOLO26, pixelate heads/plates in every box, write clip + keyframe + storyboard."""
    from ultralytics import YOLO

    norm = OUT_DIR / f"{hid}.norm.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-an", "-vf", f"scale={C.ANALYSIS_W}:-2,fps=15",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(norm)], check=True)
    model = YOLO(C.YOLO_WEIGHTS)
    cap = cv2.VideoCapture(str(norm))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    raw = OUT_DIR / f"{hid}.anon.raw.mp4"
    vw = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"mp4v"), 15, (w, h))
    frames = []
    picks = set(np.linspace(0, max(n - 1, 0), 8).astype(int).tolist())
    for i, res in enumerate(model.track(source=str(norm), stream=True, persist=True, verbose=False,
                                        classes=list(C.ROAD_USER_CLASSES), conf=0.2)):
        img = res.orig_img.copy()
        if res.boxes is not None and len(res.boxes):
            clips.redact(img, [(C.ROAD_USER_CLASSES[c], b) for b, c in zip(res.boxes.xyxy.tolist(), res.boxes.cls.int().tolist())])
        vw.write(img)
        if i in picks:
            t = cv2.resize(img, (480, int(480 * h / w)))
            cv2.rectangle(t, (0, 0), (90, 22), (0, 0, 0), -1)
            cv2.putText(t, f"{i / 15:.1f}s", (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            frames.append(t)
    vw.release()
    C.CLIPS_OUT.mkdir(parents=True, exist_ok=True)
    clip = C.CLIPS_OUT / f"{hid}.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-vf", "scale=640:-2", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(clip)], check=True)
    raw.unlink(missing_ok=True)
    while len(frames) < 8:
        frames.append(np.zeros_like(frames[0]) if frames else np.zeros((270, 480, 3), np.uint8))
    key = C.CLIPS_OUT / f"{hid}_k1.jpg"
    cv2.imwrite(str(key), cv2.resize(frames[3], (640, int(640 * frames[3].shape[0] / frames[3].shape[1]))))
    story = OUT_DIR / f"{hid}.story.jpg"
    cv2.imwrite(str(story), np.vstack([np.hstack(frames[:4]), np.hstack(frames[4:8])]), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return f"clips/{clip.name}", f"clips/{key.name}", str(story)


@tracing.op
def vote_b(hid: str, story: str) -> dict:
    per = {}
    for m in TRIO:
        r = verify_v3.ask_prompt(m, PROMPT_B, story, KEYS_B)
        per[m] = r
    ok = {m: r for m, r in per.items() if r.get("ok")}
    votes = {m: rule_b(r) for m, r in ok.items()}
    flag = len(ok) >= 2 and sum(votes.values()) >= 2
    agree = [ok[m] for m, v in votes.items() if v == flag]
    return {"verdict": "near_miss" if flag else "not_near_miss", "votes": votes,
            "evidence": agree[0].get("evidence", "") if agree else "",
            "conflict_type": agree[0].get("conflict_type", "none") if (agree and flag) else "none",
            "models_answered": len(ok)}


def main(max_hits: int = 12) -> None:
    tracing.init()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    vss = VssClient()
    vss.login()
    status = {"mode": "live", "base": vss.base, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        status["indexed_videos"] = len(vss.explore())
    except VssError as e:
        status["indexed_videos"] = None
        status["explore_error"] = str(e)[:160]
    hits: dict[str, dict] = {}
    for q in QUERIES:
        res = vss.search(q, top_k=10, min_similarity=0.3)
        for r in res.get("results", []):
            src = r.get("source")
            if not src:
                continue
            cur = hits.get(src)
            if cur is None or r.get("similarity_score", 0) > cur["similarity"]:
                hits[src] = {"source": src, "query": q, "similarity": round(float(r.get("similarity_score", 0)), 3),
                             "vss_reasoning": (r.get("reasoning_content") or "")[:600],
                             "original_video": r.get("original_video") or r.get("parent_video"),
                             "start_sec": r.get("start_sec") or r.get("segment_start_sec"),
                             "end_sec": r.get("end_sec") or r.get("segment_end_sec")}
    top = sorted(hits.values(), key=lambda x: -x["similarity"])[:max_hits]

    def one(h: dict) -> dict:
        hid = _hid(h["source"])
        local = OUT_DIR / f"{hid}.src.mp4"
        if not local.exists():
            vss.download(h["source"], local)
        clip, key, story = anonymise(str(local), hid)
        v = vote_b(hid, story)
        return {"id": hid, **h, "clip": clip, "keyframe": key, **v}

    with ThreadPoolExecutor(3) as ex:
        items = list(ex.map(one, top))
    out = {**status, "queries": QUERIES, "hits_found": len(hits), "items": items,
           "verifier": "2-of-3 vote (Qwen3.6-35B, MiniMax-M3, Gemma-4-31B on W&B Inference), dashcam prompt",
           "evaluated": False}
    (C.OUT / "track_b.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("indexed_videos", "hits_found")}), sum(i["verdict"] == "near_miss" for i in items), "flagged of", len(items))


if __name__ == "__main__":
    main()
