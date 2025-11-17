from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_authorized_user_file("storage/token.json", scopes=[
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
])
youtube = build("youtube", "v3", credentials=creds)
res = youtube.search().list(part="id", eventType="live", type="video", maxResults=1).execute()
print("API OK, response keys:", list(res.keys()))
