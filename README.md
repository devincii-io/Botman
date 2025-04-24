# Botman

![Botman Logo](https://img.shields.io/badge/Botman-Task%20Scheduling-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful Python library to schedule and manage tasks with a simple interface. Botman provides a global event loop that continuously monitors and executes scheduled bots based on cron-style expressions.

## Features

- ✅ **Cron-based Scheduling** - Schedule tasks using standard cron expressions
- ✅ **Retry Mechanism** - Built-in retry logic with configurable timeout periods
- ✅ **Event Management** - Global event system for monitoring and notifications
- ✅ **Thread Safety** - Concurrent execution with proper thread management
- ✅ **Webhook Integration** - Optional Slack and Chime webhook support for notifications
- ✅ **Multiple Schedules** - Run bots on multiple schedules with a single configuration
- ✅ **Metrics Collection** - Detailed metrics for monitoring bot performance
- ✅ **Timeout Handling** - Automatic timeout management after failures
- ✅ **Resource Management** - Clean shutdown and proper resource handling

## Installation

```bash
pip install botman
```

## Quick Start

```python
from Botman import Botman, Bot
import datetime

# Create a function to run
def hello_world():
    print(f"Hello, World! Time: {datetime.datetime.now()}")
    return "Success"

# Create a Bot instance with a schedule (runs every minute)
my_bot = Bot(
    name="hello_bot",
    schedule="* * * * *",
    function=hello_world
)

# Create a Botman instance and add the bot
manager = Botman()
manager.add_bot(my_bot)

# Start the manager
manager.start()

# To stop the manager later
# manager.stop()
```

## Architecture

Botman is designed with a clean, modular architecture:

- **Botman** - The main scheduler and coordinator that manages bots
- **Bot** - Individual task units with their own schedule and execution logic
- **EventManager** - Centralized pub/sub system for event-based communication
- **EventReceivers** - Integration points for external services (Slack, Chime)
- **Metrics** - Performance tracking and state monitoring

The library uses threading for concurrent execution while maintaining thread safety with locks.

## Detailed Bot Configuration

Bots can be configured with a wide range of parameters:

```python
from Botman import Bot, EventType

bot = Bot(
    name="advanced_bot",              # Required: Unique name for the bot
    schedule=["*/5 * * * *", "0 */1 * * *"],  # Required: One or multiple cron schedules
    function=my_function,             # Required: Function to execute
    
    # Webhook notifications
    slack_webhook="https://hooks.slack.com/...",  # Optional: Slack webhook(s)
    chime_webhook="https://hooks.chime.aws/...",  # Optional: Chime webhook(s)
    
    # Event filtering
    slack_event_types=["error", "warning"],       # Optional: Specific event types for Slack
    chime_event_types=EventType.error,            # Optional: Event types for Chime
    
    # Retry configuration
    initial_timeout=60,               # Optional: Timeout after failures (seconds)
    retries=3,                        # Optional: Number of retries before timeout
    retry_delay=10,                   # Optional: Delay between retries (seconds)
    is_com_bot=False                  # Optional: Set to True for COM integration on Windows
)
```

### Schedule Format

Botman uses standard cron expressions for scheduling:

- `* * * * *` - Run every minute
- `*/5 * * * *` - Run every 5 minutes
- `0 */1 * * *` - Run at the start of every hour
- `0 12 * * *` - Run at 12:00 PM daily
- `0 0 * * 0` - Run at midnight on Sundays

## Event System

Botman includes a powerful event system for monitoring and notifications:

```python
from Botman import GLOBAL_EVENT_MANAGER, EventType

# Define an event handler
def my_event_handler(event):
    print(f"Bot: {event.bot_name}, Type: {event.event_type}, Message: {event.description}")
    
    # Access additional data
    if event.data:
        print(f"Data: {event.data}")

# Subscribe to events from a specific bot with specific event types
GLOBAL_EVENT_MANAGER.subscribe(
    bot_name="my_bot", 
    callback=my_event_handler,
    event_types=["error", "warning"]  # Only receive these event types
)

# Or subscribe to all events from a specific bot
GLOBAL_EVENT_MANAGER.subscribe("my_bot", my_event_handler)

# Or subscribe to a specific event type from all bots
GLOBAL_EVENT_MANAGER.subscribe("all", my_event_handler, ["error"])

# Unsubscribe when no longer needed
GLOBAL_EVENT_MANAGER.unsubscribe("my_bot", my_event_handler)
```

### Available Event Types

- `info` - Informational messages
- `error` - Error conditions
- `warning` - Warning conditions
- `debug` - Detailed debugging information
- `all` - Special type that receives all event types

## Webhook Integration

Botman supports sending event notifications to Slack and Chime:

```python
# At the Bot level
bot = Bot(
    name="monitored_bot",
    schedule="*/5 * * * *",
    function=important_task,
    slack_webhook="https://hooks.slack.com/...",
    slack_event_types=["error", "warning"]  # Only send errors and warnings
)

# At the Botman level (for manager-level events)
manager = Botman()
manager.subscribe_slack_webhook(
    webhook="https://hooks.slack.com/...",
    event_types=["info", "error"]
)

# Multiple webhooks are supported
bot.add_slack_webhook([
    "https://hooks.slack.com/team1/...",
    "https://hooks.slack.com/team2/..."
])
```

## Advanced Bot Management

### Manual Bot Execution

You can manually trigger bot execution outside of scheduled times:

```python
# Run a specific bot immediately
manager.run_bot(my_bot)

# Run all managed bots
manager.run_all_bots()
```

### Bot Metrics

Track bot performance and status:

```python
# Get metrics for all bots
all_metrics = manager.get_bot_metrics()

# Get metrics for a specific bot
bot_metrics = manager.get_bot_metrics_by_name("my_bot")

# Metrics include:
print(f"Runs: {bot_metrics.runs}")
print(f"Errors: {bot_metrics.errors}")
print(f"Last Run: {bot_metrics.last_run}")
print(f"State: {bot_metrics.state}")  # IDLE, RUNNING, TIMEOUT, or ERROR
print(f"Since: {bot_metrics.since}")  # When the bot was created
```

### Managing Bot State

```python
# Check if a bot is in timeout
if my_bot.is_in_timeout():
    print(f"Bot will be available after: {my_bot.timeout_until}")

# Get the next scheduled run time
next_run = my_bot.get_next_run()
print(f"Next scheduled execution: {next_run}")

# Check if a bot is due to run
if my_bot.is_due():
    print("Bot is due to execute now")
```

## Error Handling

Botman provides a sophisticated error handling system:

```python
from Botman import Bot, SoftError

def risky_function():
    try:
        # Your code here
        result = perform_operation()
        return result
    except Exception as e:
        # You can handle exceptions yourself or let Botman handle them
        # If unhandled, Botman will retry according to configuration
        raise  # Re-raise to trigger Botman's retry mechanism
        
# Alternatively, return a SoftError object for custom error handling
def alternative_error_handling():
    try:
        # Your code here
        result = perform_operation()
        return result
    except Exception as e:
        # Create a SoftError with custom details
        return SoftError(
            bot_name="my_bot",
            bot_id="unique_id",
            message=str(e)
        )
```

## Thread Safety

Botman uses thread-safe operations to ensure reliable concurrent execution:

- Each bot runs in its own thread from a thread pool
- Internal locking mechanisms prevent race conditions
- Event processing occurs in a dedicated thread
- Proper cleanup occurs on shutdown, including during Python interpreter exit

## COM Integration

Botman supports Windows COM (Component Object Model) integration for bots that need to interact with COM objects:

```python
# Create a bot that uses COM objects
com_bot = Bot(
    name="excel_automation",
    schedule="0 9 * * 1-5",  # Weekdays at 9:00 AM
    function=update_excel_report,
    is_com_bot=True  # Enable COM integration
)
```

When `is_com_bot` is set to `True`, Botman will:
- Initialize the COM environment before executing the bot function
- Uninitialize the COM environment after execution completes
- Ensure proper COM threading model is maintained

This is particularly useful for automating Windows applications like Excel, Outlook, or other COM-enabled software.

## API Reference

### Botman Class

```python
# Main bot scheduler and manager
botman = Botman()

# Core methods
botman.add_bot(bot)                # Add a bot to the manager
botman.remove_bot(bot)             # Remove a bot from the manager
botman.start()                     # Start the scheduler
botman.stop()                      # Stop the scheduler
botman.run_bot(bot)                # Run a specific bot immediately
botman.run_all_bots()              # Run all bots immediately

# Webhook integration
botman.subscribe_slack_webhook(webhook, event_types)
botman.subscribe_chime_webhook(webhook, event_types)

# Metrics
botman.get_bot_metrics()           # Get metrics for all bots
botman.get_bot_metrics_by_name(name)  # Get metrics for a specific bot
botman.set_name(name)              # Set a custom name for this manager
```

### Bot Class

```python
# Create a bot instance
bot = Bot(name, schedule, function, **kwargs)  # kwargs includes: initial_timeout, retries, retry_delay, is_com_bot, etc.

# Schedule management
bot.add_schedule(schedule)         # Add another schedule 
bot.remove_schedule(schedule)      # Remove a schedule
bot.get_next_run()                 # Get next scheduled execution time
bot.is_due(set_last_run=False)     # Check if the bot is due to run

# State management
bot.is_in_timeout()                # Check if bot is in timeout
bot.run(set_last_run=True)         # Execute the bot's function
bot.set_last_run(datetime)         # Manually set the last run time

# Webhook management
bot.add_slack_webhook(webhook, event_types)
bot.add_chime_webhook(webhook, event_types)
bot.remove_webhook_subscriptions()
```

### EventManager

```python
from Botman import GLOBAL_EVENT_MANAGER

# Event subscription
GLOBAL_EVENT_MANAGER.subscribe(bot_name, callback, event_types)
GLOBAL_EVENT_MANAGER.unsubscribe(bot_name, callback, event_types)

# Event publishing
GLOBAL_EVENT_MANAGER.publish(event)  # Publish a BotEvent

# Manager control
GLOBAL_EVENT_MANAGER.start()        # Start the event processing thread
GLOBAL_EVENT_MANAGER.stop()         # Stop the event processing thread
GLOBAL_EVENT_MANAGER.wait_until_empty(timeout)  # Wait for all events to process
```

## Common Patterns and Best Practices

1. **Define clear bot responsibilities** - Each bot should have a single, clear purpose
2. **Use proper error handling** - Catch and log exceptions appropriately
3. **Monitor bot performance** - Subscribe to events to monitor health
4. **Use timeouts wisely** - Set appropriate timeout periods based on task criticality
5. **Clean up resources** - Ensure bots properly clean up any resources they use
6. **Use appropriate schedules** - Don't schedule CPU-intensive tasks too frequently
7. **Implement proper logging** - Add detailed logging in bot functions

## Troubleshooting

### Bot Not Running on Schedule

- Check the cron expression format
- Verify the bot is in the `IDLE` state, not `RUNNING` or `TIMEOUT`
- Check if the bot's function is taking longer than expected

### High CPU Usage

- Reduce frequency of CPU-intensive tasks
- Check for infinite loops or blocking operations in bot functions
- Monitor the thread pool usage

### Memory Leaks

- Ensure bots clean up resources properly
- Check for event handlers that accumulate data
- Monitor for large objects in bot function closures

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Made with ❤️ for simplified task scheduling