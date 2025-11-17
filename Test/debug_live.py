from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from settings import TOKEN_PATH
SCOPES = ["https://www.googleapis.com/auth/youtube","https://www.googleapis.com/auth/youtube.force-ssl"]

creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
yt = build("youtube", "v3", credentials=creds)

print("=== channels().list(mine=True) ===")
print(yt.channels().list(part="snippet,id", mine=True).execute())

print("=== search().list(eventType=live, mine=True) ===")
print(yt.search().list(part="id,snippet", type="video", eventType="live", mine=True, maxResults=10).execute())

# If you have a channel id, try with channelId explicitly:
ch = yt.channels().list(part="id", mine=True).execute()
if ch.get("items"):
    cid = ch["items"][0]["id"]
    print("=== search for channelId ===", cid)
    print(yt.search().list(part="id,snippet", type="video", eventType="live", channelId=cid, maxResults=10).execute())
