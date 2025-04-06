#!/usr/bin/env python3
import os
import sys
import time
import datetime
import random
import logging
import threading
from typing import Dict, List, Any

# Add the parent directory to path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src import Bot, Botman
from src import BotEvent, EventManager
from src import BotState

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_comprehensive.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("BotTest")

# Global test state
test_start_time = datetime.datetime.now()
bot_execution_counts = {}
bot_failure_counts = {}
bot_execution_times = {}
events_received = []

# Event listeners to track all bot events
def log_event(event: BotEvent):
    events_received.append(event)
    logger.info(f"Event: {event.type} - {event.bot_name} - {event.description}")

# Test bots with different behaviors

# 1. Reliable bot that always succeeds quickly
def reliable_function():
    logger.info("Reliable bot executing")
    time.sleep(0.5)  # Quick execution
    return {"status": "success", "data": "Reliable result"}

# 2. Slow bot that always succeeds but takes longer
def slow_function():
    logger.info("Slow bot executing")
    time.sleep(3)  # Takes 3 seconds to complete
    return {"status": "success", "data": "Slow result"}

# 3. Flaky bot that sometimes fails
def flaky_function():
    logger.info("Flaky bot executing")
    global bot_execution_counts
    execution_count = bot_execution_counts.get("flaky_bot", 0)
    bot_execution_counts["flaky_bot"] = execution_count + 1
    
    # Fail on every 3rd execution
    if execution_count % 3 == 2:
        logger.info("Flaky bot failing")
        raise Exception("Simulated flaky failure")
    
    time.sleep(1)
    return {"status": "success", "data": "Flaky result"}

# 4. Failing bot that consistently fails
failure_count = 0
def failing_function():
    logger.info("Failing bot executing")
    global failure_count
    failure_count += 1
    
    # Always fail
    raise Exception(f"Simulated consistent failure #{failure_count}")

# 5. Healing bot that fails initially but succeeds after timeout
healing_failures = 0
def healing_function():
    logger.info("Healing bot executing")
    global healing_failures
    
    if healing_failures < 2:
        healing_failures += 1
        logger.info(f"Healing bot failing (attempt {healing_failures})")
        raise Exception(f"Simulated healing failure #{healing_failures}")
    
    logger.info("Healing bot succeeded")
    return {"status": "success", "data": "Healing result"}

# 6. Resource-intensive bot that uses CPU
def resource_intensive_function():
    logger.info("Resource-intensive bot executing")
    
    # Simulate CPU-intensive work
    start = time.time()
    result = 0
    for i in range(1000000):
        result += i
    
    duration = time.time() - start
    logger.info(f"Resource-intensive bot completed in {duration:.2f}s")
    return {"status": "success", "data": f"Calculated sum: {result}"}

# 7. Long-running bot
def long_running_function():
    logger.info("Long-running bot starting")
    # Simulate a long-running process with checkpoints
    for i in range(5):
        logger.info(f"Long-running bot checkpoint {i+1}/5")
        time.sleep(1)
    
    logger.info("Long-running bot completed")
    return {"status": "success", "data": "Long-running result"}

# 8. Race condition test bot - executes concurrently with state changes
race_state = {"counter": 0, "lock": threading.Lock()}
def race_condition_function():
    logger.info("Race condition bot executing")
    
    # Simulate potential race condition with external state
    with race_state["lock"]:
        current = race_state["counter"]
        # Introduce a context switch opportunity
        time.sleep(0.001)
        race_state["counter"] = current + 1
    
    logger.info(f"Race counter now: {race_state['counter']}")
    return {"status": "success", "data": f"Race counter: {race_state['counter']}"}

