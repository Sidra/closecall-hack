"""Behaviour tests for the deterministic parts of the pipeline (no network, no video)."""
from __future__ import annotations

import numpy as np
import pytest

from pipeline import clips, pet, score_v3, verify, verify_v3


def track(cls, pts):
    """pts: list of (t, x, y_ground, w, h) -> track dict in tracks.json shape."""
    return {"cls": cls, "pts": [[t, x, y, x - w / 2, y - h, x + w / 2, y] for t, x, y, w, h in pts]}


def doc(tracks, width=960):
    return {"fps": 15, "width": width, "height": 540, "duration": 20, "tracks": tracks}


def crossing_pair(gap_s=1.0):
    # A drives left->right along y=300 through x=480 at t~2; B walks top->bottom through (480,300) later
    a = track("car", [(t / 10, 100 + 40 * t, 300, 60, 40) for t in range(0, 40)])
    tb0 = 2.4 + gap_s
    b = track("person", [(tb0 - 1.5 + t / 10, 480, 200 + 12 * t, 14, 30) for t in range(0, 20)])
    return doc({"1": a, "2": b})


def test_pet_flags_crossing_pair_and_measures_gap():
    d = crossing_pair(gap_s=1.0)
    cands = pet.candidates("x", d)
    assert len(cands) == 1
    c = cands[0]
    assert c["a"] == "1" and c["b"] == "2"
    assert 0 < c["pet_s"] < 4.0
    assert c["vulnerable"] is True


def test_pet_ignores_pairs_beyond_threshold():
    d = crossing_pair(gap_s=6.0)
    assert pet.candidates("x", d) == []


def test_simultaneous_occupancy_is_not_a_pet_event():
    # two boxes sharing the same cells at the same time = on-screen occlusion, not PET
    a = track("car", [(t / 10, 300 + t, 300, 60, 40) for t in range(30)])
    b = track("car", [(t / 10, 300 + t, 300, 60, 40) for t in range(30)])
    assert pet.candidates("x", doc({"1": a, "2": b})) == []


def test_tracker_fragment_is_dropped():
    # B starts exactly where/when A ended: same object with a new id
    a = track("car", [(t / 10, 100 + 20 * t, 300, 60, 40) for t in range(20)])
    last = a["pts"][-1]
    b = track("car", [(last[0] + 0.1 + t / 10, last[1] + 20 * (t + 1), 300, 60, 40) for t in range(20)])
    assert pet.candidates("x", doc({"1": a, "2": b})) == []


def test_physics_filter_drops_same_direction_following():
    a = track("car", [(t / 10, 100 + 20 * t, 300, 60, 40) for t in range(30)])
    b = track("car", [(1.5 + t / 10, 100 + 20 * t, 300, 60, 40) for t in range(30)])
    d = doc({"1": a, "2": b})
    naive = pet.candidates("x", d)
    assert naive, "following traffic is a naive PET flag"
    assert pet.physics_filter(naive, d) == []


def test_physics_filter_keeps_crossing_conflict_with_angle():
    d = crossing_pair(1.0)
    kept = pet.physics_filter(pet.candidates("x", d), d)
    assert len(kept) == 1 and 35 <= kept[0]["angle_deg"] <= 145


def test_rider_is_merged_with_bike():
    bike = track("bicycle", [(t / 10, 100 + 10 * t, 300, 30, 30) for t in range(30)])
    rider = track("person", [(t / 10, 100 + 10 * t, 290, 26, 50) for t in range(30)])
    assert pet.riders({"1": bike, "2": rider}) == {"2"}


def test_events_cluster_same_moment_same_place():
    base = {"source": "x", "t_b_enter": 5.0, "cell_xy": (100.0, 100.0), "vulnerable": False}
    c1 = {**base, "id": "a", "pet_s": 0.5}
    c2 = {**base, "id": "b", "pet_s": 0.2, "t_b_enter": 5.5, "vulnerable": True}
    c3 = {**base, "id": "c", "pet_s": 0.3, "t_b_enter": 12.0}
    ev = pet.events([c1, c2, c3], cell=24)
    assert len(ev) == 2
    first = next(e for e in ev if e["id"] == "b")  # lowest PET is the representative
    assert set(first["pairs"]) == {"a", "b"} and first["vulnerable"] is True


def test_parse_verdict_takes_last_json_and_validates():
    text = 'thinking {"verdict": "near_miss", "severity": "3", "confidence": "0.7"} then ' \
           '{"verdict": "not_near_miss", "severity": 1, "confidence": 0.9, "explanation": "x"}'
    v = verify.parse_verdict(text)
    assert v["verdict"] == "not_near_miss" and v["severity"] == 1
    with pytest.raises(ValueError):
        verify.parse_verdict('{"verdict": "maybe"}')
    with pytest.raises(ValueError):
        verify.parse_verdict("no json here")


def test_v3_parse_coerces_booleans():
    d = verify_v3.parse('{"a_on_road": "true", "b_on_road": true, "same_depth": false, "paths_cross": "False", "close": true, "evasive": false}')
    assert d["a_on_road"] is True and d["paths_cross"] is False


def test_strict_rule_requires_every_fact():
    f = {k: True for k in verify_v3.KEYS}
    assert score_v3.RULES["strict"](f, {}, {"pet_s": 1})
    f["same_depth"] = False
    assert not score_v3.RULES["strict"](f, {}, {"pet_s": 1})


def test_metrics_excludes_unsure_and_counts():
    labels = {"a": {"label": "near_miss"}, "b": {"label": "not_near_miss"}, "c": {"label": "unsure"}, "d": {"label": "near_miss"}}
    m = score_v3.metrics({"a": True, "b": True, "c": True, "d": False}, labels, list(labels))
    assert (m["tp"], m["fp"], m["fn"], m["n"]) == (1, 1, 1, 3)
    assert m["precision"] == 0.5 and m["recall"] == 0.5


def test_metrics_no_flags_gives_none_precision():
    labels = {"a": {"label": "near_miss"}}
    m = score_v3.metrics({"a": False}, labels, ["a"])
    assert m["precision"] is None and m["recall"] == 0.0


def test_redaction_pixelates_head_and_plate_regions():
    rng = np.random.default_rng(0)
    img = rng.integers(0, 255, (200, 200, 3), dtype=np.uint8)
    before = img.copy()
    clips.redact(img, [("person", [10, 10, 50, 110]), ("car", [100, 100, 180, 160])])
    head = img[10:40, 10:50]
    plate = img[140:160, 100:180]
    assert not np.array_equal(head, before[10:40, 10:50])
    assert not np.array_equal(plate, before[140:160, 100:180])
    # outside any box is untouched
    assert np.array_equal(img[0:5, 150:200], before[0:5, 150:200])
    # pixelation leaves far fewer distinct colours than noise
    assert len(np.unique(head.reshape(-1, 3), axis=0)) < len(np.unique(before[10:40, 10:50].reshape(-1, 3), axis=0)) / 4
