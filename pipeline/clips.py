"""Export one evidence clip per event, anonymised.

Every road user in every frame is redacted before the clip is written:
  - people: the top 35% of the box (head and face) is pixelated;
  - vehicles: the lower 40% band of the box (where plates sit, front and rear) is pixelated.
No face or plate detector is run and no identity is ever extracted; redaction is geometric and
applied to all detections, so nothing identifiable reaches storage or the model.
The two actors in the event are outlined (A = amber, B = cyan) so the verifier and the reader
know which pair is in question.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np

from . import config as C

A_COL = (0, 176, 255)   # BGR amber
B_COL = (255, 214, 0)   # BGR cyan
VEHICLES = {"car", "bus", "truck", "motorcycle"}


def _pixelate(img: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> None:
    h, w = img.shape[:2]
    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
    if x2 - x1 < 2 or y2 - y1 < 2:
        return
    roi = img[y1:y2, x1:x2]
    small = cv2.resize(roi, (max(1, (x2 - x1) // 8), max(1, (y2 - y1) // 8)), interpolation=cv2.INTER_LINEAR)
    img[y1:y2, x1:x2] = cv2.resize(small, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)


def redact(img: np.ndarray, dets: list[tuple[str, list[float]]]) -> None:
    for cls, (x1, y1, x2, y2) in dets:
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        bh = y2 - y1
        if cls in ("person", "bicycle"):
            _pixelate(img, x1 - 2, y1 - 2, x2 + 2, y1 + int(0.35 * bh) + 2)
        if cls in VEHICLES:
            _pixelate(img, x1, y2 - int(0.4 * bh), x2, y2)


def export(event: dict, tracks_doc: dict, pad_s: float = 2.5, max_len_s: float = 8.0) -> dict:
    src = C.WORK / event["source"] / "source.mp4"
    fps = tracks_doc["fps"]
    t0 = max(0.0, event["t_a_exit"] - pad_s)
    t1 = min(tracks_doc["duration"], event["t_b_enter"] + pad_s, t0 + max_len_s)
    # index detections by frame
    by_f: dict[int, list[tuple[str, str, list[float]]]] = {}
    for tid, tr in tracks_doc["tracks"].items():
        for p in tr["pts"]:
            by_f.setdefault(round(p[0] * fps), []).append((tid, tr["cls"], p[3:7]))

    C.CLIPS_OUT.mkdir(parents=True, exist_ok=True)
    tmp = C.WORK / event["source"] / f"{event['id']}.raw.mp4"
    dst = C.CLIPS_OUT / f"{event['id']}.mp4"
    cap = cv2.VideoCapture(str(src))
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(t0 * fps))
    w, h = tracks_doc["width"], tracks_doc["height"]
    vw = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    keyframes: list[Path] = []
    done: set[int] = set()
    key_ts = [event["t_a_exit"] - 0.5, (event["t_a_exit"] + event["t_b_enter"]) / 2, event["t_b_enter"] + 0.3]
    f = round(t0 * fps)
    cx, cy = (int(v) for v in event["cell_xy"])
    while f <= round(t1 * fps):
        ok, img = cap.read()
        if not ok:
            break
        dets = by_f.get(f, [])
        redact(img, [(c, b) for _, c, b in dets])
        for tid, _, b in dets:
            if tid in (event["a"], event["b"]):
                col = A_COL if tid == event["a"] else B_COL
                cv2.rectangle(img, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), col, 2)
                cv2.putText(img, "A" if tid == event["a"] else "B", (int(b[0]), int(b[1]) - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)
        cv2.circle(img, (cx, cy), 14, (60, 60, 255), 2)
        t = f / fps
        cv2.putText(img, f"t={t:5.1f}s  PET={event['pet_s']:.2f}s", (12, h - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        vw.write(img)
        for i, kt in enumerate(key_ts):
            if i not in done and t >= kt:
                done.add(i)
                kp = C.CLIPS_OUT / f"{event['id']}_k{i}.jpg"
                cv2.imwrite(str(kp), cv2.resize(img, (640, int(640 * h / w))), [cv2.IMWRITE_JPEG_QUALITY, 82])
                keyframes.append(kp)
        f += 1
    vw.release()
    cap.release()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-vf", "scale=640:-2",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(dst)], check=True)
    tmp.unlink(missing_ok=True)
    return {"clip": f"clips/{dst.name}", "keyframes": [f"clips/{k.name}" for k in keyframes],
            "clip_t0": round(t0, 2), "clip_t1": round(t1, 2)}


def export_crop(event: dict, tracks_doc: dict, pad_s: float = 2.5, max_len_s: float = 8.0) -> str:
    """v2 verifier input: the same anonymised clip, cropped around the conflict point (3x the larger
    actor box, at least 22% of frame width) and upscaled to 640 px, so small far-field road
    users are big enough for the model to judge depth and distance."""
    src = C.WORK / event["source"] / "source.mp4"
    fps = tracks_doc["fps"]
    W, H = tracks_doc["width"], tracks_doc["height"]
    t0 = max(0.0, event["t_a_exit"] - pad_s)
    t1 = min(tracks_doc["duration"], event["t_b_enter"] + pad_s, t0 + max_len_s)
    # Centre on the conflict point; window = 3x the larger actor box near the conflict, at least 22% of width.
    tc = event["t_b_enter"]
    near = [p[3:7] for tid in (event["a"], event["b"]) for p in tracks_doc["tracks"][tid]["pts"] if abs(p[0] - tc) <= 1.5]
    bw = max((b[2] - b[0] for b in near), default=0.1 * W)
    cw = min(W, max(3.0 * bw, 0.22 * W)); ch = cw * 9 / 16
    cx, cy = event["cell_xy"]
    cy -= ch * 0.15  # ground point sits low in the box; show the road users above it
    X = int(min(max(0, cx - cw / 2), W - cw)); Y = int(min(max(0, cy - ch / 2), H - ch))
    cw, ch = int(cw) // 2 * 2, int(ch) // 2 * 2
    by_f: dict[int, list] = {}
    for tid, tr in tracks_doc["tracks"].items():
        for p in tr["pts"]:
            by_f.setdefault(round(p[0] * fps), []).append((tid, tr["cls"], p[3:7]))
    tmp = C.WORK / event["source"] / f"{event['id']}.crop.raw.mp4"
    dst = C.WORK / event["source"] / f"{event['id']}.crop.mp4"
    cap = cv2.VideoCapture(str(src))
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(t0 * fps))
    vw = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), fps, (640, 360))
    f = round(t0 * fps)
    while f <= round(t1 * fps):
        ok, img = cap.read()
        if not ok:
            break
        dets = by_f.get(f, [])
        redact(img, [(c, b) for _, c, b in dets])
        for tid, _, b in dets:
            if tid in (event["a"], event["b"]):
                col = A_COL if tid == event["a"] else B_COL
                cv2.rectangle(img, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), col, 2)
        vw.write(cv2.resize(img[Y:Y + ch, X:X + cw], (640, 360)))
        f += 1
    vw.release()
    cap.release()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "24", "-pix_fmt", "yuv420p", str(dst)], check=True)
    tmp.unlink(missing_ok=True)
    return str(dst)
