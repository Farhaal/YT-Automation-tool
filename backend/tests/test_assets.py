import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
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
            if "pexels" in url: mock_resp.json.return_value = {"videos": [], "photos": []}
            elif "pixabay" in url: mock_resp.json.return_value = {"hits": []}
            elif "openverse" in url: mock_resp.json.return_value = {"results": []}
            elif "wikimedia" in url: mock_resp.json.return_value = {"query": {"pages": {}}}
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
                                "title": "File:WikiImage.jpg",
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
        
        # Backup: "Pixabay:primary_vid" fails to download (network error chunk crash).
        # We assert partial file was cleaned up.
        pixabay_hash = hashlib.md5("Pixabay:primary_vid".encode()).hexdigest()
        assert not (temp_path / f"{pixabay_hash}.mp4").exists(), "Partial download file was not cleaned up!"
        
        # So backup becomes Openverse:ov_img (Query 0, score 1000) which beats Pexels:secondary_vid (Query 1, score 995).
        # This explicitly proves the "relevance-first" ranking policy!
        backup = s1.get("backup_asset")
        assert backup is not None
        assert backup["asset_key"] == "Openverse:ov_img"
        assert backup["query"] == "primary"
        
        # Ensure httpx.stream was NOT called for secondary_vid because we pre-cached it
        called_urls = [call[0][1] for call in mock_stream.call_args_list]
        assert "http://secondary.mp4" not in called_urls, "Cache hit failed, network stream was called!"
        
        # Metadata field completeness assertions
        for meta in [best, backup]:
            assert "provider_asset_id" in meta
            assert "asset_key" in meta
            assert "media_url" in meta
            assert "source_page_url" in meta
            assert "author" in meta
            assert "license_name" in meta
            assert "attribution_required" in meta
            assert "query" in meta
            assert "cache_key" in meta
            assert "local_path" in meta
            assert meta["local_path"] is not None
        
        # Openverse & Wikimedia parsing validation (they are generated, verify they exist in manager's tracking if we specifically test them)
        ov_res = manager.providers[2].search("primary")
        assert len(ov_res) == 1
        ov = ov_res[0]
        assert ov.license_name == "CC-BY"
        assert ov.attribution_text == "Image by OV Creator CC-BY"
        
        wiki_res = manager.providers[3].search("primary")
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
                print(f"  Selected: {a['asset_key']} ({a['media_type']}) - {a['width']}x{a['height']} (Query: {a['query']})")
                print(f"  Source: {a['source_page_url']} | Author: {a['author']}")
            if s.get("backup_asset"):
                b = s["backup_asset"]
                print(f"  Backup: {b['asset_key']} ({b['media_type']}) - {b['width']}x{b['height']} (Query: {b['query']})")
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
