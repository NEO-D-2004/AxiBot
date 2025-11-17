# auth_helper.py  -- Desktop (Installed) flow (recommended for local dev)

import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request  # <- FIX: import Request
from dotenv import load_dotenv

# load .env if present (optional)
load_dotenv()

# Scopes required (read + write chat)
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

TOKEN_PATH = os.getenv("TOKEN_PATH", "storage/token.json")
Path("storage").mkdir(parents=True, exist_ok=True)

def main():
    creds = None

    # If token file exists, load it
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception as e:
            print("Warning: failed to load existing token file:", e)
            creds = None

    # If no valid credentials, do the Installed App Flow
    if not creds or not creds.valid:
        # If we have expired credentials with a refresh token, refresh them
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print("Refresh failed, will run new authorization flow:", e)
                creds = None

        # Otherwise run the install flow to get new credentials
        if not creds:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError(
                    "Missing credentials.json. Download your OAuth client (Desktop) JSON "
                    "from Google Cloud Console and save as credentials.json in the project root."
                )
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            # run_local_server will open a browser and handle redirect on an ephemeral localhost port
            creds = flow.run_local_server(port=0, prompt="consent")

        # Save credentials for next run
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())
        print("Saved token to", TOKEN_PATH)

if __name__ == "__main__":
    main()
