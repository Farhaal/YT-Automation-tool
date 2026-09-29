import asyncio
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.core.paths import DATA
from backend.app.services.job_manager import job_manager
from backend.app.services.transcription import transcribe_audio

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

def run_job_pipeline_sync(job_id: str, loop: asyncio.AbstractEventLoop, aspect_ratio: str = "landscape", enable_motion: bool = True, pace: str = "balanced", punchy_hook: bool = True):  # noqa: E501
    def sync_notify(job_id, data):
        try:
            asyncio.run_coroutine_threadsafe(notify_job_update(job_id, data), loop)
        except Exception:
            pass

    def update(progress, stage, status="PROCESSING", log_msg=None, **kwargs):
        if log_msg is None:
            log_msg = f"[{progress}%] {stage}"
        job_manager.update_job(job_id, log=log_msg, progress=progress, stage=stage, status=status, **kwargs)
        job = job_manager.get_job(job_id)
        sync_notify(job_id, job)
        logger.info(f"Job {job_id} [{progress}%]: {stage}")

    try:
        # Apply settings (including LLM settings) to current environment early
        # so process_script_to_scenes can use the latest LLM_API_KEY.
        apply_settings_to_env()
        
        job = job_manager.get_job(job_id)
        audio_path = job.get("audio_path")
        script = job.get("script")
        
        if not audio_path and script:
            update(10, "Synthesizing audio", log_msg="Generating voiceover from text script using TTS...")
            from backend.app.services.tts import synthesize
            audio_path = str(synthesize(script))
            job_manager.update_job(job_id, audio_path=audio_path)
            
        update(20, "Transcribing", log_msg="Running Whisper model to transcribe audio and map word-level timestamps...")
        transcription = transcribe_audio(audio_path)
        words = transcription.get("words", [])
        
        update(40, "Segmenting scenes", log_msg="Analyzing transcript with NLP to segment scenes and extract visual search queries...")
        from backend.app.services.nlp import process_script_to_scenes
        job_state = {"dead_providers": set(), "llm_failover_log": [], "llm_warnings": []}
        scenes = process_script_to_scenes(words, pace=pace, punchy_hook=punchy_hook, job_state=job_state)
        
        update(60, "Finding assets", log_msg=f"Searching Pexels, Pixabay, Openverse, and Wikimedia for {len(scenes)} scenes...")
        from backend.app.services.assets.manager import AssetManager
        
        s = load_settings()
        import os
        if s.get("pexels_key"):
            os.environ["PEXELS_API_KEY"] = s["pexels_key"]
        if s.get("pixabay_key"):
            os.environ["PIXABAY_API_KEY"] = s["pixabay_key"]
        
        asset_manager = AssetManager(cache_dir=DATA / "assets")
        scenes = asset_manager.select_assets_for_scenes(scenes, orientation=aspect_ratio, job_state=job_state)
        
        # Determine llm_warning
        llm_warning = None
        if job_state["llm_warnings"]:
            # If all failed
            llm_warning = {
                "used_provider": job_state.get("used_provider"),
                "failed": job_state["llm_failover_log"]
            }
            job_manager.update_job(job_id, llm_warning=llm_warning)
                
        update(80, "Building timeline", log_msg="Assembling final timeline with Ken Burns motion, transitions, and generated subtitles...")
        from backend.app.services.timeline import TimelineAssembler
        schema_path = Path(__file__).parent.parent.parent.parent / "shared" / "timeline.schema.json"
        assembler = TimelineAssembler(schema_path=schema_path)
        
        audio_dur = transcription["segments"][-1]["end"] if transcription.get("segments") else 0.0
        if audio_dur == 0.0:
            import subprocess
            res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path], capture_output=True, text=True)  # noqa: E501
            try: audio_dur = float(res.stdout.strip())  # noqa: E701
            except: audio_dur = 1.0  # noqa: E701, E722

        timeline = assembler.assemble(audio_path, audio_dur, words, scenes, aspect_ratio=aspect_ratio, enable_motion=enable_motion)  # noqa: E501
        
        timeline_path = DATA / "jobs" / f"{job_id}_timeline.json"
        with open(timeline_path, "w", encoding="utf-8") as f:
            json.dump(timeline, f, indent=2)
            
        update(100, "Ready to edit", log_msg="Timeline assembled. Ready for review and export.", status="COMPLETED", timeline_path=str(timeline_path))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        job_manager.update_job(job_id, status="ERROR", stage="Failed", error=str(e))
        job = job_manager.get_job(job_id)
        sync_notify(job_id, job)

