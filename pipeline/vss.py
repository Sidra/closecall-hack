"""Client for the team's NVIDIA VSS instance on VAST (API documented in the event's VSS skills).

Auth: POST /api/v1/auth/login {username, password} -> JWT (Bearer header; `?token=` for streams).
Config (env / .env.local, never printed or committed): VSS_INGRESS_URL, VSS_USERNAME, VSS_PASSWORD.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import config as C  # noqa: F401  (loads .env.local)


class VssError(RuntimeError):
    pass


class VssClient:
    def __init__(self, base: str | None = None, username: str | None = None, password: str | None = None) -> None:
        self.base = (base or os.getenv("VSS_INGRESS_URL", "")).rstrip("/")
        self.username = username or os.getenv("VSS_USERNAME", "")
        self._password = password or os.getenv("VSS_PASSWORD", "")
        if not (self.base and self.username and self._password):
            raise VssError("VSS not configured (VSS_INGRESS_URL / VSS_USERNAME / VSS_PASSWORD)")
        self.token: str | None = None

    # -- transport ---------------------------------------------------------------------------
    def _req(self, method: str, path: str, body: dict | None = None, params: dict | None = None,
             auth: bool = True, timeout: int = 60, raw: bool = False, retry: bool = True):
        url = f"{self.base}/api/v1{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"Content-Type": "application/json", "User-Agent": "closecall/0.1"}
        if auth:
            if not self.token:
                self.login()
            headers["Authorization"] = f"Bearer {self.token}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = r.read()
        except urllib.error.HTTPError as e:
            if e.code == 401 and auth and retry:
                self.token = None
                return self._req(method, path, body, params, auth, timeout, raw, retry=False)
            raise VssError(f"{method} {path} -> HTTP {e.code}: {e.read()[:200]!r}") from None
        return payload if raw else json.loads(payload)

    def login(self) -> None:
        d = self._req("POST", "/auth/login", {"username": self.username, "password": self._password}, auth=False)
        self.token = d["access_token"]

    # -- read --------------------------------------------------------------------------------
    def ingest_config(self) -> dict:
        return self._req("GET", "/metadata/ingest-config", auth=False)

    def schema(self) -> dict:
        return self._req("GET", "/metadata/schema")

    def explore(self, limit: int = 100) -> list[dict]:
        out, offset = [], 0
        while True:
            d = self._req("GET", "/videos/explore", params={"scope": "all", "limit": limit, "offset": offset})
            items = d.get("items") or d.get("videos") or d.get("results") or []
            out += items
            total = d.get("total", len(out))
            if not items or len(out) >= total:
                return out
            offset += limit

    def search(self, query: str, top_k: int = 15, min_similarity: float = 0.3, **filters) -> dict:
        body = {"query": query, "top_k": top_k, "llm_top_n": 3, "min_similarity": min_similarity, "include_public": True}
        body.update(filters)
        return self._req("POST", "/search", body, timeout=120)

    def metadata(self, source: str) -> dict:
        return self._req("GET", "/videos/metadata", params={"source": source})

    def detections(self, source: str) -> dict | None:
        try:
            return self._req("GET", "/videos/detections", params={"source": source})
        except VssError:
            return None

    def download(self, source: str, dst: Path) -> Path:
        if not self.token:
            self.login()
        data = self._req("GET", "/videos/stream", params={"source": source, "token": self.token}, auth=False,
                         raw=True, timeout=180)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        return dst

    def synthesize(self, original_video: str, question: str, max_segments: int = 40) -> dict:
        return self._req("POST", "/videos/synthesize",
                         {"original_video": original_video, "question": question, "max_segments": max_segments}, timeout=180)

    # -- write (re-ingest an already-indexed, provided video with a new prompt) --------------
    def reingest(self, original_video: str, custom_prompt: str, chunk_count: int = 1) -> dict:
        if len(custom_prompt) > 800:
            raise VssError("custom_prompt over the 800-character limit")
        return self._req("POST", "/dashboard/reingest",
                         {"original_video": original_video, "chunk_count": chunk_count, "custom_prompt": custom_prompt})

    def reingest_status(self, job_id: str) -> dict:
        return self._req("GET", f"/dashboard/reingest/{job_id}")

    def wait_reingest(self, job_id: str, timeout_s: int = 900) -> dict:
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            s = self.reingest_status(job_id)
            if s.get("status") in ("completed", "failed", "error"):
                return s
            time.sleep(4)
        raise VssError("re-ingest timed out")
