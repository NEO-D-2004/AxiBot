import time
from app.engagement import EngagementManager

def test_engagement_manager():
    manager = EngagementManager()
    
    print("--- Test 1: Periodic Messages ---")
    # Force min_interval to 0 for testing rotation
    manager.min_interval = 0
    
    print("Generating 10 messages (expect no immediate repeats):")
    seen_messages = set()
    for i in range(10):
        msg = manager.get_next_message()
        print(f"{i+1}: {msg}")
        if msg in seen_messages and len(seen_messages) < len(manager.messages):
            print("WARNING: Message repeated before cycling through all available!")
        seen_messages.add(msg)
        
    print("\n--- Test 2: Rate Limiting ---")
    manager.min_interval = 2 # 2 seconds for test
    manager.last_message_time = time.time()
    
    msg = manager.get_next_message()
    if msg is None:
        print("Success: Rate limit blocked message.")
    else:
        print(f"FAILURE: Rate limit failed, got: {msg}")
        
    print("Waiting 2.1 seconds...")
    time.sleep(2.1)
    msg = manager.get_next_message()
    if msg:
        print(f"Success: Message generated after wait: {msg}")
    else:
        print("FAILURE: Message still blocked after wait.")

    print("\n--- Test 3: Viewer Spike Trigger ---")
    manager.min_interval = 0 # Disable rate limit for trigger test
    manager.last_viewer_count = 100
    
    # Small increase
    msg = manager.check_triggers(102)
    if msg is None:
        print("Success: Small increase did not trigger.")
    else:
        print(f"FAILURE: Small increase triggered message: {msg}")
        
    # Big increase
    msg = manager.check_triggers(110)
    if msg:
        print(f"Success: Big increase triggered message: {msg}")
    else:
        print("FAILURE: Big increase did not trigger.")

if __name__ == "__main__":
    import sys
    with open("test_output.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        test_engagement_manager()
