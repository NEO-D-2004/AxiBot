import random
import time
from collections import deque
import asyncio
import json
import os

class EngagementManager:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.fallback_messages = [
            "Don't forget to Hit the LIKE & SUBSCRIBE Button!",
            "Let's go for 10 Likes! Smash that button!",
            "Enjoying the stream? Consider subscribing for more!",
            "New here? Say hi in the chat!",
            "If you are enjoying the content, please like and subscribe! It helps a lot!"
        ]
        self.min_interval = 300
        self.max_interval = 900
        self.viewer_spike_threshold = 8
        self.like_target_step = 10
        self.like_target = 10

        self.load_settings()

        self.last_message_time = 0
        self.next_message_time = 0 
        self.message_history = deque(maxlen=max(1, len(self.fallback_messages)))
        
        # Viewer tracking
        self.last_viewer_count = 0
        
        # Target Tracking
        self.sub_target = None # Will be set to current + 10 on first check
        
        self.categories = ["like_subscribe", "likes_target", "chat_with_me"]
        self._set_next_interval()

    def load_settings(self):
        path = "storage/engagement.json"
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    self.fallback_messages = data.get("fallback_messages", self.fallback_messages)
                    self.min_interval = int(data.get("min_interval", self.min_interval))
                    self.max_interval = int(data.get("max_interval", self.max_interval))
                    self.viewer_spike_threshold = int(data.get("viewer_spike_threshold", self.viewer_spike_threshold))
                    self.like_target_step = int(data.get("like_target_step", self.like_target_step))
                    self.like_target = int(data.get("like_target", self.like_target))
            except Exception as e:
                print(f"Error loading engagement settings: {e}")

    def _set_next_interval(self):
        # Random interval between min_interval and max_interval
        interval = random.randint(self.min_interval, self.max_interval)
        self.next_message_time = time.time() + interval
        # print(f"Next engagement message in {interval}s")

    async def get_next_message(self):
        """
        Returns a message if the random interval has passed.
        Uses LLM if available, otherwise fallback.
        """
        current_time = time.time()
        
        if current_time < self.next_message_time:
            return None

        # Time to send a message
        message = await self._generate_message()
        
        self.last_message_time = current_time
        self._set_next_interval()
        
        return message

    async def check_triggers(self, current_viewer_count):
        """
        Checks if a message should be triggered based on viewer count spike.
        """
        trigger = False
        
        # Trigger 1: Viewer Spike
        if current_viewer_count > self.last_viewer_count + self.viewer_spike_threshold:
            print(f"Viewer spike detected: {self.last_viewer_count} -> {current_viewer_count}")
            trigger = True
            
        self.last_viewer_count = current_viewer_count
        
        if trigger:
            # Enforce a smaller rate limit for triggers (e.g., don't spam if 2 triggers in 5 mins)
            if time.time() - self.last_message_time > 300:
                msg = await self._generate_message(category="welcome" if trigger else None)
                self.last_message_time = time.time()
                # Push back the periodic message timer
                self._set_next_interval() 
                return msg
            
            
        return None

    async def check_targets(self, current_likes, current_subs):
        """
        Checks if stats have reached their targets.
        """
        # Check Like Target
        if current_likes >= self.like_target:
            print(f"Like Target Reached! {current_likes} >= {self.like_target}")
            # Generate celebration message
            old_target = self.like_target
            self.like_target += self.like_target_step
            
            msg = await self._generate_message(category="like_target_met")
            if msg:
                return f"{msg} (New Goal: {self.like_target} Likes!)"
            else:
                 return f"We hit {old_target} Likes! New Goal: {self.like_target} Likes! Smash it!"

        # Check Sub Target
        if current_subs > 0: # Ensure valid sub count
            if self.sub_target is None:
                # Initialize target
                self.sub_target = current_subs + 10
                print(f"Initialized Sub Target to: {self.sub_target}")
            
            elif current_subs >= self.sub_target:
                print(f"Sub Target Reached! {current_subs} >= {self.sub_target}")
                self.sub_target = current_subs + 10
                
                msg = await self._generate_message(category="sub_target_met")
                if msg:
                    return f"{msg} (Next Goal: {self.sub_target} Subs)"
                else:
                    return f"We hit the sub goal! Next Target: {self.sub_target} Subscribers! Welcome new subs!"
                    
        return None


    async def _generate_message(self, category=None):
        if not category:
            category = random.choice(self.categories)
            
        if self.llm_client:
            msg = await self.llm_client.generate_engagement_message(category)
            if msg:
                return msg
        
        # Fallback
        available_messages = [m for m in self.fallback_messages if m not in self.message_history]
        if not available_messages:
            self.message_history.popleft()
            available_messages = [m for m in self.fallback_messages if m not in self.message_history]
            if not available_messages:
                 available_messages = self.fallback_messages
                 
        selected = random.choice(available_messages)
        self.message_history.append(selected)
        return selected

    async def force_trigger(self):
        return await self._generate_message()