# Create the bots with different schedules and configurations
def create_test_bots():
    bots = []
    
    # 1. Reliable bot - runs every minute
    reliable_bot = Bot(
        name="reliable_bot",
        schedule="* * * * *",  # Every minute
        function=reliable_function,
        retries=2,
        retry_delay=1
    )
    bots.append(reliable_bot)
    
    # 2. Slow bot - runs every 2 minutes
    slow_bot = Bot(
        name="slow_bot",
        schedule="*/2 * * * *",  # Every 2 minutes
        function=slow_function,
        retries=2,
        retry_delay=1
    )
    bots.append(slow_bot)
    
    # 3. Flaky bot - runs every minute
    flaky_bot = Bot(
        name="flaky_bot",
        schedule="* * * * *",  # Every minute
        function=flaky_function,
        retries=3,
        retry_delay=2,
        initial_timeout=30  # Short timeout to recover quickly
    )
    bots.append(flaky_bot)
    
    # 4. Failing bot - runs every 3 minutes
    failing_bot = Bot(
        name="failing_bot",
        schedule="*/3 * * * *",  # Every 3 minutes
        function=failing_function,
        retries=2,
        retry_delay=5,
        initial_timeout=60  # 1 minute timeout
    )
    bots.append(failing_bot)
    
    # 5. Healing bot - runs every 5 minutes
    healing_bot = Bot(
        name="healing_bot",
        schedule="*/5 * * * *",  # Every 5 minutes
        function=healing_function,
        retries=3,
        retry_delay=3,
        initial_timeout=120  # 2 minute timeout
    )
    bots.append(healing_bot)
    
    # 6. Resource-intensive bot - runs every 4 minutes
    resource_bot = Bot(
        name="resource_bot",
        schedule="*/4 * * * *",  # Every 4 minutes
        function=resource_intensive_function,
        retries=1,
        retry_delay=5
    )
    bots.append(resource_bot)
    
    # 7. Long-running bot - runs every 3 minutes
    long_bot = Bot(
        name="long_bot",
        schedule="*/3 * * * *",  # Every 3 minutes
        function=long_running_function,
        retries=1,
        retry_delay=2
    )
    bots.append(long_bot)
    
    # 8. Race condition bot - runs frequently
    race_bot = Bot(
        name="race_bot",
        schedule="*/1 * * * *",  # Every minute
        function=race_condition_function,
        retries=2,
        retry_delay=1
    )
    bots.append(race_bot)
    
    # 9. Multiple schedule bot - runs on complex schedule
    multiple_schedule_bot = Bot(
        name="multiple_schedule_bot",
        schedule=["*/2 * * * *", "*/3 * * * *"],  # Every 2 and 3 minutes
        function=reliable_function,
        retries=1,
        retry_delay=1
    )
    bots.append(multiple_schedule_bot)
    
    # Set up event listeners for all bots
    for bot in bots:
        bot.event_manager.start()
        bot.event_manager.subscribe(bot.name, log_event)
    
    return bots

# Run a manual forced execution of all bots once
def force_execution(botman, bots):
    logger.info("Forcing execution of all bots...")
    for bot in bots:
        logger.info(f"Forcing execution of {bot.name}")
        botman.run_bot(bot)
    
    logger.info("Forced execution complete")

# Monitor function to log bot states
def monitor_bots(botman, bots, interval=30):
    while True:
        logger.info("-" * 50)
        logger.info("Bot Status Report")
        logger.info("-" * 50)
        
        for bot in bots:
            metrics = botman.get_bot_metrics_by_name(bot.name)
            if metrics:
                logger.info(f"Bot: {bot.name}")
                logger.info(f"  State: {metrics.state}")
                logger.info(f"  Runs: {metrics.runs}")
                logger.info(f"  Errors: {metrics.errors}")
                logger.info(f"  Last Run: {metrics.last_run}")
                
                # Check if in timeout
                if metrics.state == BotState.TIMEOUT:
                    logger.info(f"  Timeout until: {bot.timeout_until}")
                    
                # Get next scheduled run
                try:
                    next_run = bot.get_next_run()
                    logger.info(f"  Next Run: {next_run}")
                except Exception as e:
                    logger.error(f"  Error getting next run: {e}")
        
        logger.info("-" * 50)
        time.sleep(interval)

def main():
    # Create bots
    bots = create_test_bots()
    
    # Create Botman instance
    botman = Botman()
    for bot in bots:
        botman.add_bot(bot)
    
    # Start the monitor in a separate thread
    monitor_thread = threading.Thread(target=monitor_bots, args=(botman, bots, 60))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    logger.info("Starting Botman...")
    botman.start()
    
    # Force execute all bots immediately to verify they work
    force_execution(botman, bots)
    
    # Run for 20 minutes
    test_duration = 20 * 60  # 20 minutes in seconds
    logger.info(f"Test will run for {test_duration} seconds")
    
    try:
        # Wait for the test duration
        time.sleep(test_duration)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    finally:
        logger.info("Stopping Botman...")
        botman.stop()
        
        # Wait for any pending events
        for bot in bots:
            bot.event_manager.wait_until_empty(timeout=5.0)
            bot.event_manager.stop()
        
        # Final report
        logger.info("=== Final Test Report ===")
        logger.info(f"Test Duration: {datetime.datetime.now() - test_start_time}")
        logger.info(f"Total Events Received: {len(events_received)}")
        logger.info("Event Counts by Type:")
        
        event_types = {}
        for event in events_received:
            if event.type not in event_types:
                event_types[event.type] = 0
            event_types[event.type] += 1
        
        for event_type, count in event_types.items():
            logger.info(f"  {event_type}: {count}")
        
        logger.info("=== End of Test ===")

if __name__ == "__main__":
    main() 