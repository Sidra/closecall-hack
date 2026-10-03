"""Behaviour tests for the live engine's incremental PET (no video, no network)."""
from __future__ import annotations

from pipeline.live import LiveEngine


def feed(engine, frames, W=960):
    tracks, recent, out = {}, {}, []
    engine.move_px = 0.01 * W
    for t, dets in frames:
        evs = engine._update(tracks, dets, t, 24.0, W, recent)
        engine.events.extend(evs)
        out += evs
    return out


def box(x, y, w=40, h=30):
    return [x - w / 2, y - h, x + w / 2, y]


def crossing(gap=1.0):
    """A car drives left->right along y=300 through x=480; a person walks down through (480,300) later."""
    frames = []
    for k in range(60):
        t = k / 15
        dets = []
        ax = 200 + 150 * t
        if ax < 760:
            dets.append(("1", "car", box(ax, 300, 60, 40)))
        tb = t - (480 - 200) / 150 - gap  # person reaches the crossing `gap` s after the car left it
        by = 300 + 60 * tb
        if 150 < by < 450:
            dets.append(("2", "person", box(480, by, 14, 30)))
        frames.append((t, dets))
    return frames


def test_emits_one_event_for_a_crossing_pair():
    e = LiveEngine()
    evs = feed(e, crossing(1.0))
    assert len(evs) == 1
    ev = evs[0]
    assert {ev["a_cls"], ev["b_cls"]} == {"car", "person"}
    assert 0 < ev["pet_s"] < 4 and ev["vulnerable"] is True
    assert 35 <= ev["angle_deg"] <= 145


def test_no_event_when_gap_exceeds_threshold():
    e = LiveEngine()
    assert feed(e, crossing(6.0)) == []


def test_same_direction_following_is_not_a_conflict():
    frames = [(k / 15, [("1", "car", box(100 + 10 * k, 300, 60, 40)), ("2", "car", box(100 + 10 * (k - 15), 300, 60, 40))]) for k in range(15, 60)]
    assert feed(LiveEngine(), frames) == []


def test_two_pedestrians_are_ignored():
    frames = []
    for k in range(60):
        t = k / 15
        frames.append((t, [("1", "person", box(200 + 150 * t, 300, 14, 30)), ("2", "person", box(480, 300 + 60 * (t - 2.9), 14, 30))]))
    assert feed(LiveEngine(), frames) == []


def test_event_ids_are_unique_and_sequential():
    e = LiveEngine()
    a = feed(e, crossing(1.0))
    later = [(t + 20, [(i + "x", c, b) for i, c, b in d]) for t, d in crossing(0.5)]
    b = feed(e, later)
    ids = [x["id"] for x in a + b]
    assert len(ids) == len(set(ids)) == 2
