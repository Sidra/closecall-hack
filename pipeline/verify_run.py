"""Stage 2 over every event, in parallel, each call traced in Weave. Cached per event."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config as C, tracing, verify

CACHE = C.WORK / "verdicts.json"


@tracing.op
def verify_event(event_id: str, a_cls: str, b_cls: str, pet_s: float, clip: str, keyframes: list[str]) -> dict:
    ev = {"a_cls": a_cls, "b_cls": b_cls, "pet_s": pet_s}
    return verify.verify(ev, str(C.ROOT / "web" / "public" / clip),
                         [str(C.ROOT / "web" / "public" / k) for k in keyframes])


def main(workers: int = 4) -> None:
    tracing.init()
    events = json.loads((C.WORK / "events.json").read_text())["events"]
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [e for e in events if e["id"] not in cache or cache[e["id"]].get("model") == "none"]

    def one(e: dict) -> tuple[str, dict]:
        return e["id"], verify_event(e["id"], e["a_cls"], e["b_cls"], e["pet_s"], e["clip"], e["keyframes"])

    with ThreadPoolExecutor(workers) as ex:
        for fut in as_completed([ex.submit(one, e) for e in todo]):
            eid, v = fut.result()
            cache[eid] = v
            CACHE.write_text(json.dumps(cache, indent=1))
            print(eid, v["verdict"], v.get("model"), v.get("latency_s"), flush=True)
    print("weave:", tracing.STATE)


if __name__ == "__main__":
    main()
