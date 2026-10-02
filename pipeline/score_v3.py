"""Score v3 variants (model x rule, ensembles, kinematic-only rule) on a split.

Same scoring as eval/PREREGISTRATION.md: unsure excluded, positive = labelled near_miss.
"""
from __future__ import annotations

import json
from itertools import combinations

from . import config as C

RULES = {
    "strict": lambda f, k, e: f["a_on_road"] and f["b_on_road"] and f["same_depth"] and f["paths_cross"] and f["close"],
    "strict_or_evasive": lambda f, k, e: f["a_on_road"] and f["b_on_road"] and f["same_depth"] and (f["close"] or f["evasive"]),
    "depth_close": lambda f, k, e: f["same_depth"] and f["close"],
    "strict_pet1.5": lambda f, k, e: RULES["strict"](f, k, e) and e["pet_s"] < 1.5,
    "evasive_only": lambda f, k, e: f["evasive"] and f["same_depth"],
}


def kin_rule(k: dict, e: dict) -> bool:
    """No model: similar box heights (same depth), ground points close vertically, short PET."""
    return (k.get("depth_ratio") or 0) > 0.5 and (k.get("ground_dy_w") or 1) < 0.03 and e["pet_s"] < 1.5


def metrics(pred: dict[str, bool], labels: dict, ids: list[str]) -> dict:
    sc = [i for i in ids if labels[i]["label"] in ("near_miss", "not_near_miss")]
    tp = sum(pred.get(i, False) and labels[i]["label"] == "near_miss" for i in sc)
    fp = sum(pred.get(i, False) and labels[i]["label"] == "not_near_miss" for i in sc)
    fn = sum((not pred.get(i, False)) and labels[i]["label"] == "near_miss" for i in sc)
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f1 = 2 * p * r / (p + r) if p and r else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "n": len(sc), "precision": p, "recall": r, "f1": round(f1, 3)}


def variants(split: str) -> list[dict]:
    ids = json.loads((C.ROOT / "eval" / "split.json").read_text())[split]
    labels = json.loads((C.ROOT / "eval" / "labels.json").read_text())["labels"]
    evs = {e["id"]: e for e in json.loads((C.WORK / "events.json").read_text())["events"]}
    kin = json.loads((C.WORK / "kinematics.json").read_text())
    from .verify_v3 import load

    v3 = load(split)
    out = []
    for name, f in (("v1", "verdicts.json"), ("v2", "verdicts_v2.json")):
        vd = json.loads((C.WORK / f).read_text())
        out.append({"variant": name, **metrics({i: vd.get(i, {}).get("verdict") == "near_miss" for i in ids}, labels, ids)})
    out.append({"variant": "kinematic-only (no model)", **metrics({i: kin_rule(kin[i], evs[i]) for i in ids}, labels, ids)})
    full = {m: r for m, r in v3.items() if all(r.get(i, {}).get("ok") for i in ids)}
    risk = {m: full.pop(m) for m in list(full) if m.endswith("@risk")}
    for m, r in risk.items():
        for th in range(3, 10):
            out.append({"variant": f"{m} >= {th}", **metrics({i: r[i]["risk"] >= th for i in ids}, labels, ids)})
    preds: dict[tuple[str, str], dict[str, bool]] = {}
    for m, r in full.items():
        for rn, rule in RULES.items():
            preds[(m, rn)] = {i: bool(rule(r[i], kin[i], evs[i])) for i in ids}
            out.append({"variant": f"{m} · {rn}", **metrics(preds[(m, rn)], labels, ids)})
    v2 = json.loads((C.WORK / "verdicts_v2.json").read_text())
    v2p = {i: v2.get(i, {}).get("verdict") == "near_miss" for i in ids}
    if all(i in v2 for i in ids):
        for (m, rn), pr in list(preds.items()):
            out.append({"variant": f"v2 AND {m} · {rn}", **metrics({i: v2p[i] and pr[i] for i in ids}, labels, ids)})
    for rn in RULES:
        ms = [m for m in full]
        for k in (3,):
            for combo in combinations(ms, k):
                pr = {i: sum(preds[(m, rn)][i] for m in combo) >= 2 for i in ids}
                out.append({"variant": f"vote2of3[{'+'.join(combo)}] · {rn}", **metrics(pr, labels, ids)})
    return sorted(out, key=lambda x: (-x["f1"], -(x["precision"] or 0)))


if __name__ == "__main__":
    import sys

    for row in variants(sys.argv[1] if len(sys.argv) > 1 else "dev")[:25]:
        print(f"{row['variant'][:70]:70s} P={row['precision']} R={row['recall']} F1={row['f1']} tp/fp/fn={row['tp']}/{row['fp']}/{row['fn']}")
