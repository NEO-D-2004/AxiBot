import os
import json
from pydantic_settings import BaseSettings

DEFAULT_NVIDIA_API_KEY = "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"

class Settings(BaseSettings):
    YOUTUBE_CLIENT_SECRET_PATH: str = "client_secret.json"
    YOUTUBE_TOKEN_PATH: str = "storage/token.json"
    YOUTUBE_STREAMER_TOKEN_PATH: str = "storage/streamer_token.json"
    STREAMER_CHANNEL_ID: str = "" # Channel ID of the streamer to watch
    STREAMER_CHANNEL_NAME: str = "" # Display name of the streamer channel
    NVIDIA_API_KEY: str = DEFAULT_NVIDIA_API_KEY
    NVIDIA_MODEL_ID: str = "openai/gpt-oss-120b"
    BOT_NAME: str = "AxiBot"
    COOLDOWN_SECONDS: int = 60
    ENABLE_DATABASE: bool = True
    ENABLE_COMMANDS: bool = True
    RADIO_MODEL_ID: str = "openai/gpt-oss-120b"
    RADIO_ENABLED: bool = True
    RADIO_AUTO: bool = False
    RADIO_INTERVAL: int = 15
    RADIO_PROVIDER: str = "Chatterbox Multilingual TTS"
    RADIO_VOICE: str = "Tamil Gaming Host"
    RADIO_LANGUAGE: str = "ta-IN"
    RADIO_SPEED: float = 1.0
    RADIO_PITCH: str = "Normal"
    RADIO_ENERGY: str = "Energetic"
    RADIO_FORMAT: str = "WAV 48kHz Stereo"
    RADIO_OUTPUT_SOURCE: str = "AxiBot Radio Audio"
    RADIO_VOLUME: int = -8
    RADIO_DUCK_AUDIO: bool = True
    RADIO_DUCK_AMOUNT: int = -12
    RADIO_AUTO_APPROVE: bool = True
    CHATTERBOX_API_KEY: str = "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"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

def load_local_settings():
    storage_path = "storage/settings.json"
    
    # Ensure storage directory exists
    os.makedirs("storage", exist_ok=True)
    
    if os.path.exists(storage_path):
        try:
            with open(storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if hasattr(settings, k):
                        # Safely cast loaded values to the expected type
                        expected_type = type(getattr(settings, k))
                        if expected_type == bool:
                            setattr(settings, k, str(v) == "True" or v is True)
                        elif expected_type == int:
                            setattr(settings, k, int(v))
                        elif expected_type == float:
                            setattr(settings, k, float(v))
                        else:
                            setattr(settings, k, str(v))
                    # Sync to os.environ so other modules using os.getenv get the same value
                    os.environ[k] = str(v)
        except Exception as e:
            print(f"Error loading local settings.json: {e}")
    else:
        # If storage/settings.json doesn't exist yet, save settings initially (which syncs default values)
        save_local_settings()

def save_local_settings():
    storage_path = "storage/settings.json"
    data = {
        "YOUTUBE_CLIENT_SECRET_PATH": settings.YOUTUBE_CLIENT_SECRET_PATH,
        "YOUTUBE_TOKEN_PATH": settings.YOUTUBE_TOKEN_PATH,
        "YOUTUBE_STREAMER_TOKEN_PATH": settings.YOUTUBE_STREAMER_TOKEN_PATH,
        "STREAMER_CHANNEL_ID": settings.STREAMER_CHANNEL_ID,
        "STREAMER_CHANNEL_NAME": settings.STREAMER_CHANNEL_NAME,
        "NVIDIA_API_KEY": settings.NVIDIA_API_KEY,
        "NVIDIA_MODEL_ID": settings.NVIDIA_MODEL_ID,
        "BOT_NAME": settings.BOT_NAME,
        "COOLDOWN_SECONDS": settings.COOLDOWN_SECONDS,
        "ENABLE_DATABASE": settings.ENABLE_DATABASE,
        "ENABLE_COMMANDS": settings.ENABLE_COMMANDS,
        "RADIO_MODEL_ID": settings.RADIO_MODEL_ID,
        "RADIO_ENABLED": settings.RADIO_ENABLED,
        "RADIO_AUTO": settings.RADIO_AUTO,
        "RADIO_INTERVAL": settings.RADIO_INTERVAL,
        "RADIO_PROVIDER": settings.RADIO_PROVIDER,
        "RADIO_VOICE": settings.RADIO_VOICE,
        "RADIO_LANGUAGE": settings.RADIO_LANGUAGE,
        "RADIO_SPEED": settings.RADIO_SPEED,
        "RADIO_PITCH": settings.RADIO_PITCH,
        "RADIO_ENERGY": settings.RADIO_ENERGY,
        "RADIO_FORMAT": settings.RADIO_FORMAT,
        "RADIO_OUTPUT_SOURCE": settings.RADIO_OUTPUT_SOURCE,
        "RADIO_VOLUME": settings.RADIO_VOLUME,
        "RADIO_DUCK_AUDIO": settings.RADIO_DUCK_AUDIO,
        "RADIO_DUCK_AMOUNT": settings.RADIO_DUCK_AMOUNT,
        "RADIO_AUTO_APPROVE": settings.RADIO_AUTO_APPROVE,
        "CHATTERBOX_API_KEY": settings.CHATTERBOX_API_KEY
    }
    try:
        os.makedirs("storage", exist_ok=True)
        with open(storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        # Sync to os.environ
        for k, v in data.items():
            os.environ[k] = str(v)
    except Exception as e:
        print(f"Error saving local settings.json: {e}")

# Automatically load local settings on import
load_local_settings()
