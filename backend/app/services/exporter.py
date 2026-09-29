import json
import shutil
import subprocess
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


def process_asset(in_path: Path, out_path: Path, is_video: bool, width: int, height: int, fps: float, dur: float):
    cmd = ["ffmpeg", "-y"]
    if is_video:
        cmd.extend(["-stream_loop", "-1", "-i", str(in_path)])
    else:
        cmd.extend(["-loop", "1", "-i", str(in_path)])
        
    cmd.extend(["-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r={fps}"])
    
    # Scale and pad
    filter_str = f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease[vid];[1:v][vid]overlay=(W-w)/2:(H-h)/2"
    cmd.extend(["-filter_complex", filter_str])
    
    cmd.extend(["-t", str(dur), "-r", str(fps), "-c:v", "libx264", "-an", "-pix_fmt", "yuv420p", str(out_path)])
    
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def generate_filler(out_path: Path, width: int, height: int, fps: float, dur: float):
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c=black:s={width}x{height}:r={fps}",
        "-t", str(dur), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out_path)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build_otio_timeline(timeline: dict, manifest: list, audio_name: str, fps: float = 30.0) -> otio.schema.Timeline:
    otio_tl = otio.schema.Timeline("Exported Timeline")
    otio_tl.global_start_time = RationalTime(0, fps)
    
    video_track = otio.schema.Track("Video", kind=otio.schema.TrackKind.Video)
    audio_track = otio.schema.Track("Audio", kind=otio.schema.TrackKind.Audio)
    otio_tl.tracks.append(video_track)
    otio_tl.tracks.append(audio_track)
    
    for scene in manifest:
        dur_sec = scene.get("duration", 0.0)
        
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

    audio_dur = timeline.get("audio", {}).get("duration", 0.0)
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
    
    width = timeline.get("resolution", {}).get("width", 1080)
    height = timeline.get("resolution", {}).get("height", 1920)
    fps = timeline.get("resolution", {}).get("fps", 30.0)
    audio_dur = timeline.get("audio", {}).get("duration", 0.0)
    
    scenes = timeline.get("scenes", [])
    for i, scene in enumerate(scenes):
        idx = i + 1
        
        start_i = 0.0 if i == 0 else scene.get("start", 0.0)
        end_i = scenes[i+1].get("start", audio_dur) if i + 1 < len(scenes) else audio_dur
        dur_i = end_i - start_i
        
        # Guard against zero or negative duration just in case
        if dur_i <= 0:
            dur_i = 0.1
        
        asset = scene.get("asset")
        clip_dest = clips_dir / f"{idx:02d}.mp4"
        
        try:
            if asset and asset.get("path") and Path(asset["path"]).exists():
                is_video = asset.get("type", "video") == "video"
                process_asset(Path(asset["path"]), clip_dest, is_video, width, height, fps, dur_i)
            else:
                generate_filler(clip_dest, width, height, fps, dur_i)
        except Exception as e:
            logger.warning(f"Failed to process clip {idx}: {e}. Generating filler.")
            try:
                generate_filler(clip_dest, width, height, fps, dur_i)
            except Exception:
                pass
            
        manifest.append({
            "index": idx,
            "start": start_i,
            "duration": dur_i,
            "file": clip_dest.name if clip_dest.exists() else None,
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
            "3. Drop clips 01..NN onto the video timeline IN ORDER.\n"
            "   (They are pre-cut to match the narration exactly, so they stay in sync automatically).\n"
            "4. Go to Text -> Local Captions -> Import 'captions.srt'.\n"
        )
    else:
        readme_text += f"Target: {target.capitalize()}\n"
        readme_text += f"Generated timeline files: {', '.join(generated_timelines) if generated_timelines else 'None'}\n\n"
        readme_text += (
            "To assemble your video:\n"
            "1. Import the generated timeline file (e.g., project.fcpxml or timeline.edl).\n"
            "   Note: You may need to 'Relink Media' if your editor requires absolute paths. Point it to the clips/ and audio/ folders in this directory.\n"
            "   The clips are pre-cut to be perfectly contiguous.\n"
            "2. Import 'captions.srt' onto your timeline as a subtitle track.\n"
        )

    with open(job_export_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_text)
        
    zip_base = str(exports_dir / job_id)
    shutil.make_archive(zip_base, 'zip', job_export_dir)
    
    return exports_dir / f"{job_id}.zip"
