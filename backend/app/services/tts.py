import uuid
from pathlib import Path

from backend.app.core.paths import DATA
from backend.app.core.config import settings
from backend.app.core.logger import logger

def synthesize(text: str) -> str:
    """
    Synthesizes text into speech and returns the path to the generated .wav file.
    """
    filename = f"{uuid.uuid4()}_narration.wav"
    output_path = DATA / "tmp" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Synthesizing text using {settings.TTS_ENGINE}...")
    
    if settings.TTS_ENGINE == "pyttsx3":
        import pyttsx3
        engine = pyttsx3.init()
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()
    elif settings.TTS_ENGINE == "piper":
        # Hook for Piper TTS
        raise NotImplementedError("Piper TTS not yet implemented")
    elif settings.TTS_ENGINE == "kokoro":
        # Hook for Kokoro TTS
        raise NotImplementedError("Kokoro TTS not yet implemented")
    else:
        raise ValueError(f"Unknown TTS engine: {settings.TTS_ENGINE}")
        
    logger.info(f"Synthesis complete: {output_path}")
    return str(output_path)
