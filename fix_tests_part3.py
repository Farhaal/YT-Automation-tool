with open('backend/tests/test_jobs.py', 'r') as f:
    content = f.read()

content = content.replace('settings.LLM_API_KEY = ""', 'settings.LLM_PROVIDERS = []')
content = content.replace('assert settings.LLM_API_KEY == "fake_llm_key_123"', 'assert settings.LLM_PROVIDERS[0]["api_key"] == "fake_llm_key_123"')
content = content.replace('json.dump({"llm_api_key": "fake_llm_key_123"}, f)', 'json.dump({"llm_providers": [{"provider": "openai", "api_key": "fake_llm_key_123", "model": "test", "enabled": True}]}, f)')

with open('backend/tests/test_jobs.py', 'w') as f:
    f.write(content)

with open('backend/tests/test_verification.py', 'r') as f:
    ver_content = f.read()

# Add raise_for_status to MockPostResp in test_gemini_provider_verification
mock_post_replacement = '''        class MockPostResp:
            status_code = 200
            text = '{"best_index": 0, "score": 0.9, "reason": "good"}'
            def json(self):
                return {"choices": [{"message": {"content": self.text}}]}
            def raise_for_status(self):
                pass'''
ver_content = ver_content.replace('''        class MockPostResp:
            status_code = 200
            text = '{"best_index": 0, "score": 0.9, "reason": "good"}'
            def json(self):
                return {"choices": [{"message": {"content": self.text}}]}''', mock_post_replacement)

with open('backend/tests/test_verification.py', 'w') as f:
    f.write(ver_content)
