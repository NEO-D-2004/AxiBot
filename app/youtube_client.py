import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.settings import settings

class YouTubeClient:
    CACHE_FILE = "storage/cache.json"

    def __init__(self):
        self.youtube = self._authenticate()
        self.live_chat_id = None
        self.video_id = None
        self._ensure_storage_dir()

    def _ensure_storage_dir(self):
        if not os.path.exists("storage"):
            os.makedirs("storage")

    def _authenticate(self):
        token_path = settings.YOUTUBE_TOKEN_PATH
        if not os.path.exists(token_path):
            print(f"Error: Token file not found at {token_path}. Run auth_helper.py first.")
            return None

        try:
            creds = Credentials.from_authorized_user_file(token_path)
            return build("youtube", "v3", credentials=creds)
        except Exception as e:
            # Check for RefreshError (Token expired/revoked)
            if "Token has been expired or revoked" in str(e):
                print(f"Error: Token expired. Deleting {token_path}. Please run auth_helper.py again.")
                if os.path.exists(token_path):
                    os.remove(token_path)
            else:
                print(f"YouTube Auth Error: {e}")
            return None

    def _load_cache(self):
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self, data):
        try:
            with open(self.CACHE_FILE, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Failed to save cache: {e}")

    def get_live_chat_id_for_channel(self, channel_id):
        """
        Searches for the active live stream on the given channel ID and returns its liveChatId.
        Checks cache first to save API quota.
        """
        if not self.youtube:
            return None

        # 1. Check Cache
        cache = self._load_cache()
        cached_video_id = cache.get("video_id")
        
        if cached_video_id:
            print(f"Checking cached live stream: {cached_video_id}")
            # This call costs 1 unit vs 100 for search
            chat_id = self.get_live_chat_id_by_video_id(cached_video_id)
            if chat_id:
                print(f"Found active live stream from cache: {cached_video_id}")
                self.video_id = cached_video_id
                return chat_id
            else:
                print("Cached stream ended or invalid. Performing full search...")

        print(f"Searching for active live stream on channel: {channel_id}...")
        try:
            # 2. Search for live video on the channel
            search_response = self.youtube.search().list(
                part="id",
                channelId=channel_id,
                eventType="live",
                type="video",
                maxResults=1
            ).execute()
            
            items = search_response.get("items", [])
            if not items:
                print("No active live stream found for this channel.")
                return None
                
            video_id = items[0]["id"]["videoId"]
            print(f"Found active live stream: {video_id}")
            
            # 3. Get the liveChatId for that video
            chat_id = self.get_live_chat_id_by_video_id(video_id)
            
            if chat_id:
                # Update Cache
                self._save_cache({"video_id": video_id, "live_chat_id": chat_id})
                self.video_id = video_id
                
            return chat_id
            
        except HttpError as e:
            print(f"YouTube Search Error: {e}")
            return None

    def get_live_chat_id_by_video_id(self, video_id):
        if not self.youtube:
            return None
            
        try:
            request = self.youtube.videos().list(
                part="liveStreamingDetails",
                id=video_id
            )
            response = request.execute()
            
            if response["items"]:
                details = response["items"][0].get("liveStreamingDetails")
                if details:
                    self.live_chat_id = details.get("activeLiveChatId")
                    # If the stream is over, activeLiveChatId might be missing or different logic
                    if self.live_chat_id:
                        return self.live_chat_id
            
            print("No active live chat found for this video.")
            return None
            
        except HttpError as e:
            print(f"YouTube API Error: {e}")
            return None

    def send_message(self, message_text, live_chat_id=None):
        target_chat_id = live_chat_id or self.live_chat_id
        
        if not self.youtube or not target_chat_id:
            print("Cannot send message: No active YouTube connection or Live Chat ID.")
            return

        try:
            request = self.youtube.liveChatMessages().insert(
                part="snippet",
                body={
                    "snippet": {
                        "liveChatId": target_chat_id,
                        "type": "textMessageEvent",
                        "textMessageDetails": {
                            "messageText": message_text
                        }
                    }
                }
            )
            response = request.execute()
            print(f"Message sent: {message_text}")
            return response
            
        except HttpError as e:
            print(f"Failed to send message: {e}")

    def get_video_details(self, video_id):
        """
        Fetches the Title and Channel Name of the video/stream.
        """
        if not self.youtube:
            return None
        
        try:
            request = self.youtube.videos().list(
                part="snippet",
                id=video_id
            )
            response = request.execute()
            
            if response["items"]:
                snippet = response["items"][0].get("snippet", {})
                return {
                    "title": snippet.get("title"),
                    "channel_title": snippet.get("channelTitle")
                }
            return None
        except Exception as e:
            print(f"Failed to get video details: {e}")
            return None

    def get_concurrent_viewers(self, video_id):
        """
        Fetches the current number of concurrent viewers.
        """
        if not self.youtube:
            return 0
            
        try:
            request = self.youtube.videos().list(
                part="liveStreamingDetails",
                id=video_id
            )
            response = request.execute()
            
            if response["items"]:
                details = response["items"][0].get("liveStreamingDetails", {})
                return int(details.get("concurrentViewers", 0))
            return 0
        except HttpError as e:
            print(f"Failed to get viewer count: {e}")
            return 0
        except Exception as e:
            print(f"Error getting viewers: {e}")
            return 0

    def get_video_likes(self, video_id):
        """
        Fetches the current like count of the video.
        """
        if not self.youtube:
            return 0
            
        try:
            request = self.youtube.videos().list(
                part="statistics",
                id=video_id
            )
            response = request.execute()
            if response["items"]:
                stats = response["items"][0].get("statistics", {})
                return int(stats.get("likeCount", 0))
            return 0
        except Exception as e:
            print(f"Failed to get likes: {e}")
            return 0

    def get_channel_subscribers(self, channel_id):
        """
        Fetches the current subscriber count of the channel.
        """
        if not self.youtube:
            return 0
            
        try:
            request = self.youtube.channels().list(
                part="statistics",
                id=channel_id
            )
            response = request.execute()
            if response["items"]:
                stats = response["items"][0].get("statistics", {})
                return int(stats.get("subscriberCount", 0))
            return 0
        except Exception as e:
            print(f"Failed to get subscribers: {e}")
            return 0

        except Exception as e:
            print(f"Failed to get subscribers: {e}")
            return 0

    def get_video_stats(self, video_id):
        """
        Fetches both concurrent viewers and like count in one call.
        Returns: (viewers, likes)
        """
        if not self.youtube:
            return 0, 0
            
        try:
            request = self.youtube.videos().list(
                part="liveStreamingDetails,statistics",
                id=video_id
            )
            response = request.execute()
            if response["items"]:
                item = response["items"][0]
                live_details = item.get("liveStreamingDetails", {})
                stats = item.get("statistics", {})
                
                viewers = int(live_details.get("concurrentViewers", 0))
                likes = int(stats.get("likeCount", 0))
                return viewers, likes
            return 0, 0
        except Exception as e:
            # print(f"Failed to get video stats: {e}")
            return 0, 0

    def delete_message(self, message_id):
        """
        Deletes (hides) a message from the live chat.
        """
        if not self.youtube:
            return
        try:
            self.youtube.liveChatMessages().delete(id=message_id).execute()
            print(f"Deleted message: {message_id}")
        except HttpError as e:
            print(f"Failed to delete message: {e}")

    def timeout_user(self, user_channel_id, duration_seconds=300, live_chat_id=None):
        """
        Timeouts a user for a specified duration.
        """
        target_chat_id = live_chat_id or self.live_chat_id
        if not self.youtube or not target_chat_id:
            return

        try:
            self.youtube.liveChatBans().insert(
                part="snippet",
                body={
                    "snippet": {
                        "liveChatId": target_chat_id,
                        "type": "temporary",
                        "banDurationSeconds": duration_seconds,
                        "bannedUserDetails": {
                            "channelId": user_channel_id
                        }
                    }
                }
            ).execute()
            print(f"Timed out user {user_channel_id} for {duration_seconds}s")
        except HttpError as e:
            print(f"Failed to timeout user: {e}")

if __name__ == "__main__":
    # Test standalone (Requires a valid live video ID)
    client = YouTubeClient()
    # video_id = "YOUR_LIVE_VIDEO_ID"
    # if client.get_live_chat_id_by_video_id(video_id):
    #     client.send_message("Hello from AxiBot!")
