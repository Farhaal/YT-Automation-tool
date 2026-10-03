"""Per-provider request quotas, rate-limit cooldowns and a failure breaker.

Shared by all providers of one AssetManager. Quota usage and cooldowns are persisted
in quota.json so a provider that is rate-limited stays paused across jobs; the
failure breaker is in-memory and only lasts for the current job.

Callers never sleep waiting for a provider: if it is unavailable they move on to
the next source immediately.
"""
import json
import os
import threading
import time
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from backend.app.core.logger import logger

# (max requests, window seconds). Kept a little under each provider's published limit.
DEFAULT_LIMITS: Dict[str, Tuple[int, float]] = {
    "Pexels": (180, 3600.0),
    "Pixabay": (90, 60.0),
    "Openverse": (18, 60.0),
    "Wikimedia": (60, 60.0),
}

BASE_COOLDOWN = 60.0
MAX_COOLDOWN = 900.0
BREAKER_THRESHOLD = 5


def parse_retry_after(headers, now: float) -> Optional[float]:
    """Seconds to wait from Retry-After / X-Ratelimit-Reset, or None if absent."""
    if not headers:
        return None
    for name in ("Retry-After", "retry-after", "X-Ratelimit-Reset", "X-RateLimit-Reset", "x-ratelimit-reset"):
        raw = headers.get(name) if hasattr(headers, "get") else None
        if raw is None or not isinstance(raw, (str, int, float)):
            continue
        raw = str(raw).strip()
        try:
            value = float(raw)
        except ValueError:
            try:
                return max(0.0, parsedate_to_datetime(raw).timestamp() - now)
            except (TypeError, ValueError):
                continue
        # Large values are absolute epoch timestamps (Pexels), small ones are seconds.
        if value > 1_000_000_000:
            return max(0.0, value - now)
        return max(0.0, value)
    return None


def _fmt_wait(seconds: float) -> str:
    if seconds < 90:
        return f"{int(round(seconds))}s"
    return f"{int(round(seconds / 60))} min"


class ProviderHealth:
    def __init__(
        self,
        state_path: Path,
        limits: Optional[Dict[str, Tuple[int, float]]] = None,
        clock: Callable[[], float] = time.time,
    ):
        self.state_path = Path(state_path)
        self.limits = dict(DEFAULT_LIMITS if limits is None else limits)
        self.clock = clock
        self._lock = threading.Lock()
        self._state: Dict[str, dict] = self._load()
        self._failures: Dict[str, int] = {}
        self._disabled: Dict[str, str] = {}
        self._quota_flagged: Dict[str, bool] = {}

    # ---------- persistence ----------
    def _load(self) -> Dict[str, dict]:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._state, f)
            os.replace(tmp, self.state_path)
        except OSError:
            pass

    def _entry(self, provider: str) -> dict:
        return self._state.setdefault(
            provider, {"window_start": 0.0, "count": 0, "cooldown_until": 0.0, "cooldown_level": 0}
        )

    # ---------- queries ----------
    def is_disabled(self, provider: str) -> bool:
        return provider in self._disabled

    def cooldown_remaining(self, provider: str) -> float:
        with self._lock:
            return max(0.0, self._entry(provider)["cooldown_until"] - self.clock())

    def acquire(self, provider: str) -> bool:
        """Reserve one request. False means: skip this provider for now."""
        with self._lock:
            if provider in self._disabled:
                return False
            now = self.clock()
            entry = self._entry(provider)
            if entry["cooldown_until"] > now:
                return False

            limit = self.limits.get(provider)
            if limit:
                max_requests, window = limit
                if now - entry["window_start"] >= window:
                    entry["window_start"] = now
                    entry["count"] = 0
                    self._quota_flagged[provider] = False
                if entry["count"] >= max_requests:
                    if not self._quota_flagged.get(provider):
                        self._quota_flagged[provider] = True
                        wait = entry["window_start"] + window - now
                        logger.warning(
                            f"{provider} request quota used up - using other sources for {_fmt_wait(wait)}"
                        )
                    return False
                entry["count"] += 1
                self._save()
            return True

    # ---------- outcomes ----------
    def record_success(self, provider: str) -> None:
        with self._lock:
            self._failures[provider] = 0
            entry = self._entry(provider)
            if entry["cooldown_level"]:
                entry["cooldown_level"] = 0
                self._save()
                logger.info(f"{provider} is responding again")

    def record_rate_limited(self, provider: str, retry_after: Optional[float] = None) -> float:
        with self._lock:
            now = self.clock()
            entry = self._entry(provider)
            if entry["cooldown_until"] > now:
                # Another in-flight request already triggered this cooldown.
                return entry["cooldown_until"] - now
            doubled = BASE_COOLDOWN * (2 ** entry["cooldown_level"])
            wait = min(MAX_COOLDOWN, max(retry_after or 0.0, doubled))
            entry["cooldown_until"] = now + wait
            entry["cooldown_level"] += 1
            self._save()
            logger.warning(f"{provider} rate-limited - pausing {_fmt_wait(wait)}, using other sources")
            return wait

    def record_failure(self, provider: str, reason: str = "error") -> None:
        """A server error or timeout that survived one retry."""
        with self._lock:
            count = self._failures.get(provider, 0) + 1
            self._failures[provider] = count
            if count >= BREAKER_THRESHOLD:
                if provider not in self._disabled:
                    self._disabled[provider] = reason
                    logger.warning(f"{provider} failed {count} times in a row - skipping it for the rest of this job")
                return
            entry = self._entry(provider)
            now = self.clock()
            if entry["cooldown_until"] <= now:
                entry["cooldown_until"] = now + BASE_COOLDOWN
                self._save()
                logger.warning(f"{provider} unavailable ({reason}) - pausing {_fmt_wait(BASE_COOLDOWN)}")

    def disable(self, provider: str, reason: str) -> None:
        with self._lock:
            if provider not in self._disabled:
                self._disabled[provider] = reason
                logger.warning(f"{provider} disabled for this job: {reason}")
