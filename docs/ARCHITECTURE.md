# OpenReel Architecture

OpenReel is a free, open-source, local "script to video" tool. It takes either a voice recording or a text script and produces a finished, edited video by automatically finding matching free stock footage, syncing it to the narration using word-level timestamps, and adding captions and effects.

## System Components

The application is built as a monorepo consisting of three cooperating parts:

### 1. Backend (Python / FastAPI)
The brain of the application. It handles all data processing and API requests.
- **Transcription & Alignment**: Uses faster-whisper to transcribe audio and generate word-level timestamps.
- **Text-to-Speech**: Converts text scripts into voiceovers (baseline: pyttsx3).
- **Scene Segmentation & Keyword Extraction**: Splits the script into scenes and extracts search phrases using spaCy and YAKE.
- **Asset Management**: Searches and downloads free footage from Pexels, Pixabay, Openverse, and Wikimedia based on extracted keywords.
- **Timeline Assembly**: Generates `timeline.json` containing the full description of the video.

### 2. Renderer (FFmpeg + MoviePy + Pillow)
The engine that turns the `timeline.json` into an actual video file (MP4).
- Processes media clips, applies Ken Burns motion, transitions, and draws word-synced animated captions and pop-ups.
- Utilizes hardware acceleration (NVENC) when available, falling back to CPU otherwise.

### 3. Frontend (React + Vite + TypeScript)
The user interface.
- Allows users to upload audio or paste a script.
- Shows live generation progress.
- Provides a preview player.
- Enables light editing like swapping clips or tweaking timings.
- Exports the final video.

## Data Flow

1. **Input**: Voice file or text script. (If text, TTS converts it to voice).
2. **Transcription & Timing**: Audio is transcribed to obtain precise word-level timestamps.
3. **Segmentation**: Words are grouped into scenes.
4. **Keyword Extraction**: 1-3 search phrases are derived for each scene.
5. **Asset Search**: Best matching free media is found, downloaded, and cached.
6. **Timeline Assembly**: A complete `timeline.json` is generated.
7. **Renderer**: The timeline is processed into a preview or a final high-resolution MP4.
