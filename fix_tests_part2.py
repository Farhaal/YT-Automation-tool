with open('backend/tests/test_jobs.py', 'r') as f:
    content = f.read()

content = content.replace('def mock_segment(words, pace="balanced"):', 'def mock_segment(words, pace="balanced", job_state=None):')
content = content.replace('original_llm_key = settings.LLM_API_KEY', 'original_llm_key = getattr(settings, "LLM_PROVIDERS", [])')
content = content.replace('assert settings.LLM_API_KEY == "secret123"', 'assert settings.LLM_PROVIDERS[0]["api_key"] == "secret123"')
content = content.replace('settings.LLM_API_KEY = original_llm_key', 'settings.LLM_PROVIDERS = original_llm_key')

with open('backend/tests/test_jobs.py', 'w') as f:
    f.write(content)

with open('backend/tests/test_verification.py', 'r') as f:
    ver_content = f.read()

ver_content = ver_content.replace('res = verify_scene_candidates("scene", "topic", candidates, "fake_gemini_key", "gemini-1.5-flash")', 'res = verify_scene_candidates("scene", "topic", candidates, job_state={})')

with open('backend/tests/test_verification.py', 'w') as f:
    f.write(ver_content)
