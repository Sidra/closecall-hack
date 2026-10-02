"""Run stages 0-1 and export one anonymised clip per event (no model calls).

Writes data/work/events.json, which stages 2-4 consume.
"""
from __future__ import annotations

import json

from . import clips, config as C, pet, track


def main() -> None:
    all_events, funnel = [], {}
    for sid, meta in C.SOURCES.items():
        doc = track.track(sid)
        naive = pet.candidates(sid, doc)
        crossing = pet.physics_filter(naive, doc)
        evs = pet.events(crossing, doc["width"] * C.CELL_FRAC)
        funnel[sid] = {"tracks": len(doc["tracks"]), "naive": len(naive), "crossing": len(crossing),
                       "events": len(evs), "duration_s": doc["duration"], "title": meta["title"]}
        for e in evs:
            e.update(clips.export(e, doc))
            all_events.append(e)
        print(sid, funnel[sid])
    (C.WORK / "events.json").write_text(json.dumps({"funnel": funnel, "events": all_events}, indent=1))


if __name__ == "__main__":
    main()
