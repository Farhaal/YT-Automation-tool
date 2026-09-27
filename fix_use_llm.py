with open('backend/app/services/nlp.py', 'r') as f:
    content = f.read()

content = content.replace('# We will try the LLM if any providers are enabled', 'use_llm = any(p.get("enabled", True) for p in getattr(settings, "LLM_PROVIDERS", []))')

with open('backend/app/services/nlp.py', 'w') as f:
    f.write(content)
