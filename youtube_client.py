# youtube_client.py
"""
Robust, Pylance-friendly YouTube client for live chat bots.

Usage:
  from youtube_client import YouTubeClient
  yt = YouTubeClient()
  lc, vid = yt.get_active_live_chat_id()
  yt.poll_chat(lc, on_message)
"""

import json
import time
import traceback
from typing import Any, Callable, Optional, Tuple, cast

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from settings import TOKEN_PATH

# default scopes used to construct Credentials (must match those used when authorizing)
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def _safe_print(*args, **kwargs):
    print(*args, **kwargs)


class YouTubeClient:
    def __init__(self):
        # mark dynamic type for pylance
        self._creds: Optional[Credentials] = None
        self._youtube: Optional[Any] = None
        self._cached_live_chat_id: Optional[Tuple[Optional[str], Optional[str], float]] = None
        self._cache_ttl = 30  # seconds to cache activeLiveChatId to reduce API calls
        self._load_credentials_and_build()

    def _load_credentials_and_build(self):
        try:
            with open(TOKEN_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._creds = Credentials.from_authorized_user_info(data, DEFAULT_SCOPES)
            # build is dynamic; cast to Any to quiet static checker
            self._youtube = cast(Any, build("youtube", "v3", credentials=self._creds))
            _safe_print("YouTube client built successfully.")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Token file not found at {TOKEN_PATH}. Run auth_helper.py to create one."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load credentials or build YouTube client: {e}")

    def refresh_if_needed(self):
        """Refresh credentials if expired and refresh_token exists."""
        try:
            if self._creds and self._creds.expired and self._creds.refresh_token:
                _safe_print("Refreshing expired credentials...")
                from google.auth.transport.requests import Request

                self._creds.refresh(Request())
                # persist updated token
                with open(TOKEN_PATH, "w", encoding="utf-8") as f:
                    f.write(self._creds.to_json())
                _safe_print("Credentials refreshed and saved.")
                self._youtube = cast(Any, build("youtube", "v3", credentials=self._creds))
        except Exception as e:
            _safe_print("Failed to refresh credentials:", e)
            # don't raise here — caller will either retry or re-run auth flow

    def get_author_channel_info(self) -> dict:
        """Return channel list response for the account associated with the token."""
        self.refresh_if_needed()
        assert self._youtube is not None, "YouTube client not initialized"
        youtube = cast(Any, self._youtube)
        try:
            resp = youtube.channels().list(part="snippet,contentDetails", mine=True).execute()
            return resp
        except HttpError as e:
            _safe_print("YouTube API error in get_author_channel_info:", e)
            raise

    def get_active_live_chat_id(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Find the activeLiveChatId for the authorized channel.

        Strategy:
        1) channels().list(mine=True) -> get channelId
        2) search().list(eventType='live', channelId=...) -> find active live videoId
        3) videos().list(part='liveStreamingDetails', id=videoId) -> extract activeLiveChatId

        Returns (liveChatId | None, videoId | None)
        """
        # return cached if still fresh
        if self._cached_live_chat_id:
            live_chat_id, video_id, expiry = self._cached_live_chat_id
            if time.time() < expiry:
                return live_chat_id, video_id
            self._cached_live_chat_id = None

        self.refresh_if_needed()
        assert self._youtube is not None, "YouTube client not initialized"
        youtube = cast(Any, self._youtube)

        try:
            # 1) get the authorized channel id
            ch_resp = youtube.channels().list(part="id,snippet", mine=True, maxResults=1).execute()
            ch_items = ch_resp.get("items", [])
            if not ch_items:
                _safe_print("channels().list(mine=True) returned no items — token may not belong to a channel owner.")
                return None, None
            channel_id = ch_items[0]["id"]
            _safe_print(f"Authorized channel id: {channel_id}")

            # 2) search for live video(s) for this channel
            s = youtube.search().list(
                part="id,snippet",
                type="video",
                eventType="live",
                channelId=channel_id,
                maxResults=5,
            ).execute()
            s_items = s.get("items", [])
            if not s_items:
                _safe_print("No live search results for the channel (no active live video).")
                return None, None

            video_id = s_items[0]["id"].get("videoId")
            _safe_print(f"Found live video id: {video_id}")

            # 3) fetch liveStreamingDetails for the video
            v = youtube.videos().list(part="liveStreamingDetails", id=video_id).execute()
            v_items = v.get("items", [])
            if not v_items:
                _safe_print("videos().list returned no items for video id:", video_id)
                return None, video_id

            details = v_items[0].get("liveStreamingDetails", {}) or {}
            live_chat_id = details.get("activeLiveChatId") or details.get("liveChatId")
            if not live_chat_id:
                _safe_print("Video has liveStreamingDetails but no activeLiveChatId (chat might be disabled).")
                return None, video_id

            # cache briefly and return
            self._cached_live_chat_id = (live_chat_id, video_id, time.time() + self._cache_ttl)
            return live_chat_id, video_id

        except HttpError as e:
            _safe_print("HttpError in get_active_live_chat_id:", e)
            try:
                _safe_print("Error content:", e.content)
            except Exception:
                pass
            return None, None
        except Exception as e:
            _safe_print("Unexpected error in get_active_live_chat_id:", e)
            traceback.print_exc()
            return None, None

    def post_message(self, live_chat_id: str, text: str) -> dict:
        """Post a text message into a live chat."""
        if not live_chat_id:
            raise ValueError("live_chat_id is required")
        self.refresh_if_needed()
        assert self._youtube is not None, "YouTube client not initialized"
        youtube = cast(Any, self._youtube)

        body = {
            "snippet": {
                "liveChatId": live_chat_id,
                "type": "textMessageEvent",
                "textMessageDetails": {"messageText": text},
            }
        }
        try:
            res = youtube.liveChatMessages().insert(part="snippet", body=body).execute()
            return res
        except HttpError as e:
            _safe_print("HttpError posting message:", e)
            raise
        except Exception as e:
            _safe_print("Unexpected error posting message:", e)
            raise

    def poll_chat(self, live_chat_id: str, on_message: Callable[[dict], None], start_page_token: Optional[str] = None):
        """
        Poll live chat messages. Calls on_message(item) for each returned message.
        Honors pollingIntervalMillis returned by the API.
        """
        if not live_chat_id:
            raise ValueError("live_chat_id is required")
        self.refresh_if_needed()
        assert self._youtube is not None, "YouTube client not initialized"
        youtube = cast(Any, self._youtube)

        page_token = start_page_token
        while True:
            try:
                resp = youtube.liveChatMessages().list(
                    liveChatId=live_chat_id,
                    part="snippet,authorDetails",
                    pageToken=page_token,
                    maxResults=200,
                ).execute()

                items = resp.get("items", [])
                for it in items:
                    try:
                        on_message(it)
                    except Exception:
                        _safe_print("Error in on_message handler:")
                        traceback.print_exc()

                polling = resp.get("pollingIntervalMillis", 2000) / 1000.0
                page_token = resp.get("nextPageToken")
                if polling < 0.5:
                    polling = 0.5
                time.sleep(polling)
            except HttpError as e:
                _safe_print("HttpError while polling chat:", e)
                try:
                    _safe_print("Error content:", e.content)
                except Exception:
                    pass
                time.sleep(5)
            except Exception as e:
                _safe_print("Unexpected error while polling chat:", e)
                traceback.print_exc()
                time.sleep(5)


# quick debug when run directly
if __name__ == "__main__":
    yc = YouTubeClient()
    _safe_print("Author channel info (short):")
    try:
        ch = yc.get_author_channel_info()
        _safe_print(json.dumps(ch.get("items", []), indent=2)[:2000])
    except Exception as e:
        _safe_print("Error fetching channel info:", e)

    _safe_print("Trying to find active live chat id...")
    lc, vid = yc.get_active_live_chat_id()
    _safe_print("live_chat_id, video_id:", lc, vid)
