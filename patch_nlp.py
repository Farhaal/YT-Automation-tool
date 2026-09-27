import re

with open('backend/app/services/nlp.py', 'r') as f:
    content = f.read()

replacement = '''HOOK_SECONDS = 30.0

def process_script_to_scenes(words: List[Dict[str, Any]], pace: str = "balanced", punchy_hook: bool = True, job_state: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    End-to-end pipeline to convert timed words into scenes with visual queries.
    """
    if pace == "dynamic":
        max_d, min_d = 2.5, 1.2
    elif pace == "relaxed":
        max_d, min_d = 5.0, 1.2
    else:
        max_d, min_d = 3.5, 1.2
        
    if punchy_hook:
        hook_words = []
        rest_words = []
        for w in words:
            if w["start"] < HOOK_SECONDS:
                hook_words.append(w)
            else:
                rest_words.append(w)
                
        hook_scenes = segment_into_scenes(hook_words, max_duration=1.8, min_duration=1.0) if hook_words else []
        rest_scenes = segment_into_scenes(rest_words, max_duration=max_d, min_duration=min_d) if rest_words else []
        
        scenes = hook_scenes + rest_scenes
        for i, s in enumerate(scenes):
            s["id"] = f"s{i+1}"
    else:
        scenes = segment_into_scenes(words, max_d, min_d)
        
    # We will try the LLM if any providers are enabled'''

old_func_pattern = r'def process_script_to_scenes.*?use_llm = any\(p\.get\("enabled", True\) for p in getattr\(settings, "LLM_PROVIDERS", \[\]\)\)'

new_content = re.sub(old_func_pattern, replacement, content, flags=re.DOTALL)

with open('backend/app/services/nlp.py', 'w') as f:
    f.write(new_content)
