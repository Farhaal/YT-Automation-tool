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
    
    # Track stream errors to simulate download failure
    def stream_side_effect(method, url, **kwargs):
        if "fail_download" in url:
            raise Exception("Network Error")
        
        mock_ctx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_bytes.return_value = [b"mockdata"]
        mock_ctx.__enter__.return_value = mock_resp
        return mock_ctx

    mock_stream.side_effect = stream_side_effect
    
    def get_side_effect(url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        
        # We simulate a search query for "ocean"
        query = kwargs.get("params", {}).get("query", kwargs.get("params", {}).get("q", ""))
        
        if query == "no_results":
            if "pexels" in url: mock_resp.json.return_value = {"videos": [], "photos": []}
            elif "pixabay" in url: mock_resp.json.return_value = {"hits": []}
            elif "openverse" in url: mock_resp.json.return_value = {"results": []}
            elif "wikimedia" in url: mock_resp.json.return_value = {"query": {"pages": {}}}
            return mock_resp
        
        if "network_fail" in query:
            raise Exception("Connection Timeout")

        if "pexels.com/videos/search" in url:
            mock_resp.json.return_value = {
                "videos": [
                    {
                        "id": "123", 
                        "user": {"name": "Pexels User"},
                        "url": "https://pexels.com/123",
                        "video_files": [{"link": "http://vid1.mp4", "width": 1920, "height": 1080}]
                    }
                ]
            }
        elif "pexels.com/v1/search" in url:
            mock_resp.json.return_value = {"photos": []}
        elif "pixabay.com/api/videos" in url:
            # Deliberately use the same raw ID "123" to prove composite key deduplication works
            mock_resp.json.return_value = {
                "hits": [
                    {
                        "id": "123",
                        "user": "Pixabay User",
                        "pageURL": "https://pixabay.com/123",
                        "videos": {"large": {"url": "http://fail_download.mp4", "width": 1280, "height": 720}}
                    },
                    {
                        "id": "456",
                        "user": "Pixabay User 2",
                        "pageURL": "https://pixabay.com/456",
                        "videos": {"large": {"url": "http://vid3.mp4", "width": 1280, "height": 720}}
                    }
                ]
            }
        elif "pixabay.com/api" in url:
            mock_resp.json.return_value = {"hits": []}
        elif "openverse" in url:
            mock_resp.json.return_value = {"results": []}
        elif "wikimedia" in url:
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
            "queries": ["ocean"]
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
        
        # We test with keys present to test logic
        with patch("backend.app.services.assets.pexels.settings.PEXELS_API_KEY", "fake_key"):
            with patch("backend.app.services.assets.pixabay.settings.PIXABAY_API_KEY", "fake_key"):
                manager = AssetManager(cache_dir=temp_path)
                result_scenes = manager.select_assets_for_scenes(scenes)
                
        # SCENE 1 (Normal hit)
        s1 = result_scenes[0]
        assert s1["start"] == 0.0, "Start time mutated"
        assert s1["end"] == 4.5, "End time mutated"
        best = s1.get("asset")
        assert best is not None
        assert best["asset_key"] == "Pexels:123"
        assert best["provider"] == "Pexels"
        assert best["source_page_url"] == "https://pexels.com/123"
        assert best["author"] == "Pexels User"
        assert best["license_name"] == "Pexels License"
        assert best["media_type"] == "video"
        assert Path(best["local_path"]).exists()
        
        # Pixabay:123 download fails, so backup should be Pixabay:456
        backup = s1.get("backup_asset")
        assert backup is not None
        assert backup["asset_key"] == "Pixabay:456"
        
        # SCENE 2 (No results)
        s2 = result_scenes[1]
        assert s2["asset"] is None
        assert s2["backup_asset"] is None
        
        # SCENE 3 (Network fail gracefully)
        s3 = result_scenes[2]
        assert s3["asset"] is None

        # Print Schema Inspection
        print("\n--- P5 Schema Inspection ---")
        for s in result_scenes:
            print(f"Scene: [{s['start']:.2f}s - {s['end']:.2f}s] Queries: {s['queries']}")
            if s.get("asset"):
                a = s["asset"]
                print(f"  Selected: {a['asset_key']} ({a['media_type']}) - {a['width']}x{a['height']}")
                print(f"  Source: {a['source_page_url']} | Author: {a['author']}")
                print(f"  License: {a['license_name']} ({a.get('license_url', 'None')})")
                print(f"  Local: {a['local_path']}")
        print("----------------------------")

def test_missing_keys_fallback(mock_httpx):
    mock_get, _ = mock_httpx
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Patch keys as empty
        with patch("backend.app.services.assets.pexels.settings.PEXELS_API_KEY", ""):
            with patch("backend.app.services.assets.pixabay.settings.PIXABAY_API_KEY", ""):
                manager = AssetManager(cache_dir=temp_path)
                scenes = [{"start": 0.0, "end": 1.0, "text": "test", "queries": ["test"]}]
                manager.select_assets_for_scenes(scenes)
                
    # Since keys are missing, pexels/pixabay should NOT be called.
    # Only openverse/wikimedia should be called.
    for call in mock_get.call_args_list:
        url = call[0][0]
        assert "pexels" not in url
        assert "pixabay" not in url
