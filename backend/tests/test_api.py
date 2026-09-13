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
    
    # Verify the audio file was actually created
    assert Path(data["audio_path"]).exists()
    
    # Verify the transcription has words
    words = data["transcription"]["words"]
    assert len(words) > 0
    
    print("\n--- TTS + Alignment Sync Test ---")
    for word_obj in words[:10]:
        print(f"[{word_obj['start']:.2f}s - {word_obj['end']:.2f}s] {word_obj['word']}")
    print("---------------------------------")
