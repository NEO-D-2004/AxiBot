import aiohttp
import json
from app.settings import settings

class LocalGemmaClient:
    def __init__(self, model_name="gemma2:2b", stream_context=None):
        self.api_url = "http://localhost:11434/api/generate"
        self.model_name = model_name
        self.stream_context = stream_context or {}
        print(f"initialized LocalGemmaClient with model: {self.model_name}")

    async def generate_reply(self, user: str, message: str) -> str:
        """
        Generates a reply using the local Ollama instance.
        """
        context_str = ""
        if self.stream_context:
            title = self.stream_context.get("title", "Unknown Stream")
            channel = self.stream_context.get("channel_title", "Unknown Channel")
            context_str = f"You are watching the stream '{title}' on channel '{channel}'. "

        prompt = (
            f"You are {settings.BOT_NAME}, a friendly human-like moderator. "
            f"{context_str}"
            "Answer the viewer casually. "
            "IMPORTANT: Limit emojis to max 1. Do not reuse the same emoji. "
            "Keep replies short (under 200 chars). No URLs. "
            f"The viewer '{user}' said: '{message}'"
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        reply = data.get("response", "").strip()
                        return reply
                    else:
                        print(f"Ollama API Error: {response.status} - {await response.text()}")
                        return None
        except Exception as e:
            print("Make sure Ollama is installed and running: 'ollama serve'")
            return None

    async def generate_engagement_message(self, category: str) -> str:
        """
        Generates a short, engaging message based on the category.
        Categories: 'like_subscribe', 'likes_target', 'chat_with_me', 'welcome'
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

        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "").strip().replace('"', '')
                    return None
        except Exception as e:
            print(f"Engagement Generation Error: {e}")
            return None

