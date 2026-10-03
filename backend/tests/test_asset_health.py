"""Provider quotas, 429 failover, search cache, 1080p picking, lazy swap."""
import json
import logging
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.base import AssetProvider, pick_video_file
from backend.app.services.assets.health import MAX_COOLDOWN, ProviderHealth, parse_retry_after
from backend.app.services.assets.search_cache import SearchCache


class FakeClock:
    def __init__(self, t: float = 1_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


class DummyProvider(AssetProvider):
    """Minimal provider that exercises the shared _get_json path."""

    def __init__(self, name: str = "Dummy"):
        super().__init__(name)
        self._sleep = lambda s: None

    def search(self, query: str, orientation: str = "landscape") -> List[AssetMetadata]:
        data = self._get_json("https://api.example.test/search", params={"q": query, "key": "SECRET"})
        return [
            AssetMetadata(provider=self.name, provider_asset_id=str(i), asset_key=f"{self.name}:{i}",
                          media_url=f"https://cdn.example.test/{i}.jpg", media_type="image")
            for i in (data or {}).get("ids", [])
        ]


def _resp(status: int, body=None, headers=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = body if body is not None else {}
    r.headers = headers or {}
    return r


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def wired(tmp_path, clock):
    """A provider wired to a fresh health tracker and cache under tmp_path."""
    health = ProviderHealth(tmp_path / "quota.json", limits={"Dummy": (100, 60.0)}, clock=clock)
    cache = SearchCache(tmp_path / "search", clock=clock)
    p = DummyProvider()
    p.health, p.search_cache = health, cache
    return p, health, cache


# ---------------- resolution picker ----------------

def test_picker_prefers_1080p_landscape():
    files = [
        {"link": "4k", "width": 3840, "height": 2160},
        {"link": "1080", "width": 1920, "height": 1080},
        {"link": "720", "width": 1280, "height": 720},
    ]
    assert pick_video_file(files)["link"] == "1080"


def test_picker_prefers_1080p_portrait_and_skips_hls():
    files = [
        {"link": "hls", "width": None, "height": None, "file_type": "application/x-mpegURL"},
        {"link": "4k", "width": 2160, "height": 3840, "file_type": "video/mp4"},
        {"link": "1080", "width": 1080, "height": 1920, "file_type": "video/mp4"},
    ]
    assert pick_video_file(files)["link"] == "1080"


def test_picker_falls_back_to_smallest_when_all_too_large():
    files = [{"url": "8k", "width": 7680, "height": 4320}, {"url": "4k", "width": 3840, "height": 2160}]
    assert pick_video_file(files, url_key="url")["url"] == "4k"


def test_picker_ignores_empty_pixabay_renditions():
    files = [{"url": "", "width": 0, "height": 0}, {"url": "m", "width": 1280, "height": 720}, None]
    assert pick_video_file(files, url_key="url")["url"] == "m"


def test_providers_request_15_results():
    from backend.app.services.assets.pexels import PexelsProvider
    from backend.app.services.assets.pixabay import PixabayProvider

    with patch("httpx.get", return_value=_resp(200, {})) as mock_get:
        with patch("backend.app.services.assets.pexels.settings.PEXELS_API_KEY", "k"), \
             patch("backend.app.services.assets.pixabay.settings.PIXABAY_API_KEY", "k"):
            PexelsProvider().search("ocean")
            PixabayProvider().search("ocean")
    sent = [c.kwargs["params"]["per_page"] for c in mock_get.call_args_list]
    assert sent and all(v == 15 for v in sent)


# ---------------- 429 failover ----------------

def test_rate_limited_provider_is_skipped_during_cooldown(wired, clock):
    p, health, _ = wired
    with patch("httpx.get", return_value=_resp(429)) as mock_get:
        assert p.search("water") == []
        assert mock_get.call_count == 1
        # Still cooling down: no further network calls, even for a new query.
        assert p.search("fire") == []
        assert mock_get.call_count == 1
    clock.t += 61
    with patch("httpx.get", return_value=_resp(200, {"ids": [1]})) as mock_get:
        assert len(p.search("fire")) == 1


def test_retry_after_is_honoured_and_cooldown_doubles(tmp_path, clock):
    health = ProviderHealth(tmp_path / "q.json", limits={}, clock=clock)
    assert health.record_rate_limited("P", retry_after=120) == 120
    clock.t += 121
    assert health.record_rate_limited("P") == 120   # 60 * 2^1
    clock.t += 121
    assert health.record_rate_limited("P") == 240   # 60 * 2^2
    for _ in range(10):
        clock.t += MAX_COOLDOWN + 1
        wait = health.record_rate_limited("P")
    assert wait == MAX_COOLDOWN


def test_success_resets_cooldown_level(tmp_path, clock):
    health = ProviderHealth(tmp_path / "q.json", limits={}, clock=clock)
    health.record_rate_limited("P")
    clock.t += 61
    health.record_success("P")
    clock.t += 1
    assert health.record_rate_limited("P") == 60


def test_parse_retry_after_formats():
    now = 1_700_000_000.0
    assert parse_retry_after({"Retry-After": "30"}, now) == 30
    assert parse_retry_after({"X-Ratelimit-Reset": str(int(now + 90))}, now) == pytest.approx(90)
    assert parse_retry_after({}, now) is None
    assert parse_retry_after(MagicMock(), now) is None


def test_failover_uses_next_provider(tmp_path):
    """With Pexels rate-limited, the manager still fills the scene from Pixabay."""
    from backend.app.services.assets.manager import AssetManager

    def fake_get(url, **kwargs):
        if "pexels" in url:
            return _resp(429, headers={"Retry-After": "120"})
        if "pixabay.com/api/videos" in url:
            return _resp(200, {"hits": [{"id": 7, "user": "u", "tags": "water",
                                         "videos": {"medium": {"url": "https://cdn.test/7.mp4", "width": 1920, "height": 1080}}}]})  # noqa: E501
        return _resp(200, {"hits": []})

    stream_ctx = MagicMock()
    stream_ctx.__enter__.return_value.iter_bytes.return_value = [b"x"]
    with patch("httpx.get", side_effect=fake_get), patch("httpx.stream", return_value=stream_ctx), \
         patch("backend.app.services.assets.pexels.settings.PEXELS_API_KEY", "k"), \
         patch("backend.app.services.assets.pixabay.settings.PIXABAY_API_KEY", "k"):
        manager = AssetManager(cache_dir=tmp_path / "assets", state_dir=tmp_path / "state")
        scenes = manager.select_assets_for_scenes([{"start": 0, "end": 2, "text": "water", "queries": ["water"]}])
    assert scenes[0]["asset"]["provider"] == "Pixabay"
    assert manager.health.cooldown_remaining("Pexels") > 0


# ---------------- errors and breaker ----------------

def test_server_error_retries_once_then_cools_down(wired):
    p, health, _ = wired
    with patch("httpx.get", return_value=_resp(503)) as mock_get:
        assert p.search("a") == []
        assert mock_get.call_count == 2          # one retry
        assert health.cooldown_remaining("Dummy") > 0
        p.search("b")
        assert mock_get.call_count == 2          # skipped while cooling down


def test_breaker_opens_after_five_failures(tmp_path, clock):
    health = ProviderHealth(tmp_path / "q.json", limits={}, clock=clock)
    for _ in range(5):
        clock.t += 61
        health.record_failure("P", "HTTP 500")
    assert health.is_disabled("P")
    clock.t += 10_000
    assert health.acquire("P") is False


def test_rejected_key_disables_provider(wired):
    p, health, _ = wired
    with patch("httpx.get", return_value=_resp(401)) as mock_get:
        p.search("a")
        p.search("b")
        assert mock_get.call_count == 1
    assert health.is_disabled("Dummy")


def test_one_log_line_per_state_change(wired, caplog, clock):
    p, _, _ = wired
    with caplog.at_level(logging.WARNING, logger="openreel"):
        with patch("httpx.get", return_value=_resp(429)):
            for q in ("a", "b", "c", "d", "e"):
                p.search(q)
    lines = [r for r in caplog.records if "rate-limited" in r.getMessage()]
    assert len(lines) == 1


def test_quota_exhaustion_skips_without_calling(tmp_path, clock, caplog):
    health = ProviderHealth(tmp_path / "q.json", limits={"Dummy": (2, 60.0)}, clock=clock)
    p = DummyProvider()
    p.health = health
    with caplog.at_level(logging.WARNING, logger="openreel"):
        with patch("httpx.get", return_value=_resp(200, {"ids": []})) as mock_get:
            for q in ("a", "b", "c", "d"):
                p.search(q)
            assert mock_get.call_count == 2
            clock.t += 61
            p.search("e")
            assert mock_get.call_count == 3
    assert sum("quota used up" in r.getMessage() for r in caplog.records) == 1


def test_quota_state_persists_across_instances(tmp_path, clock):
    path = tmp_path / "quota.json"
    h1 = ProviderHealth(path, limits={"Pexels": (3, 3600.0)}, clock=clock)
    for _ in range(3):
        assert h1.acquire("Pexels")
    h1.record_rate_limited("Pixabay", retry_after=300)
    h2 = ProviderHealth(path, limits={"Pexels": (3, 3600.0)}, clock=clock)
    assert h2.acquire("Pexels") is False
    assert h2.cooldown_remaining("Pixabay") == pytest.approx(300)
    assert "SECRET" not in path.read_text()


# ---------------- search cache ----------------

def test_same_query_hits_provider_once(wired):
    p, _, _ = wired
    with patch("httpx.get", return_value=_resp(200, {"ids": [1, 2]})) as mock_get:
        assert len(p.search("Ocean  Waves")) == 2
        assert len(p.search("Ocean  Waves")) == 2
        assert mock_get.call_count == 1


def test_cache_survives_restart_and_expires(tmp_path, clock):
    cache = SearchCache(tmp_path / "search", clock=clock)
    key = SearchCache.make_key("Pexels", "https://u", {"query": "a", "key": "SECRET"})
    cache.set("Pexels", key, {"ids": [1]})
    fresh = SearchCache(tmp_path / "search", clock=clock)
    assert fresh.get("Pexels", key) == {"ids": [1]}
    clock.t += 7 * 24 * 3600 + 1
    assert SearchCache(tmp_path / "search", clock=clock).get("Pexels", key) is None
    # Credentials never reach the cache key or files.
    assert key == SearchCache.make_key("Pexels", "https://u", {"query": "a", "key": "OTHER"})
    assert all("SECRET" not in f.read_text() for f in (tmp_path / "search").glob("*.json"))


def test_pixabay_cache_expires_within_a_day(tmp_path, clock):
    cache = SearchCache(tmp_path / "search", clock=clock)
    cache.set("Pixabay", "k1", {"hits": []})
    clock.t += 21 * 3600
    assert SearchCache(tmp_path / "search", clock=clock).get("Pixabay", "k1") is None


def test_failed_requests_are_not_cached(wired):
    p, _, cache = wired
    with patch("httpx.get", return_value=_resp(429)):
        p.search("x")
    assert not list(cache.cache_dir.glob("*.json"))


# ---------------- lazy swap ----------------

def test_swap_downloads_backup_on_demand(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from backend.app.main import app
    from backend.app.services.job_manager import job_manager

    def asset(key, path=None, url=None):
        return {"type": "video", "path": path, "source": "Pexels", "author": "a", "license": "Pexels License",
                "url": "https://pexels.test/page", "media_url": url, "asset_key": key, "provider_asset_id": key}

    current_file = tmp_path / "current.mp4"
    current_file.write_bytes(b"x")
    timeline = {"scenes": [{
        "id": "s1", "start": 0, "end": 2, "text": "hi",
        "asset": asset("Pexels:1", str(current_file)),
        "backup_asset": asset("Pexels:2", None, "https://cdn.test/broken.mp4"),
        "alternatives": [asset("Pexels:2", None, "https://cdn.test/broken.mp4"),
                         asset("Pexels:3", None, "https://cdn.test/3.mp4")],
    }]}
    tl_path = tmp_path / "timeline.json"
    tl_path.write_text(json.dumps(timeline))

    monkeypatch.setattr(job_manager, "get_job", lambda job_id: {"timeline_path": str(tl_path)})
    monkeypatch.setattr("backend.app.api.routes.DATA", tmp_path)
    downloads = []

    def fake_download(meta, cache_dir, label=None):
        downloads.append(meta.media_url)
        if "broken" in meta.media_url:
            return None
        out = cache_dir / "3.mp4"
        cache_dir.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"y")
        return str(out)

    monkeypatch.setattr("backend.app.services.assets.base.download_media", fake_download)

    res = TestClient(app).post("/jobs/j1/scenes/s1/swap")
    assert res.status_code == 200
    scene = res.json()["scene"]
    # The broken backup was tried first, then the next alternative was fetched and used.
    assert downloads == ["https://cdn.test/broken.mp4", "https://cdn.test/3.mp4"]
    assert scene["asset"]["asset_key"] == "Pexels:3" and scene["asset"]["path"]
    # The replaced clip becomes the backup, so swapping again undoes it.
    assert scene["backup_asset"]["asset_key"] == "Pexels:1"
    saved = json.loads(tl_path.read_text())
    assert saved["scenes"][0]["asset"]["asset_key"] == "Pexels:3"


def test_swap_without_alternatives_returns_400(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from backend.app.main import app
    from backend.app.services.job_manager import job_manager

    tl_path = tmp_path / "timeline.json"
    tl_path.write_text(json.dumps({"scenes": [{"id": "s1", "start": 0, "end": 1, "text": "x", "asset": None}]}))
    monkeypatch.setattr(job_manager, "get_job", lambda job_id: {"timeline_path": str(tl_path)})
    assert TestClient(app).post("/jobs/j1/scenes/s1/swap").status_code == 400
