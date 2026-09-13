from backend.app.services.nlp import segment_into_scenes, extract_keywords, process_script_to_scenes

def test_scene_segmentation():
    # 1. Empty input
    assert segment_into_scenes([]) == []

    # 2. Normal sentence boundaries
    words_normal = [
        {"word": "Hello.", "start": 0.0, "end": 1.0},
        {"word": "World.", "start": 1.1, "end": 2.0}
    ]
    scenes = segment_into_scenes(words_normal)
    assert len(scenes) == 2
    assert scenes[0]["text"] == "Hello."
    assert scenes[1]["text"] == "World."

    # 3. Timestamp-gap pause without punctuation
    words_gap = [
        {"word": "Wait", "start": 0.0, "end": 0.5},
        {"word": "for", "start": 0.6, "end": 1.0},
        {"word": "it", "start": 1.1, "end": 1.5},
        # Gap is 1.0s (> 0.8s)
        {"word": "now", "start": 2.5, "end": 3.0}
    ]
    scenes = segment_into_scenes(words_gap, pause_threshold=0.8)
    assert len(scenes) == 2
    assert scenes[0]["text"] == "Wait for it"
    assert scenes[1]["text"] == "now"

    # 4. Unpunctuated long sentence (forces split at max_duration)
    words_long = [{"word": f"w{i}", "start": float(i), "end": float(i) + 0.5} for i in range(10)]
    # Each word is 0.5s long, gaps are 0.5s. Total time 9.5s.
    scenes = segment_into_scenes(words_long, max_duration=4.0)
    # word 0 start=0.0. word 3 end=3.5 (ok). word 4 end=4.5 (>4.0). Should split before word 4.
    assert len(scenes) == 3
    assert scenes[0]["text"] == "w0 w1 w2 w3"
    assert scenes[1]["text"] == "w4 w5 w6 w7"
    assert scenes[2]["text"] == "w8 w9"
    
    # Check that all scenes obey max_duration except if a single word is too long
    for s in scenes:
        assert (s["end"] - s["start"]) <= 4.0

    # 5. Duplicate / dropped word check
    input_words = words_normal + words_gap + words_long
    # Shift times so they are sequential for realism, though segment_into_scenes doesn't care
    for i, w in enumerate(input_words):
        w["start"] = i * 2.0
        w["end"] = i * 2.0 + 1.0

    scenes = segment_into_scenes(input_words, max_duration=6.0, pause_threshold=0.8)
    output_words = []
    for s in scenes:
        output_words.extend(s["words"])
        assert s["end"] - s["start"] <= 6.0 or len(s["words"]) == 1
    
    assert input_words == output_words, "Words were duplicated or dropped!"
    
    print("\n--- P4 Comprehensive Tests Passed ---")

def test_scene_segmentation_and_keywords():
    mock_words = [
        {"word": "The", "start": 0.0, "end": 0.2},
        {"word": "ocean", "start": 0.2, "end": 0.5},
        {"word": "covers", "start": 0.5, "end": 0.8},
        {"word": "most", "start": 0.8, "end": 1.0},
        {"word": "of", "start": 1.0, "end": 1.1},
        {"word": "our", "start": 1.1, "end": 1.2},
        {"word": "planet.", "start": 1.2, "end": 1.5},
        {"word": "It", "start": 1.6, "end": 1.7},
        {"word": "is", "start": 1.7, "end": 1.8},
        {"word": "home", "start": 1.8, "end": 2.1},
        {"word": "to", "start": 2.1, "end": 2.2},
        {"word": "millions", "start": 2.2, "end": 2.6},
        {"word": "of", "start": 2.6, "end": 2.7},
        {"word": "species.", "start": 2.7, "end": 3.2},
    ]

    scenes = process_script_to_scenes(mock_words)
    assert len(scenes) == 2
