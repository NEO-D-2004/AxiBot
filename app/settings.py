from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    YOUTUBE_CLIENT_SECRET_PATH: str = "client_secret.json"
    YOUTUBE_TOKEN_PATH: str = "storage/token.json"
    STREAMER_CHANNEL_ID: str # Channel ID of the streamer to watch
    NVIDIA_API_KEY: str
    NVIDIA_MODEL_ID: str = "google/gemma-3-4b-it"  # Defaulting to gemma 3
    BOT_NAME: str = "AxiBot"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
