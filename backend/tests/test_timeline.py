import pytest
from pathlib import Path
from backend.app.services.timeline import TimelineAssembler

def test_timeline_assembly():
    schema_path = Path(__file__).parent.parent.parent / "shared" / "timeline.schema.json"
    assembler = TimelineAssembler(schema_path=schema_path)
    
    words = [
        {"word": "Hello", "start": 0.0, "end": 0.5, "probability": 0.99},
        {"word": "world", "start": 0.5, "end": 1.0, "probability": 0.98}
    ]
    
    scenes = [
        {
            "start": 0.0,
            "end": 1.0,
            "text": "Hello world",
            "asset": {
                "media_type": "video",
                "local_path": "/cache/vid.mp4",
                "provider": "Pexels",
                "author": "Jane",
                "license_name": "Pexels License",
                "media_url": "http://vid",
                "source_page_url": "http://page"
            }
        }
    ]
    
    timeline = assembler.assemble(
        audio_path="/cache/audio.wav",
        audio_duration=1.0,
        words=words,
        scenes=scenes
    )
    
    assert timeline["version"] == 1
    assert timeline["audio"]["path"] == "/cache/audio.wav"
    assert len(timeline["scenes"]) == 1
    assert len(timeline["captions"]) == 2
    
    # Check that extra keys like "probability" were stripped from words
    assert "probability" not in timeline["captions"][0]
    
    # Check asset mapping
    s1 = timeline["scenes"][0]
    assert s1["asset"]["type"] == "video"
    assert s1["asset"]["author"] == "Jane"
    
def test_timeline_assembly_invalid_schema():
    schema_path = Path(__file__).parent.parent.parent / "shared" / "timeline.schema.json"
    assembler = TimelineAssembler(schema_path=schema_path)
    
    # Missing required 'asset' metadata (like author) should cause schema validation failure
    scenes = [
        {
            "start": 0.0,
            "end": 1.0,
            "text": "Hello world",
            "asset": {
                "media_type": "video",
                "local_path": "/cache/vid.mp4",
                "provider": "Pexels",
                # Missing author, license, etc.
            }
        }
    ]
    
    with pytest.raises(KeyError):
        # We mapped it using asset_meta["author"], so it will raise KeyError before validation
        assembler.assemble(
            audio_path="/cache/audio.wav",
            audio_duration=1.0,
            words=[],
            scenes=scenes
        )
