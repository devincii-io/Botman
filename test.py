import datetime
import time
from src import Bot, Botman
import requests

# Create a bot that will fail 3 times before succeeding
def failing_function():
    global attempt_count
    attempt_count += 1
    if attempt_count < 4:  # Will fail 3 times
        raise Exception("Simulated failure")
    print(f"Success on attempt {attempt_count}")

# Initialize counter
attempt_count = 0

# Create bot with short retry delay and timeout for testing
bot = Bot(
    name="test_bot",
    schedule="* * * * *",  # Run every minute
    function=failing_function,
    initial_timeout=30,  # 30 second timeout
    retries=3,
    retry_delay=2  # 2 second delay between retries
)

# Create Botman instance
botman = Botman()
botman.add_bot(bot)

# Get initial next run time before starting
initial_next_run = bot.get_next_run()
print("Starting Botman...")
print(f"Initial next run time: {initial_next_run}")
botman.start()

try:
    # Monitor the bot's state for a few minutes
    for i in range(20):  # Monitor for 10 minutes
        try:
            # Get metrics through the Botman API to avoid lock conflicts
            metrics = botman.get_bot_metrics_by_name("test_bot")
            
            if metrics:
                print(f"\nTime: {datetime.datetime.now()}")
                print(f"Bot State: {metrics.state}")
                print(f"Total Runs: {metrics.runs}")
                print(f"Total Errors: {metrics.errors}")
                print(f"Last Run: {metrics.last_run}")
            else:
                print("\nNo metrics available, bot may have been removed")
                
            print(f"Attempt Count: {attempt_count}")
        except Exception as e:
            print(f"Error getting metrics: {e}")
            
        time.sleep(10)  # Check every 10 seconds for more frequent updates
finally:
    print("\nStopping Botman...")
    try:
        botman.stop()
    except Exception as e:
        print(f"Error stopping Botman: {e}")
        # Force exit if we can't stop cleanly
        import os
        os._exit(0)

