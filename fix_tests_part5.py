with open('backend/tests/test_verification.py', 'r') as f:
    content = f.read()

content = content.replace('res_err = verify_scene_candidates("scene", "topic", candidates, "fake_gemini_key", "gemini-1.5-flash")', 'res_err = verify_scene_candidates("scene", "topic", candidates, job_state={})')

with open('backend/tests/test_verification.py', 'w') as f:
    f.write(content)
