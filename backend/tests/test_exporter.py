import json
import shutil
import zipfile
import subprocess
from pathlib import Path
import pytest
import opentimelineio as otio

from backend.app.services.exporter import export_project, build_otio_timeline

def get_video_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
    return float(result.stdout.strip())

@pytest.fixture
def mock_timeline_env(tmp_path):
    audio_file = tmp_path / "dummy_audio.wav"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "aevalsrc=0", "-t", "10", str(audio_file)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    scene1_file = tmp_path / "scene1.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:s=320x240:r=30", "-t", "1", "-c:v", "libx264", str(scene1_file)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    scene2_file = tmp_path / "scene2.jpg"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x240", "-frames:v", "1", str(scene2_file)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    timeline_data = {
        "resolution": {"width": 320, "height": 240, "fps": 30},
        "audio": {"duration": 10.0, "path": str(audio_file)},
        "scenes": [
            {
                "id": "s1",
                "start": 1.0, 
                "end": 3.0,
                "text": "First scene",
                "asset": {"path": str(scene1_file), "source": "test", "type": "video"}
            },
            {
                "id": "s2",
                "start": 4.0, 
                "end": 6.0,
                "text": "Second scene",
                "asset": {"path": str(scene2_file), "source": "test", "type": "image"}
            },
            {
                "id": "s3",
                "start": 8.0,
                "end": 9.0,
                "text": "Third scene",
                "asset": None
            }
        ],
        "captions": []
    }
    
    timeline_path = tmp_path / "timeline.json"
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(timeline_data, f)
        
    return timeline_path, tmp_path

def test_export_precut_durations(mock_timeline_env, monkeypatch):
    timeline_path, tmp_path = mock_timeline_env
    from backend.app.core import paths
    import backend.app.services.exporter as exporter
    monkeypatch.setattr(paths, "DATA", tmp_path)
    monkeypatch.setattr(exporter, "DATA", tmp_path)

    job_id = "test_precut_job"
    zip_path = export_project(timeline_path, job_id, "capcut")
    
    assert zip_path.exists()
    
    extract_dir = tmp_path / "extracted_capcut"
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    clip1 = extract_dir / "clips" / "01.mp4"
    clip2 = extract_dir / "clips" / "02.mp4"
    clip3 = extract_dir / "clips" / "03.mp4"
    
    assert clip1.exists()
    assert clip2.exists()
    assert clip3.exists()
    
    d1 = get_video_duration(clip1)
    d2 = get_video_duration(clip2)
    d3 = get_video_duration(clip3)
    
    assert abs(d1 - 4.0) < 0.1
    assert abs(d2 - 4.0) < 0.1
    assert abs(d3 - 2.0) < 0.1
    
    assert abs((d1 + d2 + d3) - 10.0) < 0.1

def test_otio_timeline_structure_contiguous():
    manifest = [
        {"index": 1, "start": 0.0, "duration": 4.0, "file": "01.mp4"},
        {"index": 2, "start": 4.0, "duration": 6.0, "file": "02.mp4"},
    ]
    timeline = {"audio": {"duration": 10.0}}
    otio_tl = build_otio_timeline(timeline, manifest, "narration.wav", 30.0)
    
    video_track = otio_tl.tracks[0]
    
    assert len(video_track) == 2
    assert isinstance(video_track[0], otio.schema.Clip)
    assert video_track[0].source_range.duration.value == 120
    
    assert isinstance(video_track[1], otio.schema.Clip)
    assert video_track[1].source_range.duration.value == 180
