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

        if is_mentioned:
            intervention_rules = (
                "The user is talking directly to you (you were explicitly mentioned!).\n"
                "You MUST generate a friendly, context-appropriate response. DO NOT ignore the message. "
                "DO NOT output IGNORE_CHAT under any circumstances. Reply directly to their greeting, comment, or query."
            )
            examples = (
                "EXAMPLES of direct replies:\n"
                "User: '@AxiBot hello bro'\n"
                "Output: Hey bro! Welcome to the stream! Let me know if you need anything.\n\n"
                "User: '@AxiBot nice play'\n"
                "Output: GG! The streamer is playing out of their mind today! 🔥\n\n"
                "User: '@AxiBot lol 😂'\n"
                "Output: Haha right? That was so funny!\n"
            )
            output_format_rules = (
                "  * You MUST reply with a short, friendly message under 200 characters.\n"
                "  * Output ONLY the final response. Do not output IGNORE_CHAT. Do not output explanations, preambles, or quotes."
            )
        else:
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
                "2. If unsure → IGNORE_CHAT\n"
                "3. NEVER guess or force a reply\n"
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
            output_format_rules = (
                "  * If ignoring, your output MUST be EXACTLY: IGNORE_CHAT\n"
                "  * If replying, your output must be a short, friendly message under 200 characters.\n"
                "  * Output ONLY the final response or IGNORE_CHAT. Do not output any classification steps, headers, explanations, preambles, or quotes."
            )

        system_instructions = (
            f"You are {settings.BOT_NAME}, not just a bot, moderator, co-host, and the streamer's best friend. "
            "Your personality is funny, energetic, witty, cool, and a bit savage when requested. "
            "Chat like a real person live in the stream chat. "
            f"{context_str}\n"
            f"{channel_brain}\n"
            "SYSTEM INSTRUCTIONS:\n"
            "1. LANGUAGE: Match the user's language 1:1. If they chat in English, reply in English. If they use Tamil, use Tamil. "
            "If they use Tanglish, you use Tanglish. "
            "IMPORTANT: If the user explicitly requests a language (e.g. 'in tamil', 'tamil la', 'tamil pesu', 'tanglish la'), you MUST reply in that language (Tamil/Tanglish), even if the request itself is written in English.\n"
            "2. VARIETY: Do NOT repeat the same phrases, responses, or templates. Check the 'Chat Memory' to see what you have already said, and generate a completely different, fresh reply. Be natural and varied.\n"
            "3. EMOTION & VIBE: Be a source of high energy, hype up the chat, crack funny jokes, motivate the viewers. Sound like an actual human friend hanging out in the stream, not a robotic template.\n"
            "4. STYLE: Keep replies very short (under 200 chars), punchy, and conversational. Use informal 'pro-gamer' slang, cool terms, and natural flow.\n"
            "5. SELF-AWARENESS: If the user asks 'who am I?', 'tell about me', or 'do you remember me?', use the information in the 'User Profile Header' to give them a friendly, personal answer.\n"
            "6. ROASTS & RAGE BAITS: If the user asks you to roast them, roast someone else, or generate rage bait (even if they use the word 'roast' or 'rage bait' in English or Tanglish), you MUST generate a funny, playful, slightly savage roast or rage bait. Do NOT be polite, friendly, or welcoming in this case. Be witty and sarcastic, but keep it lighthearted.\n"
            f"7. INTERVENTION: {intervention_rules}\n"
            f"{examples}\n"
            "OUTPUT FORMAT RULES:\n"
            f"{output_format_rules}"
        )

        user_prompt = ""
        if user_memory:
            user_prompt += f"User Profile Header: {user_memory}\n"
        if history:
            user_prompt += f"Chat Memory (Last 15):\n{history}\n"
        user_prompt += f"User '{user}' says: '{message}'\n"

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.85,
                presence_penalty=0.6,
                frequency_penalty=0.8,
                max_tokens=400
            )
            
            if response.choices and response.choices[0].message.content:
                reply = response.choices[0].message.content.strip()
                
                # HARD FILTER
                if reply.upper() == "IGNORE_CHAT":
                    if is_mentioned:
                        return f"Hey @{user.lstrip('@')}! I'm here. How can I help you?"
                    return "IGNORE_CHAT"
                
                # Extra safety: ignore short/generic replies unless directly mentioned
                if not is_mentioned:
                    low_value = ["lol", "nice", "haha", "cool"]
                    if reply.lower() in low_value:
                        return "IGNORE_CHAT"
                    
                return reply
            return "IGNORE_CHAT" if not is_mentioned else f"Hey @{user.lstrip('@')}! I'm here. How can I help you?"
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "403" in error_str:
                print(f"Nvidia API Rate Limit Hit: {e}")
                return random.choice(self.fallback_messages)
            
            print(f"Nvidia API Error: {e}")
            if is_mentioned:
                return f"Hey @{user.lstrip('@')}! I'm here. How can I help you?"
            return "IGNORE_CHAT"


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
                max_tokens=500
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
                max_tokens=500
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
