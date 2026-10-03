import hashlib
import random
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable, List, Optional

import httpx

from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.health import ProviderHealth, parse_retry_after
from backend.app.services.assets.search_cache import SearchCache

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"  # noqa: E501

# Exports are 1080p, so a 4K download only costs time and disk.
TARGET_LONG_SIDE = 1920
MAX_LONG_SIDE = 2560
RESULTS_PER_PAGE = 15


def pick_video_file(files: Iterable[Optional[dict]], url_key: str = "link") -> Optional[dict]:
    """Choose the rendition closest to 1080p (either orientation), never above 2560px."""
    candidates = [f for f in files if f and f.get(url_key)]
    sized = [
        f for f in candidates
        if (f.get("width") or 0) > 0 and (f.get("height") or 0) > 0
        and ("mp4" in f["file_type"] if f.get("file_type") else True)
    ]
    if not sized:
        return candidates[0] if candidates else None

    def long_side(f: dict) -> int:
        return max(f["width"], f["height"])

    within = [f for f in sized if long_side(f) <= MAX_LONG_SIDE]
    if not within:
        return min(sized, key=long_side)
    # Closest to the target; on a tie prefer the larger file.
    return min(within, key=lambda f: (abs(long_side(f) - TARGET_LONG_SIDE), -long_side(f)))


def download_media(asset: AssetMetadata, cache_dir: Path, label: Optional[str] = None) -> Optional[str]:
    """Download an asset into the shared cache (or reuse a cached copy). Returns the local path."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    hash_str = hashlib.md5(asset.asset_key.encode()).hexdigest()
    asset.cache_key = hash_str
    ext = "mp4" if asset.media_type == "video" else "jpg"
    local_path = cache_dir / f"{hash_str}.{ext}"

    if local_path.exists() and local_path.stat().st_size > 0:
        asset.local_path = str(local_path)
        return asset.local_path

    try:
        with httpx.stream("GET", asset.media_url, headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=15.0) as response:  # noqa: E501
            response.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
        asset.local_path = str(local_path)
        return asset.local_path
    except Exception as e:
        logger.error(f"Download failed for {label or asset.provider} asset {asset.asset_key}: {type(e).__name__}")
        if local_path.exists():
            local_path.unlink(missing_ok=True)
        return None


class AssetProvider(ABC):
    # Injected by AssetManager; providers also work standalone without them.
    health: Optional[ProviderHealth] = None
    search_cache: Optional[SearchCache] = None
    _sleep = staticmethod(time.sleep)

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def search(self, query: str, orientation: str = "landscape") -> List[AssetMetadata]:
        pass

    def download(self, asset: AssetMetadata, cache_dir: Path) -> Optional[str]:
        return download_media(asset, cache_dir, label=self.name)

    def _get_json(self, url: str, params: Optional[dict] = None, headers: Optional[dict] = None,
                  timeout: float = 5.0, **kwargs) -> Optional[Any]:
        """GET a JSON search endpoint with caching, quotas and failover.

        Returns the parsed body, or None when the provider should be skipped for this
        query (cooldown, quota, error). Never sleeps waiting for a rate limit.
        """
        cache_key = None
        if self.search_cache is not None:
            cache_key = SearchCache.make_key(self.name, url, params)
            cached = self.search_cache.get(self.name, cache_key)
            if cached is not None:
                return cached

        for attempt in (1, 2):
            if self.health is not None and not self.health.acquire(self.name):
                return None
            try:
                resp = httpx.get(url, params=params, headers=headers, timeout=timeout, **kwargs)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                if attempt == 1:
                    self._sleep(random.uniform(0.3, 0.8))
                    continue
                self._fail(type(e).__name__)
                return None
            except Exception as e:
                self._fail(type(e).__name__)
                return None

            status = resp.status_code
            if status == 200:
                try:
                    data = resp.json()
                except ValueError:
                    self._fail("invalid response")
                    return None
                if self.health is not None:
                    self.health.record_success(self.name)
                if cache_key is not None:
                    self.search_cache.set(self.name, cache_key, data)
                return data
            if status == 429:
                if self.health is not None:
                    self.health.record_rate_limited(self.name, parse_retry_after(resp.headers, time.time()))
                return None
            if status in (401, 403):
                if self.health is not None:
                    self.health.disable(self.name, f"API key rejected (HTTP {status})")
                return None
            if status >= 500:
                if attempt == 1:
                    self._sleep(random.uniform(0.3, 0.8))
                    continue
                self._fail(f"HTTP {status}")
                return None
            return None  # other 4xx: treat as no results
        return None

    def _fail(self, reason: str) -> None:
        if self.health is not None:
            self.health.record_failure(self.name, reason)
        else:
            logger.warning(f"{self.name} search failed: {reason}")
