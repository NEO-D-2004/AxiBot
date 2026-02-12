from google import genai
from app.settings import settings
import asyncio
import random

class GeminiClient:
    def __init__(self):
        # Initialize the new Client from google-genai
        # We MUST use this because the user's key only sees gemini-2.0 (not 1.5)
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = 'gemini-2.5-pro'
        self.fallback_messages = [
            "I'm overloaded right now! 😵",
            "Too many messages! Give me a second... 🕒",
            "Thinking... (API Rate Limit)",
            "🤖 *beeping noises*",
            "Need to recharge! 🔋"
        ]

    async def generate_reply(self, user: str, message: str) -> str:
        """
        Generates a friendly, short reply.
        Handles Rate Limits (429) by returning a fallback message.
        """
        try:
            prompt = (
                f"You are {settings.BOT_NAME}, a friendly and helpful YouTube live stream moderator bot. "
                "Keep your replies very short (under 200 characters). "
                "Do not use URLs. Be casual and enthusiastic. "
                f"The viewer '{user}' said: '{message}'"
            )

            # New SDK usage
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            
            if response.text:
                return response.text.strip()
            return None
            
        except Exception as e:
            error_str = str(e)
            # Check for Rate Limit (429) or Quota (403 sometimes)
            if "429" in error_str or "403" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print(f"Gemini Rate Limit Hit: {e}")
                # Return a random fallback message so the bot 'responds' even if API is dead
                return random.choice(self.fallback_messages)
            
            print(f"Gemini API Error: {e}")
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
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=full_prompt
            )
            if response.text:
                return response.text.strip().replace('"', '')
            return None
        except Exception as e:
            # print(f"Gemini Engagement Error: {e}")
            return None


if __name__ == "__main__":
    # Test standalone
    async def test():
        print("Testing Gemini Client 2.0...")
        client = GeminiClient()
        reply = await client.generate_reply("TestUser", "Hello bot")
        print(f"Reply: {reply}")
    
    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        print("Stopped.")
