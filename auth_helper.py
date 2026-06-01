import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes required for the bot
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

def authenticate_youtube(token_path=None):
    # Load settings from .env manually or via python-dotenv if available
    from dotenv import load_dotenv
    load_dotenv()
    
    client_secret_path = os.getenv("YOUTUBE_CLIENT_SECRET_PATH", "client_secret.json")
    if token_path is None:
        token_path = os.getenv("YOUTUBE_TOKEN_PATH", "storage/token.json")

    # Check if client secret exists
    if not os.path.exists(client_secret_path):
        raise FileNotFoundError(
            f"Client secret file not found at '{os.path.abspath(client_secret_path)}'. "
            "Please download your OAuth client ID JSON from Google Cloud Console and save it as 'client_secret.json' in the application folder."
        )

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_path, SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
            print(f"Token saved to {token_path}")

    print("Authentication successful!")

if __name__ == "__main__":
    authenticate_youtube()
