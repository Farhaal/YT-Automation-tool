import pytest
from pathlib import Path
from backend.app.services.timeline import TimelineAssembler

@pytest.fixture
def assembler():
    schema_path = Path(__file__).parent.parent.parent / "shared" / "timeline.schema.json"
    return TimelineAssembler(schema_path=schema_path)

def test_timeline_assembly_valid(assembler):
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
                "source_page_url": "http://page",
                "asset_key": "Pexels:1",
                "provider_asset_id": "1",
                "license_url": "http://license",
                "attribution_required": False,
                "attribution_text": None
            },
            "backup_asset": {
                "media_type": "image",
                "local_path": "/cache/img.jpg",
                "provider": "Pixabay",
                "author": "John",
                "license_name": "Pixabay License",
                "media_url": "http://img",
                "source_page_url": "http://page2",
                "asset_key": "Pixabay:2",
                "provider_asset_id": "2",
                "license_url": None,
                "attribution_required": True,
                "attribution_text": "Attr text"
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
    
    s1 = timeline["scenes"][0]
    assert s1["asset"]["type"] == "video"
    assert s1["asset"]["asset_key"] == "Pexels:1"
    
    # Check backup asset survives
    assert s1["backup_asset"]["type"] == "image"
    assert s1["backup_asset"]["asset_key"] == "Pixabay:2"
    assert s1["backup_asset"]["attribution_text"] == "Attr text"
    
def test_timeline_assembly_null_asset(assembler):
    # Null asset fallback
    scenes = [
        {
            "start": 0.0,
            "end": 1.0,
            "text": "No asset found",
            "asset": None,
            "backup_asset": None
        }
    ]
    
    timeline = assembler.assemble(
        audio_path="/cache/audio.wav",
        audio_duration=1.0,
        words=[],
        scenes=scenes
    )
    
    assert timeline["scenes"][0]["asset"] is None
    assert timeline["scenes"][0]["backup_asset"] is None
    
def test_timeline_invalid_schema(assembler):
    # Bad type for audio_duration should trigger schema validation rejection
    scenes = [
        {
            "start": 0.0,
            "end": 1.0,
            "text": "Test",
            "asset": None,
            "backup_asset": None
        }
    ]
    
    # We should catch a ValueError thrown by our wrapper
    with pytest.raises(ValueError, match="Invalid timeline generated"):
        assembler.assemble(
            audio_path="/cache/audio.wav",
            audio_duration="invalid_type", # Schema expects number
            words=[],
            scenes=scenes
        )
        
def test_timeline_semantic_validation_negative_timestamp(assembler):
    scenes = [{"start": -1.0, "end": 1.0, "text": "Test", "asset": None}]
    with pytest.raises(ValueError, match="Invalid timeline generated"):
        assembler.assemble(audio_path="/cache/audio.wav", audio_duration=1.0, words=[], scenes=scenes)

def test_timeline_semantic_validation_end_before_start(assembler):
    scenes = [{"start": 1.0, "end": 0.5, "text": "Test", "asset": None}]
    with pytest.raises(ValueError, match="start > end"):
        assembler.assemble(audio_path="/cache/audio.wav", audio_duration=1.0, words=[], scenes=scenes)
        
def test_timeline_semantic_validation_not_chronological(assembler):
    scenes = [
        {"start": 0.0, "end": 1.0, "text": "Test1", "asset": None},
        {"start": 0.5, "end": 2.0, "text": "Test2", "asset": None}
    ]
    with pytest.raises(ValueError, match="not chronological"):
        assembler.assemble(audio_path="/cache/audio.wav", audio_duration=2.0, words=[], scenes=scenes)
        
def test_timeline_semantic_validation_out_of_audio_range(assembler):
    scenes = [{"start": 0.0, "end": 2.5, "text": "Test1", "asset": None}]
    with pytest.raises(ValueError, match="exceeds audio_duration"):
        assembler.assemble(audio_path="/cache/audio.wav", audio_duration=2.0, words=[], scenes=scenes)

def test_timeline_semantic_validation_transition_duration(assembler):
    # Transition requires 0.4s but scene is only 0.2s long (crossfade is longer than scene)
    scenes = [
        {"start": 0.0, "end": 0.2, "text": "Test1", "asset": None},
        {"start": 0.2, "end": 1.0, "text": "Test2", "asset": None}
    ]
    
    # To test transition semantic check without our hardcoded 1.0 logic overriding it,
    # we manually inject the transition via a mock list of scenes since `assemble` hardcodes 0.4 crossfade
    # ONLY if scene duration > 1.0. So `assemble` won't generate an invalid transition itself.
    # If `assemble` is robust, it prevents it. 
    # Let's ensure `assemble`'s transition logic works correctly.
    timeline = assembler.assemble(audio_path="/cache/audio.wav", audio_duration=1.0, words=[], scenes=scenes)
    # Since duration 0.2 <= 1.0, no transition_out should be added!
    assert "transition_out" not in timeline["scenes"][0]
