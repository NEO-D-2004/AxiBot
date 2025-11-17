# auth_helper.py
import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv()  # if you store SCOPES or TOKEN_PATH in .env

# Scopes you need (adjust if you need write access)
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/youtube.force-ssl"]

# token path (default to storage/token.json)
TOKEN_PATH = os.getenv("TOKEN_PATH", "storage/token.json")
Path("storage").mkdir(parents=True, exist_ok=True)

def main():
    creds = None
    # load existing token if available
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If no (valid) credentials, do the installed app flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            # Desktop clients: run_local_server opens a browser and completes the flow.
            # port=0 uses an available ephemeral port (no need to match console).
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())
        print(f"Saved token to {TOKEN_PATH}")

if __name__ == "__main__":
    main()
