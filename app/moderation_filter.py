class ModerationFilter:
    # A basic list of bad words to filter.
    # In a real production app, this should be loaded from a file or env.
    BAD_WORDS = {
        "badword", "abuse", "spam", "scam", 
        # Add common abusive words here (keeping it safe for this example)
        "idiot", "stupid", "hate"
    }
    TIMEOUT_DURATION = 300
    ENABLE_TIMEOUT = True
    ENABLE_DELETE = True

    @classmethod
    def check_message(cls, message: str) -> bool:
        """
        Returns True if the message contains banned words.
        """
        if not message:
            return False
            
        message_lower = message.lower()
        for word in cls.BAD_WORDS:
            # Simple check: word in message
            # For better filtering, use regex or whole-word checking
            if word in message_lower:
                return True
        return False
