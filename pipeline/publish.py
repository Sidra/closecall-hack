"""Stages 3-5: ledger rows + search index -> store, fix memo (W&B Inference), eval (W&B Weave).

Reads data/work/{events,verdicts}.json and eval/labels.json.
Writes the UI's pre-cached run to web/public/data/*.json.
"""
from __future__ import annotations

import asyncio
import json
import time
from collections import Counter
from pathlib import Path

from . import config as C, memo, store, tracing

DEMO_QUERIES = [
    "turning car cutting across a pedestrian at the crosswalk",
    "left-turn conflicts with cyclists",
    "vehicles crossing paths in the middle of the intersection",
]


def row_text(r: dict) -> str:
    return (f"{r['pair']}. {r['conflict_type'].replace('_', ' ')}. {r['explanation']} "
            f"Evasive action: {r['evasive_action']}. {r['intersection']}.")


def build_rows(events: list[dict], verdicts: dict, labels: dict, v1: dict | None = None) -> list[dict]:
    """One row per event. `verdicts` is the version the ledger uses (v2); v1 is kept alongside."""
    rows = []
    v1 = v1 or {}
    for e in events:
        v = verdicts.get(e["id"])
        if not v:
            continue
        o = v1.get(e["id"], {})
        meta = C.SOURCES[e["source"]]
        rows.append({
            "id": e["id"], "source": e["source"], "intersection": meta["title"],
            "pair": f"{e['a_cls']} then {e['b_cls']}", "a_cls": e["a_cls"], "b_cls": e["b_cls"],
            "pet_s": e["pet_s"], "t": e["t_b_enter"], "angle_deg": e.get("angle_deg"),
            "vulnerable": e["vulnerable"], "pairs_in_event": len(e["pairs"]),
            "clip": e["clip"], "keyframes": e["keyframes"],
            "verdict": v["verdict"], "conflict_type": v.get("conflict_type", "none"),
            "severity": v.get("severity", 0), "evasive_action": v.get("evasive_action", "none"),
            "explanation": v.get("explanation", ""), "confidence": v.get("confidence", 0.0),
            "verifier_model": v.get("model"), "verifier_input": v.get("input"),
            "verifier_latency_s": v.get("latency_s"),
            "label": labels.get(e["id"], {}).get("label"),
            "verifier_version": v.get("version", "v1"),
            "v1_verdict": o.get("verdict"), "v1_explanation": o.get("explanation"),
        })
    return rows


def metrics(rows: list[dict]) -> dict:
    scored = [r for r in rows if r["label"] in ("near_miss", "not_near_miss")]
    tp = [r["id"] for r in scored if r["verdict"] == "near_miss" and r["label"] == "near_miss"]
    fp = [r["id"] for r in scored if r["verdict"] == "near_miss" and r["label"] == "not_near_miss"]
    fn = [r["id"] for r in scored if r["verdict"] != "near_miss" and r["label"] == "near_miss"]
    tn = [r["id"] for r in scored if r["verdict"] != "near_miss" and r["label"] == "not_near_miss"]
    pos = len(tp) + len(fn)
    return {
        "scored": len(scored), "excluded_unsure": sum(r["label"] == "unsure" for r in rows),
        "tp": tp, "fp": fp, "fn": fn, "tn_count": len(tn),
        "precision": round(len(tp) / (len(tp) + len(fp)), 3) if tp or fp else None,
        "recall": round(len(tp) / pos, 3) if pos else None,
        "baseline_precision": round(pos / len(scored), 3) if scored else None,
        "unsure_flagged": [r["id"] for r in rows if r["label"] == "unsure" and r["verdict"] == "near_miss"],
    }


