# youtube_client.py
import time, json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from settings import TOKEN_PATH

SCOPES = ["https://www.googleapis.com/auth/youtube"]

def load_creds():
    with open(TOKEN_PATH, "r") as f:
        data = json.load(f)
    return Credentials.from_authorized_user_info(data, SCOPES)

class YouTubeClient:
    def __init__(self):
        self.creds = load_creds()
        self.youtube = build("youtube", "v3", credentials=self.creds)

    def get_active_live_chat_id(self, channel_id=None):
        res = self.youtube.search().list(
            part="id",
            channelId=channel_id,
            eventType="live",
            type="video",
            maxResults=1
        ).execute()
        items = res.get("items", [])
        if not items:
            return None, None
        video_id = items[0]["id"]["videoId"]
        v = self.youtube.videos().list(part="liveStreamingDetails", id=video_id).execute()
        details = v.get("items", [])[0].get("liveStreamingDetails", {})
        return details.get("activeLiveChatId"), video_id

    def post_message(self, live_chat_id, text):
        body = {
            "snippet": {
                "liveChatId": live_chat_id,
                "type": "textMessageEvent",
                "textMessageDetails": {"messageText": text}
            }
        }
        res = self.youtube.liveChatMessages().insert(part="snippet", body=body).execute()
        return res

    def poll_chat(self, live_chat_id, on_message):
        page_token = None
        while True:
            resp = self.youtube.liveChatMessages().list(
                liveChatId=live_chat_id,
                part="snippet,authorDetails",
                pageToken=page_token,
                maxResults=200
            ).execute()
            items = resp.get("items", [])
            for it in items:
                on_message(it)
            polling = resp.get("pollingIntervalMillis", 2000)/1000.0
            page_token = resp.get("nextPageToken")
            time.sleep(polling)
