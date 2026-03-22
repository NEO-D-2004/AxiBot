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
        self.fallback_messages = [
            "I'm overloaded right now! 😵",
            "Too many messages! Give me a second... 🕒",
            "Thinking... (API Rate Limit)",
            "🤖 *beeping noises*",
            "Need to recharge! 🔋"
        ]
        print(f"initialized NvidiaClient with model: {self.model_name}")

    async def generate_reply(self, user: str, message: str, history: str = "", is_mentioned: bool = False) -> str:
        """
        Generates a friendly, short reply.
        Handles context-aware dynamic jumping into chat.
        """
        context_str = ""
        if self.stream_context:
            title = self.stream_context.get("title", "Unknown Stream")
            channel = self.stream_context.get("channel_title", "Unknown Channel")
            context_str = f"You are watching the stream '{title}' on channel '{channel}'. "

        intervention_rules = (
            "You MUST reply now. " if is_mentioned else 
            "Read the chat history. If the user is asking a question, needs help, or if joining the convo adds value, then reply. If they are just chatting generally or saying hi to each other, strictly output exactly: IGNORE_CHAT"
        )

        prompt = (
            f"You are {settings.BOT_NAME}, not just a bot, but a friendly, pro-gamer moderator and streamer's best friend. "
            f"{context_str}\n"
            "SYSTEM INSTRUCTIONS:\n"
            "1. LANGUAGE: Detect the user's language (Tamil, Tanglish, English). Reply in the EXACT SAME language and modulation. "
            "If they use Tanglish (Tamil + English), you use Tanglish. Use local slang and informal 'pro-gamer' vibes.\n"
            "2. EMOTION: Catch their vibe. If they are happy, celebrate! If frustrated, be supportive. Act like a human moderator.\n"
            "3. STYLE: Keep replies very short (under 200 chars). Limit emojis to max 1. No URLs.\n"
            f"4. INTERVENTION: {intervention_rules}\n"
            "---\n"
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
            "like_subscribe": "Generate a short, fun message asking viewers to like the stream and subscribe to the channel. Be creative! Max 1 emoji.",
            "likes_target": "Generate a short message setting a small likes goal (e.g., 10 or 20 likes) for the stream. Be encouraging! Max 1 emoji.",
            "chat_with_me": "Generate a short message inviting viewers to chat with you (the bot). Ask them a simple question or just say you're ready to chat. Max 1 emoji.",
            "welcome": "Generate a short, warm welcome message for new viewers joining the stream. Max 1 emoji.",
            "like_target_met": "We hit the like goal! 🎉 Generate a short celebration message and set a new higher goal. Max 1 emoji.",
            "sub_target_met": "We hit the subscriber goal! 🚀 Generate a short celebration message for the new subscriber and mention the next goal. Max 1 emoji."
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
