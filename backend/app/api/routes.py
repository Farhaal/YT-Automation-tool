from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import uuid
import shutil
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any

from backend.app.core.paths import DATA
from backend.app.services.transcription import transcribe_audio
from backend.app.services.job_manager import job_manager
from backend.app.core.logger import logger
from backend.app.core.config import settings

router = APIRouter()
active_connections: Dict[str, List[WebSocket]] = {}

async def notify_job_update(job_id: str, data: dict):
    if job_id in active_connections:
        dead_ws = []
        for ws in active_connections[job_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead_ws.append(ws)
        for ws in dead_ws:
            active_connections[job_id].remove(ws)

def run_job_pipeline_sync(job_id: str, loop: asyncio.AbstractEventLoop, aspect_ratio: str = "landscape"):
    def sync_notify(job_id, data):
        try:
            asyncio.run_coroutine_threadsafe(notify_job_update(job_id, data), loop)
        except Exception:
            pass

    def update(progress, stage, status="PROCESSING", **kwargs):
        job_manager.update_job(job_id, progress=progress, stage=stage, status=status, **kwargs)
        job = job_manager.get_job(job_id)
        sync_notify(job_id, job)
        logger.info(f"Job {job_id} [{progress}%]: {stage}")

    try:
        job = job_manager.get_job(job_id)
        audio_path = job.get("audio_path")
        script = job.get("script")
        
        if not audio_path and script:
            update(10, "Synthesizing audio")
            from backend.app.services.tts import synthesize
            audio_path = str(synthesize(script))
            job_manager.update_job(job_id, audio_path=audio_path)
            
        update(30, "Transcribing")
        transcription = transcribe_audio(audio_path)
        words = transcription.get("words", [])
        
        update(50, "Segmenting scenes")
        from backend.app.services.nlp import process_script_to_scenes
        scenes = process_script_to_scenes(words)
        
        update(70, "Finding assets")
        from backend.app.services.assets.manager import AssetManager
        
        # Load API keys from settings if they exist
        s = load_settings()
        import os
        if s.get("pexels_key"): os.environ["PEXELS_API_KEY"] = s["pexels_key"]
        if s.get("pixabay_key"): os.environ["PIXABAY_API_KEY"] = s["pixabay_key"]
        
        asset_manager = AssetManager(cache_dir=DATA / "assets")
        scenes = asset_manager.select_assets_for_scenes(scenes, orientation=aspect_ratio)
                
        update(80, "Assembling timeline")
        from backend.app.services.timeline import TimelineAssembler
        schema_path = Path(__file__).parent.parent.parent.parent / "shared" / "timeline.schema.json"
        assembler = TimelineAssembler(schema_path=schema_path)
        
        audio_dur = transcription["segments"][-1]["end"] if transcription.get("segments") else 0.0
        if audio_dur == 0.0:
            import subprocess
            res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path], capture_output=True, text=True)
            try: audio_dur = float(res.stdout.strip())
            except: audio_dur = 1.0

        timeline = assembler.assemble(audio_path, audio_dur, words, scenes, aspect_ratio=aspect_ratio)
        
        timeline_path = DATA / "jobs" / f"{job_id}_timeline.json"
        with open(timeline_path, "w", encoding="utf-8") as f:
            json.dump(timeline, f, indent=2)
            
        update(90, "Rendering draft", timeline_path=str(timeline_path))
        from backend.app.services.renderer import render_timeline
        draft_video_path = render_timeline(timeline_path, draft_mode=True)
        
        update(100, "Done", status="COMPLETED", draft_video_path=str(draft_video_path))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        job_manager.update_job(job_id, status="ERROR", stage="Failed", error=str(e))
        job = job_manager.get_job(job_id)
        sync_notify(job_id, job)

class GenerateRequest(BaseModel):
    script: str = ""
    aspect_ratio: str = "landscape"

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.post("/generate/script")
async def generate_from_script(req: GenerateRequest, background_tasks: BackgroundTasks):
    import asyncio
    if not req.script.strip():
        raise HTTPException(status_code=400, detail="Script cannot be empty")
    job_id = str(uuid.uuid4())
    job_manager.create_job(job_id, script=req.script)
    loop = asyncio.get_running_loop()
    background_tasks.add_task(run_job_pipeline_sync, job_id, loop, req.aspect_ratio)
    return job_manager.get_job(job_id)

from fastapi import Form
@router.post("/generate/audio")
async def generate_from_audio(background_tasks: BackgroundTasks, audio_file: UploadFile = File(...), aspect_ratio: str = Form("landscape")):
    import asyncio
    job_id = str(uuid.uuid4())
    temp_path = DATA / "tmp" / f"{job_id}_{audio_file.filename}"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(audio_file.file, buffer)
        
    job_manager.create_job(job_id, audio_path=str(temp_path))
    loop = asyncio.get_running_loop()
    background_tasks.add_task(run_job_pipeline_sync, job_id, loop, aspect_ratio)
    return job_manager.get_job(job_id)

@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.websocket("/jobs/{job_id}/ws")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    if job_id not in active_connections:
        active_connections[job_id] = []
    active_connections[job_id].append(websocket)
    
    # Send current state immediately
    job = job_manager.get_job(job_id)
    if job:
        await websocket.send_json(job)
        
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections[job_id]:
            active_connections[job_id].remove(websocket)

@router.get("/jobs/{job_id}/timeline")
def get_timeline(job_id: str):
    job = job_manager.get_job(job_id)
    if not job or not job.get("timeline_path"):
        raise HTTPException(status_code=404, detail="Timeline not found")
    with open(job["timeline_path"], "r", encoding="utf-8") as f:
        return json.load(f)

