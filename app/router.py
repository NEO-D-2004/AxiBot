import asyncio
import time
import collections
from app.settings import settings
from app.moderation_filter import ModerationFilter
from app.database import DatabaseManager

class MessageRouter:
    def __init__(self, gemini_client=None, youtube_client=None):
        self.gemini_client = gemini_client
        self.youtube_client = youtube_client
        self.db = DatabaseManager()
        self.bot_name = settings.BOT_NAME.lower()
        self.cooldowns = {}
        self.COOLDOWN_SECONDS = 60
        self.chat_history = collections.deque(maxlen=15)
        
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
        if msg_type in ['superChat', 'superSticker', 'newSponsor', 'memberMilestone']:
            print(f"New Native Alert: {msg_type} from {user}")
            if self.gemini_client and self.youtube_client:
                # Generate a custom welcome/thank you message
                if msg_type == 'newSponsor':
                    prompt = "I just became a new channel member!"
                elif msg_type in ['superChat', 'superSticker']:
                    amount = message_data.get('amount', '')
                    prompt = f"I just sent a Super Chat/Sticker for {amount}!"
                else: # memberMilestone
                    level = message_data.get('member_level', '')
                    prompt = f"I just renewed my membership ({level})!"
                    
                print(f"Generating alert reply for {user}...")
                reply = await self.gemini_client.generate_reply(user, prompt)
                
                if reply and "IGNORE_CHAT" not in reply:
                    self.youtube_client.send_message(reply)
            return

        # 2. Normal Chat Handling
        if msg_type != 'chat':
            return
            
        message = message_data.get('message')
        if not message or not isinstance(message, str):
            return

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
                if user_id:
                    self.youtube_client.timeout_user(user_id, duration_seconds=300)
                if message_id:
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
        if user_id:
            # Update activity (last seen, count)
            self.db.update_user_activity(user_id, user)
            
            # Fetch existing memory
            user_data = self.db.get_user(user_id)
            if user_data:
                user_memory = user_data["personality_summary"]
            
            # Add to session history for summarization trigger
            self.user_session_history[user_id].append(message)
            if len(self.user_session_history[user_id]) >= 10:
                # Trigger background summarization
                asyncio.create_task(self._summarize_user(user_id, user))

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

                print(f"Bot Context-Aware Reply: {reply}")
                
                # Append bot output to memory
                self.chat_history.append(f"{self.bot_name}: {reply}")

                if self.youtube_client:
                    self.youtube_client.send_message(reply)
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
