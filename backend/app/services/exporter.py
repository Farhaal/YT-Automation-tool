import json
import shutil
from pathlib import Path
import opentimelineio as otio
from opentimelineio.opentime import RationalTime, TimeRange

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

def build_otio_timeline(timeline: dict, manifest: list, audio_name: str, fps: float = 30.0) -> otio.schema.Timeline:
    otio_tl = otio.schema.Timeline("Exported Timeline")
    otio_tl.global_start_time = RationalTime(0, fps)
    
    video_track = otio.schema.Track("Video", kind=otio.schema.TrackKind.Video)
    audio_track = otio.schema.Track("Audio", kind=otio.schema.TrackKind.Audio)
    otio_tl.tracks.append(video_track)
    otio_tl.tracks.append(audio_track)
    
    current_time = 0.0
    for scene in manifest:
        start_sec = scene.get("start", 0)
        end_sec = scene.get("end", 0)
        dur_sec = end_sec - start_sec
        
        if start_sec > current_time:
            gap_dur = start_sec - current_time
            video_track.append(otio.schema.Gap(
                source_range=TimeRange(
                    start_time=RationalTime(0, fps),
                    duration=RationalTime(gap_dur * fps, fps)
                )
            ))
        
        if scene["file"]:
            clip_path = f"clips/{scene['file']}"
            clip = otio.schema.Clip(
                name=f"Scene {scene['index']}",
                media_reference=otio.schema.ExternalReference(
                    target_url=clip_path,
                    available_range=TimeRange(
                        start_time=RationalTime(0, fps),
                        duration=RationalTime(dur_sec * fps, fps)
                    )
                ),
                source_range=TimeRange(
                    start_time=RationalTime(0, fps),
                    duration=RationalTime(dur_sec * fps, fps)
                )
            )
            video_track.append(clip)
        
        current_time = end_sec

    audio_dur = timeline.get("audio", {}).get("duration", 0)
    if audio_name and audio_dur > 0:
        audio_clip = otio.schema.Clip(
            name="Narration",
            media_reference=otio.schema.ExternalReference(
                target_url=f"audio/{audio_name}",
                available_range=TimeRange(
                    start_time=RationalTime(0, fps),
                    duration=RationalTime(audio_dur * fps, fps)
                )
            ),
            source_range=TimeRange(
                start_time=RationalTime(0, fps),
                duration=RationalTime(audio_dur * fps, fps)
            )
        )
        audio_track.append(audio_clip)

    return otio_tl

def export_project(timeline_path: Path, job_id: str, target: str = "resolve") -> Path:
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
        
    generated_timelines = []
    
    if target in ("resolve", "premiere"):
        fps = timeline.get("resolution", {}).get("fps", 30)
        audio_name = audio_dest.name if audio_dest else "narration.wav"
        
        otio_tl = build_otio_timeline(timeline, manifest, audio_name, float(fps))
        
        try:
            fcpxml_path = str(job_export_dir / "project.fcpxml")
            otio.adapters.write_to_file(otio_tl, fcpxml_path, adapter_name="fcp_xml")
            generated_timelines.append("project.fcpxml")
        except Exception as e:
            logger.warning(f"OTIO FCPXML generation failed: {e}")
            
        try:
            edl_path = str(job_export_dir / "timeline.edl")
            otio.adapters.write_to_file(otio_tl, edl_path, adapter_name="cmx_3600")
            generated_timelines.append("timeline.edl")
        except Exception as e:
            logger.warning(f"OTIO EDL generation failed: {e}")

    # Write README
    readme_text = "OpenReel Exported Project Instructions\n"
    readme_text += "======================================\n\n"
    
    if target == "capcut":
        readme_text += (
            "Target: CapCut\n"
            "CapCut does not support FCPXML/EDL import. To assemble your video:\n"
            "1. Import the 'clips/' folder and 'audio/narration' into your media bin.\n"
            "2. Place the audio on the timeline.\n"
            "3. Place the clips in order (they are numbered sequentially).\n"
            "4. Go to Text -> Local Captions -> Import 'captions.srt'.\n"
        )
    else:
        readme_text += f"Target: {target.capitalize()}\n"
        readme_text += f"Generated timeline files: {', '.join(generated_timelines) if generated_timelines else 'None'}\n\n"
        readme_text += (
            "To assemble your video:\n"
            "1. Import the generated timeline file (e.g., project.fcpxml or timeline.edl).\n"
            "   Note: You may need to 'Relink Media' if your editor requires absolute paths. Point it to the clips/ and audio/ folders in this directory.\n"
            "2. Import 'captions.srt' onto your timeline as a subtitle track.\n"
        )

    with open(job_export_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_text)
        
    zip_base = str(exports_dir / job_id)
    shutil.make_archive(zip_base, 'zip', job_export_dir)
    
    return exports_dir / f"{job_id}.zip"
