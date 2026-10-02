"""v3 verifier input: an 8-frame storyboard around the moment of closest approach.

Each tile is the anonymised frame, zoomed on the conflict point, with A's and B's boxes, their
trajectories so far (ground-contact points), the conflict point, and the time relative to B's
arrival. Also computes track-based kinematics used by the rule variants (no model):
speed before vs at the conflict, and the minimum ground-point distance between A and B.
"""
from __future__ import annotations

import json
import math

import cv2
import numpy as np

from . import clips, config as C

N_TILES = 8


def _pts(tr: dict, t0: float, t1: float) -> list[list[float]]:
    return [p for p in tr["pts"] if t0 <= p[0] <= t1]


def kinematics(event: dict, doc: dict) -> dict:
    A, B = doc["tracks"][event["a"]], doc["tracks"][event["b"]]
    W = doc["width"]

    def speed(pts):
        if len(pts) < 2:
            return None
        d = sum(math.dist(p[1:3], q[1:3]) for p, q in zip(pts, pts[1:]))
        dt = pts[-1][0] - pts[0][0]
        return d / dt / W if dt > 0 else None  # frame-widths per second

    out = {}
    for name, tr, tc in (("a", A, event["t_a_exit"]), ("b", B, event["t_b_enter"])):
        before = speed(_pts(tr, tc - 2.0, tc - 0.5))
        at = speed(_pts(tr, tc - 0.5, tc + 0.5))
        out[f"{name}_speed_before"] = round(before, 4) if before is not None else None
        out[f"{name}_speed_at"] = round(at, 4) if at is not None else None
        out[f"{name}_slowdown"] = round(1 - at / before, 3) if before and at is not None and before > 0 else None
    # closest simultaneous ground distance (frame-width units) and relative box size (depth proxy)
    by_t = {round(p[0], 2): p for p in A["pts"]}
    best = None
    for q in B["pts"]:
        p = by_t.get(round(q[0], 2))
        if p:
            d = math.dist(p[1:3], q[1:3]) / W
            if best is None or d < best[0]:
                best = (d, p, q)
    if best:
        d, p, q = best
        out["min_gap_w"] = round(d, 4)
        out["depth_ratio"] = round(min(p[6] - p[4], q[6] - q[4]) / max(p[6] - p[4], q[6] - q[4], 1e-6), 3)
        out["ground_dy_w"] = round(abs(p[2] - q[2]) / W, 4)
    return out


def build(event: dict, doc: dict) -> str:
    src = C.WORK / event["source"] / "source.mp4"
    fps, W, H = doc["fps"], doc["width"], doc["height"]
    A, B = doc["tracks"][event["a"]], doc["tracks"][event["b"]]
    ta, tb = event["t_a_exit"], event["t_b_enter"]
    t0, t1 = max(0.0, ta - 1.2), min(doc["duration"] - 0.05, tb + 1.2)
    times = [t0 + (t1 - t0) * i / (N_TILES - 1) for i in range(N_TILES)]
    tc = event["t_b_enter"]
    near = [p[3:7] for tr in (A, B) for p in tr["pts"] if abs(p[0] - tc) <= 1.5]
    bw = max((b[2] - b[0] for b in near), default=0.1 * W)
    cw = min(W, max(3.0 * bw, 0.22 * W)); ch = cw * 9 / 16
    cx, cy = event["cell_xy"]; cy -= ch * 0.15
    X = int(min(max(0, cx - cw / 2), W - cw)); Y = int(min(max(0, cy - ch / 2), H - ch))
    cw, ch = int(cw), int(ch)
    by_f: dict[int, list] = {}
    for tid, tr in doc["tracks"].items():
        for p in tr["pts"]:
            by_f.setdefault(round(p[0] * fps), []).append((tid, tr["cls"], p[3:7]))
    cap = cv2.VideoCapture(str(src))
    tiles = []
    for t in times:
        f = round(t * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, img = cap.read()
        if not ok:
            img = np.zeros((H, W, 3), np.uint8)
        dets = by_f.get(f, [])
        clips.redact(img, [(c, b) for _, c, b in dets])
        for tr, col in ((A, clips.A_COL), (B, clips.B_COL)):
            path = [(int(p[1]), int(p[2])) for p in tr["pts"] if p[0] <= t]
            if len(path) > 1:
                cv2.polylines(img, [np.array(path, np.int32)], False, col, 2)
        for tid, _, b in dets:
            if tid in (event["a"], event["b"]):
                col = clips.A_COL if tid == event["a"] else clips.B_COL
                cv2.rectangle(img, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), col, 2)
        cv2.circle(img, (int(event["cell_xy"][0]), int(event["cell_xy"][1])), 8, (60, 60, 255), 2)
        tile = cv2.resize(img[Y:Y + ch, X:X + cw], (480, 270))
        cv2.rectangle(tile, (0, 0), (150, 24), (0, 0, 0), -1)
        cv2.putText(tile, f"t{t - tb:+.1f}s", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        tiles.append(tile)
    cap.release()
    grid = np.vstack([np.hstack(tiles[:4]), np.hstack(tiles[4:])])
    out = C.WORK / event["source"] / f"{event['id']}.story.jpg"
    cv2.imwrite(str(out), grid, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return str(out)


def main() -> None:
    evs = json.loads((C.WORK / "events.json").read_text())["events"]
    docs: dict = {}
    kin = {}
    for e in evs:
        d = docs.setdefault(e["source"], json.loads((C.WORK / e["source"] / "tracks.json").read_text()))
        build(e, d)
        kin[e["id"]] = kinematics(e, d)
    (C.WORK / "kinematics.json").write_text(json.dumps(kin, indent=1))
    print(len(evs), "storyboards")


if __name__ == "__main__":
    main()
