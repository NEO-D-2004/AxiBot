import asyncio
import time
import collections
from app.settings import settings
from app.moderation_filter import ModerationFilter
from app.database import DatabaseManager

class MessageRouter:
    def __init__(self, gemini_client=None, youtube_client=None, tts_callback=None):
        self.gemini_client = gemini_client
        self.youtube_client = youtube_client
        self.tts_callback = tts_callback
        self.db = DatabaseManager()
        self.bot_name = settings.BOT_NAME.lower()
        self.cooldowns = {}
        self.COOLDOWN_SECONDS = getattr(settings, 'COOLDOWN_SECONDS', 60)
        self.chat_history = collections.deque(maxlen=15)
        self.last_radio_time = 0
        
        # Per-user recent history for summarization (10 messages trigger)
        self.user_session_history = collections.defaultdict(lambda: collections.deque(maxlen=10))



    async def route_message(self, message_data: dict):
        """
        Parses raw event data and routes it if it's a valid chat message or alert.
        """
        if not isinstance(message_data, dict) or message_data.get('platform') != 'youtube':
            return

        msg_type = message_data.get('type')
        user = message_data.get('user', 'Unknown User')
        user_id = message_data.get('user_id')
        message_id = message_data.get('id')
        
        # 1. Alert Handling (Native YouTube)
        if msg_type in ['superChat', 'superSticker', 'newSponsor', 'memberMilestone', 'subscription']:
            print(f"New Native Alert: {msg_type} from {user}")
            if self.gemini_client and self.youtube_client:
                # Generate a custom welcome/thank you message
                if msg_type == 'newSponsor':
                    prompt = "I just became a new channel member!"
                elif msg_type == 'subscription':
                    prompt = "I just subscribed to your YouTube channel!"
                elif msg_type in ['superChat', 'superSticker']:
                    amount = message_data.get('amount', '')
                    prompt = f"I just sent a Super Chat/Sticker for {amount}!"
                else: # memberMilestone
                    level = message_data.get('member_level', '')
                    prompt = f"I just renewed my membership ({level})!"
                    
                print(f"Generating alert reply for {user}...")
                reply = await self.gemini_client.generate_reply(user, prompt)
                
                if reply and "IGNORE_CHAT" not in reply:
                    mention_reply = self._format_mention(user, reply)
                    self.youtube_client.send_message(mention_reply)
            return

        # 2. Normal Chat Handling
        if msg_type != 'chat':
            return
            
        message = message_data.get('message')
        if not message or not isinstance(message, str):
            return
        message = message.strip()

        # 0. Self-Reply Prevention
        # Ignore messages from the bot itself
        # Debug: Check exact values
        if user:
            # check for partial match too?
            if user.lower() == self.bot_name or self.bot_name in user.lower() or "nightbot" in user.lower():
                print(f"[Router Ignore] Ignored message from {user}")
                return
            # print(f"[Debug] Message from: '{user}' (Bot name: '{self.bot_name}')")

        # 0.5 Moderation Check
        if ModerationFilter.check_message(message):
            print(f"[Moderation] Abusive message detected from {user}: {message}")
            if self.youtube_client:
                if user_id and getattr(ModerationFilter, 'ENABLE_TIMEOUT', True):
                    dur = getattr(ModerationFilter, 'TIMEOUT_DURATION', 300)
                    self.youtube_client.timeout_user(user_id, duration_seconds=dur)
                if message_id and getattr(ModerationFilter, 'ENABLE_DELETE', True):
                    self.youtube_client.delete_message(message_id)
            return

        # 1. Mention Detection
        user_lower = user.lower() if user else ""
        message_lower = message.lower()
        
        print(f"[Router Parse] User: {user}, Message: {message}")
        
        is_mentioned = False
        if f"@{self.bot_name}" in message_lower or self.bot_name in message_lower:
            is_mentioned = True
            print(f"[{user}] explicitly mentioned bot: {message}")

        # 2. Database Tracking & Memory Fetch
        user_memory = "New viewer, treat them with extra warmth!"
        if getattr(settings, 'ENABLE_DATABASE', True) and user_id:
            # Update activity (last seen, count)
            self.db.update_user_activity(user_id, user)
            
            # Award points (10 AxiCoins per message)
            self.db.add_points(user_id, user, 10)
            
            # Fetch existing memory
            user_data = self.db.get_user(user_id)
            if user_data:
                user_memory = user_data["personality_summary"]
            
            # Add to session history for summarization trigger
            self.user_session_history[user_id].append(message)
            if len(self.user_session_history[user_id]) >= 10:
                # Trigger background summarization
                asyncio.create_task(self._summarize_user(user_id, user))

        # Check for chat commands
        if message.startswith("!") and getattr(settings, 'ENABLE_COMMANDS', True):
            cmd_parts = message.split()
            cmd_name = cmd_parts[0][1:].lower()
            cmd_args = cmd_parts[1:]
            
            # 1. !axicoins
            if cmd_name == "axicoins":
                if user_id:
                    user_data = self.db.get_user(user_id)
                    pts = user_data["points"] if user_data else 0
                    reply = f"@{user} you currently have {pts} AxiCoins!"
                else:
                    reply = f"@{user} could not retrieve your points balance."
                if self.youtube_client:
                    self.youtube_client.send_message(reply)
                return
            
            # 2. !axileaderboard / !axitop
            elif cmd_name in ["axileaderboard", "axitop"]:
                top_users = self.db.get_top_users_by_points(3)
                if top_users:
                    rankings = []
                    for idx, row in enumerate(top_users):
                        rankings.append(f"{idx+1}. {row['display_name']} ({row['points']})")
                    reply = f"🏆 AxiCoins Leaderboard: " + " | ".join(rankings)
                else:
                    reply = "🏆 AxiCoins Leaderboard: No users tracked yet."
                if self.youtube_client:
                    self.youtube_client.send_message(reply)
                return
            
            # 3. !clip / !highlight
            elif cmd_name in ["clip", "highlight"]:
                from datetime import datetime, timezone
                elapsed_seconds = 0
                
                start_time_str = getattr(self.youtube_client, 'stream_start_time', None)
                if start_time_str:
                    try:
                        if start_time_str.endswith("Z"):
                            start_time_str = start_time_str[:-1] + "+00:00"
                        start_dt = datetime.fromisoformat(start_time_str)
                        now_dt = datetime.now(timezone.utc)
                        elapsed_seconds = int((now_dt - start_dt).total_seconds())
                    except Exception as ex:
                        print(f"Error parsing stream start time in router: {ex}")
                
                if elapsed_seconds <= 0:
                    elapsed_seconds = 0
                
                # Format to HH:MM:SS
                h = elapsed_seconds // 3600
                m = (elapsed_seconds % 3600) // 60
                s = elapsed_seconds % 60
                timestamp_str = f"{h:02d}:{m:02d}:{s:02d}"
                
                context_msg = " ".join(cmd_args) if cmd_args else ""
                
                # Log to DB
                video_id = getattr(self.youtube_client, 'video_id', None)
                self.db.add_highlight(timestamp_str, elapsed_seconds, user, context_msg, video_id)
                
                reply = f"@{user} Added Clip at {timestamp_str}"
                if self.youtube_client:
                    self.youtube_client.send_message(reply)
                return
            
            # 4. !radio <query>
            elif cmd_name == "radio":
                if not user_id:
                    return
                
                if not getattr(settings, 'RADIO_ENABLED', True):
                    reply = f"@{user} The radio co-host feature is currently disabled."
                    if self.youtube_client:
                        self.youtube_client.send_message(reply)
                    return

                user_data = self.db.get_user(user_id)
                current_points = user_data["points"] if user_data else 0
                
                if current_points < 100:
                    reply = f"@{user} Insufficient AxiCoins! !radio costs 100 AxiCoins. You currently have {current_points}."
                    if self.youtube_client:
                        self.youtube_client.send_message(reply)
                    return
                
                now = time.time()
                elapsed_cooldown = now - self.last_radio_time
                if elapsed_cooldown < 30:
                    remaining = int(30 - elapsed_cooldown)
                    reply = f"@{user} Radio is on cooldown! Please wait {remaining}s."
                    if self.youtube_client:
                        self.youtube_client.send_message(reply)
                    return
                
                if not cmd_args:
                    reply = f"@{user} Please specify a prompt/query for the radio! e.g., !radio hello stream"
                    if self.youtube_client:
                        self.youtube_client.send_message(reply)
                    return
                
                query = " ".join(cmd_args)
                self.last_radio_time = now
                
                # Deduct points
                self.db.deduct_points(user_id, 100)
                
                # Generate reply using separate radio model if specified
                radio_model = getattr(settings, 'RADIO_MODEL_ID', settings.NVIDIA_MODEL_ID)
                
                # Query the LLM for a speech-safe broadcast script
                reply_text = await self.gemini_client.generate_radio_reply(user, query, model_id=radio_model)
                
                # Send text response to chat
                chat_reply = f"@{user} [Radio] {reply_text}"
                if self.youtube_client:
                    self.youtube_client.send_message(chat_reply)
                
                # Play audio via callback or fallback SAPI5
                if self.tts_callback:
                    self.tts_callback(reply_text)
                else:
                    self._speak_text_sapi5(reply_text)
                return
            
            # 4. Custom Command from DB
            else:
                db_cmd = self.db.get_command(cmd_name)
                if db_cmd:
                    self.db.increment_command_use(cmd_name)
                    response_text = db_cmd["response_text"]
                    uses = db_cmd["use_count"] + 1
                    
                    # Replace placeholders
                    response_text = response_text.replace("{user}", f"@{user}")
                    response_text = response_text.replace("{count}", str(uses))
                    
                    if self.youtube_client:
                        self.youtube_client.send_message(response_text)
                    return

        # 3. Append to chat history (Listen to everything)
        self.chat_history.append(f"{user}: {message}")

        # 4. Context-Aware AI Generation (Evaluate BEFORE Cooldown)
        if self.gemini_client:
            print(f"Evaluating message from {user} for context-aware reply...")
            history_str = "\n".join(self.chat_history)
            
            # Injecting User Memory into the generation
            reply = await self.gemini_client.generate_reply(
                user, 
                message, 
                history=history_str, 
                is_mentioned=is_mentioned,
                user_memory=user_memory
            )
            
            if reply and "IGNORE_CHAT" not in reply:
                # 5. Cooldown Check (Only enforced if AI decides to speak)
                if self._is_on_cooldown(user) and not is_mentioned:
                    print(f"Bot wanted to reply, but {user} is on cooldown. Skipping to avoid spam.")
                    return

                mention_reply = self._format_mention(user, reply)
                print(f"Bot Context-Aware Reply: {mention_reply}")
                
                # Append bot output to memory
                self.chat_history.append(f"{self.bot_name}: {mention_reply}")

                if self.youtube_client:
                    self.youtube_client.send_message(mention_reply)
                else:
                    print("YouTube Client not connected, cannot send reply.")
            else:
                # Bot decided not to intervene
                pass

    async def _summarize_user(self, user_id: str, display_name: str):
        """
        Uses AI to UPDATE a brief personality summary based on the last 10 messages.
        It fetches the OLD summary and merges it with the NEW history.
        """
        # Fetch current memory
        old_summary = "No previous history."
        user_data = self.db.get_user(user_id)
        if user_data:
            old_summary = user_data["personality_summary"]

        history = list(self.user_session_history[user_id])
        # Clear the buffer after grabbing
        self.user_session_history[user_id].clear()
        
        print(f"--- Iterative Personality Update for {display_name} ---")
        
        prompt = (
            f"Existing Summary for '{display_name}': {old_summary}\n\n"
            f"New Messages from '{display_name}':\n" + "\n".join(history) + "\n\n"
            "Combine the existing summary with these new messages to create an updated 1-sentence personality summary. "
            "Keep it brief (under 150 chars). Do not lose important facts like their location or favorite game."
        )
        
        try:
            summary = await self.gemini_client.generate_custom_prompt(prompt)
            if summary:
                print(f"Updated Summary for {display_name}: {summary}")
                self.db.update_personality(user_id, summary)
        except Exception as e:
            print(f"Error during iterative summarization for {display_name}: {e}")

    def _is_on_cooldown(self, user: str) -> bool:
        now = time.time()
        last_time = self.cooldowns.get(user, 0)
        
        if now - last_time < self.COOLDOWN_SECONDS:
            return True
        
        self.cooldowns[user] = now
        return False

    def _format_mention(self, user: str, reply: str) -> str:
        """
        Formats a reply to ensure it begins with exactly one '@username' mention.
        Handles cases where user already starts with '@', or the reply already includes the mention.
        """
        clean_user = user.lstrip("@").strip()
        clean_reply = reply.strip()
        
        prefix_to_check = clean_user.lower()
        reply_lower = clean_reply.lower()
        
        if reply_lower.startswith(f"@{prefix_to_check}"):
            rest_of_reply = clean_reply[len(f"@{prefix_to_check}"):].strip()
            return f"@{clean_user} {rest_of_reply}"
        elif reply_lower.startswith(f"@ {prefix_to_check}"):
            rest_of_reply = clean_reply[len(f"@ {prefix_to_check}"):].strip()
            return f"@{clean_user} {rest_of_reply}"
        elif reply_lower.startswith(prefix_to_check):
            rest_of_reply = clean_reply[len(prefix_to_check):].strip()
            return f"@{clean_user} {rest_of_reply}"
        else:
            return f"@{clean_user} {clean_reply}"

    def _speak_text_sapi5(self, text):
        import subprocess
        try:
            escaped_text = text.replace("'", "''").replace('"', '""')
            escaped_text = escaped_text[:300]
            cmd = f"(New-Object -ComObject SAPI.SpVoice).Speak('{escaped_text}')"
            subprocess.Popen(
                ["powershell", "-Command", cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"Failed to play SAPI5 TTS: {e}")
