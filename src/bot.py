import time
from typing import Callable, List, Union, Optional
from .exceptions import SoftError
from uuid import uuid4
from croniter import croniter
import datetime
import threading
import atexit
from .btm_types import BotMetrics, BotState
from .events import BotEvent, GLOBAL_EVENT_MANAGER, SlackEventReceiver, ChimeEventReceiver
from typing import Literal

EventType = Literal["error", "info", "warning", "debug"]


class Bot:
    """Bot class representing a scheduled task or function."""
    def __init__(self, name: str, schedule: List[str] | str, function: Callable, 
                 slack_webhook: List[str] | str = None, chime_webhook: List[str] | str = None,
                 slack_event_types: List[EventType] | EventType = None, chime_event_types: List[EventType] | EventType = None,
                 initial_timeout: int = 60, retries: int = 3, retry_delay: int = 10):
        """
        Initialize a Bot instance.
        
        Args:
            name: Name of the bot
            schedule: Cron-style schedule(s) for when the bot should run
            function: Callable to execute when the bot runs
            slack_webhook: Optional Slack webhook(s) for notifications
            chime_webhook: Optional Chime webhook(s) for notifications
            slack_event_types: Optional Slack event types to subscribe to
            chime_event_types: Optional Chime event types to subscribe to
            initial_timeout: Timeout duration in seconds after failures
            retries: Number of retries before entering timeout
            retry_delay: Seconds to wait between retries
        """
        self.schedule = schedule if isinstance(schedule, list) else [schedule]
        self.name = name
        self.function = function
        self.init_time = datetime.datetime.now()
        self.id = uuid4()
        
        # Initialize webhook subscriptions tracking
        self._webhook_subscriptions = []
        
        # Setup webhooks
        if slack_webhook:
            self.add_webhook_subscriptions(slack_webhook, slack_event_types, SlackEventReceiver)
        
        if chime_webhook:
            self.add_webhook_subscriptions(chime_webhook, chime_event_types, ChimeEventReceiver)

        self.metrics = BotMetrics(
            errors=0,
            runs=0,
            last_run=None,
            since=datetime.datetime.now(),
            state=BotState.IDLE
        )

        self.initial_timeout = initial_timeout
        self.retries = retries
        self.retry_delay = retry_delay if retry_delay < 60 else 60
        self.timeout_until = None
        self._lock = threading.Lock()
        self.event_manager = GLOBAL_EVENT_MANAGER

        # Register cleanup handler
        atexit.register(self.shutdown)

        for schedule in self.schedule:
            try:
                croniter(schedule)
            except:
                raise ValueError(f"Invalid schedule format: {schedule}")
    
    def add_webhook_subscriptions(self, webhooks: Union[List[str], str], 
                                  event_types: Optional[Union[List[EventType], EventType]], 
                                  receiver_class: type):
        """
        Add webhook subscriptions using the specified receiver class.
        
        Args:
            webhooks: Single webhook URL or list of webhook URLs
            event_types: Event types to subscribe to
            receiver_class: The webhook receiver class to use (SlackEventReceiver, ChimeEventReceiver, etc.)
        """
        if not webhooks:
            return
            
        webhooks = webhooks if isinstance(webhooks, list) else [webhooks]
        
        for webhook in webhooks:
            receiver = receiver_class(webhook)
            GLOBAL_EVENT_MANAGER.subscribe(self.name, receiver.on_event, event_types)
            self._webhook_subscriptions.append((self.name, receiver.on_event))
    
    def remove_webhook_subscriptions(self):
        """Remove all webhook subscriptions."""
        for bot_name, callback in self._webhook_subscriptions:
            try:
                GLOBAL_EVENT_MANAGER.unsubscribe(bot_name, callback)
            except:
                pass
        self._webhook_subscriptions = []
    
    # Public methods for adding specific webhook types
    def add_slack_webhook(self, webhook: Union[List[str], str], 
                         event_types: Optional[Union[List[EventType], EventType]] = None):
        """
        Add a Slack webhook subscription.
        
        Args:
            webhook: Single Slack webhook URL or list of webhook URLs
            event_types: Event types to subscribe to
        """
        self.add_webhook_subscriptions(webhook, event_types, SlackEventReceiver)
    
    def add_chime_webhook(self, webhook: Union[List[str], str], 
                         event_types: Optional[Union[List[EventType], EventType]] = None):
        """
        Add a Chime webhook subscription.
        
        Args:
            webhook: Single Chime webhook URL or list of webhook URLs
            event_types: Event types to subscribe to
        """
        self.add_webhook_subscriptions(webhook, event_types, ChimeEventReceiver)
    
    def shutdown(self):
        """Safely shutdown the bot and clean up all resources."""
        try:
            self.remove_webhook_subscriptions()
        except:
            pass
        
    def __del__(self):
        """Clean up resources when the Bot is destroyed."""
        self.shutdown()

    def run(self, set_last_run: bool = True):
        """
        Execute the bot's function with retry logic.
        
        Args:
            set_last_run: Whether to update the last run time
            
        Returns:
            Result from the function or SoftError in case of failure
        """
        with self._lock:
            if self.metrics.state in [BotState.RUNNING, BotState.TIMEOUT]:
                return False
            self.metrics.state = BotState.RUNNING
            self.event_manager.publish(BotEvent(self.name, self.id, "info", "Bot started", {}))

        current_try = 0
        while current_try < self.retries:
            try:
                with self._lock:
                    self.metrics.runs += 1
                    result = self.function()
                    
                    if set_last_run:
                        self.metrics.last_run = datetime.datetime.now()
                    self.metrics.state = BotState.IDLE
                    self.event_manager.publish(BotEvent(self.name, self.id, "info", "Bot completed", {
                        "result": result
                    }))
                return result
            except Exception as e:
                current_try += 1
                self.metrics.errors += 1
                
                self.event_manager.publish(BotEvent(
                    self.name,
                    self.id,
                    "warning" if current_try < self.retries else "error",
                    f"Bot failed (attempt {current_try}/{self.retries})", 
                    {"error": str(e), "attempt": current_try, "retries": self.retries}
                ))
                
                time.sleep(self.retry_delay * current_try)    
                
                if current_try == self.retries:
                    with self._lock:
                        self.metrics.state = BotState.TIMEOUT
                        self.timeout_until = datetime.datetime.now() + datetime.timedelta(seconds=self.initial_timeout)
                        self.event_manager.publish(BotEvent(
                            self.name, 
                            self.id, 
                            "error",
                            f"Bot entered timeout for {self.initial_timeout} seconds", 
                            {"error": SoftError(self.name, self.id, str(e)).to_dict(), "timeout_seconds": self.initial_timeout}
                        ))
                    return SoftError(self.name, self.id, str(e))

    def is_in_timeout(self) -> bool:
        """Check if bot is in timeout and update state if timeout has expired"""
        with self._lock:
            if self.metrics.state == BotState.TIMEOUT:
                if self.timeout_until and datetime.datetime.now() >= self.timeout_until:
                    self.metrics.state = BotState.IDLE
                    self.timeout_until = None
                    return False
                return True
            return False

    def add_schedule(self, schedule: str):
        """Add a new schedule to the bot."""
        self.schedule.append(schedule)

    def remove_schedule(self, schedule: str):
        """Remove a schedule from the bot."""
        self.schedule.remove(schedule)

    def get_next_run(self):
        """Get the next scheduled run time for this bot"""
        if self.metrics.state == BotState.TIMEOUT and self.timeout_until:
            return self.timeout_until
            
        runs = []
        try:
            if self.metrics.last_run is None:
                for schedule in self.schedule:
                    cron = croniter(schedule, self.init_time)
                    next_run = cron.get_next(datetime.datetime)
                    runs.append(next_run)
            else:
                for schedule in self.schedule:
                    cron = croniter(schedule, self.metrics.last_run)
                    next_run = cron.get_next(datetime.datetime)
                    runs.append(next_run)
            return min(runs)
        except Exception as e:
            return datetime.datetime.now() + datetime.timedelta(hours=1)

    def is_due(self, set_last_run: bool = False):
        """Check if the bot is due to run"""
        with self._lock:
            if self.metrics.state in [BotState.RUNNING, BotState.TIMEOUT]:
                return False
        
        now = datetime.datetime.now()
        try:
            next_run = self.get_next_run()
            is_due = next_run <= now
            
            if is_due and set_last_run:
                with self._lock:
                    self.metrics.last_run = now
                
            return is_due
        except Exception:
            return False

    def set_last_run(self, last_run: datetime.datetime):
        """Manually set the last run time."""
        with self._lock:
            self.metrics.last_run = last_run
