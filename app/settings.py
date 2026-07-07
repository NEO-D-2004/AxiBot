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
    NVIDIA_MODEL_ID: str = "qwen/qwen3.5-122b-a10b"  # Defaulting to qwen/qwen3.5-122b-a10b
    BOT_NAME: str = "AxiBot"
    COOLDOWN_SECONDS: int = 60
    ENABLE_DATABASE: bool = True
    ENABLE_COMMANDS: bool = True

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
        "ENABLE_COMMANDS": settings.ENABLE_COMMANDS
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
