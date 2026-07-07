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
        self.radio_queue = []
        self.radio_logs = []
        self.radio_queue_id_counter = 0
        # Pre-populate settings from .env
        load_dotenv(override=True)

    def _get_cached_channel_data(self):
        cache_path = "storage/channel_cache.json"
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading channel cache: {e}")
        return {}

    def _save_channel_cache(self, channel_id, channel_name, avatar_url=""):
        cache_path = "storage/channel_cache.json"
        os.makedirs("storage", exist_ok=True)
        try:
            data = {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "avatar_url": avatar_url
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving channel cache: {e}")

    def check_streamer_auth_status(self):
        """ Returns True if the Streamer YouTube OAuth token exists """
        token_path = settings.YOUTUBE_STREAMER_TOKEN_PATH
        return os.path.exists(token_path)

    def check_auth_status(self):
        """ Returns True if the Streamer YouTube OAuth token exists (used by frontend) """
        return self.check_streamer_auth_status()

    def check_bot_auth_status(self):
        """ Returns True if the Bot YouTube OAuth token exists """
        token_path = settings.YOUTUBE_TOKEN_PATH
        return os.path.exists(token_path)

    def get_linked_channel_name(self):
        """ Returns the linked YouTube channel name/title """
        token_path = settings.YOUTUBE_STREAMER_TOKEN_PATH
        if not os.path.exists(token_path):
            return ""
        
        # 1. Check local cache first to avoid calling API and preventing transient logout/errors
        cached_data = self._get_cached_channel_data()
        if cached_data.get("channel_name"):
            return cached_data["channel_name"]
            
        # 2. If not cached, fetch from YouTube API
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            creds = Credentials.from_authorized_user_file(token_path)
            youtube = build("youtube", "v3", credentials=creds)
            response = youtube.channels().list(part="id,snippet", mine=True).execute()
            if response.get("items"):
                channel_data = response["items"][0]
                channel_id = channel_data["id"]
                channel_title = channel_data["snippet"]["title"]
                avatar_url = channel_data["snippet"].get("thumbnails", {}).get("default", {}).get("url", "")
                
                # Cache it
                self._save_channel_cache(channel_id, channel_title, avatar_url)
                return channel_title
        except Exception as e:
            print(f"Error fetching channel name: {e}")
            if settings.STREAMER_CHANNEL_NAME:
                return settings.STREAMER_CHANNEL_NAME
        return ""

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
        if account_type == "bot":
            print("Cannot connect bot account: it is configured as permanent.")
            return {"success": False, "error": "Bot account is permanent and pre-configured."}
        print(f"Starting YouTube OAuth Connection Flow for {account_type}...")
        try:
            from auth_helper import authenticate_youtube
            token_path = settings.YOUTUBE_STREAMER_TOKEN_PATH
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
                                # Cache it locally
                                avatar_url = channel_data["snippet"].get("thumbnails", {}).get("default", {}).get("url", "")
                                self._save_channel_cache(channel_id, channel_title, avatar_url)
                                
                                # Persist this to settings and .env
                                current_config = self.get_settings()
                                current_config["STREAMER_CHANNEL_ID"] = channel_id
                                current_config["STREAMER_CHANNEL_NAME"] = channel_title
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
        if account_type == "bot":
            print("Cannot disconnect bot account: it is configured as permanent.")
            return False
        token_path = settings.YOUTUBE_STREAMER_TOKEN_PATH
        if os.path.exists(token_path):
            os.remove(token_path)
            # Remove local channel cache on disconnect
            cache_path = "storage/channel_cache.json"
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except Exception:
                    pass
            print(f"Disconnected YouTube {account_type} account. Token deleted.")
            return True
        return False

    def get_settings(self):
        """ Reads the current configurations """
        from app.settings import load_local_settings
        load_local_settings()
        
        channel_name = settings.STREAMER_CHANNEL_NAME
        channel_id = settings.STREAMER_CHANNEL_ID
        avatar_url = ""
        
        # Restore channel details from local cache if we are authenticated
        if self.check_streamer_auth_status():
            cached_data = self._get_cached_channel_data()
            if cached_data:
                avatar_url = cached_data.get("avatar_url", "")
                if not channel_name:
                    channel_name = cached_data.get("channel_name", "")
                    settings.STREAMER_CHANNEL_NAME = channel_name
                if not channel_id:
                    channel_id = cached_data.get("channel_id", "")
                    settings.STREAMER_CHANNEL_ID = channel_id
            
            # Fetch from API only if name is still missing
            if not channel_name:
                channel_name = self.get_linked_channel_name()
                if channel_name:
                    settings.STREAMER_CHANNEL_NAME = channel_name
                    # Reload cached data to grab the channel ID
                    cached_data = self._get_cached_channel_data()
                    channel_id = cached_data.get("channel_id", settings.STREAMER_CHANNEL_ID)
                    settings.STREAMER_CHANNEL_ID = channel_id
                    avatar_url = cached_data.get("avatar_url", "")
            
            # If values were missing from memory but found in cache/API, persist them
            if channel_name != settings.STREAMER_CHANNEL_NAME or channel_id != settings.STREAMER_CHANNEL_ID:
                current_config = {
                    "BOT_NAME": settings.BOT_NAME,
                    "STREAMER_CHANNEL_ID": settings.STREAMER_CHANNEL_ID,
                    "NVIDIA_API_KEY": settings.NVIDIA_API_KEY,
                    "NVIDIA_MODEL_ID": settings.NVIDIA_MODEL_ID,
                    "COOLDOWN_SECONDS": str(settings.COOLDOWN_SECONDS),
                    "ENABLE_DATABASE": "True" if settings.ENABLE_DATABASE else "False",
                    "ENABLE_COMMANDS": "True" if settings.ENABLE_COMMANDS else "False",
                    "STREAMER_CHANNEL_NAME": settings.STREAMER_CHANNEL_NAME
                }
                self.save_settings(current_config)

        return {
            "BOT_NAME": settings.BOT_NAME,
            "STREAMER_CHANNEL_ID": settings.STREAMER_CHANNEL_ID,
            "NVIDIA_API_KEY": settings.NVIDIA_API_KEY,
            "NVIDIA_MODEL_ID": settings.NVIDIA_MODEL_ID,
            "COOLDOWN_SECONDS": str(settings.COOLDOWN_SECONDS),
            "STREAMER_CONNECTED": self.check_streamer_auth_status(),
            "BOT_CONNECTED": self.check_bot_auth_status(),
            "ENABLE_DATABASE": settings.ENABLE_DATABASE,
            "ENABLE_COMMANDS": settings.ENABLE_COMMANDS,
            "STREAMER_CHANNEL_NAME": settings.STREAMER_CHANNEL_NAME,
            "STREAMER_AVATAR_URL": avatar_url,
            "RADIO_MODEL_ID": settings.RADIO_MODEL_ID,
            "RADIO_ENABLED": settings.RADIO_ENABLED,
            "RADIO_AUTO": settings.RADIO_AUTO,
            "RADIO_INTERVAL": settings.RADIO_INTERVAL,
            "RADIO_PROVIDER": settings.RADIO_PROVIDER,
            "RADIO_VOICE": settings.RADIO_VOICE,
            "RADIO_LANGUAGE": settings.RADIO_LANGUAGE,
            "RADIO_SPEED": settings.RADIO_SPEED,
            "RADIO_PITCH": settings.RADIO_PITCH,
            "RADIO_ENERGY": settings.RADIO_ENERGY,
            "RADIO_FORMAT": settings.RADIO_FORMAT,
            "RADIO_OUTPUT_SOURCE": settings.RADIO_OUTPUT_SOURCE,
            "RADIO_VOLUME": settings.RADIO_VOLUME,
            "RADIO_DUCK_AUDIO": settings.RADIO_DUCK_AUDIO,
            "RADIO_DUCK_AMOUNT": settings.RADIO_DUCK_AMOUNT,
            "RADIO_AUTO_APPROVE": settings.RADIO_AUTO_APPROVE,
            "CHATTERBOX_API_KEY": settings.CHATTERBOX_API_KEY
        }

    def save_settings(self, new_settings):
        """ Updates local settings.json, the .env file, and memory variables """
        try:
            print("Saving new configuration settings...")
            # Update settings object properties
            settings.BOT_NAME = new_settings.get("BOT_NAME", settings.BOT_NAME)
            settings.STREAMER_CHANNEL_ID = new_settings.get("STREAMER_CHANNEL_ID", settings.STREAMER_CHANNEL_ID)
            settings.NVIDIA_API_KEY = new_settings.get("NVIDIA_API_KEY", settings.NVIDIA_API_KEY)
            settings.NVIDIA_MODEL_ID = new_settings.get("NVIDIA_MODEL_ID", settings.NVIDIA_MODEL_ID)
            if "ENABLE_DATABASE" in new_settings:
                settings.ENABLE_DATABASE = new_settings.get("ENABLE_DATABASE") == "True" or new_settings.get("ENABLE_DATABASE") is True
            if "ENABLE_COMMANDS" in new_settings:
                settings.ENABLE_COMMANDS = new_settings.get("ENABLE_COMMANDS") == "True" or new_settings.get("ENABLE_COMMANDS") is True
            if "STREAMER_CHANNEL_NAME" in new_settings:
                settings.STREAMER_CHANNEL_NAME = new_settings.get("STREAMER_CHANNEL_NAME", "")
            
            # Cooldown check
            cooldown_val = int(new_settings.get("COOLDOWN_SECONDS", 60))
            settings.COOLDOWN_SECONDS = cooldown_val

            # Radio configuration save parameters
            if "RADIO_MODEL_ID" in new_settings:
                settings.RADIO_MODEL_ID = new_settings.get("RADIO_MODEL_ID")
            if "RADIO_ENABLED" in new_settings:
                settings.RADIO_ENABLED = str(new_settings.get("RADIO_ENABLED")) == "True" or new_settings.get("RADIO_ENABLED") is True
            if "RADIO_AUTO" in new_settings:
                settings.RADIO_AUTO = str(new_settings.get("RADIO_AUTO")) == "True" or new_settings.get("RADIO_AUTO") is True
            if "RADIO_INTERVAL" in new_settings:
                settings.RADIO_INTERVAL = int(new_settings.get("RADIO_INTERVAL"))
            if "RADIO_PROVIDER" in new_settings:
                settings.RADIO_PROVIDER = new_settings.get("RADIO_PROVIDER")
            if "RADIO_VOICE" in new_settings:
                settings.RADIO_VOICE = new_settings.get("RADIO_VOICE")
            if "RADIO_LANGUAGE" in new_settings:
                settings.RADIO_LANGUAGE = new_settings.get("RADIO_LANGUAGE")
            if "RADIO_SPEED" in new_settings:
                settings.RADIO_SPEED = float(new_settings.get("RADIO_SPEED"))
            if "RADIO_PITCH" in new_settings:
                settings.RADIO_PITCH = new_settings.get("RADIO_PITCH")
            if "RADIO_ENERGY" in new_settings:
                settings.RADIO_ENERGY = new_settings.get("RADIO_ENERGY")
            if "RADIO_FORMAT" in new_settings:
                settings.RADIO_FORMAT = new_settings.get("RADIO_FORMAT")
            if "RADIO_OUTPUT_SOURCE" in new_settings:
                settings.RADIO_OUTPUT_SOURCE = new_settings.get("RADIO_OUTPUT_SOURCE")
            if "RADIO_VOLUME" in new_settings:
                settings.RADIO_VOLUME = int(new_settings.get("RADIO_VOLUME"))
            if "RADIO_DUCK_AUDIO" in new_settings:
                settings.RADIO_DUCK_AUDIO = str(new_settings.get("RADIO_DUCK_AUDIO")) == "True" or new_settings.get("RADIO_DUCK_AUDIO") is True
            if "RADIO_DUCK_AMOUNT" in new_settings:
                settings.RADIO_DUCK_AMOUNT = int(new_settings.get("RADIO_DUCK_AMOUNT"))
            if "RADIO_AUTO_APPROVE" in new_settings:
                settings.RADIO_AUTO_APPROVE = str(new_settings.get("RADIO_AUTO_APPROVE")) == "True" or new_settings.get("RADIO_AUTO_APPROVE") is True
            if "CHATTERBOX_API_KEY" in new_settings:
                settings.CHATTERBOX_API_KEY = new_settings.get("CHATTERBOX_API_KEY")

            # Save locally to storage/settings.json
            from app.settings import save_local_settings
            save_local_settings()

            # Attempt to write to .env (non-blocking if write-protected/packaged)
            try:
                env_lines = []
                env_keys_written = set()
                
                if os.path.exists(".env"):
                    with open(".env", "r", encoding="utf-8") as f:
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
                
                with open(".env", "w", encoding="utf-8") as f:
                    f.writelines(env_lines)
                
                load_dotenv(override=True)
            except Exception as env_err:
                print(f"Warning: Could not write to .env file (non-fatal): {env_err}")
            
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
            print("Cannot start: Pre-configured YouTube Bot Account token is missing from storage/token.json.")
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

            # Create a callback to speak text in the GUI via JS synthesis or fallback to python SAPI5
            def play_tts_callback(text):
                if getattr(settings, 'RADIO_PROVIDER', '') == "Chatterbox Multilingual TTS":
                    self._speak_chatterbox_tts(text)
                else:
                    try:
                        import json
                        window.evaluate_js(f"if (window.playRadioTTS) {{ window.playRadioTTS({json.dumps(text)}); }}")
                    except Exception as e:
                        # Fallback to local python speech synthese if PyWebView window not ready/active
                        import subprocess
                        try:
                            escaped_text = text.replace("'", "''").replace('"', '""')
                            cmd = f"(New-Object -ComObject SAPI.SpVoice).Speak('{escaped_text}')"
                            subprocess.Popen(["powershell", "-Command", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except Exception:
                            pass

            router = MessageRouter(gemini_client=gemini, youtube_client=youtube, tts_callback=play_tts_callback)
            
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

    def update_db_user(self, user_id, display_name, personality_summary, message_count, points=0):
        """ Updates details for a viewer in the database """
        try:
            self.db.update_user_details(user_id, display_name, personality_summary, int(message_count), int(points))
            print(f"Updated user details for {display_name} (ID: {user_id}).")
            return True
        except Exception as e:
            print(f"Error updating user details: {e}")
            return False

    def get_all_commands(self):
        """ Returns all custom commands """
        try:
            cmds = self.db.get_all_commands()
            return [dict(c) for c in cmds]
        except Exception as e:
            print(f"Error reading SQLite commands: {e}")
            return []

    def save_command(self, name, response):
        """ Adds or edits a custom command """
        try:
            self.db.add_command(name, response)
            print(f"Custom command !{name} saved successfully.")
            return True
        except Exception as e:
            print(f"Error saving custom command: {e}")
            return False

    def delete_command(self, name):
        """ Deletes a custom command """
        try:
            self.db.delete_command(name)
            print(f"Custom command !{name} deleted successfully.")
            return True
        except Exception as e:
            print(f"Error deleting custom command: {e}")
            return False

    def get_highlights(self):
        """ Returns all stream highlights """
        try:
            hl = self.db.get_all_highlights()
            return [dict(h) for h in hl]
        except Exception as e:
            print(f"Error reading SQLite highlights: {e}")
            return []

    def delete_highlight(self, highlight_id):
        """ Deletes a specific highlight entry """
        try:
            self.db.delete_highlight(int(highlight_id))
            print(f"Highlight entry ID {highlight_id} deleted successfully.")
            return True
        except Exception as e:
            print(f"Error deleting highlight: {e}")
            return False

    def clear_highlights(self):
        """ Clears all highlight log entries """
        try:
            self.db.clear_all_highlights()
            print("All highlights logs cleared successfully.")
            return True
        except Exception as e:
            print(f"Error clearing highlights: {e}")
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

    def check_tour_status(self):
        """ Returns True if the onboarding tour has been marked completed on the backend """
        return os.path.exists("storage/tour_done.txt")

    def mark_tour_done(self):
        """ Marks the onboarding tour as completed on the backend """
        try:
            os.makedirs("storage", exist_ok=True)
            with open("storage/tour_done.txt", "w") as f:
                f.write("true")
            print("Onboarding tour marked as done on backend.")
            return True
        except Exception as e:
            print(f"Error marking tour as done: {e}")
            return False

    def get_radio_queue(self):
        """ Returns all items in the pending audio queue """
        return self.radio_queue

    def get_radio_logs(self):
        """ Returns all items in the radio activity log """
        return self.radio_logs

    def add_radio_queue_item(self, text, source="Streamer"):
        """ Adds a manually composed script to the queue """
        self.radio_queue_id_counter += 1
        item = {
            "id": self.radio_queue_id_counter,
            "text": text,
            "source": source,
            "status": "Pending",
            "time": datetime.now().strftime("%H:%M:%S")
        }
        self.radio_queue.append(item)
        print(f"Added item to Radio Queue: {text} (Source: {source})")
        
        if settings.RADIO_AUTO_APPROVE:
            self.approve_and_speak(item["id"])
        return True

    def approve_and_speak(self, queue_id):
        """ Approves a queue item and plays it """
        found_item = None
        for item in self.radio_queue:
            if item["id"] == int(queue_id):
                found_item = item
                break
        
        if found_item:
            self.radio_queue.remove(found_item)
            found_item["status"] = "Played"
            self.radio_logs.append(found_item)
            print(f"[Radio Co-Host] Speaking approved text: {found_item['text']}")
            
            if getattr(settings, 'RADIO_PROVIDER', '') == "Chatterbox Multilingual TTS":
                self._speak_chatterbox_tts(found_item['text'])
            else:
                try:
                    window.evaluate_js(f"if (window.playRadioTTS) {{ window.playRadioTTS({json.dumps(found_item['text'])}); }}")
                except Exception as e:
                    import subprocess
                    try:
                        escaped_text = found_item['text'].replace("'", "''").replace('"', '""')
                        cmd = f"(New-Object -ComObject SAPI.SpVoice).Speak('{escaped_text}')"
                        subprocess.Popen(["powershell", "-Command", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
            return True
        return False

    def _generate_chatterbox_tts_sync(self, text):
        import os
        import riva.client
        from app.settings import settings
        
        api_key = getattr(settings, 'CHATTERBOX_API_KEY', '')
        if api_key:
            api_key = api_key.strip()
        if not api_key:
            from app.settings import DEFAULT_NVIDIA_API_KEY
            api_key = DEFAULT_NVIDIA_API_KEY
            
        selected_voice = getattr(settings, 'RADIO_VOICE', 'Tamil Gaming Host')
        riva_voice = "Chatterbox-Multilingual.en-US.Male"
        if "female" in selected_voice.lower():
            riva_voice = "Chatterbox-Multilingual.en-US.Female"
            
        lang_code = getattr(settings, 'RADIO_LANGUAGE', 'ta-IN')
        
        print(f"[Riva Client] Querying gRPC server for TTS: '{text}' (Voice: {riva_voice}, Lang: {lang_code})")
        
        auth = riva.client.Auth(
            uri="grpc.nvcf.nvidia.com:443",
            use_ssl=True,
            metadata_args=[
                ("function-id", "ddacc747-1269-4fab-bfd9-8f593dead106"),
                ("authorization", f"Bearer {api_key}")
            ]
        )
        
        tts_service = riva.client.SpeechSynthesisService(auth)
        
        response = tts_service.synthesize(
            text=text,
            voice_name=riva_voice,
            language_code=lang_code
        )
        
        os.makedirs("storage", exist_ok=True)
        wav_path = "storage/radio_tts.wav"
        with open(wav_path, "wb") as f:
            f.write(response.audio)
            
        return wav_path

    def _update_ui_speaking(self, text):
        try:
            import json
            window.evaluate_js(f"document.getElementById('radio-active-marquee').innerText = {json.dumps(text)};")
            window.evaluate_js("document.getElementById('radio-state-indicator').style.background = '#4caf50';")
            window.evaluate_js("document.getElementById('radio-state-text').innerText = 'Speaking';")
            window.evaluate_js("document.getElementById('radio-state-text').style.color = '#4caf50';")
        except Exception:
            pass

    def _generate_google_tts_sync(self, text, lang="ta"):
        import urllib.request
        import urllib.parse
        import os
        
        encoded_text = urllib.parse.quote(text)
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q={encoded_text}&tl={lang}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        req = urllib.request.Request(url, headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                os.makedirs("storage", exist_ok=True)
                mp3_path = "storage/radio_tts.mp3"
                with open(mp3_path, "wb") as f:
                    f.write(response.read())
                return mp3_path
        except Exception as e:
            raise Exception(f"Google TTS Generation failed: {e}")

    def _play_audio_mci(self, file_path):
        import ctypes
        import time
        import threading
        
        def run():
            try:
                ctypes.windll.winmm.mciSendStringW("close mymp3", None, 0, 0)
                ctypes.windll.winmm.mciSendStringW(f"open \"{file_path}\" type mpegvideo alias mymp3", None, 0, 0)
                ctypes.windll.winmm.mciSendStringW("play mymp3", None, 0, 0)
                
                buffer = ctypes.create_unicode_buffer(128)
                while True:
                    ctypes.windll.winmm.mciSendStringW("status mymp3 mode", buffer, 128, 0)
                    if buffer.value != "playing":
                        break
                    time.sleep(0.1)
                ctypes.windll.winmm.mciSendStringW("close mymp3", None, 0, 0)
            except Exception as e:
                print(f"MCI playback error: {e}")
        
        threading.Thread(target=run, daemon=True).start()

    def _speak_chatterbox_tts(self, text):
        def run_thread():
            try:
                # Generate WAV file from NVIDIA Integrate API
                wav_path = self._generate_chatterbox_tts_sync(text)
                # Play WAV asynchronously using native winsound on Windows
                import winsound
                # Cancel any playing background sounds
                winsound.PlaySound(None, winsound.SND_PURGE)
                winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                self._update_ui_speaking(text)
            except Exception as e:
                print(f"Chatterbox API failed ({e}). Falling back to Google Neural Translate TTS...")
                try:
                    lang_code = "ta" if "ta" in getattr(settings, 'RADIO_LANGUAGE', 'ta-IN').lower() else "en"
                    audio_path = self._generate_google_tts_sync(text, lang=lang_code)
                    self._play_audio_mci(audio_path)
                    self._update_ui_speaking(text)
                except Exception as ex:
                    print(f"Google TTS Fallback failed ({ex}). Falling back to Windows SAPI5...")
                    import subprocess
                    try:
                        escaped_text = text.replace("'", "''").replace('"', '""')
                        cmd = f"(New-Object -ComObject SAPI.SpVoice).Speak('{escaped_text}')"
                        subprocess.Popen(["powershell", "-Command", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
        import threading
        threading.Thread(target=run_thread, daemon=True).start()

    def delete_queue_item(self, queue_id):
        """ Deletes a pending queue item """
        for item in self.radio_queue:
            if item["id"] == int(queue_id):
                self.radio_queue.remove(item)
                print(f"Deleted radio queue item ID {queue_id}")
                return True
        return False

    def generate_radio_script(self, topic):
        """ Asynchronously calls the LLM to generate a clean broadcast-safe Tanglish script """
        if not topic:
            return "No topic specified."
        
        from app.nvidia_client import NvidiaClient
        gemini = NvidiaClient()
        
        async def run_gen():
            try:
                return await gemini.generate_radio_reply("Streamer", topic, model_id=settings.RADIO_MODEL_ID)
            except Exception as e:
                return f"Generation error: {e}"
        
        future = asyncio.run_coroutine_threadsafe(run_gen(), self.loop)
        return future.result()

    def control_playback(self, action):
        """ Handles playback controls (Pause, Resume, Skip, Replay, Panic Mute) """
        print(f"[Radio Playback Control] Action triggered: {action}")
        if action == "panic" or action == "stop":
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
            try:
                import ctypes
                ctypes.windll.winmm.mciSendStringW("close mymp3", None, 0, 0)
            except Exception:
                pass
            print("Emergency stop executed: all TTS voice channels silenced.")
            return True
        return True

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
        width=1920,
        height=1080,
        resizable=True,
        background_color="#e5dbff"
    )
    
    # Run PyWebView main thread (blocking)
    webview.start(debug=False)
