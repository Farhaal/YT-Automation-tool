from fastapi.testclient import TestClient
from backend.app.main import app
import os
from pathlib import Path

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_generate_stub():
    response = client.post("/generate", json={"text": "Hello world"})
    assert response.status_code == 200
    assert "job_id" in response.json()
    assert response.json()["status"] == "queued"

def test_transcribe():
    # Use the tiny test audio generated
    sample_path = Path(__file__).resolve().parents[2] / "samples" / "test_audio.wav"
    assert sample_path.exists(), "test_audio.wav not found in samples/"
    
    with open(sample_path, "rb") as f:
        response = client.post("/transcribe", files={"audio_file": ("test_audio.wav", f, "audio/wav")})
    
    assert response.status_code == 200
    data = response.json()
    assert "segments" in data
    assert "words" in data
    assert len(data["words"]) > 0
    
    print("\n--- Transcription Sync Test ---")
    for word_obj in data["words"][:10]:
        print(f"[{word_obj['start']:.2f}s - {word_obj['end']:.2f}s] {word_obj['word']}")
    print("-------------------------------")

def test_synthesize():
    text = "This is a synthesized test sentence."
    response = client.post("/synthesize", json={"text": text})
    
    assert response.status_code == 200
    data = response.json()
    assert "audio_path" in data
    assert "transcription" in data
    
    audio_path = Path(data["audio_path"])
    assert audio_path.exists(), "Audio file was not created"
    assert os.path.getsize(audio_path) > 1024, "Audio file is suspiciously small or empty"
    
    words = data["transcription"]["words"]
    assert len(words) > 0, "No words returned from transcription"
    
    # Check timings are ordered and valid
    for i in range(len(words)):
        assert words[i]["start"] <= words[i]["end"], "Word end is before word start"
        if i > 0:
            assert words[i]["start"] >= words[i-1]["start"], "Word starts are not monotonically increasing"
            
    # Normalize input and output words for comparison
    import re
    def normalize(text_val):
        return re.sub(r'[^\w\s]', '', text_val).lower().strip()
        
    input_normalized_words = normalize(text).split()
    output_normalized_words = [normalize(w["word"]) for w in words]
    
    # A substantial match is expected, allowing for TTS engine mispronunciations or transcriber differences
    # E.g. we expect at least 3 matching words in this short sentence
    matches = sum(1 for w in input_normalized_words if w in output_normalized_words)
    assert matches >= len(input_normalized_words) // 2, f"Transcription heavily mismatched TTS input: {output_normalized_words}"
    
    print("\n--- P3 TTS Test Output (Requires manual listening check for actual sync accuracy) ---")
    for word_obj in words[:10]:
        print(f"[{word_obj['start']:.2f}s - {word_obj['end']:.2f}s] {word_obj['word']}")
    print("-------------------------------------------------------------------------------------")
