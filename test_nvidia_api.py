import asyncio
import sys
import os

# Add project root to sys.path so we can import app modules easily
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.nvidia_client import NvidiaClient

async def test_nvidia_api():
    print("\n=== Initializing Nvidia Client Test ===")
    try:
        client = NvidiaClient()
        print(f"Successfully loaded client for model: {client.model_name}")
        
        print("\n--- 1. Testing Context-Aware Chat ---")
        history = "UserA: What's up guys?\nUserB: Nm, just watching the stream."
        
        print("Test A: User just chatting (should ignore)")
        reply_a = await client.generate_reply("UserC", "lol true", history=history, is_mentioned=False)
        print(f"Bot Output: {reply_a}")

        print("\nTest B: User asking for game name in Tanglish (should reply)")
        reply_b = await client.generate_reply("UserD", "bro indha game per enna?", history=history, is_mentioned=False)
        print(f"Bot Output: {reply_b}")
        
        print("\nTest C: Multi-lingual emotion check (Tamil)")
        reply_c = await client.generate_reply("UserE", "indha strategy semmaya iruku! super bro!", history=history, is_mentioned=False)
        print(f"Bot Output: {reply_c}")

        print("\nTest D: Explicit Mention")
        reply_d = await client.generate_reply("UserF", "Hello @AxiBot!", history=history, is_mentioned=True)
        print(f"Bot Output: {reply_d}")
            
        print("\n--- 2. Testing Engagement Message ---")
        engagement = await client.generate_engagement_message("like_subscribe")
        if engagement:
            print(f"✅ Engagement Output: {engagement}")
        else:
            print("❌ Failed to get an engagement message.")
            
        print("\n=== Test Complete ===")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        print("Please check your .env file and ensure NVIDIA_API_KEY is correctly set.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_nvidia_api())
