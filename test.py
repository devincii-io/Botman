import datetime
import time
from src import Bot
import requests

requests.post("http://localhost:5000/slack/events", json={"text": "Hello, world!"})

bot = Bot("test", "* * * * *", lambda: print("Hello, world!"))

while True:
    if bot.is_due():
        print("Running bot")
        bot.run()
        requests.post("http://localhost:5000/slack/events", json={"text": "Hello, world!"})	
    time.sleep(1)

