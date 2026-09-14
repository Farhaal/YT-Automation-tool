from backend.app.services.nlp import process_script_to_scenes, segment_into_scenes


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
    
    # 6. Final punctuation word pushing over max_duration
    words_final_punct = [{"word": f"w{i}", "start": float(i), "end": float(i) + 0.5} for i in range(4)]
    words_final_punct.append({"word": "w4.", "start": 4.0, "end": 4.5})
    # Total duration is 4.5s. Let's set max_duration=4.0
    scenes_fp = segment_into_scenes(words_final_punct, max_duration=4.0)
    # w0 to w3 = 3.5s (valid). Adding w4. makes it 4.5s (>4.0s).
    # Should split before w4.. Then w4. is a sentence end, so it emits.
    assert len(scenes_fp) == 2
    assert scenes_fp[0]["text"] == "w0 w1 w2 w3"
    assert scenes_fp[1]["text"] == "w4."
    
    # 7. Early comma + long remainder
    words_comma = [{"word": "Hi,", "start": 0.0, "end": 0.5}]
    words_comma += [{"word": f"w{i}", "start": float(i+1), "end": float(i+1)+0.5} for i in range(5)]
    # w0(0-0.5), w1(1-1.5), w2(2-2.5), w3(3-3.5), w4(4-4.5), w5(5-5.5)
    # Total time 5.5s. If max_duration=4.0:
    # Adding w4 makes end=4.5, start=0.0 -> duration 4.5 > 4.0.
    # Soft boundary at Hi,. Splits Hi,. Remainder is w1 w2 w3 w4.
    # Remainder duration: 4.5 - 1.0 = 3.5 <= 4.0. Loop ends.
    # Next, add w5 (end 5.5). Remainder duration: 5.5 - 1.0 = 4.5 > 4.0.
    # No soft boundary in remainder. Splits before w5.
    scenes_comma = segment_into_scenes(words_comma, max_duration=4.0)
    assert len(scenes_comma) == 3
    assert scenes_comma[0]["text"] == "Hi,"
    assert scenes_comma[1]["text"] == "w0 w1 w2 w3"
    assert scenes_comma[2]["text"] == "w4"
    
    for s in scenes_comma:
        assert s["end"] - s["start"] <= 4.0

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
    
    scene_1 = scenes[0]
    assert scene_1["text"] == "The ocean covers most of our planet."
    assert 1 <= len(scene_1["queries"]) <= 3
    assert all(len(q.strip()) > 0 for q in scene_1["queries"])
    
    scene_2 = scenes[1]
    assert scene_2["text"] == "It is home to millions of species."
    assert 1 <= len(scene_2["queries"]) <= 3
    assert all(len(q.strip()) > 0 for q in scene_2["queries"])
