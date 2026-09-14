import json
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, ImageClip, TextClip, VideoFileClip, vfx

from backend.app.core.logger import logger
from backend.app.core.paths import DATA


def has_nvenc() -> bool:
    try:
        res = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
        return "h264_nvenc" in res.stdout
    except Exception:
        return False

def _get_font_path():
    import os
    import sys
    if os.name == 'nt': return "C:/Windows/Fonts/arial.ttf"  # noqa: E701
    elif sys.platform == 'darwin': return "/Library/Fonts/Arial.ttf"  # noqa: E701
    return "DejaVuSans"

def _run_render_pass(timeline: dict, codec: str, out_path: Path, draft_mode: bool):
    resources_to_close = []
    
    try:
        audio_path = timeline["audio"]["path"]
        audio_dur = timeline["audio"]["duration"]
        timeline_audio = AudioFileClip(audio_path)
        resources_to_close.append(timeline_audio)
        
        W = timeline["resolution"]["width"]
        H = timeline["resolution"]["height"]
        fps = timeline["resolution"]["fps"]
        
        if draft_mode:
            W, H = W // 2, H // 2
            fps = min(fps, 15)
            
        font_path = _get_font_path()
        import os
        if not Path(font_path).exists() and os.name == 'nt':
            font_path = "Arial"
            
        clips = []
        
        def create_fallback(dur, text):
            bg = ColorClip(size=(W, H), color=(40, 40, 40)).with_duration(dur)
            txt = TextClip(font=font_path, text=text, font_size=int(H*0.05), color="white").with_position("center").with_duration(dur)  # noqa: E501
            resources_to_close.extend([bg, txt])
            c = CompositeVideoClip([bg, txt], size=(W, H)).with_duration(dur)
            resources_to_close.append(c)
            return c

        scenes = timeline.get("scenes", [])
        for i, scene in enumerate(scenes):
            # Make visual scenes contiguous to avoid black frames
            visual_start = 0.0 if i == 0 else scene["start"]
            visual_end = scenes[i+1]["start"] if i < len(scenes) - 1 else audio_dur
            
            # Clamp bounds
            visual_start = min(max(visual_start, 0.0), audio_dur)
            visual_end = max(visual_start, min(visual_end, audio_dur))
            dur = visual_end - visual_start
            
            asset = scene.get("asset")
            clip = None
            motion = scene.get("motion", "none")
            
            if asset is not None:
                atype = asset["type"]
                apath = asset["path"]
                try:
                    if atype == "video":
                        vclip = VideoFileClip(apath).without_audio()
                        resources_to_close.append(vclip)
                        if vclip.duration < dur:
                            vclip = vclip.with_effects([vfx.Loop(duration=dur)])
                        clip_sub = vclip.subclipped(0, dur)
                        scale = max(W / clip_sub.w, H / clip_sub.h)
                        clip = clip_sub.resized(scale)
                    else:
                        iclip = ImageClip(apath).with_duration(dur)
                        resources_to_close.append(iclip)
                        scale = max(W / iclip.w, H / iclip.h)
                        clip = iclip.resized(scale)
                        
                    if motion == "kenburns_in":
                        clip = clip.with_effects([vfx.Resize(lambda t: 1.0 + 0.05 * (t / max(dur, 0.1)))])
                    elif motion == "kenburns_out":
                        clip = clip.resized(1.05).with_effects([vfx.Resize(lambda t: 1.0 - 0.0476 * (t / max(dur, 0.1)))])  # noqa: E501
                        
                except Exception as e:
                    logger.warning(f"Failed to load asset {apath} ({type(e).__name__}). Using fallback.")
                    clip = None
            
            if clip is None:
                clip = create_fallback(dur, scene["text"])
                
            clip = CompositeVideoClip([clip.with_position("center")], size=(W, H)).with_duration(dur).with_start(visual_start)  # noqa: E501
            resources_to_close.append(clip)
            
            # Transition overlap logic
            if i > 0 and "transition_out" in scenes[i-1]:
                tdur = scenes[i-1]["transition_out"]["duration"]
                clip = clip.with_effects([vfx.CrossFadeIn(tdur)])
                
            if "transition_out" in scene:
                tdur = scene["transition_out"]["duration"]
                clip = clip.with_effects([vfx.CrossFadeOut(tdur)])
                clip = clip.with_duration(dur + tdur)
                
            clips.append(clip)
            
        captions = timeline.get("captions", [])
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

        for line_words in grouped_lines:
            try:
                text = " ".join(w["word"] for w in line_words)
                start_time = line_words[0]["start"]
                end_time = line_words[-1]["end"]
                
                txt = TextClip(
                    font=font_path, text=text, font_size=int(H*0.06), 
                    color="white", stroke_color="black", stroke_width=2,
                    method="caption", size=(int(W*0.9), None)
                )
                
                # Position near bottom with 15% title-safe margin
                margin = int(H * 0.15)
                text_h = txt.h or int(H * 0.10)
                y_pos = H - margin - text_h
                y_pos = max(int(H * 0.60), min(y_pos, int(H * 0.90) - text_h))
                
                txt = txt.with_start(start_time).with_end(end_time).with_position(("center", y_pos))
                resources_to_close.append(txt)
                clips.append(txt)
            except Exception as e:
                logger.warning(f"Failed to render caption line '{text}': {type(e).__name__}")

        for p in timeline.get("popups", []):
            try:
                pop = None
                if p["type"] == "image":
                    pop = ImageClip(p["path"]).with_duration(p["duration"]).with_start(p["at"])
                    resources_to_close.append(pop)
                    pop = pop.resized(height=int(H*0.2))
                elif p["type"] == "text":
                    p_text = p.get("text", p.get("path", "TEXT"))
                    pop = TextClip(font=font_path, text=p_text, font_size=int(H*0.08), color="white", bg_color="black")
                    pop = pop.with_duration(p["duration"]).with_start(p["at"])
                    resources_to_close.append(pop)
                elif p["type"] == "shape":
                    color = p.get("color", "red")
                    c_map = {"red": (255,0,0), "green": (0,255,0), "blue": (0,0,255), "white": (255,255,255), "black": (0,0,0)}  # noqa: E501
                    rgb = c_map.get(color.lower(), (255,0,0))
                    size = p.get("size", 200)
                    pop = ColorClip(size=(size, size), color=rgb).with_duration(p["duration"]).with_start(p["at"])
                    resources_to_close.append(pop)

                if pop:
                    pos = p.get("position", "center")
                    if pos == "top": pos_tuple = ("center", "top")  # noqa: E701
                    elif pos == "bottom": pos_tuple = ("center", "bottom")  # noqa: E701
                    elif pos == "left": pos_tuple = ("left", "center")  # noqa: E701
                    elif pos == "right": pos_tuple = ("right", "center")  # noqa: E701
                    else: pos_tuple = ("center", "center")  # noqa: E701
                    pop = pop.with_position(pos_tuple)
                    
                    anim = p.get("animation", "none")
                    if anim == "fade":
                        pop = pop.with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)])
                    elif anim == "slide":
                        pop = pop.with_position(lambda t: ("center", int(H - (H/2)*(t/max(p["duration"], 0.1)))))
                        
                    clips.append(pop)
            except Exception as e:
                logger.warning(f"Failed to render popup {p}: {type(e).__name__}")
                
        final_video = CompositeVideoClip(clips, size=(W, H)).with_audio(timeline_audio)
        final_video = final_video.with_duration(audio_dur)
        resources_to_close.append(final_video)
        
        logger.info(f"Rendering {out_path.name} with codec {codec} at {W}x{H} {fps}fps")
        
        if codec == "h264_nvenc":
            ffmpeg_params = ["-preset", "p4", "-tune", "hq"]
        else:
            ffmpeg_params = ["-preset", "veryfast"]

        final_video.write_videofile(
            str(out_path),
            fps=fps,
            codec=codec,
            audio_codec="aac",
            threads=4,
            ffmpeg_params=ffmpeg_params,
            logger=None 
        )
    finally:
        for r in resources_to_close:
            try:
                r.close()
            except Exception:
                pass

def render_timeline(timeline_path: Path, draft_mode: bool = False, output_path: Optional[Path] = None) -> Path:
    with open(timeline_path, "r", encoding="utf-8") as f:
        timeline = json.load(f)
        
    if output_path is None:
        renders_dir = DATA / "renders"
        renders_dir.mkdir(parents=True, exist_ok=True)
        out_name = f"render_{uuid.uuid4().hex[:8]}_{'draft' if draft_mode else 'final'}.mp4"
        output_path = renders_dir / out_name
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
    codecs_to_try = ["h264_nvenc", "libx264"] if has_nvenc() else ["libx264"]
    
    for i, codec in enumerate(codecs_to_try):
        try:
            _run_render_pass(timeline, codec, output_path, draft_mode)
            return output_path
        except Exception as e:
            logger.warning(f"Encoder {codec} failed with {type(e).__name__}")
            if i == len(codecs_to_try) - 1:
                raise e
                
    return output_path
