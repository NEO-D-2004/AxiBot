import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.settings import settings
from app.youtube_client import YouTubeClient
from app.router import MessageRouter

async def main():
    print(f"=== Starting {settings.BOT_NAME} ===")
    
    # 1. Initialize Clients
    print("Initializing clients...")
    from app.nvidia_client import NvidiaClient
    gemini = NvidiaClient()
    
    youtube = YouTubeClient()
    
    # 2. Find Active Live Chat
    # We need to find the chat ID before we start listening, 
    # so we know where to post replies.
    try:
        if settings.STREAMER_CHANNEL_ID:
            print(f"Auto-detecting live stream for channel: {settings.STREAMER_CHANNEL_ID}")
            chat_id = youtube.get_live_chat_id_for_channel(settings.STREAMER_CHANNEL_ID)
            if chat_id:
                print(f"Connected to Live Chat ID: {chat_id}")
                youtube.send_message("Hey Viewers Now Iam active you can chat with me by mentioning me...")
                
                # Fetch Stream Context for AI
                if youtube.video_id:
                    details = youtube.get_video_details(youtube.video_id)
                    if details:
                        print(f"Stream Context: {details.get('title')} | Channel: {details.get('channel_title')}")
                        # Update the AI client with this context
                        if hasattr(gemini, 'stream_context'):
                            gemini.stream_context = details
            else:
                print("WARNING: No active live stream found. The bot will NOT be able to reply.")
                # We continue anyway, maybe they just want to test reading?
                # Or maybe we should retry periodically? For MVP, we warn.
        else:
            print("ERROR: STREAMER_CHANNEL_ID not set in .env")
            return
            
    except Exception as e:
        error_str = str(e)
        if "Token has been expired" in error_str or "invalid_grant" in error_str or "revoked" in error_str:
            print("\n❌ CRITICAL AUTH ERROR: YouTube Token Expired!")
            print(f"Deleting invalid token file at: {settings.YOUTUBE_TOKEN_PATH}")
            if os.path.exists(settings.YOUTUBE_TOKEN_PATH):
                os.remove(settings.YOUTUBE_TOKEN_PATH)
            print("Please run 'python auth_helper.py' to re-authenticate.")
            return
        else:
            print(f"Error during initialization: {error_str}")
            # raise # Optionally suppress raise if we want to debug, but raising is correct.
            raise

    # 3. Setup Router with clients
    router = MessageRouter(gemini_client=gemini, youtube_client=youtube)

    # 4. Setup Listeners
    async def on_event(event_data):
        await router.route_message(event_data)
    
    # Import locally to avoid circular imports if any, or just for clarity
    from app.youtube_listener import YouTubeChatListener
    yt_listener = YouTubeChatListener(youtube_client=youtube, callback=on_event)

    engagement = None
    from app.engagement import EngagementManager
    engagement = EngagementManager(llm_client=gemini)

    # 5. Start Event Loops
    print("Starting Listeners (Native YouTube)...")
    
    # Background task for engagement
    async def engagement_loop():
        print("Starting Engagement Loop...")
        while True:
            try:
                if youtube.video_id:
                    viewers, likes = youtube.get_video_stats(youtube.video_id)
                    
                    # Assume channel ID from settings or fetch from video details if needed
                    # ideally we store channel_id in youtube client once found
                    channel_id = settings.STREAMER_CHANNEL_ID
                    subs = youtube.get_channel_subscribers(channel_id) if channel_id else 0
                    
                    # 1. Check Targets (Highest Priority)
                    target_msg = await engagement.check_targets(likes, subs)
                    if target_msg:
                        print(f"Target Met: {target_msg}")
                        youtube.send_message(target_msg)
                        # Skip other engagement this turn to avoid spamming
                        await asyncio.sleep(60)
                        continue

                    # 2. Check Triggers (Spikes)
                    msg = await engagement.check_triggers(viewers)
                    if not msg:
                        # 3. Periodic Message
                        msg = await engagement.get_next_message()
                    
                    if msg:
                        print(f"Engagement Triggered: {msg}")
                        youtube.send_message(msg)
                        
                await asyncio.sleep(120) # Check every 2 minutes (Quota Optimization)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Engagement Loop Error: {e}")
                await asyncio.sleep(60)

    try:
        # Run listeners and engagement loop concurrently
        await asyncio.gather(
            yt_listener.start(),
            engagement_loop()
        )
    except asyncio.CancelledError:
        print("Bot stopping...")
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot Interrupted.")
