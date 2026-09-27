import re

# FIX test_nlp.py
with open('backend/tests/test_nlp.py', 'r') as f:
    nlp_content = f.read()

nlp_content = nlp_content.replace('monkeypatch.setattr(settings, "LLM_API_KEY", "fake_key")', 'monkeypatch.setattr(settings, "LLM_PROVIDERS", [{"provider": "openai", "api_key": "fake_key", "model": "gpt-3.5-turbo", "enabled": True}])')
nlp_content = nlp_content.replace('monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")', 'monkeypatch.setattr(settings, "LLM_PROVIDERS", [{"provider": "gemini", "api_key": "fake_key", "model": "gemini-1.5-flash", "enabled": True}])')
nlp_content = nlp_content.replace('monkeypatch.setattr("backend.app.services.nlp._call_llm_chat", mock_call_llm_chat)', 'monkeypatch.setattr("backend.app.services.nlp.call_llm", mock_call_llm_chat)')
nlp_content = nlp_content.replace('def mock_call_llm_chat(messages, temperature=0.3):', 'def mock_call_llm_chat(messages, temperature=0.3, require_vision=False, job_state=None):')

# Fix test_gemini_provider_nlp in test_nlp.py
gemini_test_replacement = '''def test_gemini_provider_nlp(monkeypatch):
    from backend.app.core.config import settings
    from backend.app.services.nlp import call_llm
    import httpx
    
    monkeypatch.setattr(settings, "LLM_PROVIDERS", [{"provider": "gemini", "api_key": "fake", "model": "gemini-1.5-flash", "enabled": True}])
    
    calls = []
    class MockResponse:
        def __init__(self):
            self.status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": "underwater footage, coral reef"}}]}
        def raise_for_status(self):
            pass
            
    def mock_post(*args, **kwargs):
        calls.append((args, kwargs))
        return MockResponse()
        
    monkeypatch.setattr(httpx, "post", mock_post)
    
    content = call_llm([{"role": "user", "content": "test"}])
    assert "underwater footage" in content
    
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[0] == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer fake"
    assert kwargs["json"]["model"] == "gemini-1.5-flash"'''

nlp_content = re.sub(r'def test_gemini_provider_nlp\(monkeypatch\):.*?(?=\n\S|\Z)', gemini_test_replacement, nlp_content, flags=re.DOTALL)

with open('backend/tests/test_nlp.py', 'w') as f:
    f.write(nlp_content)

# FIX test_jobs.py
with open('backend/tests/test_jobs.py', 'r') as f:
    jobs_content = f.read()

jobs_content = jobs_content.replace('settings.LLM_API_KEY = "test"', 'settings.LLM_PROVIDERS = [{"provider": "openai", "api_key": "test", "model": "test", "enabled": True}]')
jobs_content = jobs_content.replace('monkeypatch.setattr("backend.app.services.nlp._call_llm_chat", mock_llm)', 'monkeypatch.setattr("backend.app.services.nlp.call_llm", mock_llm)')
jobs_content = jobs_content.replace('def mock_llm(messages, temperature=0.3):', 'def mock_llm(messages, temperature=0.3, require_vision=False, job_state=None):')

with open('backend/tests/test_jobs.py', 'w') as f:
    f.write(jobs_content)

# FIX test_verification.py
with open('backend/tests/test_verification.py', 'r') as f:
    ver_content = f.read()

ver_content = ver_content.replace('result = verify_scene_candidates(\n            "test scene", "topic", candidates, "dummy-key", "dummy-model"\n        )', 'result = verify_scene_candidates("test scene", "topic", candidates, job_state={})')
ver_content = ver_content.replace('result = verify_scene_candidates("test scene", "topic", candidates, "dummy-key", "dummy-model")', 'result = verify_scene_candidates("test scene", "topic", candidates, job_state={})')

# We need to mock call_llm instead of httpx.post for verification tests because we changed verification.py to use call_llm.
# Actually, verification.py uses call_llm which uses httpx.post. So mocking httpx.post still works! Wait, if call_llm is used, we need LLM_PROVIDERS set in settings.
ver_content = ver_content.replace('def test_verify_scene_candidates_success():', 'def test_verify_scene_candidates_success(monkeypatch):\n    from backend.app.core.config import settings\n    monkeypatch.setattr(settings, "LLM_PROVIDERS", [{"provider": "openai", "api_key": "dummy-key", "model": "dummy-model", "enabled": True}])')
ver_content = ver_content.replace('def test_verify_scene_candidates_http_error():', 'def test_verify_scene_candidates_http_error(monkeypatch):\n    from backend.app.core.config import settings\n    monkeypatch.setattr(settings, "LLM_PROVIDERS", [{"provider": "openai", "api_key": "dummy-key", "model": "dummy-model", "enabled": True}])')
ver_content = ver_content.replace('def test_gemini_provider_verification(monkeypatch):', 'def test_gemini_provider_verification(monkeypatch):\n    from backend.app.core.config import settings\n    monkeypatch.setattr(settings, "LLM_PROVIDERS", [{"provider": "gemini", "api_key": "dummy-key", "model": "dummy-model", "enabled": True}])')
ver_content = ver_content.replace('monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")', '')
ver_content = ver_content.replace('monkeypatch.setattr(settings, "LLM_API_KEY", "dummy-key")', '')
ver_content = ver_content.replace('monkeypatch.setattr(settings, "VISION_MODEL", "dummy-model")', '')
# Make sure mock_resp for http error throws raise_for_status
ver_content = ver_content.replace('mock_resp.status_code = 429\n        mock_post.return_value = mock_resp', 'mock_resp.status_code = 429\n        import httpx\n        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp)\n        mock_post.return_value = mock_resp')


with open('backend/tests/test_verification.py', 'w') as f:
    f.write(ver_content)

