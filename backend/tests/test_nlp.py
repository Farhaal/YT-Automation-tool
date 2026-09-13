from backend.app.services.nlp import segment_into_scenes, extract_keywords, process_script_to_scenes

def test_scene_segmentation_and_keywords():
    # Mock data representing the output from faster-whisper
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
    
    assert len(scenes) == 2, f"Expected 2 scenes, got {len(scenes)}"
    
    scene_1 = scenes[0]
    assert scene_1["text"] == "The ocean covers most of our planet."
    assert scene_1["start"] == 0.0
    assert scene_1["end"] == 1.5
    assert len(scene_1["queries"]) > 0
    assert len(scene_1["queries"]) <= 3
    
    scene_2 = scenes[1]
    assert scene_2["text"] == "It is home to millions of species."
    assert scene_2["start"] == 1.6
    assert scene_2["end"] == 3.2
    assert len(scene_2["queries"]) > 0
    assert len(scene_2["queries"]) <= 3

    print("\n--- Scene Segmentation Test ---")
    for i, scene in enumerate(scenes):
        print(f"Scene {i+1}: [{scene['start']:.2f}s - {scene['end']:.2f}s]")
        print(f"  Text: {scene['text']}")
        print(f"  Queries: {scene['queries']}")
    print("-------------------------------")
