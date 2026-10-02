"""W&B Weave tracing. If Weave can't initialise (no key, offline), the pipeline still runs:
`op` falls back to a no-op decorator and the run records that tracing was off."""
from __future__ import annotations

import os

from . import config as C

STATE = {"weave": False, "url": None, "error": None}


def init() -> None:
    if STATE["weave"]:
        return
    os.environ.setdefault("WANDB_API_KEY", C.WANDB_API_KEY)
    try:
        import weave

        client = weave.init(C.WEAVE_PROJECT)
        STATE["weave"] = True
        ent = getattr(client, "entity", None)
        proj = getattr(client, "project", C.WEAVE_PROJECT)
        STATE["url"] = f"https://wandb.ai/{ent}/{proj}/weave" if ent else None
    except Exception as e:  # noqa: BLE001
        STATE["error"] = str(e)[:200]


def op(fn):
    try:
        import weave

        return weave.op(fn)
    except Exception:  # noqa: BLE001
        return fn
