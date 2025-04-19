import time
from typing import Callable, List
from .exceptions import SoftError
from uuid import uuid4
from croniter import croniter
import datetime
import threading
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
        self.slack_webhook = (slack_webhook, slack_event_types) if slack_webhook else None
        self.chime_webhook = (chime_webhook, chime_event_types) if chime_webhook else None
        self._slack_event_subs = []
        self._chime_event_subs = []

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

        for schedule in self.schedule:
            try:
                croniter(schedule)
            except:
                raise ValueError(f"Invalid schedule format: {schedule}")
    
    @property
    def slack_webhook(self):
        return self._slack_webhook
    
    @slack_webhook.setter
    def slack_webhook(self, webhook_event_types: tuple[str, List[EventType] | EventType]):
        if not webhook_event_types:
            self._slack_webhook = None
            self._slack_event_subs = []
            return
        self._slack_webhook = webhook_event_types[0] if isinstance(webhook_event_types[0], list) else [webhook_event_types[0]]
        self._slack_event_subs = [SlackEventReceiver(webhook).on_event for webhook in self._slack_webhook]
        for sub in self._slack_event_subs:
           GLOBAL_EVENT_MANAGER.subscribe(self.name, sub, webhook_event_types[1] if webhook_event_types[1] else None)

    @property
    def chime_webhook(self):
        return self._chime_webhook
    
    @chime_webhook.setter
    def chime_webhook(self, webhook_event_types: tuple[str, List[EventType] | EventType]):
        if not webhook_event_types:
            self._chime_webhook = None
            self._chime_event_subs = []
            return
        self._chime_webhook = webhook_event_types[0] if isinstance(webhook_event_types[0], list) else [webhook_event_types[0]]
        self._chime_event_subs = [ChimeEventReceiver(webhook).on_event for webhook in self._chime_webhook]
        for sub in self._chime_event_subs:
            GLOBAL_EVENT_MANAGER.subscribe(self.name, sub, webhook_event_types[1] if webhook_event_types[1] else None)

    def __del__(self):
        """Clean up resources when the Bot is destroyed."""
        if hasattr(self, '_slack_event_subs'):
            try:
                for sub in self._slack_event_subs:
                    GLOBAL_EVENT_MANAGER.unsubscribe(self.name, sub)
            except:
                pass    
        if hasattr(self, '_chime_event_subs'):
            try:
                for sub in self._chime_event_subs:
                    GLOBAL_EVENT_MANAGER.unsubscribe(self.name, sub)
            except:
                pass
    

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
