import asyncio
from googleapiclient.errors import HttpError

from collections import deque

class YouTubeChatListener:
    def __init__(self, youtube_client, callback):
        self.youtube_client = youtube_client
        self.callback = callback
        self.is_running = False
        self.next_page_token = None
        
        # Dedicated client for the background polling thread to fix SSL socket thread-safety issues
        orig_client = self.youtube_client.get_new_client()
        self.polling_client = orig_client if orig_client else self.youtube_client.youtube
        
        # Deduplication
        self.processed_ids = deque(maxlen=200)
        
        # Adaptive Polling Settings
        self.min_poll_interval = 30   # Active chat (30s = ~8.6 hours runtime)
        self.max_poll_interval = 60  # Idle chat
        self.current_poll_interval = self.min_poll_interval
        self.idle_loops = 0
        self.IDLE_THRESHOLD = 3      # Loops without messages before slowing down

    async def start(self):
        """
        Starts the polling loop for YouTube Live Chat messages.
        """
        print("Starting YouTube Chat Listener (Native Polling)...")
        self.is_running = True
        
        # Ensure we have a valid chat ID
        if not self.youtube_client.live_chat_id:
            print("No Live Chat ID found. Listener cannot start.")
            return

        print(f"Listening to Chat ID: {self.youtube_client.live_chat_id}")

        while self.is_running:
            try:
                # Poll for messages
                await self._poll_messages()
                
                # Sleep for the current interval
                await asyncio.sleep(self.current_poll_interval)
                
            except asyncio.CancelledError:
                print("YouTube Listener stopping...")
                self.is_running = False
            except Exception as e:
                print(f"Polling Loop Error: {e}")
                await asyncio.sleep(10) # Safety backoff

    async def _poll_messages(self):
        if not self.youtube_client.youtube:
            return

        try:
            # We must run the blocking API call in a thread to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            
            # Prepare request arguments
            kwargs = {
                "liveChatId": self.youtube_client.live_chat_id,
                "part": "snippet,authorDetails"
            }
            if self.next_page_token:
                kwargs["pageToken"] = self.next_page_token

            # Execute API call in thread
            # Use the dedicated polling client to maintain thread safety
            response = await loop.run_in_executor(
                None, 
                lambda: self.polling_client.liveChatMessages().list(**kwargs).execute()
            )

            # If this is the very first poll, we want to discard these historical items 
            # so the bot doesn't spam replies to old chats upon starting.
            is_first_request = (kwargs.get("pageToken") is None)

            # Update pagination
            self.next_page_token = response.get("nextPageToken")
            
            items = response.get("items", [])
            new_messages_count = 0
            
            if items:
                for item in items:
                    # Parse and process message
                    message_data = self._parse_item(item)
                    if message_data:
                        msg_id = message_data.get("id")
                        if msg_id and msg_id not in self.processed_ids:
                            self.processed_ids.append(msg_id)
                            
                            # Ignore processing old messages on first boot
                            if not is_first_request:
                                new_messages_count += 1
                                if self.callback:
                                    await self.callback(message_data)
            
            # Adaptive Logic
            if new_messages_count > 0:
                self.current_poll_interval = self.min_poll_interval
                self.idle_loops = 0
                # print(f"Active chat! Polling every {self.current_poll_interval}s")
            else:
                self.idle_loops += 1
                if self.idle_loops >= self.IDLE_THRESHOLD:
                    self.current_poll_interval = min(self.current_poll_interval + 5, self.max_poll_interval)
                    # print(f"Chat idle. Slowing poll to {self.current_poll_interval}s")

        except HttpError as e:
            print(f"YouTube Polling API Error: {e}")
            # If 403/QuotaExceeded, we should probably stop or sleep long
            self.current_poll_interval = 60 # Sleep longer on error
        except Exception as e:
            print(f"Unexpected Polling Error: {e}")
            self.current_poll_interval = 30 # Safety backoff

    def _parse_item(self, item):
        """
        Converts a YouTube API item into our standard internal message format.
        """
        snippet = item.get("snippet", {})
        msg_type = snippet.get("type")
        
        user_name = item.get("authorDetails", {}).get("displayName", "Unknown")
        user_id = item.get("authorDetails", {}).get("channelId")
        
        base_data = {
            "id": item.get("id"),
            "platform": "youtube",
            "type": "chat",
            "user": user_name,
            "user_id": user_id,
            "message": "",
            "timestamp": snippet.get("publishedAt"),
            "raw_type": msg_type
        }

        if msg_type == "textMessageEvent":
            base_data["message"] = snippet.get("textMessageDetails", {}).get("messageText", "")
            return base_data
            
        elif msg_type == "superChatEvent":
            details = snippet.get("superChatDetails", {})
            amount = details.get("amountDisplayString", "")
            msg = details.get("userComment", "")
            base_data["type"] = "superChat"
            base_data["message"] = msg
            base_data["amount"] = amount
            return base_data
            
        elif msg_type == "superStickerEvent":
            details = snippet.get("superStickerDetails", {})
            amount = details.get("amountDisplayString", "")
            base_data["type"] = "superSticker"
            base_data["amount"] = amount
            return base_data
            
        elif msg_type == "newSponsorEvent":
            base_data["type"] = "newSponsor"
            return base_data
            
        elif msg_type == "memberMilestoneChatEvent":
            details = snippet.get("memberMilestoneChatDetails", {})
            msg = details.get("userComment", "")
            level = details.get("memberLevelName", "")
            base_data["type"] = "memberMilestone"
            base_data["message"] = msg
            base_data["member_level"] = level
            return base_data
            
        return None
