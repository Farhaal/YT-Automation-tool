import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.assets.manager import AssetManager
from backend.app.services.assets import AssetMetadata

@pytest.fixture
def mock_httpx():
    with patch("httpx.get") as mock_get, patch("httpx.stream") as mock_stream:
        yield mock_get, mock_stream

def test_asset_manager_selection(mock_httpx):
    mock_get, mock_stream = mock_httpx
    
    # Mock search responses
    def get_side_effect(url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        if "pexels.com/videos/search" in url:
            mock_resp.json.return_value = {
                "videos": [
                    {
                        "id": "111", 
                        "user": {"name": "Pexels User"}, 
                        "duration": 10.0,
                        "video_files": [{"link": "http://vid1.mp4", "width": 1920, "height": 1080}]
                    }
                ]
            }
        elif "pexels.com/v1/search" in url:
            mock_resp.json.return_value = {"photos": []}
        elif "pixabay.com/api/videos" in url:
            mock_resp.json.return_value = {
                "hits": [
                    {
                        "id": "222",
                        "user": "Pixabay User",
                        "duration": 5.0,
                        "videos": {"large": {"url": "http://vid2.mp4", "width": 1280, "height": 720}}
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
    
    # Mock stream response for downloads
    mock_stream_ctx = MagicMock()
    mock_stream_resp = MagicMock()
    mock_stream_resp.raise_for_status = MagicMock()
    mock_stream_resp.iter_bytes.return_value = [b"mockdata"]
    mock_stream_ctx.__enter__.return_value = mock_stream_resp
    mock_stream.return_value = mock_stream_ctx

    # Fake scenes with fixed audio-timed data from P4
    scenes = [
        {
            "start": 0.0,
            "end": 4.5,
            "text": "The ocean covers most of our planet.",
            "queries": ["ocean", "planet"]
        }
    ]
    
    # Need to patch os.path.exists so it doesn't think it's cached from previous runs
    with patch("os.path.exists", return_value=False), patch("builtins.open", MagicMock()):
        with patch("backend.app.services.assets.pexels.settings.PEXELS_API_KEY", "fake_key"):
            with patch("backend.app.services.assets.pixabay.settings.PIXABAY_API_KEY", "fake_key"):
                manager = AssetManager()
                result_scenes = manager.select_assets_for_scenes(scenes)
        
        
    assert len(result_scenes) == 1
    scene = result_scenes[0]
    
    assert scene["start"] == 0.0
    assert scene["end"] == 4.5
    assert "asset" in scene
    assert "backup_asset" in scene
    
    best = scene["asset"]
    backup = scene["backup_asset"]
    
    assert best["id"] == "111"  # Pexels 1080p video wins
    assert best["media_type"] == "video"
    assert "local_path" in best
    
    assert backup["id"] == "222"  # Pixabay 720p video is backup
    
    print("\n--- P5 Audio-Timed Scene Asset Selection Inspection ---")
    for s in result_scenes:
        print(f"Scene: [{s['start']:.2f}s - {s['end']:.2f}s]")
        print(f"  Queries: {s['queries']}")
        
        a = s.get("asset")
        if a:
            print(f"  Selected: [{a['provider']}] {a['media_type'].upper()} ({a['width']}x{a['height']}) - License: {a['license']}")
            print(f"            Path: {a['local_path']}")
        
        b = s.get("backup_asset")
        if b:
            print(f"  Backup:   [{b['provider']}] {b['media_type'].upper()} ({b['width']}x{b['height']}) - License: {b['license']}")
    print("-------------------------------------------------------")