class GenerateRequest(BaseModel):
    script: str = ""
    aspect_ratio: str = "landscape"
    enable_motion: bool = True
    pace: str = "balanced"
    punchy_hook: bool = True

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
    background_tasks.add_task(run_job_pipeline_sync, job_id, loop, req.aspect_ratio, req.enable_motion, req.pace, req.punchy_hook)
    return job_manager.get_job(job_id)

from fastapi import Form  # noqa: E402


@router.post("/generate/audio")
async def generate_from_audio(background_tasks: BackgroundTasks, audio_file: UploadFile = File(...), aspect_ratio: str = Form("landscape"), enable_motion: bool = Form(True), pace: str = Form("balanced"), punchy_hook: bool = Form(True)):  # noqa: E501
    import asyncio
    job_id = str(uuid.uuid4())
    temp_path = DATA / "tmp" / f"{job_id}_{audio_file.filename}"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(await audio_file.read())
    job_manager.create_job(job_id, audio_path=str(temp_path))
    loop = asyncio.get_running_loop()
    background_tasks.add_task(run_job_pipeline_sync, job_id, loop, aspect_ratio, enable_motion, pace, punchy_hook)
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
    if not timeline_path: return  # noqa: E701
    
    job_manager.update_job(job_id, status="PROCESSING", stage="Rendering draft" if draft_mode else "Rendering final", progress=90)  # noqa: E501
    sync_notify(job_id, job_manager.get_job(job_id))
    
    try:
        from backend.app.services.renderer import render_timeline
        out_path = render_timeline(timeline_path, draft_mode=draft_mode)
        
        if draft_mode:
            job_manager.update_job(job_id, status="COMPLETED", stage="Done", progress=100, draft_video_path=str(out_path))  # noqa: E501
        else:
            job_manager.update_job(job_id, status="COMPLETED", stage="Done", progress=100, final_video_path=str(out_path))  # noqa: E501
            
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

class ExportRequest(BaseModel):
    target: str = "resolve"

@router.post("/jobs/{job_id}/export")
async def export_job(job_id: str, req: ExportRequest):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    timeline_path = job.get("timeline_path")
    if not timeline_path or not Path(timeline_path).exists():
        raise HTTPException(status_code=400, detail="Timeline not ready")
        
    from backend.app.services.exporter import export_project
    try:
        zip_path = export_project(Path(timeline_path), job_id, req.target)
        return {"export_path": str(zip_path.absolute())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Settings API ---
SETTINGS_PATH = DATA / "settings.json"

class LLMProviderConfig(BaseModel):
    provider: str
    api_key: str = ""
    model: str = ""
    enabled: bool = True

class SettingsUpdate(BaseModel):
    pexels_key: Optional[str] = None
    pixabay_key: Optional[str] = None
    llm_providers: Optional[List[LLMProviderConfig]] = None
    enable_visual_verification: Optional[bool] = None
    vision_model: Optional[str] = None

class TestLLMRequest(BaseModel):
    provider: str
    api_key: str = ""
    model: str = ""

def load_settings():
    base_settings = {
        "pexels_key": settings.PEXELS_API_KEY or "",
        "pixabay_key": settings.PIXABAY_API_KEY or "",
        "enable_visual_verification": settings.ENABLE_VISUAL_VERIFICATION,
        "vision_model": settings.VISION_MODEL,
        "llm_providers": settings.LLM_PROVIDERS or []
    }
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, "r") as f:
                saved = json.load(f)
                
                if "llm_provider" in saved and "llm_providers" not in saved:
                    prov_list = []
                    if saved.get("llm_provider"):
                        prov_list.append({
                            "provider": saved.get("llm_provider", ""),
                            "api_key": saved.get("llm_api_key", ""),
                            "model": saved.get("llm_model", ""),
                            "enabled": True
                        })
                    saved["llm_providers"] = prov_list
                    
                if "llm_providers" in saved:
                    base_settings["llm_providers"] = saved["llm_providers"]
                    
                base_settings["pexels_key"] = saved.get("pexels_key", base_settings["pexels_key"])
                base_settings["pixabay_key"] = saved.get("pixabay_key", base_settings["pixabay_key"])
                base_settings["enable_visual_verification"] = saved.get("enable_visual_verification", base_settings["enable_visual_verification"])
                base_settings["vision_model"] = saved.get("vision_model", base_settings["vision_model"])
        except Exception:
            pass
    return base_settings

