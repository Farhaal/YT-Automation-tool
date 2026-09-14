import pytest
from unittest.mock import patch, MagicMock

from backend.app.services.assets import AssetMetadata
from backend.app.services.verification import verify_scene_candidates

def test_verify_scene_candidates_success():
    candidates = [
        AssetMetadata(
            provider="dummy", provider_asset_id="1", asset_key="dummy:1", media_url="1", media_type="image",
            preview_image_url="http://example.com/1.jpg"
        ),
        AssetMetadata(
            provider="dummy", provider_asset_id="2", asset_key="dummy:2", media_url="2", media_type="image",
            preview_image_url="http://example.com/2.jpg"
        )
    ]
    
    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"best_index": 1, "score": 0.9, "reason": "Perfect fit"}'}}]
        }
        mock_post.return_value = mock_resp
        
        result = verify_scene_candidates(
            "test scene", "topic", candidates, "dummy-key", "dummy-model"
        )
        
        assert result is not None
        assert result["best_index"] == 1
        assert result["score"] == 0.9
        assert result["reason"] == "Perfect fit"

def test_verify_scene_candidates_no_previews():
    candidates = [
        AssetMetadata(provider="dummy", provider_asset_id="1", asset_key="dummy:1", media_url="1", media_type="image")
    ]
    result = verify_scene_candidates("test scene", "topic", candidates, "dummy-key", "dummy-model")
    assert result is None

def test_verify_scene_candidates_http_error():
    candidates = [
        AssetMetadata(provider="dummy", provider_asset_id="1", asset_key="dummy:1", media_url="1", media_type="image", preview_image_url="x")
    ]
    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp
        result = verify_scene_candidates("test scene", "topic", candidates, "dummy-key", "dummy-model")
        assert result is None
