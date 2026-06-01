import os
import sys
import json
import asyncio
import threading
from datetime import datetime
import webview
from dotenv import load_dotenv

# Path resolution for PyInstaller
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Handle current working directory for executable persistence
if hasattr(sys, '_MEIPASS'):
    exe_dir = os.path.dirname(sys.executable)
    os.chdir(exe_dir)

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Log capture to stream stdout/stderr into GUI
class LogCapture:
    def __init__(self, max_logs=400):
        self.logs = []
        self.max_logs = max_logs
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def write(self, message):
        if message.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message.strip()}"
            self.logs.append(log_entry)
            if len(self.logs) > self.max_logs:
                self.logs.pop(0)
        try:
            self.original_stdout.write(message)
        except Exception:
            try:
                # Fallback to replace unencodable characters for the Windows console
                encoding = getattr(self.original_stdout, 'encoding', 'utf-8') or 'utf-8'
                safe_message = message.encode(encoding, errors='replace').decode(encoding)
                self.original_stdout.write(safe_message)
            except Exception:
                pass

    def flush(self):
        self.original_stdout.flush()

    def get_logs(self):
        return self.logs

log_capture = LogCapture()
sys.stdout = log_capture
sys.stderr = log_capture

# Import AxiBot components after setting path and changing directory
from app.settings import settings
from app.database import DatabaseManager

