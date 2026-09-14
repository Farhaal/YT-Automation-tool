# OpenReel Project Status

## Current Status
**Phase 0 through Phase 8** are fully implemented and currently staged on the \phase-8-frontend\ (and \ix/aspect-ratio\) branches, pending final review and merge into \main\.

### Implemented Phases (P0–P8)
- **P0**: Foundation & Project Structure
- **P1**: Backend Skeleton (FastAPI setup)
- **P2**: Transcription & word-level alignment (faster-whisper)
- **P3**: Text-to-Speech fallback path
- **P4**: NLP Scene Segmentation & Query Extraction
- **P5**: Asset Provider Integrations (Pexels, Pixabay, Openverse, Wikimedia)
- **P6**: Timeline Assembly & Strict Schema Validation
- **P7**: Draft Renderer (MoviePy, NVENC/libx264, Popups, Ken Burns)
- **P8**: React Frontend UI, WebSocket Orchestration, & Editor Controls (Aspect ratio, Swap assets, popups)

### Remaining Phases (P9–P11)
- **P9 (Next up)**: Full-resolution export pipeline and auto-generated credits file logic.
- **P10**: Application packaging and polish (e.g. Tauri Desktop shell, v1.0 docs).
- **P11**: Optional upgrades (LLM-based scripting enhancements, visual verification, upscaling).

---

## How to Run OpenReel Locally

Ensure you have activated your local Python virtual environment and installed all dependencies from \equirements.txt\ as well as the \en_core_web_sm\ spaCy model.

### 1. Start the Backend
`powershell
# From the project root:
Start-Process -NoNewWindow -Wait -ArgumentList "-m", "uvicorn", "backend.app.main:app", "--reload" -FilePath "python"
`
*The backend runs on \http://127.0.0.1:8000\.*

### 2. Start the Frontend
`powershell
# Open a new terminal, navigate to the frontend folder:
cd frontend
npm install
npm run dev
`
*The frontend is accessible at \http://localhost:5173\.*

---

## Known Limitations & Notes
- **Export Resolution**: Currently renders in Draft mode (halved resolution and capped FPS for speed). P9 will introduce full-resolution final exports.
- **Hardware Acceleration**: GPU (NVENC) usage is attempted but will gracefully fallback to CPU (\libx264\) if unavailable.
- **CORS/Origin**: The application is configured strictly for local runs (\localhost:5173\). Do not expose without securing the endpoints.