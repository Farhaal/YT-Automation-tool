"""On-disk cache of provider search responses.

Keyed by provider + endpoint + request params (credentials excluded), so the same
query, orientation and media type is never requested twice. Entries live in memory
for the job and as small JSON files for later runs.
"""
import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

DEFAULT_TTL = 7 * 24 * 3600.0
# Pixabay image URLs are temporary (about 24h), so its responses must expire sooner.
PROVIDER_TTL = {"Pixabay": 20 * 3600.0}

_SECRET_KEYS = {"key", "api_key", "apikey", "client_id", "access_key", "access_token", "token"}


def normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").strip().lower())


class SearchCache:
    def __init__(self, cache_dir: Path, clock: Callable[[], float] = time.time):
        self.cache_dir = Path(cache_dir)
        self.clock = clock
        self._memory: Dict[str, tuple] = {}
        self._lock = threading.Lock()

    @staticmethod
    def make_key(provider: str, url: str, params: Optional[dict]) -> str:
        clean = {k: v for k, v in (params or {}).items() if k.lower() not in _SECRET_KEYS}
        raw = json.dumps([provider, url, clean], sort_keys=True, default=str)
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def _ttl(self, provider: str) -> float:
        return PROVIDER_TTL.get(provider, DEFAULT_TTL)

    def get(self, provider: str, key: str) -> Optional[Any]:
        now = self.clock()
        ttl = self._ttl(provider)
        with self._lock:
            hit = self._memory.get(key)
            if hit and now - hit[0] < ttl:
                return hit[1]
        path = self.cache_dir / f"{key}.json"
        try:
            with open(path, "r", encoding="utf-8") as f:
                entry = json.load(f)
        except (OSError, ValueError):
            return None
        ts = entry.get("ts", 0.0)
        if now - ts >= ttl:
            return None
        with self._lock:
            self._memory[key] = (ts, entry.get("data"))
        return entry.get("data")

    def set(self, provider: str, key: str, data: Any) -> None:
        now = self.clock()
        with self._lock:
            self._memory[key] = (now, data)
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            path = self.cache_dir / f"{key}.json"
            tmp = path.with_suffix(f".{threading.get_ident()}.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"ts": now, "provider": provider, "data": data}, f)
            os.replace(tmp, path)
        except OSError:
            pass
