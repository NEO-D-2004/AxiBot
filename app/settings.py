from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    YOUTUBE_CLIENT_SECRET_PATH: str = "client_secret.json"
    YOUTUBE_TOKEN_PATH: str = "storage/token.json"
    YOUTUBE_STREAMER_TOKEN_PATH: str = "storage/streamer_token.json"
    STREAMER_CHANNEL_ID: str = "" # Channel ID of the streamer to watch
    NVIDIA_API_KEY: str = ""
    NVIDIA_MODEL_ID: str = "google/gemma-3n-e2b-it"  # Defaulting to gemma-3n-e2b-it
    BOT_NAME: str = "AxiBot"
    COOLDOWN_SECONDS: int = 60
    ENABLE_DATABASE: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
