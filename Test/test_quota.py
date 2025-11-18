import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Path to your token.json or credentials
TOKEN_PATH = "../storage/token.json"

# YouTube API costs (Google official)
COST_TABLE = {
    "search.list": 100,
    "videos.list": 1,
    "liveChatMessages.list": 5,
    "liveChatMessages.insert": 50,
    "channels.list": 1,
}

# Global counter
quota_used = 0


def add_cost(api_name):
    global quota_used
    quota_used += COST_TABLE.get(api_name, 0)


def build_client():
    """Build YT client and wrap execution to count quota usage."""
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    creds = Credentials.from_authorized_user_info(data)

    yt = build("youtube", "v3", credentials=creds)

    # Wrap each endpoint method to track quota
    original_search_list = yt.search().list

    def wrapped_search_list(*args, **kwargs):
        add_cost("search.list")
        return original_search_list(*args, **kwargs)

    yt.search().list = wrapped_search_list

    original_videos_list = yt.videos().list
    yt.videos().list = lambda *a, **k: (add_cost("videos.list") or original_videos_list(*a, **k))

    original_channels_list = yt.channels().list
    yt.channels().list = lambda *a, **k: (add_cost("channels.list") or original_channels_list(*a, **k))

    original_chat_list = yt.liveChatMessages().list
    yt.liveChatMessages().list = lambda *a, **k: (add_cost("liveChatMessages.list") or original_chat_list(*a, **k))

    original_chat_insert = yt.liveChatMessages().insert
    yt.liveChatMessages().insert = lambda *a, **k: (add_cost("liveChatMessages.insert") or original_chat_insert(*a, **k))

    return yt


def run_quota_test():
    global quota_used
    quota_used = 0

    yt = build_client()

    print("\n--- Running Test API Calls ---")

    # Example calls (safe + low impact)
    try:
        yt.channels().list(part="id", mine=True).execute()
        yt.search().list(q="test", part="id", maxResults=1).execute()
        yt.videos().list(part="snippet", id="Ks-_Mh1QhMc").execute()

    except Exception as e:
        print("Some API calls failed:", e)

    print("\n--- Quota Report ---")
    print(f"Units used in this test      : {quota_used}")
    print(f"Remaining if limit = 10000   : {10000 - quota_used}")
    print("-------------------------------\n")


if __name__ == "__main__":
    run_quota_test()
