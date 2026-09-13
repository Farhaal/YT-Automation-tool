from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
import uuid

router = APIRouter()

class GenerateRequest(BaseModel):
    # Depending on voice vs text path, we might have text or an audio file.
    # For now we stub it.
    text: str = ""

@router.get("/health")
def health_check():
    return {"status": "ok"}

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
