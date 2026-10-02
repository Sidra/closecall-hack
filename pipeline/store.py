"""Ledger + clip storage behind one adapter.

  CLOSECALL_STORE=local (default)  -> LocalStandIn: files under web/public, vectors in JSON.
                                      The UI labels this "Local stand-in, VAST not connected".
  CLOSECALL_STORE=vast             -> VastStore: clips + ledger rows go to the VAST S3 endpoint
                                      (VAST_S3_ENDPOINT / VAST_ACCESS_KEY / VAST_SECRET_KEY /
                                      VAST_BUCKET), and, when VSS_URL is set, each clip is also
                                      ingested into a VSS blueprint deployment with the
                                      near-miss prompt (POST /files, then POST /summarize).

Switching is a config change; nothing else in the pipeline knows which store is live.
If VAST is configured but unreachable, `get_store()` falls back to the stand-in and records why.
"""
from __future__ import annotations

import json
import math
import os
import urllib.request
from pathlib import Path
from typing import Protocol

from . import config as C

NEAR_MISS_INGEST_PROMPT = (
    "You are watching a fixed traffic camera at an intersection. List every moment where two road "
    "users (cars, buses, trucks, cyclists, pedestrians) come close to colliding: a turning vehicle "
    "cutting across a pedestrian or cyclist, a vehicle entering a space another just left, hard "
    "braking or swerving. Give the timestamp, the road users, and what happened. Do not describe "
    "or identify any person or licence plate."
)


class Store(Protocol):
    name: str
    is_standin: bool
    detail: str

    def put_clip(self, local: Path) -> str: ...
    def write_ledger(self, rows: list[dict], vectors: dict[str, list[float]]) -> None: ...


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class LocalStandIn:
    name = "Local stand-in"
    is_standin = True

    def __init__(self, reason: str = "VAST credentials not configured") -> None:
        self.detail = reason

    def put_clip(self, local: Path) -> str:
        return f"clips/{local.name}"

    def write_ledger(self, rows: list[dict], vectors: dict[str, list[float]]) -> None:
        C.OUT.mkdir(parents=True, exist_ok=True)
        (C.OUT / "ledger.json").write_text(json.dumps(rows, indent=1))
        (C.OUT / "vectors.json").write_text(json.dumps(vectors))


class VastStore:
    name = "VAST Data"
    is_standin = False

    def __init__(self) -> None:
        import boto3  # only needed when VAST is live

        self.bucket = os.environ["VAST_BUCKET"]
        self.s3 = boto3.client("s3", endpoint_url=os.environ["VAST_S3_ENDPOINT"],
                               aws_access_key_id=os.environ["VAST_ACCESS_KEY"],
                               aws_secret_access_key=os.environ["VAST_SECRET_KEY"])
        self.s3.head_bucket(Bucket=self.bucket)  # fail fast -> fallback
        self.vss = os.getenv("VSS_URL", "").rstrip("/")
        self.detail = f"s3://{self.bucket} on {os.environ['VAST_S3_ENDPOINT']}" + (f"; VSS {self.vss}" if self.vss else "")
        self.local = LocalStandIn()

    def put_clip(self, local: Path) -> str:
        key = f"closecall/clips/{local.name}"
        self.s3.upload_file(str(local), self.bucket, key, ExtraArgs={"ContentType": "video/mp4"})
        if self.vss:
            self._vss_ingest(local)
        return self.local.put_clip(local)  # UI still serves its cached copy

    def _vss_ingest(self, local: Path) -> None:
        import requests

        with open(local, "rb") as fh:
            r = requests.post(f"{self.vss}/files", files={"file": (local.name, fh, "video/mp4")},
                              data={"purpose": "vision", "media_type": "video"}, timeout=120)
        r.raise_for_status()
        fid = r.json()["id"]
        requests.post(f"{self.vss}/summarize", json={"id": fid, "prompt": NEAR_MISS_INGEST_PROMPT,
                                                     "chunk_duration": 10, "enable_chat": True}, timeout=600)

    def write_ledger(self, rows: list[dict], vectors: dict[str, list[float]]) -> None:
        body = "\n".join(json.dumps(r) for r in rows).encode()
        self.s3.put_object(Bucket=self.bucket, Key="closecall/ledger/rows.jsonl", Body=body)
        self.s3.put_object(Bucket=self.bucket, Key="closecall/ledger/vectors.json", Body=json.dumps(vectors).encode())
        self.local.write_ledger(rows, vectors)


def get_store() -> Store:
    if os.getenv("CLOSECALL_STORE", "local") == "vast":
        try:
            return VastStore()
        except Exception as e:  # noqa: BLE001
            return LocalStandIn(f"VAST configured but unreachable: {str(e)[:120]}")
    return LocalStandIn()


def embed(texts: list[str], input_type: str = "passage") -> list[list[float]]:
    body = {"model": C.EMBED_MODEL, "input": texts, "input_type": input_type}
    req = urllib.request.Request(f"{C.NVIDIA_BASE}/embeddings", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {C.NVIDIA_API_KEY}", "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    return [x["embedding"] for x in sorted(d["data"], key=lambda x: x["index"])]