@router.put("/jobs/{job_id}/timeline")
def update_timeline(job_id: str, timeline: dict):
    job = job_manager.get_job(job_id)
    if not job or not job.get("timeline_path"):
        raise HTTPException(status_code=404, detail="Timeline not found")
        
    from backend.app.services.timeline import TimelineAssembler
    schema_path = Path(__file__).parent.parent.parent.parent / "shared" / "timeline.schema.json"
    assembler = TimelineAssembler(schema_path=schema_path)
        
    # Enforce timestamp immutability from original timeline
    with open(job["timeline_path"], "r", encoding="utf-8") as f:
        old_timeline = json.load(f)
        
    timeline["audio"] = old_timeline["audio"]
    
    # Enforce strict structural immutability
    old_scenes = old_timeline.get("scenes", [])
    new_scenes = timeline.get("scenes", [])
    if len(new_scenes) != len(old_scenes):
        raise HTTPException(status_code=400, detail="Scene count mismatch")
    
    for i, sc in enumerate(new_scenes):
        if sc.get("id") != old_scenes[i].get("id"):
            raise HTTPException(status_code=400, detail=f"Scene ID mismatch at index {i}")
        # Always restore original timestamps
        sc["start"] = old_scenes[i]["start"]
        sc["end"] = old_scenes[i]["end"]
            
    old_caps = old_timeline.get("captions", [])
    new_caps = timeline.get("captions", [])
    if len(new_caps) != len(old_caps):
        raise HTTPException(status_code=400, detail="Caption count mismatch")
    
    for i, cap in enumerate(new_caps):
        # Always restore original timestamps
        cap["start"] = old_caps[i]["start"]
        cap["end"] = old_caps[i]["end"]
            
    try:
        assembler.validate(timeline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    with open(job["timeline_path"], "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2)
    return {"status": "ok"}

def run_render_sync(job_id: str, draft_mode: bool, loop: asyncio.AbstractEventLoop):
    def sync_notify(job_id, data):
        try:
            asyncio.run_coroutine_threadsafe(notify_job_update(job_id, data), loop)
        except Exception:
            pass
            
    job = job_manager.get_job(job_id)
    timeline_path = job.get("timeline_path")
    if not timeline_path: return
    
    job_manager.update_job(job_id, status="PROCESSING", stage="Rendering draft" if draft_mode else "Rendering final", progress=90)
    sync_notify(job_id, job_manager.get_job(job_id))
    
    try:
        from backend.app.services.renderer import render_timeline
        out_path = render_timeline(timeline_path, draft_mode=draft_mode)
        
        if draft_mode:
            job_manager.update_job(job_id, status="COMPLETED", stage="Done", progress=100, draft_video_path=str(out_path))
        else:
            job_manager.update_job(job_id, status="COMPLETED", stage="Done", progress=100, final_video_path=str(out_path))
            
    except Exception as e:
        job_manager.update_job(job_id, status="ERROR", stage="Failed", error=str(e))
        
    sync_notify(job_id, job_manager.get_job(job_id))

class RenderRequest(BaseModel):
    draft_mode: bool = True

@router.post("/jobs/{job_id}/render")
async def render_job(job_id: str, req: RenderRequest, background_tasks: BackgroundTasks):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    loop = asyncio.get_running_loop()
    background_tasks.add_task(run_render_sync, job_id, req.draft_mode, loop)
    return {"status": "ok"}

# --- Settings API ---
SETTINGS_PATH = DATA / "settings.json"

class SettingsUpdate(BaseModel):
    pexels_key: str = ""
    pixabay_key: str = ""

def load_settings():
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, "r") as f:
                return json.load(f)
        except:
            pass
    return {"pexels_key": settings.PEXELS_API_KEY or "", "pixabay_key": settings.PIXABAY_API_KEY or ""}

@router.get("/settings")
def get_settings():
    s = load_settings()
    return {
        "pexels": "Configured" if s.get("pexels_key") else "Not configured",
        "pixabay": "Configured" if s.get("pixabay_key") else "Not configured",
        "openverse": "No key required",
        "wikimedia": "No key required"
    }

@router.post("/settings")
def update_settings(req: SettingsUpdate):
    s = load_settings()
    if req.pexels_key: s["pexels_key"] = req.pexels_key
    if req.pixabay_key: s["pixabay_key"] = req.pixabay_key
    with open(SETTINGS_PATH, "w") as f:
        json.dump(s, f)
    settings.PEXELS_API_KEY = s["pexels_key"]
    settings.PIXABAY_API_KEY = s["pixabay_key"]
    return get_settings()

@router.delete("/settings/{provider}")
def delete_setting(provider: str):
    s = load_settings()
    if provider.lower() == "pexels":
        s["pexels_key"] = ""
        settings.PEXELS_API_KEY = ""
    elif provider.lower() == "pixabay":
        s["pixabay_key"] = ""
        settings.PIXABAY_API_KEY = ""
    with open(SETTINGS_PATH, "w") as f:
        json.dump(s, f)
    return get_settings()

from fastapi.responses import FileResponse
@router.get("/media")
def get_media(path: str):
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    # For security, could check if p is inside DATA dir
    try:
        if not p.resolve().is_relative_to(DATA.resolve()):
            raise HTTPException(status_code=403, detail="Forbidden")
    except ValueError:
        raise HTTPException(status_code=403, detail="Forbidden")
    return FileResponse(p)

