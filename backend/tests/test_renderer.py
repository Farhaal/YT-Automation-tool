import json
import pytest
import subprocess
from pathlib import Path
from backend.app.services.renderer import render_timeline, has_nvenc
from backend.app.core.paths import DATA

def create_test_media(temp_dir: Path):
    from moviepy import ColorClip, AudioFileClip
    from moviepy.audio.AudioClip import AudioArrayClip
    import numpy as np

    # Audio (2 seconds)
    audio_data = np.zeros((40000, 2))  # 2 seconds of silence
    audio = AudioArrayClip(audio_data, fps=20000)
    audio_path = temp_dir / "test_audio.wav"
    audio.write_audiofile(str(audio_path), logger=None)

    # Video (1 second)
    vclip = ColorClip(size=(320, 240), color=(255, 0, 0)).with_duration(1.0)
    vid_path = temp_dir / "test_vid.mp4"
    vclip.write_videofile(str(vid_path), fps=10, logger=None)

    # Image (1 second)
    iclip = ColorClip(size=(320, 240), color=(0, 255, 0)).with_duration(1.0)
    img_path = temp_dir / "test_img.png"
    # MoviePy ColorClip doesn't have save_frame directly in older versions, let's just use PIL
    from PIL import Image
    im = Image.new("RGB", (320, 240), "green")
    im.save(img_path)
    
    # Popup image
    pop_path = temp_dir / "popup.png"
    im2 = Image.new("RGB", (100, 100), "blue")
    im2.save(pop_path)

    return {
        "audio": str(audio_path),
        "video": str(vid_path),
        "image": str(img_path),
        "popup": str(pop_path)
    }

def get_ffprobe_duration(filepath: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", str(filepath)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return float(res.stdout.strip())

def test_renderer_pipeline(tmp_path):
    media = create_test_media(tmp_path)
    
    timeline = {
        "version": 1,
        "resolution": {"width": 640, "height": 480, "fps": 15},
        "audio": {"path": media["audio"], "duration": 2.0},
        "scenes": [
            {
                "id": "s1",
                "start": 0.0,
                "end": 0.8,
                "text": "Scene 1",
                "asset": {
                    "type": "video",
                    "path": media["video"],
                    "source": "mock", "author": "mock", "license": "mock", "url": "mock", "asset_key": "mock:1", "provider_asset_id": "1"
                },
                "transition_out": {"type": "crossfade", "duration": 0.2}
            },
            {
                "id": "s2",
                "start": 0.8,
                "end": 1.5,
                "text": "Scene 2",
                "asset": {
                    "type": "image",
                    "path": media["image"],
                    "source": "mock", "author": "mock", "license": "mock", "url": "mock", "asset_key": "mock:2", "provider_asset_id": "2"
                }
            },
            {
                "id": "s3",
                "start": 1.5,
                "end": 2.0,
                "text": "Null fallback",
                "asset": None
            }
        ],
        "captions": [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "World", "start": 0.8, "end": 1.5}
        ],
        "popups": [
            {"at": 0.5, "duration": 1.0, "type": "image", "path": media["popup"], "position": "top-right"}
        ]
    }
    
    timeline_path = tmp_path / "timeline.json"
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(timeline, f)
        
    # Test Draft mode
    draft_path = render_timeline(timeline_path, draft_mode=True)
    assert draft_path.exists()
    assert draft_path.stat().st_size > 0
    draft_dur = get_ffprobe_duration(draft_path)
    print(f"Draft Render Output: {draft_path} | Duration: {draft_dur}")
    assert abs(draft_dur - 2.0) < 0.2
    
    # Test Final mode
    final_path = render_timeline(timeline_path, draft_mode=False)
    assert final_path.exists()
    assert final_path.stat().st_size > 0
    final_dur = get_ffprobe_duration(final_path)
    print(f"Final Render Output: {final_path} | Duration: {final_dur}")
    assert abs(final_dur - 2.0) < 0.2
    
    nvenc_avail = has_nvenc()
    print(f"NVENC Available: {nvenc_avail}")
    
def test_fallback_encoder_when_nvenc_false(tmp_path, monkeypatch):
    # Force has_nvenc to false
    import backend.app.services.renderer as r
    monkeypatch.setattr(r, "has_nvenc", lambda: False)
    
    media = create_test_media(tmp_path)
    timeline = {
        "version": 1,
        "resolution": {"width": 320, "height": 240, "fps": 10},
        "audio": {"path": media["audio"], "duration": 1.0},
        "scenes": [
            {"id": "s1", "start": 0.0, "end": 1.0, "text": "Fallback", "asset": None}
        ],
        "captions": []
    }
    timeline_path = tmp_path / "timeline.json"
    with open(timeline_path, "w") as f:
        json.dump(timeline, f)
        
    out_path = render_timeline(timeline_path)
    assert out_path.exists()
    assert abs(get_ffprobe_duration(out_path) - 1.0) < 0.2
