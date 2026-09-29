import json

import pytest
from fastapi.testclient import TestClient

from backend.app.core.paths import DATA
from backend.app.main import app
from backend.app.services.job_manager import job_manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_env(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.app.api.routes.SETTINGS_PATH", tmp_path / "settings.json")
    
    # We must patch job_manager paths
    job_dir = tmp_path / "jobs"
    job_dir.mkdir()
    monkeypatch.setattr("backend.app.services.job_manager.job_manager.jobs_dir", job_dir)
    
    # Also patch DATA for anything else
    monkeypatch.setattr("backend.app.api.routes.DATA", tmp_path)
    monkeypatch.setattr("backend.app.services.job_manager.DATA", tmp_path)

def test_settings_api(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.app.api.routes.SETTINGS_PATH", tmp_path / "settings.json")
    
    # Verify keys are masked / only return status
    res = client.post("/settings", json={"pexels_key": "secret_abc", "pixabay_key": "secret_xyz"})
    assert res.status_code == 200
    data = res.json()
    assert "secret_abc" not in str(data)
    assert data["pexels"] == "Configured"
    assert data["pixabay"] == "Configured"
    
    # Verify GET
    res = client.get("/settings")
    data = res.json()
    assert "secret_abc" not in str(data)
    assert data["pexels"] == "Configured"
    
    # Clean up
    client.delete("/settings/pexels")
    res = client.get("/settings")
    assert res.json()["pexels"] == "Not configured"

def test_job_orchestration(monkeypatch):
    # We want to mock run_job_pipeline_sync so it doesn't actually run heavy ML,
    # but instead we test that the script flow generates audio, then transcribes it (verifying logic).
    
    
    called_stages = []
    
    def mock_synthesize(text):
        called_stages.append("synthesize")
        # Return fake audio path
        return DATA / "tmp" / "fake.wav"
        
    def mock_transcribe(audio_path):
        called_stages.append("transcribe")
        assert str(audio_path).endswith("fake.wav")
        return {"words": [{"word": "fake", "start": 0, "end": 1}]}
        
    def mock_segment(words, pace="balanced", job_state=None, **kwargs):
        called_stages.append("segment")
        return [{"start": 0, "end": 1, "text": "fake", "asset": None}]

    def mock_assemble(*args, **kwargs):
        called_stages.append("assemble")
        return {"scenes": []}

    monkeypatch.setattr("backend.app.services.tts.synthesize", mock_synthesize)
    monkeypatch.setattr("backend.app.api.routes.transcribe_audio", mock_transcribe)
    monkeypatch.setattr("backend.app.services.nlp.process_script_to_scenes", mock_segment)
    monkeypatch.setattr("backend.app.services.timeline.TimelineAssembler.assemble", mock_assemble)
    monkeypatch.setattr("backend.app.services.assets.manager.AssetManager.select_assets_for_scenes", lambda self, scenes, **kwargs: scenes)  # noqa: E501
    
    # Trigger script flow
    res = client.post("/generate/script", json={"script": "Hello world"})
    assert res.status_code == 200
    job_id = res.json()["job_id"]
    
    # The background task is executed immediately by TestClient depending on starlette BackgroundTasks
    # Actually TestClient runs background tasks synchronously after returning the response!
    
    job = job_manager.get_job(job_id)
    assert job["status"] == "COMPLETED"
    
    # Verify Audio was synthesized FIRST, then transcribed
    assert called_stages == ["synthesize", "transcribe", "segment", "assemble"]

def test_timeline_immutability(monkeypatch, tmp_path):
    job_id = "test-job-immutable"
    from backend.app.services.job_manager import job_manager
    job_manager.create_job(job_id)
    
    import copy
    timeline = {
        "version": 1,
        "resolution": {"width": 1080, "height": 1920, "fps": 30},
        "audio": {"path": "test.wav", "duration": 10},
        "scenes": [{"id": "s1", "start": 0, "end": 10, "text": "scene", "motion": "none"}],
        "captions": [{"word": "word", "start": 0, "end": 1}],
        "popups": []
    }
    
    t_path = tmp_path / "jobs" / job_id / "timeline.json"
    t_path.parent.mkdir(parents=True, exist_ok=True)
    with open(t_path, "w", encoding="utf-8") as f_time:
        json.dump(timeline, f_time)
        
    job_manager.update_job(job_id, timeline_path=str(t_path))
    
    # Try adding a scene
    bad_timeline = copy.deepcopy(timeline)
    bad_timeline["scenes"] = [{"id": "s1", "start": 0, "end": 5, "text": "s1"}, {"id": "s2", "start": 5, "end": 10, "text": "s2"}]  # noqa: E501
    res = client.put(f"/jobs/{job_id}/timeline", json=bad_timeline)
    assert res.status_code == 400
    assert "Scene count mismatch" in res.json()["detail"]
    
    # Try modifying an ID
    bad_timeline = copy.deepcopy(timeline)
    bad_timeline["scenes"] = [{"id": "s-hacked", "start": 0, "end": 10, "text": "s1"}]
    res = client.put(f"/jobs/{job_id}/timeline", json=bad_timeline)
    assert res.status_code == 400
    assert "Scene ID mismatch" in res.json()["detail"]
    
    # Try modifying timestamps (should be restored)
    valid_edit = copy.deepcopy(timeline)
    valid_edit["scenes"][0]["motion"] = "kenburns_in"
    valid_edit["scenes"][0]["start"] = 999 
    res = client.put(f"/jobs/{job_id}/timeline", json=valid_edit)
    assert res.status_code == 200
    
    with open(t_path, "r", encoding="utf-8") as f_read:
        saved = json.load(f_read)
        assert saved["scenes"][0]["motion"] == "kenburns_in"
        assert saved["scenes"][0]["start"] == 0 

def test_pipeline_applies_settings_before_nlp(monkeypatch, tmp_path):
    from backend.app.core.config import settings
    
    # Isolate settings path explicitly
    fake_settings_path = tmp_path / "settings.json"
    monkeypatch.setattr("backend.app.api.routes.SETTINGS_PATH", fake_settings_path)
    
    # Save original key to restore later
    original_llm_key = getattr(settings, "LLM_PROVIDERS", [])
    
    try:
        # Write a fake settings file with an LLM key
        with open(fake_settings_path, "w") as f:
            json.dump({"llm_providers": [{"provider": "openai", "api_key": "fake_llm_key_123", "model": "test", "enabled": True}]}, f)
            
        called = []
        
        def mock_synthesize(text): return DATA / "tmp" / "fake.wav"
        def mock_transcribe(audio_path): return {"words": [{"word": "fake", "start": 0, "end": 1}]}
        
        def mock_segment(words, pace="balanced", job_state=None, **kwargs):
            # By the time this runs, settings should have the LLM API key
            assert settings.LLM_PROVIDERS[0]["api_key"] == "fake_llm_key_123"
            called.append("segment_with_settings_applied")
            return [{"start": 0, "end": 1, "text": "fake", "asset": None}]

        def mock_assemble(*args, **kwargs): return {"scenes": []}

        monkeypatch.setattr("backend.app.services.tts.synthesize", mock_synthesize)
        monkeypatch.setattr("backend.app.api.routes.transcribe_audio", mock_transcribe)
        monkeypatch.setattr("backend.app.services.nlp.process_script_to_scenes", mock_segment)
        monkeypatch.setattr("backend.app.services.timeline.TimelineAssembler.assemble", mock_assemble)
        monkeypatch.setattr("backend.app.services.assets.manager.AssetManager.select_assets_for_scenes", lambda self, scenes, **kwargs: scenes)  # noqa: E501
        
        # Ensure settings is cleared out first so we know it loaded from file
        settings.LLM_PROVIDERS = []

        # Trigger script flow
        res = client.post("/generate/script", json={"script": "Test settings order"})
        assert res.status_code == 200
        
        assert "segment_with_settings_applied" in called
    finally:
        # Restore original LLM key
        settings.LLM_PROVIDERS = original_llm_key
