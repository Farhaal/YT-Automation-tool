import json
import zipfile

from backend.app.services.exporter import export_project, format_srt_time


def test_format_srt_time():
    assert format_srt_time(0.0) == "00:00:00,000"
    assert format_srt_time(1.5) == "00:00:01,500"
    assert format_srt_time(3661.123) == "01:01:01,123"


def test_export_project(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.services.exporter.DATA", tmp_path)
    
    # Create fake media
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    audio = media_dir / "audio.wav"
    audio.write_text("audio data")
    vid = media_dir / "vid.mp4"
    vid.write_text("vid data")
    
    timeline = {
        "audio": {"path": str(audio), "duration": 2.0},
        "scenes": [
            {
                "start": 0.0,
                "end": 1.0,
                "text": "Hello world",
                "asset": {"path": str(vid), "source": "mock"}
            },
            {
                "start": 1.0,
                "end": 2.0,
                "text": "No asset scene",
                "asset": None
            }
        ],
        "captions": [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "world.", "start": 0.5, "end": 1.0},
            {"word": "Wait", "start": 1.0, "end": 1.5}
        ]
    }
    
    tl_path = tmp_path / "timeline.json"
    tl_path.write_text(json.dumps(timeline))
    
    job_id = "test_job_123"
    zip_path = export_project(tl_path, job_id)
    
    assert zip_path.exists()
    assert zip_path.suffix == ".zip"
    
    # Unzip and verify
    extract_dir = tmp_path / "extracted"
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    assert (extract_dir / "audio" / "narration.wav").exists()
    assert (extract_dir / "clips" / "01.mp4").exists()
    assert not (extract_dir / "clips" / "02.mp4").exists()  # no asset
    
    srt_content = (extract_dir / "captions.srt").read_text()
    assert "00:00:00,000 --> 00:00:01,000" in srt_content
    assert "Hello world." in srt_content
    
    manifest = json.loads((extract_dir / "manifest.json").read_text())
    assert len(manifest) == 2
    assert manifest[0]["file"] == "01.mp4"
    assert manifest[1]["file"] is None
    
    assert (extract_dir / "README.txt").exists()
    assert (extract_dir / "project.fcpxml").exists()
    
    # Check original timeline remains untouched
    assert json.loads(tl_path.read_text()) == timeline
