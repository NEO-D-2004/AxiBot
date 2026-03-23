import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.nvidia_client import NvidiaClient

async def test_selective_response():
    print("\n=== Testing Selective Response & Channel Brain ===")
    client = NvidiaClient()
    
    # Mock Channel Knowledge
    client.channel_knowledge = {
        "latest_videos": [
            {"title": "Epic Minecraft Build", "id": "vid123"},
            {"title": "How to Pro Game", "id": "vid456"}
        ],
        "upcoming_streams": [
            {"title": "Live: Friday Fun!", "id": "stream789"}
        ]
    }
    
    test_cases = [
        {
            "user": "Viewer1",
            "message": "Bro nice play!",
            "is_mentioned": False,
            "expected": "IGNORE_CHAT",
            "desc": "Streamer Praise (Should ignore)"
        },
        {
            "user": "Viewer2",
            "message": "How are you streamer?",
            "is_mentioned": False,
            "expected": "IGNORE_CHAT",
            "desc": "Streamer Greeting (Should ignore)"
        },
        {
            "user": "Viewer3",
            "message": "Hello @AxiBot, how are you?",
            "is_mentioned": True,
            "expected": "REPLY",
            "desc": "Direct Mention (Should reply)"
        },
        {
            "user": "Viewer4",
            "message": "When is the next live stream?",
            "is_mentioned": False,
            "expected": "REPLY",
            "desc": "Question about schedule (Should reply using Brain)"
        },
        {
            "user": "Viewer5",
            "message": "What was the last video about?",
            "is_mentioned": False,
            "expected": "REPLY",
            "desc": "Question about recent content (Should reply using Brain)"
        },
        {
            "user": "Viewer6",
            "message": "enna sapta bro",
            "is_mentioned": False,
            "expected": "IGNORE_CHAT",
            "desc": "Casual 'bro' question (Should ignore)"
        },
        {
            "user": "Viewer7",
            "message": "bro reply pannu",
            "is_mentioned": False,
            "expected": "IGNORE_CHAT",
            "desc": "'bro' request to streamer (Should ignore)"
        }
    ]

    for case in test_cases:
        print(f"\n--- {case['desc']} ---")
        print(f"User: {case['user']}")
        print(f"Message: {case['message']}")
        
        reply = await client.generate_reply(
            case['user'], 
            case['message'], 
            is_mentioned=case['is_mentioned']
        )
        
        print(f"Bot Output: {reply}")
        
        if case['expected'] == "IGNORE_CHAT":
            if reply == "IGNORE_CHAT":
                print("✅ Pass: Correctly ignored.")
            else:
                print("❌ Fail: Should have ignored.")
        else:
            if reply != "IGNORE_CHAT" and reply is not None:
                print("✅ Pass: Replied correctly.")
            else:
                print("❌ Fail: Should have replied.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_selective_response())
