"""Stage 1 (cheap, statistical): post-encroachment time (PET) between road-user pairs.

PET = time between road user A leaving a patch of road and road user B entering that same
patch. Small PET = they nearly occupied the same space. A pair is a *candidate* when
PET < PET_CANDIDATE_S.

Honest limits (also in the README): PET is measured in the image plane on a coarse grid,
without a ground-plane homography, so it is an approximation of true PET. This is why every
candidate goes to stage 2 (a video-reasoning model) before it reaches the ledger.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from . import config as C


@dataclass
class Candidate:
    id: str
    source: str
    a: str
    b: str
    a_cls: str
    b_cls: str
    pet_s: float
    t_a_exit: float
    t_b_enter: float
    cell_xy: tuple[float, float]
    a_speed_pxs: float
    b_speed_pxs: float
    vulnerable: bool


def _footprint_cells(pt: list[float], cell: float) -> set[tuple[int, int]]:
    """Cells under the bottom edge of the box (where the road user touches the road)."""
    _, _, y, x1, _, x2, _ = pt
    cy = int(y // cell)
    return {(cx, cy) for cx in range(int(x1 // cell), int(x2 // cell) + 1)}


def _speed(pts: list[list[float]]) -> float:
    if len(pts) < 2:
        return 0.0
    dist = sum(math.dist(p[1:3], q[1:3]) for p, q in zip(pts, pts[1:]))
    dur = pts[-1][0] - pts[0][0]
    return dist / dur if dur > 0 else 0.0


def _path_len(pts: list[list[float]]) -> float:
    return math.dist(pts[0][1:3], pts[-1][1:3]) if pts else 0.0


def _heading(pts: list[list[float]], t: float, win: float = 1.0) -> tuple[float, float] | None:
    """Unit direction of travel around time t (None if the user is ~stationary there)."""
    near = [p for p in pts if abs(p[0] - t) <= win]
    if len(near) < 2:
        near = pts[:2] if t < pts[0][0] else pts[-2:]
    dx, dy = near[-1][1] - near[0][1], near[-1][2] - near[0][2]
    n = math.hypot(dx, dy)
    return (dx / n, dy / n) if n > 6 else None


def _iou(p: list[float], q: list[float]) -> float:
    ix = max(0.0, min(p[5], q[5]) - max(p[3], q[3]))
    iy = max(0.0, min(p[6], q[6]) - max(p[4], q[4]))
    inter = ix * iy
    ua = (p[5] - p[3]) * (p[6] - p[4]) + (q[5] - q[3]) * (q[6] - q[4]) - inter
    return inter / ua if ua > 0 else 0.0


def riders(tracks: dict) -> set[str]:
    """Person tracks that ride a bicycle/motorcycle track (boxes overlap most of their shared life)."""
    two_wheel = {t: tr for t, tr in tracks.items() if tr["cls"] in ("bicycle", "motorcycle")}
    out = set()
    for tid, tr in tracks.items():
        if tr["cls"] != "person":
            continue
        by_t = {round(p[0], 2): p for p in tr["pts"]}
        for vt in two_wheel.values():
            shared = [(by_t[round(q[0], 2)], q) for q in vt["pts"] if round(q[0], 2) in by_t]
            if len(shared) >= 5 and sum(_iou(a, b) > 0.1 for a, b in shared) / len(shared) > 0.6:
                out.add(tid)
                break
    return out


def physics_filter(cands: list[dict], tracks_doc: dict, min_angle_deg: float = 35.0,
                   max_angle_deg: float = 145.0) -> list[dict]:
    """Stage 1b: keep crossing/turning conflicts only.

    Drops (a) riders counted against their own bike, (b) same-direction following (that is a
    headway question, not a crossing conflict), (c) pedestrian-pedestrian pairs, (d) opposite-direction passes (>145 deg: in the
    image plane, perspective makes far lanes overlap), (e) pairs where either user is stationary at the
    conflict. Rule-based, no model.
    """
    tr = tracks_doc["tracks"]
    rid = riders(tr)
    keep = []
    for c in cands:
        if c["a"] in rid or c["b"] in rid:
            continue
        if c["a_cls"] == "person" and c["b_cls"] == "person":
            continue  # two pedestrians crossing paths is not a traffic conflict
        ha = _heading(tr[c["a"]]["pts"], c["t_a_exit"])
        hb = _heading(tr[c["b"]]["pts"], c["t_b_enter"])
        if ha is None or hb is None:
            continue
        cos = max(-1.0, min(1.0, ha[0] * hb[0] + ha[1] * hb[1]))
        ang = math.degrees(math.acos(cos))
        if not (min_angle_deg <= ang <= max_angle_deg):
            continue
        keep.append({**c, "angle_deg": round(ang, 1)})
    return keep


def candidates(src_id: str, tracks_doc: dict, pet_max: float = C.PET_CANDIDATE_S) -> list[dict]:
    W = tracks_doc["width"]
    cell = W * C.CELL_FRAC
    tracks = {
        tid: tr for tid, tr in tracks_doc["tracks"].items()
        if tr["pts"] and tr["pts"][-1][0] - tr["pts"][0][0] >= C.MIN_TRACK_S
    }
    occ: dict[str, dict[tuple[int, int], list[float]]] = {}
    for tid, tr in tracks.items():
        o: dict[tuple[int, int], list[float]] = {}
        for pt in tr["pts"]:
            for c in _footprint_cells(pt, cell):
                if c in o:
                    o[c][1] = pt[0]
                else:
                    o[c] = [pt[0], pt[0]]
        occ[tid] = o
    moving = {tid for tid, tr in tracks.items() if _path_len(tr["pts"]) > 0.04 * W}

    out: list[Candidate] = []
    ids = sorted(tracks, key=int)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if a not in moving and b not in moving:
                continue
            ta, tb = tracks[a], tracks[b]
            best = None
            for c in occ[a].keys() & occ[b].keys():
                (a0, a1), (b0, b1) = occ[a][c], occ[b][c]
                if a1 < b0:
                    first, second, gap = (a, b), (a1, b0), b0 - a1
                elif b1 < a0:
                    first, second, gap = (b, a), (b1, a0), a0 - b1
                else:
                    continue  # simultaneous occupancy in the image = occlusion, not a PET event
                if best is None or gap < best[0]:
                    best = (gap, first, second, c)
            if best is None or best[0] >= pet_max:
                continue
            gap, (fa, fb), (t_exit, t_enter), c = best
            A, B = tracks[fa], tracks[fb]
            # Tracker fragment: B starts where A ended, right after A ended -> same object, new ID.
            if (abs(B["pts"][0][0] - A["pts"][-1][0]) < 1.0
                    and math.dist(B["pts"][0][1:3], A["pts"][-1][1:3]) < 2.5 * cell):
                continue
            out.append(Candidate(
                id=f"{src_id}-{fa}-{fb}", source=src_id, a=fa, b=fb, a_cls=A["cls"], b_cls=B["cls"],
                pet_s=round(gap, 2), t_a_exit=t_exit, t_b_enter=t_enter,
                cell_xy=(round((c[0] + 0.5) * cell, 1), round((c[1] + 0.5) * cell, 1)),
                a_speed_pxs=round(_speed(A["pts"]), 1), b_speed_pxs=round(_speed(B["pts"]), 1),
                vulnerable=bool({A["cls"], B["cls"]} & C.VULNERABLE),
            ))
    out.sort(key=lambda c: c.pet_s)
    return [asdict(c) for c in out]


def events(cands: list[dict], cell: float, window_s: float = 2.0) -> list[dict]:
    """Collapse candidates that describe the same moment at the same place into one event.

    The representative is the lowest-PET pair; the rest are kept as `pairs` for the ledger.
    """
    out: list[dict] = []
    for c in sorted(cands, key=lambda c: c["pet_s"]):
        for e in out:
            if (e["source"] == c["source"] and abs(e["t_b_enter"] - c["t_b_enter"]) <= window_s
                    and math.dist(e["cell_xy"], c["cell_xy"]) <= 6 * cell):
                e["pairs"].append(c["id"])
                e["vulnerable"] = e["vulnerable"] or c["vulnerable"]
                break
        else:
            out.append({**c, "pairs": [c["id"]]})
    return out


if __name__ == "__main__":
    import json

    for sid in C.SOURCES:
        doc = json.loads((C.WORK / sid / "tracks.json").read_text())
        cs = candidates(sid, doc)
        ks = physics_filter(cs, doc)
        ev = events(ks, doc["width"] * C.CELL_FRAC)
        print(sid, len(cs), "naive ->", len(ks), "crossing ->", len(ev), "events;", sum(e["vulnerable"] for e in ev), "vulnerable")
        for c in ks[:6]:
            print("   ", c["a_cls"], "->", c["b_cls"], c["pet_s"], "s at", c["t_b_enter"], c["angle_deg"])
