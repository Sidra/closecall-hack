"""The pre-registered v3 triage verifier (eval/PREREGISTRATION-v3-test.md), as ledger verdicts."""
from __future__ import annotations

import json

from . import config as C
from .score_v3 import RULES, metrics
from .verify_v3 import MODELS, load

TRIO = ["qwen3.6-35b", "minimax-m3", "gemma-4-31b"]
RULE = "strict"
LABEL = "v3 · storyboard · 2-of-3 vote (Qwen3.6-35B, MiniMax-M3, Gemma-4-31B on W&B Inference)"


def verdicts() -> dict[str, dict]:
    """event id -> verdict dict in the same shape as v1/v2, for every event both splits cover."""
    evs = {e["id"]: e for e in json.loads((C.WORK / "events.json").read_text())["events"]}
    kin = json.loads((C.WORK / "kinematics.json").read_text())
    out = {}
    for split in ("dev", "test"):
        res = load(split)
        ids = json.loads((C.ROOT / "eval" / "split.json").read_text())[split]
        for i in ids:
            per = [res.get(m, {}).get(i) for m in TRIO]
            if not all(p and p.get("ok") for p in per):
                continue
            votes = [bool(RULES[RULE](p, kin[i], evs[i])) for p in per]
            flag = sum(votes) >= 2
            agree = [p for p, v in zip(per, votes) if v == flag]
            out[i] = {
                "verdict": "near_miss" if flag else "not_near_miss",
                "conflict_type": agree[0].get("conflict_type", "none") if flag else "none",
                "severity": sum(votes) + 2 if flag else 0,
                "evasive_action": "yes" if any(p.get("evasive") for p in agree) else "none",
                "explanation": agree[0].get("evidence", ""),
                "confidence": round(sum(votes) / 3, 2),
                "model": "vote: " + " + ".join(MODELS[m][1].split("/")[-1] for m in TRIO),
                "input": "storyboard", "version": "v3", "split": split,
                "votes": dict(zip(TRIO, votes)),
                "latency_s": round(max(p.get("latency_s", 0) for p in per), 1),
            }
    return out


def split_metrics(v: dict) -> dict:
    labels = json.loads((C.ROOT / "eval" / "labels.json").read_text())["labels"]
    sp = json.loads((C.ROOT / "eval" / "split.json").read_text())
    out = {}
    for name, ids in (("dev", sp["dev"]), ("test", sp["test"]), ("all", sp["dev"] + sp["test"])):
        ids = [i for i in ids if i in v]
        m = metrics({i: v[i]["verdict"] == "near_miss" for i in ids}, labels, ids)
        m["flags"] = sum(v[i]["verdict"] == "near_miss" for i in ids)
        m["candidates"] = len(ids)
        out[name] = m
    return out
