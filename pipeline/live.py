"""CloseCall live: real-time near-miss detection on a camera stream (or a recorded clip at 1x).

Run:  .venv/bin/python -m pipeline.live            (serves http://localhost:3503)

Per frame: YOLO26 + ByteTrack -> incremental PET on a ground-contact grid -> the same physics
filter as the batch pipeline -> an event the moment PET < threshold. Every frame is pixelated
(heads + plates in tracked boxes) before it is encoded or stored. Events go asynchronously to the
pre-registered 3-model vote on W&B Inference (when a key is set); cards update when it returns.

Endpoints: GET /sources · POST /start {source} · POST /stop · GET /stream.mjpg · GET /events (SSE)
           GET /thumb/{id}.jpg · GET /search?q= · GET /state
Nothing is faked: every number is measured on this machine; the recorded source is labelled
"simulated live (recorded clip at 1x)".
"""
from __future__ import annotations

import asyncio
import json
import math
import queue
import statistics
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from . import clips, config as C, score_v3, tracing, verify_v3

LIVE_DIR = C.WORK / "live"
PET_S = C.PET_CANDIDATE_S
TRIO = ["qwen3.6-35b", "minimax-m3", "gemma-4-31b"]

SOURCES: dict[str, dict] = {
    "caltrans-capistrano": {
        "kind": "live", "title": "SR-1 at Capistrano Rd, Half Moon Bay (Caltrans CCTV)",
        "url": "https://wzmedia.dot.ca.gov/D4/N1_at_Capistrano_Rd.stream/playlist.m3u8",
        "license": "Caltrans CCTV, public domain unless otherwise indicated (dot.ca.gov/conditions-of-use)",
        "label": "LIVE camera",
    },
    **{
        f"recorded-{sid}": {
            "kind": "simulated", "title": meta["title"], "url": str(C.WORK / sid / "source.mp4"),
            "license": f"{meta['license']} · {meta['author']}", "label": "simulated live (recorded clip at 1x)",
        } for sid, meta in C.SOURCES.items()
    },
}


