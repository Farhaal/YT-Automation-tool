from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Free stock-media API keys
    PEXELS_API_KEY: Optional[str] = None
    PIXABAY_API_KEY: Optional[str] = None
    UNSPLASH_ACCESS_KEY: Optional[str] = None

    # Runtime configuration
    # Users can set WHISPER_MODEL=medium or large-v3 in .env for higher accuracy at the cost of speed.
    WHISPER_MODEL: str = "small"
    DEVICE: str = "auto"
    TTS_ENGINE: str = "pyttsx3"
    OLLAMA_URL: str = "http://localhost:11434"
    USE_OLLAMA: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
