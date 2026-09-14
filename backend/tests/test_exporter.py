import json
import shutil
import zipfile
from pathlib import Path
import pytest
import opentimelineio as otio

from backend.app.services.exporter import export_project, build_otio_timeline

@pytest.fixture
def mock_timeline_env(tmp_path):
    # Setup dummy source files
    audio_file = tmp_path / "dummy_audio.wav"
    audio_file.write_text("audio data")
    
    scene1_file = tmp_path / "scene1.mp4"
    scene1_file.write_text("video 1 data")
    
    scene2_file = tmp_path / "scene2.mp4"
    scene2_file.write_text("video 2 data")

    timeline_data = {
        "resolution": {"width": 1920, "height": 1080, "fps": 30},
        "audio": {"duration": 10.0, "path": str(audio_file)},
        "scenes": [
            {
                "id": "s1",
                "start": 0.0,
                "end": 4.0,
                "text": "Hello world",
                "asset": {"path": str(scene1_file), "source": "test", "type": "video"}
            },
            {
                "id": "s2",
                "start": 5.0, # Note the gap 4.0 to 5.0
                "end": 10.0,
                "text": "Second scene",
                "asset": {"path": str(scene2_file), "source": "test", "type": "video"}
            }
        ],
        "captions": [
            {"word": "Hello", "start": 0.0, "end": 1.0},
            {"word": "world.", "start": 1.0, "end": 2.0},
            {"word": "Second", "start": 5.0, "end": 6.0},
            {"word": "scene.", "start": 6.0, "end": 7.0},
        ]
    }
    
    timeline_path = tmp_path / "timeline.json"
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(timeline_data, f)
        
    return timeline_path, tmp_path

def test_export_capcut(mock_timeline_env, monkeypatch):
    timeline_path, tmp_path = mock_timeline_env
    # override DATA path to use tmp_path
    from backend.app.core import paths
    monkeypatch.setattr(paths, "DATA", tmp_path)
    import backend.app.services.exporter as exporter
    monkeypatch.setattr(exporter, "DATA", tmp_path)

    job_id = "test_capcut_job"
    original_size = timeline_path.stat().st_size
    
    zip_path = export_project(timeline_path, job_id, "capcut")
    
    assert zip_path.exists()
    assert timeline_path.stat().st_size == original_size  # Source unchanged
    
    # Extract and verify
    extract_dir = tmp_path / "extracted_capcut"
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    assert (extract_dir / "audio" / "narration.wav").exists()
    assert (extract_dir / "clips" / "01.mp4").exists()
    assert (extract_dir / "clips" / "02.mp4").exists()
    assert (extract_dir / "captions.srt").exists()
    assert (extract_dir / "manifest.json").exists()
    assert (extract_dir / "README.txt").exists()
    
    # Check no FCPXML/EDL
    assert not (extract_dir / "project.fcpxml").exists()
    assert not (extract_dir / "timeline.edl").exists()
    
    # Verify SRT
    srt = (extract_dir / "captions.srt").read_text(encoding="utf-8")
    assert "Hello world." in srt
    assert "00:00:00,000 --> 00:00:02,000" in srt
    
    # Verify README
    readme = (extract_dir / "README.txt").read_text(encoding="utf-8")
    assert "Target: CapCut" in readme

def test_export_resolve(mock_timeline_env, monkeypatch):
    timeline_path, tmp_path = mock_timeline_env
    from backend.app.core import paths
    monkeypatch.setattr(paths, "DATA", tmp_path)
    import backend.app.services.exporter as exporter
    monkeypatch.setattr(exporter, "DATA", tmp_path)

    job_id = "test_resolve_job"
    zip_path = export_project(timeline_path, job_id, "resolve")
    
    assert zip_path.exists()
    
    extract_dir = tmp_path / "extracted_resolve"
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    assert (extract_dir / "project.fcpxml").exists()
    assert (extract_dir / "timeline.edl").exists()
    
    readme = (extract_dir / "README.txt").read_text(encoding="utf-8")
    assert "Target: Resolve" in readme
    assert "project.fcpxml" in readme

def test_otio_timeline_structure():
    manifest = [
        {"index": 1, "start": 0.0, "end": 4.0, "file": "01.mp4"},
        {"index": 2, "start": 5.0, "end": 10.0, "file": "02.mp4"},
    ]
    timeline = {"audio": {"duration": 10.0}}
    otio_tl = build_otio_timeline(timeline, manifest, "narration.wav", 30.0)
    
    assert len(otio_tl.tracks) == 2
    video_track = otio_tl.tracks[0]
    audio_track = otio_tl.tracks[1]
    
    # Video track should have: Clip1, Gap, Clip2
    assert len(video_track) == 3
    assert isinstance(video_track[0], otio.schema.Clip)
    assert video_track[0].name == "Scene 1"
    assert video_track[0].source_range.duration.value == 120 # 4.0s @ 30fps
    
    assert isinstance(video_track[1], otio.schema.Gap)
    assert video_track[1].source_range.duration.value == 30 # 1.0s gap @ 30fps
    
    assert isinstance(video_track[2], otio.schema.Clip)
    assert video_track[2].name == "Scene 2"
    assert video_track[2].source_range.duration.value == 150 # 5.0s @ 30fps
    
    assert len(audio_track) == 1
    assert audio_track[0].name == "Narration"
    assert audio_track[0].source_range.duration.value == 300 # 10.0s @ 30fps