class WebAPI:
    def __init__(self, loop):
        self.loop = loop
        self.running = False
        self.running_tasks = []
        self.db = DatabaseManager()
        self.engagement_manager = None
        self.stats = {
            "viewers": 0,
            "likes": 0,
            "subs": 0,
            "messages_processed": 0
        }
        # Pre-populate settings from .env
        load_dotenv(override=True)

    def check_streamer_auth_status(self):
        """ Returns True if the Streamer YouTube OAuth token exists """
        token_path = settings.YOUTUBE_STREAMER_TOKEN_PATH
        return os.path.exists(token_path)

    def check_bot_auth_status(self):
        """ Returns True if the Bot YouTube OAuth token exists """
        token_path = settings.YOUTUBE_TOKEN_PATH
        return os.path.exists(token_path)

    def check_auth_status(self):
        """ Returns True if the YouTube Streamer OAuth token exists (compatibility check) """
        return self.check_streamer_auth_status()

    def get_bot_status(self):
        """ Returns current run status and statistics """
        return {
            "running": self.running,
            "stats": self.stats
        }

    def connect_youtube(self, account_type="streamer"):
        """ Runs the YouTube authentication flow in the browser """
        print(f"Starting YouTube OAuth Connection Flow for {account_type}...")
        try:
            from auth_helper import authenticate_youtube
            token_path = settings.YOUTUBE_TOKEN_PATH if account_type == "bot" else settings.YOUTUBE_STREAMER_TOKEN_PATH
            authenticate_youtube(token_path=token_path)
            success = os.path.exists(token_path)
            if success:
                print(f"YouTube {account_type} account connected successfully!")
                
                # Automatically retrieve the Channel ID for the authenticated user
                try:
                    from google.oauth2.credentials import Credentials
                    from googleapiclient.discovery import build
                    
                    if os.path.exists(token_path):
                        creds = Credentials.from_authorized_user_file(token_path)
                        youtube = build("youtube", "v3", credentials=creds)
                        
                        response = youtube.channels().list(part="id,snippet", mine=True).execute()
                        if response.get("items"):
                            channel_data = response["items"][0]
                            channel_id = channel_data["id"]
                            channel_title = channel_data["snippet"]["title"]
                            print(f"Linked {account_type.capitalize()} Channel: {channel_title} (ID: {channel_id})")
                            
                            if account_type == "streamer":
                                # Persist this to settings and .env
                                current_config = self.get_settings()
                                current_config["STREAMER_CHANNEL_ID"] = channel_id
                                self.save_settings(current_config)
                except Exception as ex:
                    print(f"Warning: Could not auto-detect channel details: {ex}")
                
                return {"success": True, "error": None}
            else:
                return {"success": False, "error": "Authentication completed, but token was not saved."}
        except Exception as e:
            print(f"Authentication failed: {e}")
            return {"success": False, "error": str(e)}

    def disconnect_youtube(self, account_type="streamer"):
        """ Removes the local token to disconnect YouTube for streamer or bot """
        token_path = settings.YOUTUBE_TOKEN_PATH if account_type == "bot" else settings.YOUTUBE_STREAMER_TOKEN_PATH
        if os.path.exists(token_path):
            os.remove(token_path)
            print(f"Disconnected YouTube {account_type} account. Token deleted.")
            return True
        return False

    def get_settings(self):
        """ Reads the current configurations """
        load_dotenv(override=True)
        return {
            "BOT_NAME": os.getenv("BOT_NAME", "AxiBot"),
            "STREAMER_CHANNEL_ID": os.getenv("STREAMER_CHANNEL_ID", ""),
            "NVIDIA_API_KEY": os.getenv("NVIDIA_API_KEY", ""),
            "NVIDIA_MODEL_ID": os.getenv("NVIDIA_MODEL_ID", "google/gemma-3n-e2b-it"),
            "COOLDOWN_SECONDS": str(settings.COOLDOWN_SECONDS if hasattr(settings, 'COOLDOWN_SECONDS') else 60),
            "STREAMER_CONNECTED": self.check_streamer_auth_status(),
            "BOT_CONNECTED": self.check_bot_auth_status()
        }

    def save_settings(self, new_settings):
        """ Updates the .env file and sets variables in memory """
        try:
            print("Saving new configuration settings...")
            # Update settings object properties
            settings.BOT_NAME = new_settings.get("BOT_NAME", settings.BOT_NAME)
            settings.STREAMER_CHANNEL_ID = new_settings.get("STREAMER_CHANNEL_ID", settings.STREAMER_CHANNEL_ID)
            settings.NVIDIA_API_KEY = new_settings.get("NVIDIA_API_KEY", settings.NVIDIA_API_KEY)
            settings.NVIDIA_MODEL_ID = new_settings.get("NVIDIA_MODEL_ID", settings.NVIDIA_MODEL_ID)
            
            # Cooldown check
            cooldown_val = int(new_settings.get("COOLDOWN_SECONDS", 60))
            # Modifying on instances and routing
            settings.COOLDOWN_SECONDS = cooldown_val

            # Write back to .env
            env_lines = []
            env_keys_written = set()
            
            if os.path.exists(".env"):
                with open(".env", "r") as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#") and "=" in stripped:
                            k, v = stripped.split("=", 1)
                            k = k.strip()
                            if k in new_settings:
                                env_lines.append(f"{k}={new_settings[k]}\n")
                                env_keys_written.add(k)
                                continue
                        env_lines.append(line)
            
            # Write missing ones
            for k, v in new_settings.items():
                if k not in env_keys_written:
                    env_lines.append(f"{k}={v}\n")
            
            with open(".env", "w") as f:
                f.writelines(env_lines)
            
            load_dotenv(override=True)
            print("Settings saved and reloaded successfully.")
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def start_bot(self):
        """ Starts the bot loops in the background asyncio thread """
        if self.running:
            print("Bot is already running.")
            return True
            
        if not self.check_streamer_auth_status():
            print("Cannot start: YouTube Streamer Channel is not linked. Please link it first.")
            return False
            
        if not self.check_bot_auth_status():
            print("Cannot start: YouTube Bot Account is not linked. Please link it in Settings first.")
            return False

        self.running = True
        # Run execution loop on the background loop
        asyncio.run_coroutine_threadsafe(self._run_bot_loop(), self.loop)
        return True

    def stop_bot(self):
        """ Stops the background bot tasks """
        if not self.running:
            print("Bot is not running.")
            return False
            
        print("Stopping bot listeners and loops...")
        self.running = False
        self.engagement_manager = None
        if self.running_tasks:
            for task in self.running_tasks:
                self.loop.call_soon_threadsafe(task.cancel)
            self.running_tasks = []

        # Reset stats on stop
        self.stats["viewers"] = 0
        self.stats["likes"] = 0
        self.stats["subs"] = 0
        self.stats["messages_processed"] = 0

        # Clear cached livestream IDs
        cache_path = "storage/cache.json"
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                print("Cleared cached livestream ID on stop.")
            except Exception as e:
                print(f"Error clearing cache file: {e}")

        print("Bot stopped.")
        return True

    async def _run_bot_loop(self):
        try:
            from app.nvidia_client import NvidiaClient
            from app.youtube_client import YouTubeClient
            from app.router import MessageRouter
            from app.youtube_listener import YouTubeChatListener
            from app.engagement import EngagementManager

            print("Initializing bot engine clients...")
            gemini = NvidiaClient()
            youtube = YouTubeClient()

            if not settings.STREAMER_CHANNEL_ID:
                print("CRITICAL ERROR: STREAMER_CHANNEL_ID is empty in settings.")
                self.running = False
                return

            print(f"Detecting stream for channel: {settings.STREAMER_CHANNEL_ID}")
            chat_id = youtube.get_live_chat_id_for_channel(settings.STREAMER_CHANNEL_ID)
            
            if chat_id:
                print(f"Connected to YouTube Chat. Chat ID: {chat_id}")
                youtube.send_message("Hello viewers! 🤖 AxiBot is now active and monitoring the chat. Mention me to talk!")
                
                # Fetch initial stats
                if youtube.video_id:
                    viewers, likes = youtube.get_video_stats(youtube.video_id)
                    self.stats["viewers"] = viewers
                    self.stats["likes"] = likes
                    
                    details = youtube.get_video_details(youtube.video_id)
                    if details:
                        print(f"Stream Context Loaded: {details.get('title')}")
                        if hasattr(gemini, 'stream_context'):
                            gemini.stream_context = details
                
                self.stats["subs"] = youtube.get_channel_subscribers(settings.STREAMER_CHANNEL_ID)

                # Channel brain
                latest_videos = youtube.get_latest_videos(settings.STREAMER_CHANNEL_ID)
                upcoming_streams = youtube.get_upcoming_streams(settings.STREAMER_CHANNEL_ID)
                if hasattr(gemini, 'channel_knowledge'):
                    gemini.channel_knowledge = {
                        "latest_videos": latest_videos,
                        "upcoming_streams": upcoming_streams
                    }
            else:
                print("WARNING: No active live stream detected. Bot will operate in polling idle mode.")

            router = MessageRouter(gemini_client=gemini, youtube_client=youtube)
            
            # Setup route counting
            orig_route = router.route_message
            async def wrapped_route(message_data):
                if message_data and message_data.get('type') == 'chat':
                    self.stats["messages_processed"] += 1
                await orig_route(message_data)
            router.route_message = wrapped_route

            async def on_event(event_data):
                await router.route_message(event_data)

            yt_listener = YouTubeChatListener(youtube_client=youtube, callback=on_event)
            engagement = EngagementManager(llm_client=gemini)
            self.engagement_manager = engagement

            async def stats_and_engagement_loop():
                print("Starting Stats & Engagement Loop...")
                while self.running:
                    try:
                        if youtube.video_id:
                            viewers, likes = youtube.get_video_stats(youtube.video_id)
                            self.stats["viewers"] = viewers
                            self.stats["likes"] = likes
                            
                            channel_id = settings.STREAMER_CHANNEL_ID
                            subs = youtube.get_channel_subscribers(channel_id) if channel_id else 0
                            self.stats["subs"] = subs

                            # Check targets
                            target_msg = await engagement.check_targets(likes, subs)
                            if target_msg:
                                print(f"Target Met: {target_msg}")
                                youtube.send_message(target_msg)
                                await asyncio.sleep(60)
                                continue

                            # Check triggers
                            msg = await engagement.check_triggers(viewers)
                            if not msg:
                                msg = await engagement.get_next_message()
                            
                            if msg:
                                print(f"Engagement Triggered: {msg}")
                                youtube.send_message(msg)

                        await asyncio.sleep(30) # Poll stats every 30 seconds for quick dashboard feedback
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        print(f"Stats loop error: {e}")
                        await asyncio.sleep(15)

            # Start processes
            self.running_tasks = [
                asyncio.create_task(yt_listener.start()),
                asyncio.create_task(stats_and_engagement_loop())
            ]
            
            await asyncio.gather(*self.running_tasks)
            
        except asyncio.CancelledError:
            print("Background bot services stopped.")
        except Exception as e:
            print(f"Critical Bot Loop Error: {e}")
        finally:
            self.running = False

    def get_logs(self):
        """ Returns captured logs for rendering in dashboard """
        return log_capture.get_logs()

    def get_db_users(self):
        """ Returns all users tracked in SQLite """
        try:
            users = self.db.get_all_users()
            return [dict(u) for u in users]
        except Exception as e:
            print(f"Error reading SQLite users: {e}")
            return []

    def update_user_summary(self, user_id, summary):
        """ Edits a viewer's personality summary in the database """
        try:
            self.db.update_personality(user_id, summary)
            print(f"Updated personality summary for User ID: {user_id}")
            return True
        except Exception as e:
            print(f"Failed to update user personality: {e}")
            return False

    def get_moderation_rules(self):
        """ Loads blocked words and moderation config from storage or default """
        words_path = "storage/moderation.json"
        from app.moderation_filter import ModerationFilter
        
        # Load from class default first
        data = {
            "words": list(ModerationFilter.BAD_WORDS),
            "timeout_duration": getattr(ModerationFilter, 'TIMEOUT_DURATION', 300),
            "enable_timeout": getattr(ModerationFilter, 'ENABLE_TIMEOUT', True),
            "enable_delete": getattr(ModerationFilter, 'ENABLE_DELETE', True)
        }
        
        if os.path.exists(words_path):
            try:
                with open(words_path, "r") as f:
                    file_data = json.load(f)
                    # Support legacy format (list of words) or new format (dict)
                    if isinstance(file_data, list):
                        data["words"] = file_data
                    elif isinstance(file_data, dict):
                        data["words"] = file_data.get("words", data["words"])
                        data["timeout_duration"] = file_data.get("timeout_duration", data["timeout_duration"])
                        data["enable_timeout"] = file_data.get("enable_timeout", data["enable_timeout"])
                        data["enable_delete"] = file_data.get("enable_delete", data["enable_delete"])
            except Exception as e:
                print(f"Error loading moderation rules: {e}")
        
        # Apply to class variables just to be safe
        ModerationFilter.BAD_WORDS = set(data["words"])
        ModerationFilter.TIMEOUT_DURATION = int(data["timeout_duration"])
        ModerationFilter.ENABLE_TIMEOUT = bool(data["enable_timeout"])
        ModerationFilter.ENABLE_DELETE = bool(data["enable_delete"])
        
        return data

    def save_moderation_rules(self, data):
        """ Saves custom blocked words list and rules """
        try:
            from app.moderation_filter import ModerationFilter
            
            # support receiving either raw list (legacy compatibility) or full config dict
            if isinstance(data, list):
                words = data
                timeout_duration = getattr(ModerationFilter, 'TIMEOUT_DURATION', 300)
                enable_timeout = getattr(ModerationFilter, 'ENABLE_TIMEOUT', True)
                enable_delete = getattr(ModerationFilter, 'ENABLE_DELETE', True)
            else:
                words = data.get("words", list(ModerationFilter.BAD_WORDS))
                timeout_duration = int(data.get("timeout_duration", 300))
                enable_timeout = bool(data.get("enable_timeout", True))
                enable_delete = bool(data.get("enable_delete", True))
            
            # Apply in memory
            ModerationFilter.BAD_WORDS = set(words)
            ModerationFilter.TIMEOUT_DURATION = timeout_duration
            ModerationFilter.ENABLE_TIMEOUT = enable_timeout
            ModerationFilter.ENABLE_DELETE = enable_delete
            
            # Save to disk
            save_data = {
                "words": words,
                "timeout_duration": timeout_duration,
                "enable_timeout": enable_timeout,
                "enable_delete": enable_delete
            }
            
            os.makedirs("storage", exist_ok=True)
            with open("storage/moderation.json", "w") as f:
                json.dump(save_data, f, indent=4)
            print("Moderation filter list and rules updated.")
            return True
        except Exception as e:
            print(f"Failed to save moderation rules: {e}")
            return False

    def restart_bot(self):
        """ Stops the bot if running, and starts it again """
        print("Restarting bot engine...")
        if self.running:
            self.stop_bot()
            import time
            time.sleep(0.5)
        return self.start_bot()

    def get_engagement_settings(self):
        """ Reads engagement configurations """
        from app.engagement import EngagementManager
        mgr = EngagementManager()
        return {
            "fallback_messages": mgr.fallback_messages,
            "min_interval": mgr.min_interval,
            "max_interval": mgr.max_interval,
            "viewer_spike_threshold": mgr.viewer_spike_threshold,
            "like_target_step": mgr.like_target_step,
            "like_target": mgr.like_target
        }

    def save_engagement_settings(self, config):
        """ Saves engagement configurations to storage/engagement.json """
        try:
            from collections import deque
            os.makedirs("storage", exist_ok=True)
            save_data = {
                "fallback_messages": config.get("fallback_messages", []),
                "min_interval": int(config.get("min_interval", 300)),
                "max_interval": int(config.get("max_interval", 900)),
                "viewer_spike_threshold": int(config.get("viewer_spike_threshold", 8)),
                "like_target_step": int(config.get("like_target_step", 10)),
                "like_target": int(config.get("like_target", 10))
            }
            with open("storage/engagement.json", "w") as f:
                json.dump(save_data, f, indent=4)
            
            # Reload on running instance if active
            if self.engagement_manager:
                self.engagement_manager.load_settings()
                self.engagement_manager.message_history = deque(
                    self.engagement_manager.message_history, 
                    maxlen=max(1, len(self.engagement_manager.fallback_messages))
                )
                print("Reloaded engagement settings on running engine.")
                
            print("Engagement settings saved successfully.")
            return True
        except Exception as e:
            print(f"Failed to save engagement settings: {e}")
            return False

    def force_trigger_engagement(self):
        """ Forces an engagement message generation and posts to chat """
        if self.running and self.engagement_manager:
            async def run_force():
                try:
                     msg = await self.engagement_manager.force_trigger()
                     if msg:
                         from app.youtube_client import YouTubeClient
                         yt = YouTubeClient()
                         print(f"[Force Engagement] Posting: {msg}")
                         yt.send_message(msg)
                except Exception as e:
                     print(f"Force trigger failed: {e}")
            import asyncio
            asyncio.run_coroutine_threadsafe(run_force(), self.loop)
            return True
        else:
            print("Bot is not running or engagement manager not active.")
            return False

    def delete_db_user(self, user_id):
        """ Deletes a viewer from the database """
        try:
            self.db.delete_user(user_id)
            print(f"Deleted user {user_id} from SQLite database.")
            return True
        except Exception as e:
            print(f"Error deleting user {user_id}: {e}")
            return False

    def update_db_user(self, user_id, display_name, personality_summary, message_count):
        """ Updates details for a viewer in the database """
        try:
            self.db.update_user_details(user_id, display_name, personality_summary, int(message_count))
            print(f"Updated user details for {display_name} (ID: {user_id}).")
            return True
        except Exception as e:
            print(f"Error updating user details: {e}")
            return False

    def clear_stream_cache(self):
        """ Clears cached livestream video and chat IDs from storage/cache.json """
        cache_path = "storage/cache.json"
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                print("Manual cache clear: deleted storage/cache.json")
                return True
            except Exception as e:
                print(f"Failed to delete cache file: {e}")
                return False
        return True

    def reset_db(self):
        """ Resets the SQLite viewers database """
        try:
            self.db.reset_database()
            print("Database has been reset successfully.")
            return True
        except Exception as e:
            print(f"Failed to reset database: {e}")
            return False

def start_asyncio_thread(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

if __name__ == "__main__":
    print("Initializing AxiBot GUI application...")
    
    # Start background thread for Asyncio operations
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=start_asyncio_thread, args=(loop,), daemon=True)
    t.start()
    
    # Create pywebview API
    api = WebAPI(loop)
    
    # Locate UI file
    ui_html = get_resource_path(os.path.join("app", "ui", "index.html"))
    
    # Launch Desktop window
    window = webview.create_window(
        title="AxiBot Streaming Dashboard",
        url=ui_html,
        js_api=api,
        width=1100,
        height=720,
        resizable=True,
        background_color="#e5dbff"
    )
    
    # Run PyWebView main thread (blocking)
    webview.start(debug=True)
