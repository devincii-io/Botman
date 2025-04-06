import time
from typing import Callable, List
from .exceptions import SoftError
from uuid import uuid4
from croniter import croniter
import datetime
import threading
from .btm_types import BotMetrics, BotState
from .events import EventManager, BotEvent

class Bot:
    def __init__(self, name: str, schedule: List[str] | str, function: Callable, 
                 slack_webhook: List[str] | str = None, chime_webhook: List[str] | str = None,
                 initial_timeout: int = 60, retries: int = 3, retry_delay: int = 10):
        
        self.schedule = schedule if isinstance(schedule, list) else [schedule]
        self.name = name
        self.function = function
        self.init_time = datetime.datetime.now()
        self.id = uuid4()
        self.slack_webhook = slack_webhook if isinstance(slack_webhook, list) else [slack_webhook]
        self.chime_webhook = chime_webhook if isinstance(chime_webhook, list) else [chime_webhook]
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
        self._lock = threading.Lock()  # Keep this lock for state transitions
        self.event_manager = EventManager()

        for schedule in self.schedule:
            try:
                croniter(schedule)  # Validate during initialization
            except:
                raise ValueError(f"Invalid schedule format: {schedule}")
    
    def run(self, set_last_run: bool = True):
        # Check and update state atomically
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
                    self.event_manager.publish(BotEvent(self.name, self.id, "info", "Bot completed", {}))
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
                            {"error": str(e), "timeout_seconds": self.initial_timeout}
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
        self.schedule.append(schedule)

    def remove_schedule(self, schedule: str):
        self.schedule.remove(schedule)

    def get_next_run(self):
        """Get the next scheduled run time for this bot"""
        # Check timeout state without lock since we only read
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
            # In case of scheduling errors, return a time far in the future
            return datetime.datetime.now() + datetime.timedelta(hours=1)

    def is_due(self, set_last_run: bool = False):
        """Check if the bot is due to run"""
        with self._lock:
            # If bot is running or in timeout, it's not due
            if self.metrics.state in [BotState.RUNNING, BotState.TIMEOUT]:
                return False
        
        # Get next run time outside the lock
        now = datetime.datetime.now()
        try:
            next_run = self.get_next_run()
            is_due = next_run <= now
            
            # Update last_run if needed, under lock
            if is_due and set_last_run:
                with self._lock:
                    self.metrics.last_run = now
                
            return is_due
        except Exception:
            return False

    def set_last_run(self, last_run: datetime.datetime):
        with self._lock:
            self.metrics.last_run = last_run
