import json
import subprocess
from pathlib import Path
from moviepy import VideoFileClip, ImageClip, ColorClip, TextClip, CompositeVideoClip, AudioFileClip, vfx
from backend.app.core.paths import DATA
from backend.app.core.logger import logger

def has_nvenc() -> bool:
    try:
        res = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
        return "h264_nvenc" in res.stdout
    except Exception:
        return False

def render_timeline(timeline_path: Path, draft_mode: bool = False) -> Path:
    with open(timeline_path, "r", encoding="utf-8") as f:
        timeline = json.load(f)
        
    audio_path = timeline["audio"]["path"]
    audio_dur = timeline["audio"]["duration"]
    timeline_audio = AudioFileClip(audio_path)
    
    W = timeline["resolution"]["width"]
    H = timeline["resolution"]["height"]
    fps = timeline["resolution"]["fps"]
    
    if draft_mode:
        W, H = W // 2, H // 2
        fps = min(fps, 15)
        
    import sys
    import os
    if os.name == 'nt':
        font_path = "C:/Windows/Fonts/arial.ttf"
    elif sys.platform == 'darwin':
        font_path = "/Library/Fonts/Arial.ttf"
    else:
        font_path = "DejaVuSans" # Linux default
        
    if not Path(font_path).exists() and os.name == 'nt':
        font_path = "Arial" # Fallback if specific file missing
    
    clips = []
    
    scenes = timeline.get("scenes", [])
    for i, scene in enumerate(scenes):
        start = scene["start"]
        end = scene["end"]
        dur = end - start
        
        asset = scene.get("asset")
        if asset is None:
            bg = ColorClip(size=(W, H), color=(40, 40, 40)).with_duration(dur)
            # Use TextClip carefully for scene text fallback
            txt = TextClip(font=font_path, text=scene["text"], font_size=int(H*0.05), color="white").with_position("center").with_duration(dur)
            clip = CompositeVideoClip([bg, txt], size=(W, H)).with_duration(dur)
        else:
            atype = asset["type"]
            apath = asset["path"]
            if atype == "video":
                vclip = VideoFileClip(apath).without_audio()
                if vclip.duration < dur:
                    vclip = vclip.with_effects([vfx.Loop(duration=dur)])
                clip = vclip.subclipped(0, dur)
                scale = max(W / clip.w, H / clip.h)
                clip = clip.resized(scale)
            else:
                clip = ImageClip(apath).with_duration(dur)
                scale = max(W / clip.w, H / clip.h)
                clip = clip.resized(scale).with_effects([vfx.Resize(lambda t: 1.0 + 0.05 * (t / dur))])
                
        # Composite into a WxH canvas to crop overlaps
        clip = CompositeVideoClip([clip.with_position("center")], size=(W, H)).with_duration(dur).with_start(start)
        
        if i > 0 and "transition_out" in scenes[i-1]:
            tdur = scenes[i-1]["transition_out"]["duration"]
            clip = clip.with_effects([vfx.CrossFadeIn(tdur)])
            
        if "transition_out" in scene:
            tdur = scene["transition_out"]["duration"]
            clip = clip.with_effects([vfx.CrossFadeOut(tdur)])
            clip = clip.with_duration(dur + tdur)
            
        clips.append(clip)
        
    for w in timeline.get("captions", []):
        try:
            txt = TextClip(font=font_path, text=w["word"], font_size=int(H*0.06), color="yellow", stroke_color="black", stroke_width=2)
            txt = txt.with_start(w["start"]).with_end(w["end"]).with_position(("center", int(H*0.75)))
            clips.append(txt)
        except Exception as e:
            logger.warning(f"Failed to render caption word {w['word']}: {e}")

    for p in timeline.get("popups", []):
        try:
            if p["type"] == "image":
                pop = ImageClip(p["path"]).with_duration(p["duration"]).with_start(p["at"])
                pop = pop.resized(height=int(H*0.2))
                pos = p.get("position", "center")
                if pos == "top-right":
                    pop = pop.with_position(("right", "top"))
                else:
                    pop = pop.with_position("center")
                clips.append(pop)
        except Exception as e:
            logger.warning(f"Failed to render popup {p}: {e}")
            
    final_video = CompositeVideoClip(clips, size=(W, H)).with_audio(timeline_audio)
    final_video = final_video.with_duration(audio_dur)
    
    renders_dir = DATA / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)
    
    out_name = f"render_{'draft' if draft_mode else 'final'}.mp4"
    out_path = renders_dir / out_name
    
    codec = "h264_nvenc" if has_nvenc() else "libx264"
    logger.info(f"Rendering {out_path} with codec {codec} at {W}x{H} {fps}fps")
    
    final_video.write_videofile(
        str(out_path),
        fps=fps,
        codec=codec,
        audio_codec="aac",
        threads=4,
        logger=None # Suppress huge logs in test output
    )
    
    return out_path
