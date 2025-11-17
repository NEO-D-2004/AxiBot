# main.py
import threading
import re
import time
import traceback
from fastapi import FastAPI
from youtube_client import YouTubeClient
from gemini_client import generate_reply
from settings import BOT_DISPLAY_NAME

app = FastAPI()
yt = YouTubeClient()

# mention regex: matches @YourBot (case-insensitive) with word boundary
MENTION_RE = re.compile(rf"@{re.escape(BOT_DISPLAY_NAME)}\b", re.IGNORECASE)

# simple in-memory cooldown store: {author_channel_id: last_ts}
cooldowns = {}
COOLDOWN_SECONDS = 30  # change as you like

# limit reply length to avoid long posts
MAX_REPLY_CHARS = 300

def safe_print(*args, **kwargs):
    """Helper wrapper for consistent logging to console."""
    print(*args, **kwargs)

def handle_message(item: dict):
    """
    Called for every chat message arriving from poller.
    - Detects mention
    - Applies cooldown
    - Builds a short prompt to Gemini
    - Posts the reply
    """
    try:
        snippet = item.get("snippet", {}) or {}
        author = item.get("authorDetails", {}) or {}
        text = snippet.get("textMessageDetails", {}).get("messageText", "")
        if not text:
            return

        # Avoid replying to self: simple check for bot display name in author name
        display_name = author.get("displayName", "") or ""
        if BOT_DISPLAY_NAME.lower() in display_name.lower():
            return

        # If not mentioned, ignore
        if not MENTION_RE.search(text):
            return

        # Author id for cooldown; fallback to display name if channelId not present
        author_id = author.get("channelId") or author.get("channelId") or display_name

        # Cooldown check
        now = time.time()
        last_ts = cooldowns.get(author_id, 0)
        if now - last_ts < COOLDOWN_SECONDS:
            safe_print(f"Skipping reply due cooldown for {display_name}")
            return
        cooldowns[author_id] = now

        # Remove mention from user text for a clean prompt
        user_text = MENTION_RE.sub("", text).strip()
        if not user_text:
            # if nothing after mention, send a simple help message
            user_text = "Hello! How can I help you?"

        # Build prompt: keep it short and instruct model to be brief
        prompt = f"You are a friendly YouTube chat helper. A viewer asked: \"{user_text}\". Reply in 1-2 short sentences, friendly and concise."

        safe_print(f"Generating reply for: {user_text!r} (author={display_name})")
        try:
            reply = generate_reply(prompt)
        except Exception as exc:
            safe_print("Gemini generation error:", exc)
            traceback.print_exc()
            reply = "Sorry, I'm having trouble answering right now."

        # sanitize length
        if len(reply) > MAX_REPLY_CHARS:
            reply = reply[:MAX_REPLY_CHARS].rsplit(".", 1)[0] + "."

        # Optionally prefix the reply to address the viewer by name
        display_safe = display_name.split(" ")[0] if display_name else ""
        if display_safe:
            final_text = f"@{display_safe} {reply}"
        else:
            final_text = reply

        # Get current active live chat id (caches can be added later)
        live_chat_id, vid = yt.get_active_live_chat_id()
        if not live_chat_id:
            safe_print("No active live chat found when trying to reply.")
            return

        # Post the message
        try:
            res = yt.post_message(live_chat_id, final_text)
            safe_print("Posted reply:", final_text)
        except Exception as exc:
            safe_print("Failed to post reply:", exc)
            traceback.print_exc()

    except Exception as e:
        safe_print("Unhandled error in handle_message:", e)
        traceback.print_exc()

def background_poller():
    """
    Main loop:
    - Find active live chat id
    - Call poll_chat(live_chat_id, handle_message)
    - If no active stream, sleep and retry
    """
    safe_print("Background poller started.")
    while True:
        try:
            live_chat_id, vid = yt.get_active_live_chat_id()
            if live_chat_id:
                safe_print("Watching live chat:", live_chat_id, "video:", vid)
                # poll_chat blocks in a loop and calls handle_message for each item
                yt.poll_chat(live_chat_id, handle_message)
            else:
                safe_print("No active live stream found. Sleeping 10s.")
                time.sleep(10)
        except Exception as e:
            safe_print("Poller encountered an error:", e)
            traceback.print_exc()
            # small backoff on errors
            time.sleep(5)

@app.on_event("startup")
def start_background_thread():
    t = threading.Thread(target=background_poller, daemon=True)
    t.start()

@app.get("/")
def root():
    return {"status": "running"}