def apply_settings_to_env():
    s = load_settings()
    settings.PEXELS_API_KEY = s.get("pexels_key", settings.PEXELS_API_KEY)
    settings.PIXABAY_API_KEY = s.get("pixabay_key", settings.PIXABAY_API_KEY)
    settings.LLM_PROVIDERS = s.get("llm_providers", settings.LLM_PROVIDERS)
    settings.ENABLE_VISUAL_VERIFICATION = s.get("enable_visual_verification", settings.ENABLE_VISUAL_VERIFICATION)
    settings.VISION_MODEL = s.get("vision_model", settings.VISION_MODEL)

@router.get("/settings")
def get_settings():
    s = load_settings()
    masked = []
    for p in s.get("llm_providers", []):
        masked.append({
            "provider": p.get("provider", ""),
            "model": p.get("model", ""),
            "enabled": p.get("enabled", True),
            "status": "Configured" if p.get("api_key") else "Not configured"
        })
    return {
        "pexels": "Configured" if s.get("pexels_key") else "Not configured",
        "pixabay": "Configured" if s.get("pixabay_key") else "Not configured",
        "openverse": "No key required",
        "wikimedia": "No key required",
        "llm_providers": masked,
        "enable_visual_verification": s.get("enable_visual_verification", False),
        "vision_model": s.get("vision_model", "")
    }

@router.post("/settings")
def update_settings(req: SettingsUpdate):
    s = load_settings()
    if req.pexels_key is not None and req.pexels_key != "":
        s["pexels_key"] = req.pexels_key
    if req.pixabay_key is not None and req.pixabay_key != "":
        s["pixabay_key"] = req.pixabay_key
    if req.llm_providers is not None:
        s["llm_providers"] = [p.dict() for p in req.llm_providers]
    if req.enable_visual_verification is not None:
        s["enable_visual_verification"] = req.enable_visual_verification
    if req.vision_model is not None:
        s["vision_model"] = req.vision_model
    
    with open(SETTINGS_PATH, "w") as f:
        json.dump(s, f)
    apply_settings_to_env()
    return get_settings()

@router.delete("/settings/{provider}")
def delete_setting(provider: str):
    s = load_settings()
    if provider.lower() == "pexels":
        s["pexels_key"] = ""
    elif provider.lower() == "pixabay":
        s["pixabay_key"] = ""
    elif provider.lower() == "llm":
        s["llm_providers"] = []
        
    with open(SETTINGS_PATH, "w") as f:
        json.dump(s, f)
    apply_settings_to_env()
    return get_settings()

@router.post("/settings/test-llm")
def test_llm_settings(req: TestLLMRequest):
    import httpx
    
    provider = req.provider.lower()
    base_url = "https://api.openai.com/v1"
    model = req.model or "gpt-3.5-turbo"
    
    if provider == "groq":
        base_url = "https://api.groq.com/openai/v1"
        model = req.model or "llama3-8b-8192"
    elif provider == "openrouter":
        base_url = "https://openrouter.ai/api/v1"
    elif provider == "ollama":
        base_url = "http://localhost:11434/v1"
        model = req.model or "llama3"
    elif provider in ["gemini", "google"]:
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
        model = req.model or "gemini-2.0-flash"
        
    headers = {"Content-Type": "application/json"}
    if req.api_key:
        headers["Authorization"] = f"Bearer {req.api_key}"
        
    try:
        resp = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            },
            timeout=10.0
        )
        resp.raise_for_status()
        return {"ok": True}
    except Exception as e:
        msg = str(e)
        if isinstance(e, httpx.HTTPStatusError):
            try:
                msg = e.response.json().get("error", {}).get("message", msg)
            except Exception:
                msg = e.response.text or msg
        return {"ok": False, "status": getattr(e, "response", None) and getattr(e.response, "status_code", None), "message": msg}

from fastapi.responses import FileResponse  # noqa: E402


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
    return FileResponse(p, filename=p.name)

