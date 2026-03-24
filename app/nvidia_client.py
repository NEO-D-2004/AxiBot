from openai import AsyncOpenAI
import random
from app.settings import settings

class NvidiaClient:
    def __init__(self, model_name=None):
        self.model_name = model_name or settings.NVIDIA_MODEL_ID
        self.client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.NVIDIA_API_KEY
        )
        self.stream_context = {}
        self.channel_knowledge = {
            "latest_videos": [],
            "upcoming_streams": []
        }
        self.fallback_messages = [
            "I'm overloaded right now! 😵",
            "Too many messages! Give me a second... 🕒",
            "Thinking... (API Rate Limit)",
            "🤖 *beeping noises*",
            "Need to recharge! 🔋"
        ]
        print(f"initialized NvidiaClient with model: {self.model_name}")

    async def generate_reply(self, user: str, message: str, history: str = "", is_mentioned: bool = False, user_memory: str = "") -> str:
        """
        Generates a friendly, short reply.
        Handles context-aware dynamic jumping into chat.
        """
        context_str = ""
        if self.stream_context:
            title = self.stream_context.get("title", "Unknown Stream")
            channel = self.stream_context.get("channel_title", "Unknown Channel")
            context_str = f"You are watching the stream '{title}' on channel '{channel}'. "

        # Format Channel Knowledge for prompt
        videos_str = "\n".join([f"- {v['title']} (ID: {v['id']})" for v in self.channel_knowledge.get("latest_videos", [])])
        streams_str = "\n".join([f"- {s['title']} (ID: {s['id']})" for s in self.channel_knowledge.get("upcoming_streams", [])])
        
        channel_brain = (
            f"CHANNEL KNOWLEDGE:\n"
            f"Latest Videos:\n{videos_str if videos_str else 'No recent videos.'}\n"
            f"Upcoming Streams:\n{streams_str if streams_str else 'No streams scheduled.'}\n"
        )

        intervention_rules = (
            "You MUST classify the message first.\n"
            "STEP 1: CLASSIFY MESSAGE TYPE:\n"
            "- QUESTION: contains a clear question about stream, channel, game, commands, or schedule.\n"
            "- NON-QUESTION: greetings, reactions, jokes, casual chat, emojis, or talking to streamer.\n\n"
            "STEP 2: DECISION:\n"
            "- If NOT a QUESTION → output EXACTLY: IGNORE_CHAT\n"
            "- If QUESTION but NOT related to stream/channel/game → output EXACTLY: IGNORE_CHAT\n"
            "- If QUESTION and RELATED → answer briefly\n\n"
            "STRICT RULES:\n"
            "1. Messages with 'bro', 'nice', 'lol', 'haha', '🔥', etc → IGNORE_CHAT\n"
            "2. Messages without '?' are usually NOT questions → IGNORE_CHAT\n"
            "3. If unsure → IGNORE_CHAT\n"
            "4. NEVER guess or force a reply\n"
        )

        examples = (
            "EXAMPLES:\n"
            "User: 'nice play bro'\n"
            "Output: IGNORE_CHAT\n\n"
            "User: 'lol 😂'\n"
            "Output: IGNORE_CHAT\n\n"
            "User: 'when is next stream?'\n"
            "Output: Answer\n\n"
            "User: 'what game is this?'\n"
            "Output: Answer\n\n"
            "User: 'sapta bro'\n"
            "Output: IGNORE_CHAT\n\n"
        )

        prompt = (
            f"You are {settings.BOT_NAME}, not just a bot, but a friendly, pro-gamer moderator and streamer's best friend. "
            f"{context_str}\n"
            f"{channel_brain}\n"
            "SYSTEM INSTRUCTIONS:\n"
            "1. LANGUAGE: Match the user's language 1:1. If they chat in English, reply in English. If they use Tamil, use Tamil. "
            "If they use Tanglish, you use Tanglish. DO NOT force Tamil if the user is speaking English.\n"
            "2. VARIETY: Do NOT repeat the same phrases or prefixes (like 'Aiyyo!') in every message. Be natural and varied.\n"
            "3. EMOTION: Catch their vibe. If they are happy, celebrate! If frustrated, be supportive. Act like a human moderator friend.\n"
            "4. STYLE: Keep replies very short (under 200 chars). Avoid emojis unless absolutely necessary for the emotion. Use informal 'pro-gamer' vibes.\n"
            "5. SELF-AWARENESS: If the user asks 'who am I?', 'tell about me', or 'do you remember me?', use the information in the 'User Profile Header' to give them a friendly, personal answer.\n"
            f"6. INTERVENTION: {intervention_rules}\n"
            f"{examples}\n"
            f"User Profile Header: {user_memory}\n"
            f"Chat Memory (Last 15):\n{history}\n"
            "---\n"
            f"User '{user}' says: '{message}'\n"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            )
            
            if response.choices and response.choices[0].message.content:
                reply = response.choices[0].message.content.strip()
                
                # HARD FILTER
                if reply.upper() == "IGNORE_CHAT":
                    return None
                
                # Extra safety: ignore short/generic replies
                low_value = ["lol", "nice", "haha", "cool"]
                if reply.lower() in low_value:
                    return None
                    
                return reply
            return None
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "403" in error_str:
                print(f"Nvidia API Rate Limit Hit: {e}")
                return random.choice(self.fallback_messages)
            
            print(f"Nvidia API Error: {e}")
            return None


    async def generate_engagement_message(self, category: str) -> str:
        """
        Generates a short, engaging message based on the category.
        """
        prompts = {
            "like_subscribe": "Generate a short, fun message asking viewers to like the stream and subscribe. Be creative! Avoid emojis unless necessary.",
            "likes_target": "Generate a short message setting a small likes goal. Be encouraging! Avoid emojis unless necessary.",
            "chat_with_me": "Generate a short message inviting viewers to chat. Ask a simple question or just say hi. Avoid emojis unless necessary.",
            "welcome": "Generate a short, warm welcome message for new viewers. Avoid emojis unless necessary.",
            "like_target_met": "We hit the like goal! Generate a short celebration message and set a new higher goal. Avoid emojis unless necessary.",
            "sub_target_met": "We hit the subscriber goal! Generate a short celebration message for the new subscriber and mention the next goal. Avoid emojis unless necessary."
        }
        
        base_prompt = prompts.get(category, prompts["like_subscribe"])
        
        full_prompt = (
            f"You are {settings.BOT_NAME}, a friendly YouTube moderator. "
            f"{base_prompt} "
            "Keep it under 100 characters. No URLs. Do not repeat typical phrases exactly."
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.8,
                max_tokens=60
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip().replace('"', '')
            return None
        except Exception as e:
            # print(f"Nvidia Engagement Error: {e}")
            return None

    async def generate_custom_prompt(self, prompt: str) -> str:
        """
        Executes a raw prompt (used for summarization or internal tasks).
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=200
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            return None
        except Exception as e:
            print(f"Nvidia Custom Prompt Error: {e}")
            return None


if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("Testing Nvidia Client...")
        client = NvidiaClient()
        reply = await client.generate_reply("TestUser", "Hello bot! How are you doing?")
        print(f"Reply: {reply}")
        
        engagement = await client.generate_engagement_message("chat_with_me")
        print(f"Engagement: {engagement}")
    
    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        print("Stopped.")
