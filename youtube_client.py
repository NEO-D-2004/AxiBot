"""
Optimized YouTube client to reduce quota usage and improve polling efficiency.

Key improvements:
- Cache channel id for a longer TTL to avoid repeated channels().list calls.
- Keep previously discovered (liveChatId, videoId) in a short TTL cache to avoid re-discovery.
- Expose set_channel_id(channel_id) so you can configure a channel id directly (useful for separate bot accounts).
- Respect and honor pollingIntervalMillis returned by the API, with configurable minimum and maximum.
- Add an adaptive polling helper poll_chat_with_quota(target_units, duration_seconds) which computes a safe sleep interval to spread allowed quota over a timeframe.
- Better error handling + exponential backoff on HttpError responses.
- Persist refreshed tokens only when refresh actually occurs (keeps disk writes minimal).

Usage examples (short):
  yt = YouTubeClient()
  yt.set_channel_id('UCBLA...')  # optional if you already know the channel id
  live_chat_id, video_id = yt.get_active_live_chat_id()
  yt.poll_chat(live_chat_id, on_message)

For quota-aware polling that aims to spend `target_units` over `duration_seconds`:
  yt.poll_chat_with_quota(live_chat_id, on_message, target_units=10000, duration_seconds=3*3600)

"""

import json
import time
import traceback
from typing import Any, Callable, Optional, Tuple, cast

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from settings import TOKEN_PATH

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def _safe_print(*args, **kwargs):
    print(*args, **kwargs)


