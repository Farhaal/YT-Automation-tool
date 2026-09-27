import pytest
from backend.app.services.nlp import process_script_to_scenes

def test_hook_density():
    # Generate words covering 60 seconds.
    # We'll just place one word every 0.5 seconds.
    words = []
    for i in range(120):
        words.append({
            "word": f"word{i}.",
            "start": i * 0.5,
            "end": (i + 1) * 0.5
        })
        
    # With punchy_hook=True, first 30 seconds (60 words) should be denser.
    # Base pace is max_duration=3.5, min_duration=1.2
    # Hook pace is max_duration=1.8, min_duration=1.0
    scenes_hook = process_script_to_scenes(words, pace="balanced", punchy_hook=True, job_state={"dead_providers": set()})
    
    # Without punchy_hook, everything is base pace.
    scenes_normal = process_script_to_scenes(words, pace="balanced", punchy_hook=False, job_state={"dead_providers": set()})
    
    # Count scenes in the first 30 seconds
    hook_scenes_count_hook = len([s for s in scenes_hook if s["start"] < 30.0])
    hook_scenes_count_normal = len([s for s in scenes_normal if s["start"] < 30.0])
    
    assert hook_scenes_count_hook > hook_scenes_count_normal, "Hook region should produce more scenes"
    
    # Word preservation
    words_out_text = []
    for s in scenes_hook:
        words_out_text.append(s["text"])
        # Min duration check:
        if s["id"] != scenes_hook[-1]["id"]: # not last scene
            dur = s["end"] - s["start"]
            assert dur >= 1.0, f"Min duration violated in hook logic: {dur}"
            
    assert " ".join(words_out_text) == " ".join(w["word"] for w in words), "Word order violated"

    print("Hook test passed!")