def pctl(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    k = min(len(s) - 1, max(0, round(p / 100 * (len(s) - 1))))
    return round(s[k], 1)


@dataclass
class Track:
    cls: str
    pts: deque = field(default_factory=lambda: deque(maxlen=90))  # (t, x, y, box)
    cells: dict = field(default_factory=dict)  # cell -> [t_first, t_last]
    first_t: float = 0.0


class LiveEngine:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.subscribers: list[queue.Queue] = []
        self.thread: threading.Thread | None = None
        self.stop_flag = threading.Event()
        self.jpeg: bytes | None = None
        self.events: list[dict] = []
        self.thumbs: dict[str, bytes] = {}
        self.pool = ThreadPoolExecutor(4)
        self.in_flight = 0
        self.max_in_flight = 6  # W&B votes take ~15-20 s; beyond this, events are labelled "vote skipped"
        self.seq = 0
        self.vote_on = bool(C.WANDB_API_KEY)
        self.reset_stats()
        self.source_id: str | None = None

    # ---------- pub/sub ----------
    def publish(self, kind: str, data: dict) -> None:
        msg = f"event: {kind}\ndata: {json.dumps(data)}\n\n"
        for q in list(self.subscribers):
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass

    def reset_stats(self) -> None:
        self.frames = 0
        self.dropped = 0
        self.proc_times: deque = deque(maxlen=300)
        self.frame_walls: deque = deque(maxlen=600)
        self.flag_lat: list[float] = []
        self.vote_lat: list[float] = []
        self.started_wall = time.time()

    def stats(self) -> dict:
        now = time.time()
        recent = [w for w in self.frame_walls if w >= now - 10]
        span = min(10.0, now - self.started_wall)
        fps = round(len(recent) / span, 1) if span > 1 else None  # frames processed per second, rolling 10 s
        return {
            "source": self.source_id, "running": bool(self.thread and self.thread.is_alive()),
            "fps": fps, "frames": self.frames, "dropped": self.dropped,
            "detect_ms_p50": pctl(list(self.proc_times), 50),
            "events": len(self.events), "flag_ms_p50": pctl(self.flag_lat, 50), "flag_ms_p95": pctl(self.flag_lat, 95),
            "vote_ms_p50": pctl(self.vote_lat, 50), "vote_ms_p95": pctl(self.vote_lat, 95),
            "votes_done": len(self.vote_lat), "vote_on": self.vote_on,
            "uptime_s": round(time.time() - self.started_wall, 1),
        }

    # ---------- control ----------
    def start(self, source_id: str) -> None:
        if source_id not in SOURCES:
            raise KeyError(source_id)
        self.stop()
        with self.lock:
            self.events, self.thumbs = [], {}
            self.seq = 0
            self.in_flight = 0
            self.reset_stats()
            self.source_id = source_id
            self.stop_flag.clear()
            self.session = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + source_id
            LIVE_DIR.mkdir(parents=True, exist_ok=True)
            self.thread = threading.Thread(target=self._run, args=(SOURCES[source_id],), daemon=True)
            self.thread.start()
        self.publish("reset", {"source": source_id, **SOURCES[source_id]})

    def stop(self) -> None:
        self.stop_flag.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

    # ---------- frame source ----------
    def _frames(self, src: dict):
        """Yields (frame, stream_t, wall_capture). Recorded clips are paced to real time (1x),
        dropping frames if processing falls behind; live streams always yield the newest frame."""
        cap = cv2.VideoCapture(src["url"])
        if not cap.isOpened():
            raise RuntimeError(f"cannot open {src['title']}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
        if fps > 60 or fps <= 0:
            fps = 15.0
        if src["kind"] == "simulated":
            t0 = time.monotonic()
            idx = 0
            while not self.stop_flag.is_set():
                target = idx / fps
                now = time.monotonic() - t0
                if now < target:
                    time.sleep(target - now)
                elif now - target > 1.5 / fps:  # behind: skip to real time
                    skip = int((now - target) * fps)
                    for _ in range(skip):
                        cap.grab()
                    idx += skip
                    self.dropped += skip
                ok, f = cap.read()
                if not ok:  # loop the clip, keep the clock running
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    t0 = time.monotonic() - (idx + 1) / fps
                    ok, f = cap.read()
                    if not ok:
                        return
                yield f, idx / fps, time.time()
                idx += 1
        else:
            # Live HLS: ffmpeg decodes at a fixed 15 fps into raw BGR frames on a pipe (robust, no
            # GIL-starved grabber thread). Frames are read in order; processing (~90 fps) keeps up.
            import subprocess

            cap.release()
            probe = cv2.VideoCapture(src["url"])
            ok, f0 = probe.read()
            probe.release()
            if not ok:
                raise RuntimeError("live stream returned no frames")
            h, w = f0.shape[:2]
            proc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", src["url"], "-an", "-vf", "fps=15",
                                     "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1"], stdout=subprocess.PIPE)
            size = w * h * 3
            t_start = time.monotonic()
            try:
                while not self.stop_flag.is_set():
                    buf = proc.stdout.read(size)
                    if len(buf) < size:
                        break
                    yield np.frombuffer(buf, np.uint8).reshape(h, w, 3).copy(), time.monotonic() - t_start, time.time()
            finally:
                proc.kill()
            return
        cap.release()

    # ---------- main loop ----------
    def _run(self, src: dict) -> None:
        from ultralytics import YOLO
        import torch

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        model = YOLO(C.YOLO_WEIGHTS)
        tracks: dict[str, Track] = {}
        ring: deque = deque(maxlen=120)  # (stream_t, redacted frame)
        recent_pairs: dict[tuple, float] = {}
        log = (LIVE_DIR / f"{self.session}.jsonl").open("a")
        try:
            for frame, t, wall in self._frames(src):
                h0, w0 = frame.shape[:2]
                if w0 > 960:
                    frame = cv2.resize(frame, (960, int(960 * h0 / w0)))
                H, W = frame.shape[:2]
                cell = max(6.0, W * C.CELL_FRAC)
                self.move_px = max(3.0, 0.01 * W)  # "moving" = >1% of frame width in the last second
                p0 = time.perf_counter()
                res = model.track(frame, persist=True, verbose=False, device=device,
                                  classes=list(C.ROAD_USER_CLASSES), conf=0.25, tracker="bytetrack.yaml")[0]
                dets = []
                if res.boxes is not None and res.boxes.id is not None:
                    for b, tid, c in zip(res.boxes.xyxy.tolist(), res.boxes.id.int().tolist(), res.boxes.cls.int().tolist()):
                        dets.append((str(tid), C.ROAD_USER_CLASSES[c], b))
                new_events = self._update(tracks, dets, t, cell, W, recent_pairs)
                self.proc_times.append((time.perf_counter() - p0) * 1000)
                img = frame.copy()
                clips.redact(img, [(c, b) for _, c, b in dets])
                for tid, c, b in dets:
                    col = (0, 176, 255) if c in C.VULNERABLE else (255, 214, 0)
                    cv2.rectangle(img, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), col, 1 if W < 500 else 2)
                for e in self.events[-5:]:
                    if t - e["t"] < 1.5:
                        cv2.circle(img, (int(e["x"]), int(e["y"])), 14, (60, 60, 255), 2)
                ring.append((t, img))
                ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if ok:
                    self.jpeg = jpg.tobytes()
                self.frames += 1
                self.frame_walls.append(time.time())
                for e in new_events:
                    e["flag_ms"] = round((time.time() - wall) * 1000, 1)
                    self.flag_lat.append(e["flag_ms"])
                    x1, y1 = max(0, int(e["x"] - W * 0.2)), max(0, int(e["y"] - H * 0.25))
                    crop = img[y1:y1 + int(H * 0.5), x1:x1 + int(W * 0.4)]
                    if crop.size:
                        okt, th = cv2.imencode(".jpg", cv2.resize(crop, (320, 200)), [cv2.IMWRITE_JPEG_QUALITY, 80])
                        if okt:
                            self.thumbs[e["id"]] = th.tobytes()
                    self.events.append(e)
                    log.write(json.dumps({k: v for k, v in e.items()}) + "\n")
                    log.flush()
                    self.publish("near_miss", e)
                    priority = e["vulnerable"] or e["pet_s"] < 1.5
                    if self.vote_on and not priority:
                        e["vote"] = "low_priority"
                        self.publish("vote", {"id": e["id"], "vote": "low_priority", "votes": {}, "evidence": "not voted: no vulnerable road user and PET ≥ 1.5 s", "vote_ms": None})
                    elif self.vote_on and self.in_flight < self.max_in_flight:
                        self.in_flight += 1
                        self.pool.submit(self._vote_later, e, ring, W, H)
                    elif self.vote_on:
                        e["vote"] = "skipped"
                        self.publish("vote", {"id": e["id"], "vote": "skipped", "votes": {}, "evidence": "vote queue full (W&B calls take ~15-20 s); not voted", "vote_ms": None})
                if self.frames % 15 == 0:
                    self.publish("stats", self.stats())
        except Exception as ex:  # noqa: BLE001 - surfaced to the UI, never silent
            self.publish("error", {"message": str(ex)[:200]})
        finally:
            log.close()
            self.publish("stats", self.stats())

    # ---------- incremental PET ----------
    def _update(self, tracks: dict, dets: list, t: float, cell: float, W: int, recent_pairs: dict) -> list[dict]:
        out = []
        present = set()
        for tid, cls, b in dets:
            tr = tracks.get(tid)
            if tr is None:
                tr = tracks[tid] = Track(cls=cls, first_t=t)
            x, y = (b[0] + b[2]) / 2, b[3]
            tr.pts.append((t, x, y, b))
            present.add(tid)
            cy = int(y // cell)
            for cx in range(int(b[0] // cell), int(b[2] // cell) + 1):
                c = (cx, cy)
                if c in tr.cells:
                    tr.cells[c][1] = t
                    continue
                tr.cells[c] = [t, t]
                # B (=tr) just entered cell c: who left it within the last PET_S seconds?
                for aid, a in tracks.items():
                    if aid == tid or c not in a.cells or aid in present and a.cells[c][1] >= t - 1e-6:
                        continue
                    gap = t - a.cells[c][1]
                    if 0 < gap < PET_S:
                        e = self._candidate(aid, a, tid, tr, gap, t, (cx + 0.5) * cell, (cy + 0.5) * cell, W, recent_pairs)
                        if e:
                            out.append(e)
        # prune
        for tid in list(tracks):
            tr = tracks[tid]
            if tid not in present and tr.pts and t - tr.pts[-1][0] > PET_S + 3:
                del tracks[tid]
                continue
            for c in [c for c, (_, l) in tr.cells.items() if t - l > PET_S + 3]:
                del tr.cells[c]
        return out

    def _heading(self, tr: Track, t: float):
        near = [p for p in tr.pts if abs(p[0] - t) <= 1.0]
        if len(near) < 2:
            return None
        dx, dy = near[-1][1] - near[0][1], near[-1][2] - near[0][2]
        n = math.hypot(dx, dy)
        return (dx / n, dy / n) if n > self.move_px else None

    def _candidate(self, aid, a: Track, bid, b: Track, gap, t, x, y, W, recent_pairs) -> dict | None:
        if a.cls == "person" and b.cls == "person":
            return None
        key = tuple(sorted((aid, bid)))
        if t - recent_pairs.get(key, -1e9) < 5:
            return None
        # fragment: B appeared right where/when A vanished
        if b.first_t - a.pts[-1][0] < 1.0 and math.dist(b.pts[0][1:3], a.pts[-1][1:3]) < 0.06 * W:
            return None
        # rider: overlapping boxes person vs two-wheeler
        if {a.cls, b.cls} & {"person"} and {a.cls, b.cls} & {"bicycle", "motorcycle"}:
            ab, bb = a.pts[-1][3], b.pts[-1][3]
            ix = max(0, min(ab[2], bb[2]) - max(ab[0], bb[0])); iy = max(0, min(ab[3], bb[3]) - max(ab[1], bb[1]))
            if ix * iy > 0:
                return None
        ha, hb = self._heading(a, a.pts[-1][0]), self._heading(b, t)  # A around when it left, B now
        if ha is None or hb is None:
            return None
        ang = math.degrees(math.acos(max(-1.0, min(1.0, ha[0] * hb[0] + ha[1] * hb[1]))))
        if not 35 <= ang <= 145:
            return None
        recent_pairs[key] = t
        # cluster: same moment (2 s) and same place (6 cells) as a recent event -> refine that one
        for ev in reversed(self.events[-20:]):
            if t - ev["t"] <= 2.0 and math.dist((ev["x"], ev["y"]), (x, y)) <= 6 * max(6.0, W * C.CELL_FRAC):
                ev["pairs"] = ev.get("pairs", 1) + 1
                if gap < ev["pet_s"]:
                    ev.update(pet_s=round(gap, 2), a_cls=a.cls, b_cls=b.cls)
                self.publish("update", {"id": ev["id"], "pet_s": ev["pet_s"], "pairs": ev["pairs"], "a_cls": ev["a_cls"], "b_cls": ev["b_cls"]})
                return None
        self.seq += 1
        return {"id": f"live-{self.seq:04d}", "pairs": 1, "a_cls": a.cls, "b_cls": b.cls, "pet_s": round(gap, 2),
                "angle_deg": round(ang, 1), "t": round(t, 2), "t_a_exit": round(t - gap, 2), "x": round(x, 1), "y": round(y, 1),
                "vulnerable": bool({a.cls, b.cls} & C.VULNERABLE), "wall": time.time(), "vote": "pending" if self.vote_on else "off"}

    # ---------- async vote ----------
    def _vote_later(self, e: dict, ring: deque, W: int, H: int) -> None:
        time.sleep(1.3)  # let the after-frames arrive
        t0, t1 = e["t_a_exit"] - 1.2, e["t"] + 1.2
        frames = [f for (t, f) in list(ring) if t0 <= t <= t1]
        if len(frames) < 4:
            frames = [f for _, f in list(ring)[-16:]]
        pick = [frames[int(i)] for i in np.linspace(0, len(frames) - 1, 8)]
        cw = min(W, max(int(W * 0.35), 200)); ch = int(cw * 9 / 16)
        X = int(min(max(0, e["x"] - cw / 2), W - cw)); Y = int(min(max(0, e["y"] - ch * 0.65), H - ch))
        tiles = [cv2.resize(f[Y:Y + ch, X:X + cw], (480, 270)) for f in pick]
        story = LIVE_DIR / f"{e['id']}.story.jpg"
        cv2.imwrite(str(story), np.vstack([np.hstack(tiles[:4]), np.hstack(tiles[4:])]), [cv2.IMWRITE_JPEG_QUALITY, 85])
        w0 = time.time()
        try:
            res = live_vote(e["id"], e["a_cls"], e["b_cls"], e["pet_s"], str(story))
        finally:
            self.in_flight -= 1
        ms = round((time.time() - w0) * 1000)
        self.vote_lat.append(ms)
        e.update(vote=res["verdict"], votes=res["votes"], evidence=res["evidence"], vote_ms=ms, flag_to_vote_ms=round((time.time() - e["wall"]) * 1000))
        self.publish("vote", {"id": e["id"], "vote": e["vote"], "votes": e["votes"], "evidence": e["evidence"], "vote_ms": ms,
                              "flag_to_vote_ms": e["flag_to_vote_ms"]})
        self.publish("stats", self.stats())


@tracing.op
def live_vote(event_id: str, a_cls: str, b_cls: str, pet_s: float, story: str) -> dict:
    ev = {"a_cls": a_cls, "b_cls": b_cls, "pet_s": pet_s}
    with ThreadPoolExecutor(len(TRIO)) as ex:  # the three models in parallel
        per = dict(zip(TRIO, ex.map(lambda m: verify_v3.ask(m, ev, story, retries=2), TRIO)))
    ok = {m: r for m, r in per.items() if r.get("ok")}
    votes = {m: bool(score_v3.RULES["strict"](r, {}, ev)) for m, r in ok.items()}
    flag = len(ok) >= 2 and sum(votes.values()) >= 2
    agree = [ok[m] for m, v in votes.items() if v == flag]
    return {"verdict": ("near_miss" if flag else "not_near_miss") if len(ok) >= 2 else "unavailable",
            "votes": votes, "evidence": agree[0].get("evidence", "") if agree else ""}


ENGINE = LiveEngine()


def search(q: str) -> list[dict]:
    """Keyword search over live events (pair, PET, vote evidence); grows as events and votes arrive."""
    terms = [w for w in q.lower().split() if len(w) > 2]
    scored = []
    for e in ENGINE.events:
        text = f"{e['a_cls']} {e['b_cls']} {e.get('evidence', '')} {'vulnerable pedestrian cyclist' if e['vulnerable'] else ''}".lower()
        s = sum(w.rstrip("s") in text for w in terms) / len(terms) if terms else 0
        if s > 0:
            scored.append({"id": e["id"], "score": round(s, 2)})
    return sorted(scored, key=lambda x: -x["score"])[:10]


def create_app():
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import Response, StreamingResponse

    app = FastAPI(title="CloseCall live")
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3502", "http://127.0.0.1:3502"],
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.on_event("startup")
    def _init() -> None:
        tracing.init()

    @app.get("/sources")
    def sources():
        return [{"id": k, **{x: v[x] for x in ("kind", "title", "license", "label")}} for k, v in SOURCES.items()]

    @app.post("/start")
    def start(body: dict):
        sid = str(body.get("source", ""))
        if sid not in SOURCES:
            raise HTTPException(400, "unknown source")
        ENGINE.start(sid)
        return {"ok": True, "source": sid}

    @app.post("/stop")
    def stop():
        ENGINE.stop()
        return {"ok": True}

    @app.get("/state")
    def state():
        return {"stats": ENGINE.stats(), "events": ENGINE.events[-50:],
                "source": SOURCES.get(ENGINE.source_id or "", {}).get("label")}

    @app.get("/search")
    def do_search(q: str = ""):
        return {"mode": "keyword (live index)", "results": search(q[:200])}

    @app.get("/thumb/{eid}.jpg")
    def thumb(eid: str):
        b = ENGINE.thumbs.get(eid)
        if b is None:
            raise HTTPException(404)
        return Response(b, media_type="image/jpeg")

    @app.get("/stream.mjpg")
    async def mjpeg():
        async def gen():
            last = None
            while True:
                j = ENGINE.jpeg
                if j is not None and j is not last:
                    last = j
                    yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(j)).encode() + b"\r\n\r\n" + j + b"\r\n"
                await asyncio.sleep(1 / 20)
        return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get("/events")
    async def events():
        q: queue.Queue = queue.Queue(maxsize=500)
        ENGINE.subscribers.append(q)

        async def gen():
            try:
                yield f"event: stats\ndata: {json.dumps(ENGINE.stats())}\n\n"
                while True:
                    try:
                        yield q.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(0.05)
            finally:
                if q in ENGINE.subscribers:
                    ENGINE.subscribers.remove(q)
        return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=3503, log_level="warning")
