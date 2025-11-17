# debug_youtube.py
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from settings import TOKEN_PATH

SCOPES = ["https://www.googleapis.com/auth/youtube",
          "https://www.googleapis.com/auth/youtube.force-ssl"]

creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
youtube = build("youtube", "v3", credentials=creds)

# 1) Show authorized channel info (confirms which account)
ch = youtube.channels().list(part="snippet,contentDetails", mine=True).execute()
print("CHANNEL LIST RESPONSE KEYS:", list(ch.keys()))
print(json.dumps(ch.get("items", []), indent=2))

# 2) Try to list active live broadcasts (preferred, reliable)
live = youtube.liveBroadcasts().list(part="id,snippet,contentDetails", broadcastStatus="active", mine=True).execute()
print("LIVE BROADCASTS RESPONSE KEYS:", list(live.keys()))
print(json.dumps(live.get("items", []), indent=2))

# 3) Fallback: search for live video if liveBroadcasts is empty
search = youtube.search().list(part="id,snippet", type="video", eventType="live", mine=True, maxResults=5).execute()
print("SEARCH (live) RESPONSE KEYS:", list(search.keys()))
print(json.dumps(search.get("items", []), indent=2))