def weave_eval(rows: list[dict], version: str = "v1") -> str | None:
    """Log the same scoring as a Weave Evaluation so it is browsable next to the traces."""
    if not tracing.STATE["weave"]:
        return None
    import weave

    data = [{"event_id": r["id"], "label": r["label"]} for r in rows if r["label"] in ("near_miss", "not_near_miss")]
    by_id = {r["id"]: r for r in rows}

    class CachedVerifier(weave.Model):
        """The verdicts produced (and traced) by pipeline.verify_run, replayed for scoring."""
        verifier: str = C.VERIFY_MODEL

        @weave.op
        def predict(self, event_id: str) -> dict:
            r = by_id[event_id]
            return {"verdict": r["verdict"], "model": r["verifier_model"], "explanation": r["explanation"]}

    class NearMissScorer(weave.Scorer):
        @weave.op
        def score(self, output: dict, label: str) -> dict:
            flagged = output["verdict"] == "near_miss"
            pos = label == "near_miss"
            return {"tp": flagged and pos, "fp": flagged and not pos, "fn": (not flagged) and pos}

        def summarize(self, score_rows: list) -> dict:
            tp = sum(s["tp"] for s in score_rows)
            fp = sum(s["fp"] for s in score_rows)
            fn = sum(s["fn"] for s in score_rows)
            return {"precision": tp / (tp + fp) if tp + fp else None,
                    "recall": tp / (tp + fn) if tp + fn else None, "tp": tp, "fp": fp, "fn": fn}

    ev = weave.Evaluation(name=f"closecall-near-miss-precision-{version}", dataset=data, scorers=[NearMissScorer()])
    asyncio.run(ev.evaluate(CachedVerifier()))
    return tracing.STATE["url"]


