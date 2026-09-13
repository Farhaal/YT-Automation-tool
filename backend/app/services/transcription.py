import os
from pathlib import Path
from typing import List, Dict, Any
from faster_whisper import WhisperModel
import ctranslate2

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.core.paths import DATA

_model_instance = None

def get_transcription_model() -> WhisperModel:
    global _model_instance
    if _model_instance is None:
        device = settings.DEVICE
        compute_type = "int8"

        if device == "auto":
            try:
                if ctranslate2.get_cuda_device_count() > 0:
                    device = "cuda"
                    compute_type = "float16"
                else:
                    device = "cpu"
                    compute_type = "int8"
            except Exception:
                device = "cpu"
                compute_type = "int8"

        elif device == "cuda":
            compute_type = "float16"
        elif device == "cpu":
            compute_type = "int8"
        
        logger.info(f"Loading Whisper model '{settings.WHISPER_MODEL}' on {device} (compute_type: {compute_type})...")
        download_root = str(DATA / "models" / "whisper")
        
        try:
            _model_instance = WhisperModel(
                settings.WHISPER_MODEL, 
                device=device, 
                compute_type=compute_type,
                download_root=download_root
            )
            logger.info("Whisper model loaded successfully.")
        except RuntimeError as e:
            if device == "cuda" and settings.DEVICE == "auto":
                logger.warning(f"Failed to load Whisper on CUDA ({e}). Falling back to CPU...")
                device = "cpu"
                compute_type = "int8"
                _model_instance = WhisperModel(
                    settings.WHISPER_MODEL, 
                    device=device, 
                    compute_type=compute_type,
                    download_root=download_root
                )
                logger.info("Whisper model loaded successfully on CPU fallback.")
            else:
                raise

    return _model_instance

def transcribe_audio(audio_path: str) -> Dict[str, Any]:
    """
    Transcribes audio and returns word-level timestamps and segments.
    """
    model = get_transcription_model()
    
    logger.info(f"Transcribing {audio_path}...")
    try:
        segments_gen, info = model.transcribe(audio_path, word_timestamps=True)
        # Try to pull the first segment to trigger the encode step
        segments = []
        words = []
        try:
            first_segment = next(segments_gen)
            segments_gen = [first_segment] + list(segments_gen)
        except StopIteration:
            segments_gen = []
    except RuntimeError as e:
        if settings.DEVICE == "auto":
            logger.warning(f"CUDA transcription failed at runtime ({e}). Falling back to CPU...")
            global _model_instance
            download_root = str(DATA / "models" / "whisper")
            _model_instance = WhisperModel(
                settings.WHISPER_MODEL, 
                device="cpu", 
                compute_type="int8",
                download_root=download_root
            )
            model = _model_instance
            segments_gen, info = model.transcribe(audio_path, word_timestamps=True)
            segments = []
            words = []
            try:
                first_segment = next(segments_gen)
                segments_gen = [first_segment] + list(segments_gen)
            except StopIteration:
                segments_gen = []
        else:
            raise
    
    for segment in segments_gen:
        segments.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
        })
        if segment.words:
            for word in segment.words:
                words.append({
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end
                })
                
    # Hook for WhisperX alignment goes here later
    # if settings.USE_WHISPERX:
    #     words = align_with_whisperx(audio_path, words)
                
    return {
        "language": info.language,
        "language_probability": info.language_probability,
        "segments": segments,
        "words": words
    }
