# settings.py
from dotenv import load_dotenv
import os
load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8080/oauth2callback")
TOKEN_PATH = os.getenv("TOKEN_PATH", "storage/token.json")
BOT_DISPLAY_NAME = os.getenv("BOT_DISPLAY_NAME", "YourBot")
