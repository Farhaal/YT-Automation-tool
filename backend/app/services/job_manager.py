import json
from typing import Any, Dict, Optional

from backend.app.core.paths import DATA


class JobManager:
    def __init__(self):
        self.jobs_dir = DATA / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: Dict[str, Dict[str, Any]] = {}
        for f in self.jobs_dir.glob("*.json"):
            try:
                with open(f, "r") as fp:
                    j = json.load(fp)
                    self.jobs[j["job_id"]] = j
            except Exception:
                pass
                
    def _save(self, job_id: str):
        path = self.jobs_dir / f"{job_id}.json"
        with open(path, "w") as f:
            json.dump(self.jobs[job_id], f)
            
    def create_job(self, job_id: str, audio_path: Optional[str] = None, script: Optional[str] = None):
        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "PENDING",
            "progress": 0.0,
            "stage": "Initializing",
            "audio_path": audio_path,
            "script": script,
            "timeline_path": None,
            "draft_video_path": None,
            "llm_warning": None,
            "error": None,
            "logs": []
        }
        self.update_job(job_id)
        
    def update_job(self, job_id: str, log: Optional[str] = None, **kwargs):
        if job_id in self.jobs:
            self.jobs[job_id].update(kwargs)
            if log:
                if "logs" not in self.jobs[job_id]:
                    self.jobs[job_id]["logs"] = []
                self.jobs[job_id]["logs"].append(log)
            self._save(job_id)
            
    def get_job(self, job_id: str):
        return self.jobs.get(job_id)
        
job_manager = JobManager()
