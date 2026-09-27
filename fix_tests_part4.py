with open('backend/tests/test_verification.py', 'r') as f:
    content = f.read()

content = content.replace('assert req_kwargs["headers"]["Authorization"] == "Bearer fake_gemini_key"', 'assert req_kwargs["headers"]["Authorization"] == "Bearer dummy-key"')

with open('backend/tests/test_verification.py', 'w') as f:
    f.write(content)
