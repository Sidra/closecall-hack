"""Stage 0: YOLO26 detection + ByteTrack tracking of road users.

Output per source: data/work/<id>/tracks.json
  {fps, width, height, duration, tracks: {tid: {cls, pts: [[t, x, y, x1, y1, x2, y2], ...]}}}
where (x, y) is the ground-contact point (bottom-centre of the box) in analysis pixels.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import cv2

from . import config as C


def transcode(src_id: str) -> Path:
    """Normalise any source container to a constant-rate H.264 mp4 at analysis width."""
    src = C.RAW / C.SOURCES[src_id]["file"]
    out_dir = C.WORK / src_id
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / "source.mp4"
    if not dst.exists():
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-an", "-vf",
             f"scale={C.ANALYSIS_W}:-2,fps=15", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "20", "-pix_fmt", "yuv420p", str(dst)],
            check=True,
        )
    return dst


def track(src_id: str, force: bool = False) -> dict:
    from ultralytics import YOLO

    video = transcode(src_id)
    out = C.WORK / src_id / "tracks.json"
    if out.exists() and not force:
        return json.loads(out.read_text())

    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    model = YOLO(C.YOLO_WEIGHTS)
    tracks: dict[str, dict] = {}
    for i, res in enumerate(model.track(source=str(video), stream=True, persist=True, verbose=False,
                                        classes=list(C.ROAD_USER_CLASSES), conf=0.25,
                                        tracker="bytetrack.yaml")):
        boxes = res.boxes
        if boxes is None or boxes.id is None:
            continue
        t = round(i / fps, 3)
        for xyxy, tid, cls in zip(boxes.xyxy.tolist(), boxes.id.int().tolist(), boxes.cls.int().tolist()):
            x1, y1, x2, y2 = (round(v, 1) for v in xyxy)
            rec = tracks.setdefault(str(tid), {"cls": C.ROAD_USER_CLASSES[cls], "pts": [], "votes": {}})
            rec["votes"][C.ROAD_USER_CLASSES[cls]] = rec["votes"].get(C.ROAD_USER_CLASSES[cls], 0) + 1
            rec["pts"].append([t, round((x1 + x2) / 2, 1), y2, x1, y1, x2, y2])
    for rec in tracks.values():  # majority class over the track's life
        rec["cls"] = max(rec.pop("votes").items(), key=lambda kv: kv[1])[0]
    data = {"fps": fps, "width": w, "height": h, "duration": round(n / fps, 2), "tracks": tracks}
    out.write_text(json.dumps(data))
    return data


if __name__ == "__main__":
    import sys

    for sid in sys.argv[1:] or list(C.SOURCES):
        d = track(sid)
        print(sid, len(d["tracks"]), "tracks", d["duration"], "s")
