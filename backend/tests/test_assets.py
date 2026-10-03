import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.assets.manager import AssetManager


@pytest.fixture
def mock_httpx():
    with patch("httpx.get") as mock_get, patch("httpx.stream") as mock_stream:
        yield mock_get, mock_stream

def test_asset_manager_comprehensive(mock_httpx):
    mock_get, mock_stream = mock_httpx
    
    def stream_side_effect(method, url, **kwargs):
        mock_ctx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        
        if "fail_download" in url:
            # Partial download: yield one chunk then crash
            def faulty_iter():
                yield b"chunk_1"
                raise Exception("Mid-download crash")
            mock_resp.iter_bytes.side_effect = faulty_iter
        else:
            mock_resp.iter_bytes.return_value = [b"mockdata"]
            
        mock_ctx.__enter__.return_value = mock_resp
        return mock_ctx

    mock_stream.side_effect = stream_side_effect
    
    def get_side_effect(url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        
        query = kwargs.get("params", {}).get("query", kwargs.get("params", {}).get("q", ""))
        # Openverse param is "q", Pixabay is "q", Wikimedia is buried in "gsrsearch"
        if not query and "gsrsearch" in kwargs.get("params", {}):
            query = kwargs["params"]["gsrsearch"].replace("filetype:bitmap ", "")
            
        if "no_results" in query:
            if "pexels" in url:
                mock_resp.json.return_value = {"videos": [], "photos": []}
            elif "pixabay" in url:
                mock_resp.json.return_value = {"hits": []}
            elif "openverse" in url:
                mock_resp.json.return_value = {"results": []}
            elif "wikimedia" in url:
                mock_resp.json.return_value = {"query": {"pages": {}}}
            return mock_resp
        
        if "network_fail" in query:
            raise Exception("Connection Timeout")

        if "pexels.com/videos/search" in url:
            if query == "primary":
                mock_resp.json.return_value = {
                    "videos": [
                        {
                            "id": "primary_vid", 
                            "user": {"name": "Pexels User"},
                            "url": "https://pexels.com/primary",
                            "video_files": [{"link": "http://primary.mp4", "width": 1920, "height": 1080}],
                            "duration": 10.0
                        }
                    ]
                }
            elif query == "secondary":
                mock_resp.json.return_value = {
                    "videos": [
                        {
                            "id": "secondary_vid", 
                            "user": {"name": "Pexels User 2"},
                            "url": "https://pexels.com/secondary",
                            "video_files": [{"link": "http://secondary.mp4", "width": 1920, "height": 1080}],
                            "duration": 10.0
                        }
                    ]
                }
            else:
                mock_resp.json.return_value = {"videos": []}
        elif "pexels.com/v1/search" in url:
            mock_resp.json.return_value = {"photos": []}
        elif "pixabay.com/api/videos" in url:
            if query == "primary":
                # Duplicating "primary_vid" to test composite key deduplication across providers.
                mock_resp.json.return_value = {
                    "hits": [
                        {
                            "id": "primary_vid",
                            "user": "Pixabay User",
                            "pageURL": "https://pixabay.com/123",
                            "videos": {"large": {"url": "http://fail_download.mp4", "width": 1280, "height": 720}},
                            "duration": 5.0
                        }
                    ]
                }
            else:
                mock_resp.json.return_value = {"hits": []}
        elif "pixabay.com/api" in url:
            mock_resp.json.return_value = {"hits": []}
        elif "openverse" in url:
            if query == "primary":
                mock_resp.json.return_value = {
                    "results": [
                        {
                            "id": "ov_img",
                            "url": "http://openverse.jpg",
                            "foreign_landing_url": "http://source.ov",
                            "creator": "OV Creator",
                            "license": "CC-BY",
                            "license_url": "http://license.ov",
                            "attribution": "Image by OV Creator CC-BY",
                            "width": 800,
                            "height": 600
                        }
                    ]
                }
            else:
                mock_resp.json.return_value = {"results": []}
        elif "wikimedia" in url:
            if query == "primary":
                mock_resp.json.return_value = {
                    "query": {
                        "pages": {
                            "999": {
                                "title": "File:primary WikiImage.jpg",
                                "imageinfo": [
                                    {
                                        "url": "http://wiki.jpg",
                                        "descriptionurl": "http://desc.wiki",
                                        "width": 1024,
                                        "height": 768,
                                        "extmetadata": {
                                            "Artist": {"value": "Wiki <br> Artist"},
                                            "LicenseShortName": {"value": "CC-BY-SA"},
                                            "LicenseUrl": {"value": "http://license.wiki"}
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            else:
                mock_resp.json.return_value = {"query": {"pages": {}}}
        else:
            mock_resp.status_code = 404
            
        return mock_resp
        
    mock_get.side_effect = get_side_effect
    
    scenes = [
        {
            "start": 0.0,
            "end": 4.5,
            "text": "The ocean.",
            "queries": ["primary", "secondary"]
        },
        {
            "start": 4.5,
            "end": 6.0,
            "text": "Nothing found here.",
            "queries": ["no_results"]
        },
        {
            "start": 6.0,
            "end": 8.0,
            "text": "Network crash.",
            "queries": ["network_fail"]
        }
    ]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test Cache Hit: pre-create the cache file for Pexels:secondary_vid
        import hashlib
        secondary_hash = hashlib.md5("Pexels:secondary_vid".encode()).hexdigest()
        secondary_cache_path = temp_path / f"{secondary_hash}.mp4"
        with open(secondary_cache_path, "wb") as f:
            f.write(b"cached_data")
            
        with patch("backend.app.services.assets.pexels.settings.PEXELS_API_KEY", "fake_key"):
            with patch("backend.app.services.assets.pixabay.settings.PIXABAY_API_KEY", "fake_key"):
                manager = AssetManager(cache_dir=temp_path)
                result_scenes = manager.select_assets_for_scenes(scenes)
                
        # SCENE 1
        s1 = result_scenes[0]
        assert s1["start"] == 0.0, "Start time mutated"
        assert s1["end"] == 4.5, "End time mutated"
        best = s1.get("asset")
        assert best is not None
        
        # Relevance: "primary" query (idx 0) beats "secondary" query (idx 1). 
        # "Pexels:primary_vid" is queried first and has highest score.
        assert best["asset_key"] == "Pexels:primary_vid"
        assert best["query"] == "primary"
        
        # Backup: the runner-up "Pixabay:primary_vid" is kept as metadata only. It is NOT
        # downloaded during the job (it is fetched on demand when the user swaps).
        backup = s1.get("backup_asset")
        assert backup is not None
        assert backup["asset_key"] == "Pixabay:primary_vid"
        assert backup["local_path"] is None
        assert s1["alternatives"][0]["asset_key"] == "Pixabay:primary_vid"

        called_urls = [call[0][1] for call in mock_stream.call_args_list]
        assert "http://fail_download.mp4" not in called_urls, "Backup must not be downloaded eagerly"
        # Exactly one download for the scene: the chosen clip.
        assert called_urls.count("http://primary.mp4") == 1

        # Ensure httpx.stream was NOT called for secondary_vid because we pre-cached it
        assert "http://secondary.mp4" not in called_urls, "Cache hit failed, network stream was called!"

        # Metadata field completeness assertions
        for meta in [best]:
            assert "provider_asset_id" in meta
            assert "asset_key" in meta
            assert "media_url" in meta
            assert "media_type" in meta
            assert meta["media_type"] in ["video", "image"]
            assert "source_page_url" in meta
            assert "author" in meta
            assert "license_name" in meta
            assert "attribution_text" in meta
            assert "attribution_required" in meta
            assert "query" in meta
            assert "cache_key" in meta
            assert "local_path" in meta
            assert meta["local_path"] is not None
        
        # The "network_fail" scene put every provider of this job into a cooldown, so the
        # parsing checks below use fresh providers that don't share the job's health state.
        assert manager.health.cooldown_remaining("Openverse") > 0
        from backend.app.services.assets.openverse import OpenverseProvider
        from backend.app.services.assets.wikimedia import WikimediaProvider

        # Openverse & Wikimedia parsing validation
        ov_res = OpenverseProvider().search("primary")
        assert len(ov_res) == 1
        ov = ov_res[0]
        assert ov.license_name == "CC-BY"
        assert ov.attribution_text == "Image by OV Creator CC-BY"
        
        wiki_res = WikimediaProvider().search("primary")
        assert len(wiki_res) == 1
        wiki = wiki_res[0]
        assert wiki.license_name == "CC-BY-SA"
        assert "Wiki   Artist" in wiki.attribution_text or "Wiki  Artist" in wiki.attribution_text
        
        # SCENE 2 (No results)
        s2 = result_scenes[1]
        assert s2["asset"] is None
        assert s2["backup_asset"] is None
        
        # SCENE 3 (Network fail gracefully)
        s3 = result_scenes[2]
        assert s3["asset"] is None

        print("\n--- P5 Re-Inspection ---")
        for s in result_scenes:
            print(f"Scene: [{s['start']:.2f}s - {s['end']:.2f}s] Queries: {s['queries']}")
            if s.get("asset"):
                a = s["asset"]
                print(f"  Selected: {a['asset_key']} ({a['media_type']}) - {a['width']}x{a['height']} (Query: {a['query']})")  # noqa: E501
                print(f"  Source: {a['source_page_url']} | Author: {a['author']}")
            if s.get("backup_asset"):
                b = s["backup_asset"]
                print(f"  Backup: {b['asset_key']} ({b['media_type']}) - {b['width']}x{b['height']} (Query: {b['query']})")  # noqa: E501
        print("------------------------")

def test_missing_keys_fallback(mock_httpx):
    mock_get, _ = mock_httpx
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        with patch("backend.app.services.assets.pexels.settings.PEXELS_API_KEY", ""):
            with patch("backend.app.services.assets.pixabay.settings.PIXABAY_API_KEY", ""):
                manager = AssetManager(cache_dir=temp_path)
                scenes = [{"start": 0.0, "end": 1.0, "text": "test", "queries": ["test"]}]
                manager.select_assets_for_scenes(scenes)
                
    for call in mock_get.call_args_list:
        url = call[0][0]
        assert "pexels" not in url
        assert "pixabay" not in url

def test_lexicographic_ranking_regression():
    # Prove that secondary-query quality bonuses can NEVER outrank a primary-query candidate
    # solely due to non-relevance traits (e.g. video, 4k, no attribution).
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        manager = AssetManager(cache_dir=Path(td))
        
        from backend.app.services.assets import AssetMetadata
        
        primary_candidate = AssetMetadata(
            provider="Openverse",
            provider_asset_id="1",
            asset_key="Openverse:1",
            media_url="http://img",
            media_type="image",
            width=800,
            height=600,
            attribution_required=True,
            query="primary",
            query_priority=0,      # Primary query
            result_position=0      # First result
        )
        
        secondary_candidate = AssetMetadata(
            provider="Pexels",
            provider_asset_id="2",
            asset_key="Pexels:2",
            media_url="http://vid",
            media_type="video",     # Better media type
            width=3840,             # Better resolution (4k)
            height=2160,
            duration=20.0,          # Better duration
            attribution_required=False, # Better attribution
            query="secondary",
            query_priority=1,       # Secondary query (worse)
            result_position=0
        )
        
        assets = [secondary_candidate, primary_candidate]
        ranked = manager.rank_assets(assets, orientation="landscape", scene_duration=5.0)
        
        # Despite the secondary candidate being a 4K, attribution-free video of perfect duration,
        # the primary candidate (a low-res, attribution-required image) MUST win because
        # its query_priority (0) strictly beats the secondary's query_priority (1) in a tuple comparison.
        assert ranked[0].asset_key == "Openverse:1"
        assert ranked[1].asset_key == "Pexels:2"

def test_asset_relevance_ranking():
    import tempfile
    from pathlib import Path

    from backend.app.services.assets import AssetMetadata
    from backend.app.services.assets.manager import AssetManager

    with tempfile.TemporaryDirectory() as td:
        manager = AssetManager(cache_dir=Path(td))
        scene_query = "beautiful sunset over mountains"
        
        # Asset 1: Perfect match in title and tags
        asset_perfect = AssetMetadata(
            provider="Pexels",
            provider_asset_id="1",
            asset_key="Pexels:1",
            media_url="http://vid1",
            media_type="video",
            width=1920,
            height=1080,
            title="A beautiful sunset",
            tags=["mountains", "nature"],
            query="sunset",
            query_priority=0,
            result_position=0
        )
        
        # Asset 2: High quality video, but completely unrelated title/tags
        asset_unrelated = AssetMetadata(
            provider="Pexels",
            provider_asset_id="2",
            asset_key="Pexels:2",
            media_url="http://vid2",
            media_type="video",
            width=3840,
            height=2160, # better resolution
            title="City traffic night",
            tags=["cars", "city"],
            query="city", # accidentally returned by a bad search provider
            query_priority=0,
            result_position=1
        )
        
        # Asset 3: Partial match
        asset_partial = AssetMetadata(
            provider="Pixabay",
            provider_asset_id="3",
            asset_key="Pixabay:3",
            media_url="http://vid3",
            media_type="video",
            width=1920,
            height=1080,
            title="Mountains",
            tags=["landscape"],
            query="mountains",
            query_priority=1,
            result_position=0
        )
        
        assets = [asset_unrelated, asset_partial, asset_perfect]
        ranked = manager.rank_assets(assets, orientation="landscape", scene_duration=5.0, scene_query=scene_query)
        
        # Rankings:
        # 1. Perfect match (3 tokens: beautiful, sunset, mountains)
        # 2. Partial match (1 token: mountains)
        # 3. Unrelated (0 tokens) -> Must be ranked absolutely last (-1 penalty)
        
        assert ranked[0].asset_key == "Pexels:1"
        assert ranked[1].asset_key == "Pixabay:3"
        assert ranked[2].asset_key == "Pexels:2"

def test_pixabay_tags_relevance_ranking(tmp_path):
    from backend.app.services.assets import AssetMetadata
    from backend.app.services.assets.manager import AssetManager

    manager = AssetManager(cache_dir=tmp_path)
    scene_query = "futuristic city cyberpunk neon"
    
    # Candidate 1: High quality Pixabay asset, but tags DO NOT match the scene query
    # (Maybe the fallback query "city" got us here, but we want a better match)
    asset_high_quality_no_overlap = AssetMetadata(
        provider="Pixabay",
        provider_asset_id="1",
        asset_key="Pixabay:1",
        media_url="http://vid1",
        media_type="video",
        width=3840,
        height=2160, # 4k
        duration=15.0,
        tags=["modern", "architecture", "urban"], # No overlap with scene_query
        query="city",
        query_priority=0,
        result_position=0
    )
    
    # Candidate 2: Lower quality Pixabay asset, but tags DO match the scene query
    asset_lower_quality_overlap = AssetMetadata(
        provider="Pixabay",
        provider_asset_id="2",
        asset_key="Pixabay:2",
        media_url="http://vid2",
        media_type="video",
        width=1920,
        height=1080, # 1080p
        duration=10.0,
        tags=["futuristic", "cyberpunk", "cityscape"], # "futuristic", "cyberpunk" overlaps
        query="city",
        query_priority=0,
        result_position=1
    )
    
    assets = [asset_high_quality_no_overlap, asset_lower_quality_overlap]
    ranked = manager.rank_assets(assets, orientation="landscape", scene_duration=5.0, scene_query=scene_query)
    
    # The one with overlap MUST rank first!
    assert ranked[0].asset_key == "Pixabay:2"
    assert ranked[1].asset_key == "Pixabay:1"


def test_concurrent_fast_tier_early_exit(tmp_path, monkeypatch):
    from backend.app.services.assets import AssetMetadata
    from backend.app.services.assets.manager import AssetManager
    
    manager = AssetManager(cache_dir=tmp_path)
    
    # Track calls
    calls = {"fast": 0, "slow": 0}
    
    # Mock providers
    class MockFast:
        name = "MockFast"
        def search(self, q, orientation):
            calls["fast"] += 1
            return [AssetMetadata(provider="MockFast", provider_asset_id="1", asset_key="F:1", media_url="http://x", media_type="image", width=100, height=100, query=q, query_priority=0, result_position=0)]
        def download(self, a, d): return "mock_path"

    class MockSlow:
        name = "MockSlow"
        def search(self, q, orientation):
            calls["slow"] += 1
            return []
        def download(self, a, d): return None

    manager.fast_tier = [MockFast()]
    manager.slow_tier = [MockSlow()]
    manager.providers = manager.fast_tier + manager.slow_tier
    
    scenes = [{"start": 0.0, "end": 1.0, "text": "hello", "queries": ["hello", "world"]}]
    res = manager.select_assets_for_scenes(scenes)
    
    assert res[0]["asset"]["provider"] == "MockFast"
    assert calls["fast"] == 1  # Only 1 fast provider was called (for query 1)
    assert calls["slow"] == 0  # Should NOT be called because fast tier returned an asset
    # Only 1 query used because early exit worked on the first query!
    
def test_slow_tier_fallback(tmp_path, monkeypatch):
    from backend.app.services.assets import AssetMetadata
    from backend.app.services.assets.manager import AssetManager
    
    manager = AssetManager(cache_dir=tmp_path)
    calls = {"fast": 0, "slow": 0}
    
    class MockFastEmpty:
        name = "MockFastEmpty"
        def search(self, q, orientation):
            calls["fast"] += 1
            return []
        def download(self, a, d): return None
        
    class MockSlowFound:
        name = "MockSlowFound"
        def search(self, q, orientation):
            calls["slow"] += 1
            if q == "world": # Second query finds it
                return [AssetMetadata(provider="MockSlowFound", provider_asset_id="1", asset_key="S:1", media_url="http://x", media_type="image", width=100, height=100, query=q, query_priority=0, result_position=0)]
            return []
        def download(self, a, d): return "mock_path"
        
    manager.fast_tier = [MockFastEmpty()]
    manager.slow_tier = [MockSlowFound()]
    manager.providers = manager.fast_tier + manager.slow_tier
    
    scenes = [{"start": 0.0, "end": 1.0, "text": "hello", "queries": ["hello", "world"]}]
    res = manager.select_assets_for_scenes(scenes)
    
    assert res[0]["asset"]["provider"] == "MockSlowFound"
    assert res[0]["asset"]["query"] == "world"
    # Query 1: Fast(0), Slow(0 returns) -> Next query
    # Query 2: Fast(0), Slow(1 returns) -> Done
    assert calls["fast"] == 2
    assert calls["slow"] == 2

