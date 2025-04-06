class SoftError():
    """
    Represents a non-critical error in a bot's execution.
    
    Used to report bot failures that trigger timeouts rather than crashing
    the entire application.
    """
    def __init__(self, bot_name: str, bot_id: str, message: str):
        """
        Initialize a SoftError.
        
        Args:
            bot_name: Name of the bot that encountered the error
            bot_id: ID of the bot that encountered the error
            message: Description of the error
        """
        self.bot_name = bot_name
        self.bot_id = bot_id
        self.message = message

    def __str__(self):
        """Return a string representation of the error."""
        return f"{self.bot_name} ({self.bot_id}) - {self.message}"
    