def main(skip_memo: bool = False, dry: bool = False) -> None:
    tracing.init()
    events_doc = json.loads((C.WORK / "events.json").read_text())
    v1 = json.loads((C.WORK / "verdicts.json").read_text())
    v2_path = C.WORK / "verdicts_v2.json"
    v2 = json.loads(v2_path.read_text()) if v2_path.exists() else {}
    labels = json.loads((C.ROOT / "eval" / "labels.json").read_text())["labels"]
    from . import v3_final

    v3 = v3_final.verdicts()
    n_ev = len(events_doc["events"])
    use_v2 = len(v2) >= n_ev  # PREREGISTRATION-v2: ledger uses v2 once complete...
    use_v3 = len(v3) >= n_ev  # ...superseded by PREREGISTRATION-v3-test once v3 covers all 51
    ledger_v = v3 if use_v3 else v2 if use_v2 else v1
    version = "v3" if use_v3 else "v2" if use_v2 else "v1"
    rows = build_rows(events_doc["events"], ledger_v, labels, v1)
    for r in rows:
        r["v2_verdict"] = v2.get(r["id"], {}).get("verdict")
        r["v2_explanation"] = v2.get(r["id"], {}).get("explanation")
        if use_v3:
            r["votes"] = v3[r["id"]].get("votes")
            r["split"] = v3[r["id"]].get("split")
    rows_v2 = build_rows(events_doc["events"], v2, labels) if use_v2 else []
    rows_v1 = build_rows(events_doc["events"], v1, labels)
    st = store.get_store()
    for r in rows:
        r["clip_ref"] = st.put_clip(C.ROOT / "web" / "public" / r["clip"])

    # Search index: every event the verifier flagged or the reviewer confirmed (cards show both)
    ledger = [r for r in rows if r["verdict"] == "near_miss"]
    indexed = [r for r in rows if r["verdict"] == "near_miss" or r["label"] == "near_miss"]
    confirmed = [r for r in rows if r["label"] == "near_miss"]
    for r in rows:
        r["reviewer_note"] = labels.get(r["id"], {}).get("note", "")
    vecs: dict[str, list[float]] = {}
    search_mode = "nvidia-embeddings"
    try:
        for i in range(0, len(indexed), 16):
            chunk = indexed[i:i + 16]
            for r, v in zip(chunk, store.embed([row_text(r) for r in chunk], "passage")):
                vecs[r["id"]] = v
        qvecs = store.embed(DEMO_QUERIES, "query")
        demo_search = {q: sorted(({"id": r["id"], "score": round(store.cosine(qv, vecs[r["id"]]), 4)} for r in indexed),
                                 key=lambda x: -x["score"])[:5] for q, qv in zip(DEMO_QUERIES, qvecs)}
    except Exception as e:  # noqa: BLE001
        search_mode = f"keyword fallback ({str(e)[:80]})"
        demo_search = {}
    for r in rows:
        r["search_text"] = row_text(r)
    st.write_ledger(rows, vecs)

    m = metrics(rows)
    m_v1 = metrics(rows_v1)
    weave_url = None
    try:
        weave_url = None if dry else weave_eval(rows, version)
        if not dry:
            weave_eval(rows_v1, "v1")
            if use_v2 and version != "v2":
                weave_eval(rows_v2, "v2")
    except Exception as e:  # noqa: BLE001
        m["weave_error"] = str(e)[:200]

    funnel = events_doc["funnel"]
    totals = {k: sum(f[k] for f in funnel.values()) for k in ("tracks", "naive", "crossing", "events", "duration_s")}
    totals["verified"] = len(ledger)
    totals["confirmed"] = len(confirmed)
    totals["confirmed_and_flagged"] = sum(r["verdict"] == "near_miss" for r in confirmed)
    totals["verifier_calls"] = len(rows)
    totals["fallback_verdicts"] = sum(r["verifier_input"] == "keyframe" for r in rows)  # Llama-vision fallback only

    memo_path = C.OUT / "memo.json"
    if not skip_memo:
        # The memo cites reviewer-confirmed clips only (the reviewer is the human step before filing).
        by_x = Counter(r["intersection"] for r in confirmed)
        memos = []
        for inter, _ in by_x.most_common():
            sub = [r for r in confirmed if r["intersection"] == inter]
            try:
                out = memo.draft_memo(inter, sub)
                memos.append({"intersection": inter, "clips": [r["id"] for r in sub], **out,
                              "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cached": False})
            except Exception as e:  # noqa: BLE001
                memos.append({"intersection": inter, "clips": [r["id"] for r in sub], "error": str(e)[:200]})
        memo_path.write_text(json.dumps(memos, indent=1))

    run = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "funnel": funnel, "totals": totals,
        "store": {"name": st.name, "standin": st.is_standin, "detail": st.detail},
        "verifier_version": version,
        "verifier_label": v3_final.LABEL if use_v3 else version,
        "models": {"tracker": Path(C.YOLO_WEIGHTS).name,
                   "verifier": v3_final.LABEL if use_v3 else C.VERIFY_MODEL,
                   "verifier_v1_v2": C.VERIFY_MODEL, "verifier_fallback": C.VERIFY_FALLBACK,
                   "embed": C.EMBED_MODEL, "memo": C.MEMO_MODEL},
        "thresholds": {"pet_candidate_s": C.PET_CANDIDATE_S, "cell_frac": C.CELL_FRAC, "angle_deg": [35, 145]},
        "search": {"mode": search_mode, "demo": demo_search},
        "weave": {"enabled": tracing.STATE["weave"], "url": tracing.STATE["url"], "error": tracing.STATE["error"]},
        "sources": C.SOURCES,
    }
    (C.OUT / "run.json").write_text(json.dumps(run, indent=1))
    v3m = v3_final.split_metrics(v3) if v3 else None
    headline = None
    if v3m:
        a = v3m["all"]
        headline = {"caught": a["tp"], "confirmed": a["tp"] + a["fn"], "flags": a["flags"], "candidates": a["candidates"],
                    "footage_s": round(totals["duration_s"]), "test": v3m["test"], "dev": v3m["dev"]}
    (C.OUT / "eval.json").write_text(json.dumps({**m, "version": version, "v1": m_v1,
                                                  "v2": metrics(rows_v2) if rows_v2 else None,
                                                  "v3": v3m, "headline": headline, "v3_label": v3_final.LABEL,
                                                  "v1_calls": len(rows_v1), "labeller": json.loads((C.ROOT / "eval" / "labels.json").read_text())["labeller"],
                                                  "labels": labels}, indent=1))
    print(json.dumps({"totals": totals, "eval": {k: m[k] for k in ("precision", "recall", "baseline_precision", "scored", "excluded_unsure")}}, indent=1))


if __name__ == "__main__":
    import sys

    main(skip_memo="--skip-memo" in sys.argv or "--dry" in sys.argv, dry="--dry" in sys.argv)
