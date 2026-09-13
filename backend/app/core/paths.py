import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # repo root
DATA = Path(os.getenv("OPENREEL_DATA_DIR", ROOT / "data"))
for sub in ("models", "cache", "downloads", "renders", "tmp"):
    (DATA / sub).mkdir(parents=True, exist_ok=True)

# Force every library to cache inside the project, not your home drive:
os.environ.setdefault("HF_HOME",        str(DATA / "cache" / "huggingface"))
os.environ.setdefault("TORCH_HOME",     str(DATA / "cache" / "torch"))
os.environ.setdefault("XDG_CACHE_HOME", str(DATA / "cache"))
# faster-whisper: pass download_root=str(DATA / "models" / "whisper") when loading the model
# renders + temp files: always write under DATA/"renders" and DATA/"tmp"
