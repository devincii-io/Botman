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

## Installation

```bash
pip install botman
```

## Quick Start

```python
from botman import Botman, Bot
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

## Bot Configuration

Bots can be configured with various parameters:

```python
bot = Bot(
    name="advanced_bot",              # Name for the bot
    schedule=["*/5 * * * *", "0 */1 * * *"],  # Multiple schedules supported
    function=my_function,             # Function to execute
    slack_webhook="https://hooks.slack.com/...",  # Optional Slack notifications
    chime_webhook="https://hooks.chime.aws/...",  # Optional Chime notifications
    initial_timeout=60,               # Timeout after failures (seconds)
    retries=3,                        # Number of retries before timeout
    retry_delay=10                    # Delay between retries (seconds)
)
```

## Error Handling

Botman includes a robust error handling system:

```python
from botman import Botman, Bot, SoftError

def risky_function():
    # If this raises an exception, Botman will:
    # 1. Retry up to the configured number of times
    # 2. Enter timeout state if all retries fail
    # 3. Emit appropriate events for monitoring
    # 4. Return a SoftError object with details
    pass
```

## Monitoring Bot Activity

```python
# Get metrics for all bots
metrics = manager.get_bot_metrics()

# Get metrics for a specific bot
bot_metrics = manager.get_bot_metrics_by_name("hello_bot")

# Metrics include:
# - Number of runs
# - Last run time
# - Error count
# - Current state (IDLE, RUNNING, TIMEOUT)
```

## Event System

Subscribe to events for monitoring bot activity:

```python
from botman.events import GLOBAL_EVENT_MANAGER

def event_handler(event):
    print(f"Bot {event.source}: {event.message}")

# Subscribe to events from a specific bot
GLOBAL_EVENT_MANAGER.subscribe("hello_bot", event_handler)

# Or subscribe to all events
GLOBAL_EVENT_MANAGER.subscribe("*", event_handler)
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

Made with ❤️ for simplified task scheduling