import json
import shutil
from pathlib import Path

from backend.app.core.logger import logger
from backend.app.core.paths import DATA


def format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt_lines(captions: list) -> str:
    grouped_lines = []
    current_line = []
    for w in captions:
        current_line.append(w)
        is_end = w["word"].endswith(('.', '?', '!', '\n'))
        if len(current_line) >= 6 or is_end:
            grouped_lines.append(current_line)
            current_line = []
    if current_line:
        grouped_lines.append(current_line)
    
    srt_content = ""
    for i, line in enumerate(grouped_lines, 1):
        start_time = format_srt_time(line[0]["start"])
        end_time = format_srt_time(line[-1]["end"])
        text = " ".join(w["word"] for w in line)
        srt_content += f"{i}\n{start_time} --> {end_time}\n{text}\n\n"
    return srt_content


def generate_fcpxml(timeline: dict, manifest: list, audio_name: str) -> str:
    """Best effort minimal FCPXML 1.9 generation"""
    fps = timeline.get("resolution", {}).get("fps", 30)
    width = timeline.get("resolution", {}).get("width", 1080)
    height = timeline.get("resolution", {}).get("height", 1920)
    audio_dur = timeline.get("audio", {}).get("duration", 0)
    
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.9">
    <resources>
        <format id="r1" width="{width}" height="{height}" frameDuration="1/{fps}s"/>
    </resources>
    <library>
        <event name="OpenReel Export">
            <project name="Generated Video">
                <sequence format="r1" duration="{audio_dur}s" tcStart="0s" tcFormat="NDF">
                    <spine>
"""
    xml += f"""                        <clip name="Narration" duration="{audio_dur}s">
"""
    for idx, scene in enumerate(manifest):
        if scene["file"]:
            start = scene["start"]
            dur = scene["end"] - scene["start"]
            xml += f"""                            <video offset="{start}s" name="Scene {scene['index']}" duration="{dur}s" start="0s"/>
"""  # noqa: E501
    xml += """                        </clip>
                    </spine>
                </sequence>
            </project>
        </event>
    </library>
</fcpxml>"""
    return xml


def export_project(timeline_path: Path, job_id: str) -> Path:
    exports_dir = DATA / "exports"
    job_export_dir = exports_dir / job_id
    
    if job_export_dir.exists():
        shutil.rmtree(job_export_dir)
    job_export_dir.mkdir(parents=True)
    
    with open(timeline_path, "r", encoding="utf-8") as f:
        timeline = json.load(f)
        
    audio_path = timeline.get("audio", {}).get("path")
    audio_dest = None
    audio_dir = job_export_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    if audio_path and Path(audio_path).exists():
        ext = Path(audio_path).suffix
        audio_dest = audio_dir / f"narration{ext}"
        shutil.copy2(audio_path, audio_dest)
        
    clips_dir = job_export_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    
    scenes = timeline.get("scenes", [])
    for i, scene in enumerate(scenes):
        idx = i + 1
        asset = scene.get("asset")
        clip_dest = None
        if asset and asset.get("path") and Path(asset["path"]).exists():
            ext = Path(asset["path"]).suffix
            clip_dest = clips_dir / f"{idx:02d}{ext}"
            shutil.copy2(asset["path"], clip_dest)
            
        backup = scene.get("backup_asset")
        if backup and backup.get("path") and Path(backup["path"]).exists():
            b_ext = Path(backup["path"]).suffix
            shutil.copy2(backup["path"], clips_dir / f"{idx:02d}_backup{b_ext}")
            
        manifest.append({
            "index": idx,
            "start": scene.get("start"),
            "end": scene.get("end"),
            "file": clip_dest.name if clip_dest else None,
            "caption_text": scene.get("text"),
            "source": asset.get("source") if asset else None,
            "license": asset.get("license") if asset else None,
            "attribution": asset.get("author") if asset else None
        })
        
    srt_content = build_srt_lines(timeline.get("captions", []))
    with open(job_export_dir / "captions.srt", "w", encoding="utf-8") as f:
        f.write(srt_content)
        
    with open(job_export_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    readme_text = (
        "Exported Project Instructions\n"
        "=============================\n\n"
        "CapCut:\n"
        "1. Import the clips/ folder and audio/narration into your media bin.\n"
        "2. Place them on the timeline.\n"
        "3. Import Captions -> select captions.srt.\n\n"
        "DaVinci Resolve / Premiere Pro:\n"
        "1. File -> Import -> project.fcpxml.\n"
    )
    with open(job_export_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_text)
        
    try:
        audio_name = audio_dest.name if audio_dest else "narration.wav"
        fcpxml_str = generate_fcpxml(timeline, manifest, audio_name)
        with open(job_export_dir / "project.fcpxml", "w", encoding="utf-8") as f:
            f.write(fcpxml_str)
    except Exception as e:
        logger.warning(f"FCPXML generation failed: {e}")
        
    zip_base = str(exports_dir / job_id)
    shutil.make_archive(zip_base, 'zip', job_export_dir)
    
    return exports_dir / f"{job_id}.zip"