class YouTubeClient:
    def __init__(self):
        self._creds: Optional[Credentials] = None
        self._youtube: Optional[Any] = None

        # cached (live_chat_id, video_id, expiry)
        self._cached_live_chat_id: Optional[Tuple[Optional[str], Optional[str], float]] = None
        self._cache_ttl = 30  # seconds to cache activeLiveChatId (short)

        # cached channel id to avoid calling channels().list repeatedly
        self._cached_channel_id: Optional[Tuple[str, float]] = None
        self._channel_cache_ttl = 3600  # cache channel id for 1 hour by default

        # polling config
        self.min_poll_seconds = 2.0  # don't poll faster than this
        self.max_poll_seconds = 60.0  # throttle upper bound

        self._load_credentials_and_build()

    def _load_credentials_and_build(self):
        try:
            with open(TOKEN_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._creds = Credentials.from_authorized_user_info(data, DEFAULT_SCOPES)
            self._youtube = cast(Any, build("youtube", "v3", credentials=self._creds))
            _safe_print("YouTube client built successfully.")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Token file not found at {TOKEN_PATH}. Run auth_helper.py to create one."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load credentials or build YouTube client: {e}")

    def refresh_if_needed(self):
        """Refresh credentials if expired and refresh_token exists. Persist only when refreshed."""
        try:
            if self._creds and self._creds.expired and self._creds.refresh_token:
                _safe_print("Refreshing expired credentials...")
                from google.auth.transport.requests import Request

                before = self._creds.token
                self._creds.refresh(Request())
                after = self._creds.token
                if after != before:
                    # persist updated token only when it changed
                    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
                        f.write(self._creds.to_json())
                    _safe_print("Credentials refreshed and saved.")
                    # rebuild client with refreshed creds
                    self._youtube = cast(Any, build("youtube", "v3", credentials=self._creds))
        except Exception as e:
            _safe_print("Failed to refresh credentials:", e)

    def set_channel_id(self, channel_id: str, ttl: Optional[int] = None):
        """Manually set the channel id; useful when you have a separate bot account or want to avoid channels().list()."""
        expiry = time.time() + (ttl if ttl is not None else self._channel_cache_ttl)
        self._cached_channel_id = (channel_id, expiry)
        _safe_print(f"Manually set channel id and cached for {ttl or self._channel_cache_ttl} seconds")

    def _get_channel_id(self) -> Optional[str]:
        """Return cached channel id or fetch via channels().list(mine=true).
        This centralizes the channels call so it happens at most once per TTL."""
        # cached
        if self._cached_channel_id:
            channel_id, expiry = self._cached_channel_id
            if time.time() < expiry:
                return channel_id
            self._cached_channel_id = None

        # otherwise fetch (this is the only place that calls channels().list)
        self.refresh_if_needed()
        assert self._youtube is not None, "YouTube client not initialized"
        youtube = cast(Any, self._youtube)
        try:
            resp = youtube.channels().list(part="id", mine=True, maxResults=1).execute()
            items = resp.get("items", [])
            if not items:
                _safe_print("channels().list(mine=True) returned no items — token may not belong to a channel owner.")
                return None
            channel_id = items[0]["id"]
            self._cached_channel_id = (channel_id, time.time() + self._channel_cache_ttl)
            _safe_print(f"Authorized channel id: {channel_id}")
            return channel_id
        except HttpError as e:
            _safe_print("HttpError in _get_channel_id:", e)
            try:
                _safe_print("Error content:", e.content)
            except Exception:
                pass
            return None
        except Exception as e:
            _safe_print("Unexpected error in _get_channel_id:", e)
            traceback.print_exc()
            return None

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
        """Find the activeLiveChatId for the authorized channel.

        Strategy (same as before) but we:
        - use cached channel id if available
        - use maxResults=1 on search to lower cost
        - cache (live_chat_id, video_id) briefly
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
            # 1) get the authorized channel id (centralized method)
            channel_id = self._get_channel_id()
            if not channel_id:
                return None, None

            # 2) search for live video(s) for this channel (only 1 result needed)
            s = youtube.search().list(
                part="id",
                type="video",
                eventType="live",
                channelId=channel_id,
                maxResults=1,
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

    def poll_chat(self, live_chat_id: str, on_message: Callable[[dict], None], start_page_token: Optional[str] = None,
                  min_poll_seconds: Optional[float] = None, max_poll_seconds: Optional[float] = None):
        """Poll live chat messages.

        - Honors pollingIntervalMillis returned by the API.
        - Applies a configurable lower bound (min_poll_seconds).
        - Implements simple exponential backoff on repeated HttpErrors.
        """
        if not live_chat_id:
            raise ValueError("live_chat_id is required")
        self.refresh_if_needed()
        assert self._youtube is not None, "YouTube client not initialized"
        youtube = cast(Any, self._youtube)

        page_token = start_page_token
        error_backoff = 1.0
        min_poll = min_poll_seconds if min_poll_seconds is not None else self.min_poll_seconds
        max_poll = max_poll_seconds if max_poll_seconds is not None else self.max_poll_seconds

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

                # API tells us how often to poll
                polling = resp.get("pollingIntervalMillis", 2000) / 1000.0
                # enforce bounds
                if polling < min_poll:
                    polling = min_poll
                if polling > max_poll:
                    polling = max_poll

                page_token = resp.get("nextPageToken")

                # reset backoff on success
                error_backoff = 1.0
                time.sleep(polling)

            except HttpError as e:
                _safe_print("HttpError while polling chat:", e)
                try:
                    _safe_print("Error content:", e.content)
                except Exception:
                    pass
                # exponential backoff then continue
                time.sleep(min(max(1.0, error_backoff), max_poll))
                error_backoff = min(error_backoff * 2.0, max_poll)
            except Exception as e:
                _safe_print("Unexpected error while polling chat:", e)
                traceback.print_exc()
                time.sleep(min(max(1.0, error_backoff), max_poll))
                error_backoff = min(error_backoff * 2.0, max_poll)

    def poll_chat_with_quota(self, live_chat_id: str, on_message: Callable[[dict], None],
                             target_units: int = 10000, duration_seconds: int = 3 * 3600,
                             units_per_request: int = 5):
        """A convenience helper that computes an appropriate sleep interval so that
        `target_units` will be consumed over `duration_seconds`, assuming each poll costs `units_per_request`.

        This only controls the *polling* frequency. The API may still recommend a different pollingIntervalMillis; this
        helper uses the maximum between the API-suggested value and the computed quota-driven interval.
        """
        if not live_chat_id:
            raise ValueError("live_chat_id is required")
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be > 0")

        # compute allowed requests
        allowed_requests = max(1, target_units // max(1, units_per_request))
        interval_by_quota = duration_seconds / allowed_requests
        # clamp to reasonable bounds
        interval_by_quota = max(self.min_poll_seconds, min(interval_by_quota, self.max_poll_seconds))

        _safe_print(f"Quota helper: target_units={target_units}, units_per_request={units_per_request},"
                    f" allowed_requests={allowed_requests}, interval_by_quota={interval_by_quota:.2f}s")

        # wrapper on_message that keeps user's handler unchanged
        def _on_message(it: dict):
            try:
                on_message(it)
            except Exception:
                _safe_print("Error in on_message handler:")
                traceback.print_exc()

        # Now poll but ensure we never sleep less than interval_by_quota
        self.poll_chat(live_chat_id, _on_message, min_poll_seconds=interval_by_quota)


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
