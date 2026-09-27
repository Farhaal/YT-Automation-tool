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

def test_gemini_provider_verification(monkeypatch):
    from backend.app.core.config import settings
    from backend.app.services.verification import verify_scene_candidates
    from backend.app.services.assets import AssetMetadata
    import httpx
    import base64
    
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    
    # Mock httpx.get for base64 image fetch
    def mock_get(url, **kwargs):
        class MockGetResp:
            status_code = 200
            content = b"fakeimage"
            headers = {"content-type": "image/jpeg"}
        return MockGetResp()
        
    monkeypatch.setattr(httpx, "get", mock_get)
    
    # Mock httpx.post for LLM
    req_kwargs = {}
    def mock_post(url, **kwargs):
        req_kwargs["url"] = url
        req_kwargs["headers"] = kwargs.get("headers")
        req_kwargs["json"] = kwargs.get("json")
        class MockPostResp:
            status_code = 200
            text = '{"best_index": 0, "score": 0.9, "reason": "good"}'
            def json(self):
                return {"choices": [{"message": {"content": self.text}}]}
        return MockPostResp()
        
    monkeypatch.setattr(httpx, "post", mock_post)
    
    candidates = [
        AssetMetadata(id="1", provider="pexels", type="video", path="", duration=5.0,
                     preview_image_url="http://fake.url/img.jpg",
                     provider_asset_id="123", asset_key="123", media_url="url", media_type="mp4")
    ]
    
    res = verify_scene_candidates("scene", "topic", candidates, "fake_gemini_key", "gemini-1.5-flash")
    
    assert res is not None
    assert res["score"] == 0.9
    assert req_kwargs["url"] == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert req_kwargs["headers"]["Authorization"] == "Bearer fake_gemini_key"
    
    # Verify the image was converted to base64 inline
    messages = req_kwargs["json"]["messages"]
    content = messages[1]["content"]
    image_url_obj = next(c for c in content if c["type"] == "image_url")
    expected_b64 = base64.b64encode(b"fakeimage").decode("utf-8")
    assert image_url_obj["image_url"]["url"] == f"data:image/jpeg;base64,{expected_b64}"

    # Test graceful fallback (no failure/exception)
    def mock_post_err(url, **kwargs):
        class ErrResp:
            status_code = 500
            text = "error"
        return ErrResp()
    monkeypatch.setattr(httpx, "post", mock_post_err)
    
    res_err = verify_scene_candidates("scene", "topic", candidates, "fake_gemini_key", "gemini-1.5-flash")
    assert res_err is None
