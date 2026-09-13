from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException
from pydantic import BaseModel
import uuid
import shutil
from pathlib import Path

from backend.app.core.paths import DATA
from backend.app.services.transcription import transcribe_audio

router = APIRouter()

class GenerateRequest(BaseModel):
    # Depending on voice vs text path, we might have text or an audio file.
    # For now we stub it.
    text: str = ""

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.post("/transcribe")
async def transcribe(audio_file: UploadFile = File(...)):
    if not audio_file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    temp_path = DATA / "tmp" / f"{uuid.uuid4()}_{audio_file.filename}"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
            
        result = transcribe_audio(str(temp_path))
        return result
    finally:
        if temp_path.exists():
            temp_path.unlink()

class SynthesizeRequest(BaseModel):
    text: str

@router.post("/synthesize")
def synthesize_and_align(req: SynthesizeRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
        
    from backend.app.services.tts import synthesize
    
    # 1. Synthesize text to audio
    audio_path = synthesize(req.text)
    
    # 2. Run it through transcription to get words+timestamps
    transcription = transcribe_audio(audio_path)
    
    # We could delete the audio_path if we just wanted the JSON,
    # but the pipeline needs the audio file for the renderer.
    # We'll return its path so the frontend/pipeline knows where it is.
    return {
        "audio_path": str(audio_path),
        "transcription": transcription
    }

@router.post("/generate")
def generate_video(req: GenerateRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    # In the future, we would start processing the audio/script here in background
    return {"job_id": job_id, "status": "queued"}

@router.get("/status/{job_id}")
def get_status(job_id: str):
    # Stub: return a dummy status
    return {"job_id": job_id, "status": "processing", "progress": 0.5}

@router.post("/export/{job_id}")
def export_video(job_id: str):
    # Stub: start high-res render and export
    return {"job_id": job_id, "status": "exporting"}
