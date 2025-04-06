class SoftError():
    def __init__(self, bot_name: str, bot_id: str, message: str):
        self.bot_name = bot_name
        self.bot_id = bot_id
        self.message = message

    def __str__(self):
        return f"{self.bot_name} ({self.bot_id}) - {self.message}"
    

