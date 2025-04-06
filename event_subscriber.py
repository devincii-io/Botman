#!/usr/bin/env python3
import os
import sys
import time
import datetime
import random
import logging
import threading
import json
import locale
from typing import Dict, List, Any
from collections import defaultdict, Counter

# Add the parent directory to path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src import Bot, Botman
from src import BotEvent
from src import BotState
from src.events import GLOBAL_EVENT_MANAGER, EventType

# Set up logging with proper encoding for Windows
# Check if we can use Unicode in this terminal
try:
    # Force UTF-8 for file output
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler("test_comprehensive.log", encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    
    # For console output, use simpler formatting without emojis if on Windows
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    
    logger = logging.getLogger("BotTest")
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Clear any default handlers
    logger.propagate = False
except Exception as e:
    # Fallback to basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("test_comprehensive.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("BotTest")

# Check if we can use emoji
try:
    # Test if console can handle emoji
    USE_EMOJI = True
    if sys.platform == 'win32':
        # Windows often has encoding issues with emoji
        USE_EMOJI = False
except:
    USE_EMOJI = False

# Status symbols - with fallbacks for terminals that don't support Unicode
STATUS_SUCCESS = "✓" if USE_EMOJI else "[SUCCESS]"
STATUS_ERROR = "✗" if USE_EMOJI else "[ERROR]"
STATUS_WARNING = "!" if USE_EMOJI else "[WARNING]"
STATUS_INFO = "i" if USE_EMOJI else "[INFO]"
STATUS_RUNNING = ">" if USE_EMOJI else "[RUNNING]"
STATUS_IDLE = "•" if USE_EMOJI else "[IDLE]"
STATUS_TIMEOUT = "T" if USE_EMOJI else "[TIMEOUT]"

# Global test state
test_start_time = datetime.datetime.now()
bot_execution_counts = {}
bot_failure_counts = {}
bot_execution_times = {}
events_received = []

# Statistics tracking
class EventStatistics:
    def __init__(self):
        self.event_counts = Counter()
        self.event_types = Counter()
        self.errors_by_bot = defaultdict(int)
        self.successes_by_bot = defaultdict(int)
        self.bot_states = {}
        self.recent_events = []  # Keep most recent events
        self.last_update = datetime.datetime.now()
        self._lock = threading.Lock()
    
    def record_event(self, event: BotEvent):
        with self._lock:
            self.event_counts[event.bot_name] += 1
            self.event_types[event.type] += 1
            
            # Track bot state through events
            if "Bot started" in event.description:
                self.bot_states[event.bot_name] = "RUNNING"
            elif "Bot completed" in event.description:
                self.bot_states[event.bot_name] = "IDLE"
                self.successes_by_bot[event.bot_name] += 1
            elif "entered timeout" in event.description:
                self.bot_states[event.bot_name] = "TIMEOUT"
            elif "Bot failed" in event.description and event.type == "error":
                self.errors_by_bot[event.bot_name] += 1
            
            # Keep the 20 most recent events
            self.recent_events.append({
                'time': datetime.datetime.now().strftime("%H:%M:%S"),
                'bot': event.bot_name,
                'type': event.type,
                'description': event.description
            })
            if len(self.recent_events) > 20:
                self.recent_events.pop(0)
            
            self.last_update = datetime.datetime.now()
    
    def print_summary(self):
        with self._lock:
            logger.info("=" * 60)
            logger.info("EVENT STATISTICS SUMMARY")
            logger.info("=" * 60)
            
            logger.info("\nEvents by bot:")
            for bot_name, count in self.event_counts.most_common():
                logger.info(f"  {bot_name}: {count} events")
            
            logger.info("\nEvents by type:")
            for event_type, count in self.event_types.most_common():
                logger.info(f"  {event_type}: {count} events")
            
            logger.info("\nErrors by bot:")
            for bot_name, count in sorted(self.errors_by_bot.items(), key=lambda x: x[1], reverse=True):
                if count > 0:
                    logger.info(f"  {bot_name}: {count} errors")
            
            logger.info("\nSuccesses by bot:")
            for bot_name, count in sorted(self.successes_by_bot.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {bot_name}: {count} successful runs")
            
            logger.info("\nCurrent bot states:")
            for bot_name, state in sorted(self.bot_states.items()):
                logger.info(f"  {bot_name}: {state}")
            
            logger.info("\nRecent events:")
            for i, event in enumerate(reversed(self.recent_events[:10]), 1):
                logger.info(f"  {i}. [{event['time']}] {event['bot']} - {event['type']}: {event['description']}")
            
            logger.info("=" * 60)

# Create statistics tracker
stats = EventStatistics()

# Event listeners to track all bot events
def log_event(event: BotEvent):
    events_received.append(event)
    logger.info(f"Event: {event.type} - {event.bot_name} - {event.description}")
    stats.record_event(event)

# Specific handlers for different event types
def handle_info_event(event: BotEvent):
    if "completed" in event.description:
        logger.info(f"{STATUS_SUCCESS} SUCCESS: {event.bot_name} completed successfully")

def handle_error_event(event: BotEvent):
    error_details = event.data.get('error', 'Unknown error')
    logger.error(f"{STATUS_ERROR} ERROR: {event.bot_name} - {error_details}")

def handle_warning_event(event: BotEvent):
    logger.warning(f"{STATUS_WARNING} WARNING: {event.bot_name} - {event.description}")

# Specific handler for Botman events
def handle_botman_event(event: BotEvent):
    logger.info(f"{STATUS_INFO} BOTMAN EVENT: {event.description}")
    logger.info(f"  Details: {event.data}")
    stats.record_event(event)

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
    
    # Set up event listeners for all bots - now using the global event manager
    for bot in bots:
        # Subscribe to different event types with specific handlers
        GLOBAL_EVENT_MANAGER.subscribe(bot.name, log_event)
        GLOBAL_EVENT_MANAGER.subscribe(bot.name, handle_info_event, "info")
        GLOBAL_EVENT_MANAGER.subscribe(bot.name, handle_error_event, "error")
        GLOBAL_EVENT_MANAGER.subscribe(bot.name, handle_warning_event, "warning")
    
    return bots

# Run a manual forced execution of all bots once
def force_execution(botman, bots):
    logger.info(f"{STATUS_INFO} Forcing execution of all bots...")
    for bot in bots:
        logger.info(f"=> Forcing execution of {bot.name}")
        botman.run_bot(bot)
    
    logger.info(f"{STATUS_SUCCESS} Forced execution complete")

# Monitor function to log bot states
def monitor_bots(botman, bots, interval=30):
    while True:
        logger.info("-" * 60)
        logger.info(f"{STATUS_INFO} BOT STATUS REPORT")
        logger.info("-" * 60)
        
        for bot in bots:
            metrics = botman.get_bot_metrics_by_name(bot.name)
            if metrics:
                state_icon = STATUS_IDLE if metrics.state == BotState.IDLE else STATUS_TIMEOUT if metrics.state == BotState.TIMEOUT else STATUS_RUNNING
                logger.info(f"{state_icon} Bot: {bot.name}")
                logger.info(f"  State: {metrics.state}")
                logger.info(f"  Runs: {metrics.runs}")
                logger.info(f"  Errors: {metrics.errors}")
                logger.info(f"  Last Run: {metrics.last_run}")
                
                # Check if in timeout
                if metrics.state == BotState.TIMEOUT:
                    timeout_remaining = (bot.timeout_until - datetime.datetime.now()).total_seconds()
                    logger.info(f"  Timeout until: {bot.timeout_until} ({int(timeout_remaining)}s remaining)")
                    
                # Get next scheduled run
                try:
                    next_run = bot.get_next_run()
                    time_until_next = (next_run - datetime.datetime.now()).total_seconds()
                    logger.info(f"  Next Run: {next_run} (in {int(time_until_next)}s)")
                except Exception as e:
                    logger.error(f"  Error getting next run: {e}")
        
        # Print event statistics
        stats.print_summary()
        
        logger.info("-" * 60)
        time.sleep(interval)

def statistics_monitor(interval=30):
    """Monitor and log statistics regularly"""
    while True:
        # Print stats to console
        stats.print_summary()
        time.sleep(interval)

def main():
    # Make sure global event manager is started
    if not GLOBAL_EVENT_MANAGER._running:
        GLOBAL_EVENT_MANAGER.start()
    
    # Create bots
    bots = create_test_bots()
    
    # Create Botman instance with custom name
    botman = Botman()
    botman.set_name("TestBotman")  # Give it a custom name
    
    # Subscribe to Botman events
    GLOBAL_EVENT_MANAGER.subscribe(botman.name, handle_botman_event)
    
    # Add all bots to the manager
    for bot in bots:
        botman.add_bot(bot)
    
    # Start the monitoring threads
    monitor_thread = threading.Thread(target=monitor_bots, args=(botman, bots, 60))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Starting the statistics monitoring in its own thread
    stats_thread = threading.Thread(target=statistics_monitor, args=(120,))  # every 2 minutes
    stats_thread.daemon = True
    stats_thread.start()
    
    # Print welcome message
    logger.info("=" * 70)
    logger.info(f"{STATUS_INFO} BOTMAN TEST HARNESS - Starting at {datetime.datetime.now()}")
    logger.info(f"{STATUS_INFO} Total bots: {len(bots)}")
    logger.info(f"{STATUS_INFO} Test duration: 20 minutes")
    logger.info("=" * 70)
    
    # Start Botman
    logger.info(f"{STATUS_INFO} Starting Botman...")
    botman.start()
    
    # Force execute all bots immediately to verify they work
    force_execution(botman, bots)
    
    # Run for 20 minutes
    test_duration = 20 * 60  # 20 minutes in seconds
    logger.info(f"{STATUS_INFO} Test will run for {test_duration} seconds")
    
    try:
        # Wait for the test duration
        time.sleep(test_duration)
    except KeyboardInterrupt:
        logger.info(f"{STATUS_WARNING} Test interrupted by user")
    finally:
        logger.info(f"{STATUS_INFO} Stopping Botman...")
        botman.stop()
        
        # Wait for any pending events
        GLOBAL_EVENT_MANAGER.wait_until_empty(timeout=5.0)
        # Don't stop the global event manager here as it might be needed by other components
        
        # Final report
        logger.info("=" * 70)
        logger.info(f"{STATUS_INFO} FINAL TEST REPORT")
        logger.info("=" * 70)
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
        
        # Print final statistics
        stats.print_summary()
        
        logger.info("=" * 70)
        logger.info(f"{STATUS_SUCCESS} Test completed successfully")
        logger.info("=" * 70)

if __name__ == "__main__":
    main() 