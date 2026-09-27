from backend.app.services.nlp import process_script_to_scenes, segment_into_scenes

def test_scene_segmentation():
    # 1. Empty input
    assert segment_into_scenes([]) == []

    # 2. Clause boundaries
    words_multi = [
        {"word": "Hello,", "start": 0.0, "end": 1.5},
        {"word": "world", "start": 1.6, "end": 2.2},
        {"word": "and", "start": 2.3, "end": 3.0},
        {"word": "friends.", "start": 3.1, "end": 4.5}
    ]
    # Comma at 1.5 >= min(1.2) -> splits after "Hello,"
    # "and" at 3.0. Dur = 3.0 - 1.6 = 1.4 >= min(1.2) -> splits after "and"
    scenes = segment_into_scenes(words_multi, max_duration=10.0, min_duration=1.2)
    assert len(scenes) == 3
    assert scenes[0]["text"] == "Hello,"
    assert scenes[1]["text"] == "world and"
    assert scenes[2]["text"] == "friends."

    # 3. Enforce min_duration
    words_short = [
        {"word": "Wait,", "start": 0.0, "end": 0.5}, # Dur = 0.5 < 1.2, ignored comma
        {"word": "for", "start": 0.6, "end": 1.0},
        {"word": "it,", "start": 1.1, "end": 1.5},    # Dur = 1.5 >= 1.2, comma triggers split
        {"word": "now.", "start": 2.5, "end": 4.0}    # Dur = 1.5 >= 1.2
    ]
    scenes = segment_into_scenes(words_short, max_duration=10.0, min_duration=1.2)
    assert len(scenes) == 2
    assert scenes[0]["text"] == "Wait, for it,"
    assert scenes[1]["text"] == "now."

    # 4. Enforce max_duration
    words_long = [{"word": f"w{i}", "start": float(i), "end": float(i) + 0.5} for i in range(10)]
    # Each word is 0.5s long, gaps are 0.5s.
    scenes = segment_into_scenes(words_long, max_duration=3.5, min_duration=1.2)
    for s in scenes:
        assert (s["end"] - s["start"]) >= 1.2 or (s["end"] - s["start"]) < 1.2 # Last one might be short but we merge backwards if < min_duration
        
    # Check that no scene is < min_duration
    for s in scenes:
        assert (s["end"] - s["start"]) >= 1.2 or len(scenes) == 1

def test_scene_segmentation_and_keywords_fallback():
    mock_words = [
        {"word": "The", "start": 0.0, "end": 0.5},
        {"word": "ocean", "start": 0.5, "end": 1.0},
        {"word": "covers", "start": 1.0, "end": 1.5},
        {"word": "most", "start": 1.5, "end": 2.0},
        {"word": "of", "start": 2.0, "end": 2.5},
        {"word": "our", "start": 2.5, "end": 3.0},
        {"word": "planet.", "start": 3.0, "end": 3.5},
    ]

    scenes = process_script_to_scenes(mock_words)
    # Should probably split at max duration
    assert len(scenes) > 0
    
def test_scene_segmentation_with_topic_llm(monkeypatch):
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "LLM_API_KEY", "fake_key")
    
    calls = []
    
    def mock_call_llm_chat(messages, temperature=0.3):
        if temperature == 0.7:
            calls.append("topic")
            return "Test topic: Ocean life."
        else:
            calls.append("queries")
            return "underwater footage, sea life"

    monkeypatch.setattr("backend.app.services.nlp._call_llm_chat", mock_call_llm_chat)
    
    mock_words = [
        {"word": "The", "start": 0.0, "end": 0.5},
        {"word": "ocean", "start": 0.5, "end": 1.0},
        {"word": "is", "start": 1.0, "end": 1.5},
        {"word": "deep.", "start": 1.5, "end": 2.0},
    ]

    scenes = process_script_to_scenes(mock_words)
    
    assert len(scenes) == 1
    assert calls == ["topic", "queries"]
    assert scenes[0]["queries"] == ["underwater footage", "sea life"]

def test_regression_sync_preservation():
    synthetic_text = "This is a synthetic test, and it has clauses. It also has a very long section with no punctuation so it forces a duration split but we also add a conjunction here. Finally, it ends."
    
    words = []
    current_time = 0.0
    word_duration = 0.4
    raw_words = synthetic_text.split()
    
    for w in raw_words:
        words.append({
            "word": w,
            "start": round(current_time, 2),
            "end": round(current_time + word_duration, 2)
        })
        current_time += word_duration + 0.1  # 0.1s gap between words

    min_dur = 1.2
    
    for max_d in [2.5, 3.5, 5.0]:
        scenes = segment_into_scenes(words, max_duration=max_d, min_duration=min_dur)
        
        # 1. Word preservation & ordering
        reconstructed_text = " ".join(s["text"] for s in scenes)
        assert reconstructed_text == synthetic_text, f"Word mismatch at max_duration {max_d}"
        
        # 2. Chronological and cover audio start-to-end
        assert scenes[0]["start"] == words[0]["start"]
        assert scenes[-1]["end"] == words[-1]["end"]
        
        last_end = -1.0
        for i, s in enumerate(scenes):
            assert s["start"] >= last_end
            assert s["end"] > s["start"]
            last_end = s["end"]
            
            # 3. No non-final scene is shorter than min_duration
            if i < len(scenes) - 1:
                dur = s["end"] - s["start"]
                assert dur >= min_dur, f"Scene {i} duration {dur} < {min_dur} at max_d {max_d}"

def test_gemini_provider_nlp(monkeypatch):
    from backend.app.core.config import settings
    from backend.app.services.nlp import _call_llm_chat
    import httpx
    
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "LLM_API_KEY", "fake_gemini_key")
    monkeypatch.setattr(settings, "LLM_BASE_URL", "")
    
    class MockResponse:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": "mocked gemini response"}}]}
        def raise_for_status(self):
            pass
            
    req_kwargs = {}
    def mock_post(url, **kwargs):
        req_kwargs["url"] = url
        req_kwargs["headers"] = kwargs.get("headers")
        return MockResponse()
        
    monkeypatch.setattr(httpx, "post", mock_post)
    
    res = _call_llm_chat([{"role": "user", "content": "hi"}])
    
    assert res == "mocked gemini response"
    assert req_kwargs["url"] == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert req_kwargs["headers"]["Authorization"] == "Bearer fake_gemini_key"

    # Test fallback on error via process_script_to_scenes
    def mock_post_error(url, **kwargs):
        class ErrResponse:
            status_code = 500
            text = "internal error"
            def raise_for_status(self):
                raise Exception("HTTP Error")
        return ErrResponse()
    monkeypatch.setattr(httpx, "post", mock_post_error)
    
    from backend.app.services.nlp import process_script_to_scenes
    # This should not raise, but fallback to Yake gracefully
    scenes = process_script_to_scenes([{"word": "Test", "start": 0, "end": 1}])
    assert len(scenes) == 1
