"""Verifier v2 over every event (zoomed crop + explicit decision rule). Cached separately."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config as C, tracing, verify

CACHE = C.WORK / "verdicts_v2.json"


@tracing.op
def verify_event_v2(event_id: str, a_cls: str, b_cls: str, pet_s: float, crop: str) -> dict:
    return verify.verify_v2({"a_cls": a_cls, "b_cls": b_cls, "pet_s": pet_s}, crop)


def main(workers: int = 5) -> None:
    tracing.init()
    events = json.loads((C.WORK / "events.json").read_text())["events"]
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [e for e in events if e["id"] not in cache or cache[e["id"]].get("model") == "none"]

    def one(e: dict) -> tuple[str, dict]:
        crop = str(C.WORK / e["source"] / f"{e['id']}.crop.mp4")
        return e["id"], verify_event_v2(e["id"], e["a_cls"], e["b_cls"], e["pet_s"], crop)

    with ThreadPoolExecutor(workers) as ex:
        for fut in as_completed([ex.submit(one, e) for e in todo]):
            eid, v = fut.result()
            cache[eid] = v
            CACHE.write_text(json.dumps(cache, indent=1))
            print(eid, v["verdict"], v.get("latency_s"), flush=True)


if __name__ == "__main__":
    main()
