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
            "You MUST reply now. " if is_mentioned else 
            "Read the chat history and the latest message. "
            "STRICT FILTERING RULES:\n"
            "1. MESSAGE TARGET: Determine who the message is for. Most casual messages and messages containing 'bro' are for the streamer (e.g., 'nice play bro', 'sapta bro', 'clutch god'). "
            "If the message is for the streamer, you MUST strictly output exactly: IGNORE_CHAT.\n"
            "2. BOT DUTY: You only speak if the user is asking a direct question about the channel, the game, the schedule, or needs help with something binary (like commands). "
            "If it's just casual chat, greeting, or reaction to the stream, output: IGNORE_CHAT.\n"
            "3. MODERATOR ROLE: If there is a doubt about the stream or channel, use your 'CHANNEL KNOWLEDGE' to answer accurately. "
            "If you don't know the answer and it's not in your knowledge, do not make it up; just stay silent or say the streamer will answer soon.\n"
            "4. NO PLAIN EMOJIS: Never reply with only an emoji. Your reply must contain text. If you feel only an emoji is needed, it's better to IGNORE_CHAT.\n"
            "5. NEVER be over-talkative. Quality over quantity."
            "6. CASUAL CHAT FILTER: If the user says 'bro', 'lol', 'haha', 'nice', 'cool', or any short casual reaction, you dont reply "
            "7. If the user asks 'who am I?', 'tell about me', or 'do you remember me?', use the information in the 'User Profile Header' to give them a friendly, personal answer."
            "8. Do Not reply to the messages that are only with emojis like reactions , output: IGNORE_CHAT.\n"   
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
