import time
import threading
from .bot import Bot
from .btm_types import BotMetrics, BotState
from concurrent.futures import ThreadPoolExecutor
import datetime
import copy
import atexit
from .events import GLOBAL_EVENT_MANAGER, BotEvent, SlackEventReceiver, ChimeEventReceiver, EventType 
import uuid

class Botman:
    """Main bot management class that coordinates bot execution and scheduling."""
    def __init__(self):
        """Initialize a new Botman instance with an empty bot collection."""
        self.bots: list[Bot] = []
        self._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="Botman")
        self.running = False
        self._lock = threading.Lock()
        self.id = str(uuid.uuid4())
        self.name = "botman"
        self._slack_subscribers = []
        self._chime_subscribers = []
        
        if not GLOBAL_EVENT_MANAGER._running:
            GLOBAL_EVENT_MANAGER.start()
        
        atexit.register(self.stop)

    def add_bot(self, bot: Bot):
        """
        Add a bot to the manager.
        
        Args:
            bot: The Bot instance to add
        """
        with self._lock:
            self.bots.append(bot)
            
        GLOBAL_EVENT_MANAGER.publish(BotEvent(
            self.name,
            self.id,
            "info",
            f"Bot '{bot.name}' added to Botman",
            {"bot_name": bot.name, "bot_id": str(bot.id)}
        ))
    
    def subscribe_slack_webhook(self, webhook: str, event_types: list[EventType] = None):
        """
        Subscribe to a Slack webhook.
        
        Args:
            webhook: The Slack webhook to subscribe to
        """
        with self._lock:
            self._slack_subscribers.append(webhook)
            GLOBAL_EVENT_MANAGER.subscribe(self.name, SlackEventReceiver(webhook).on_event, event_types)
    
    def subscribe_chime_webhook(self, webhook: str, event_types: list[EventType] = None):
        """
        Subscribe to a Chime webhook.
        
        Args:
            webhook: The Chime webhook to subscribe to
        """
        with self._lock:
            self._chime_subscribers.append(webhook)
            GLOBAL_EVENT_MANAGER.subscribe(self.name, ChimeEventReceiver(webhook).on_event, event_types)
    

    def remove_bot(self, bot: Bot):
        """
        Remove a bot from the manager.
        
        Args:
            bot: The Bot instance to remove
        """
        with self._lock:
            if bot in self.bots:
                GLOBAL_EVENT_MANAGER.unsubscribe(bot.name)
                self.bots.remove(bot)
                
                GLOBAL_EVENT_MANAGER.publish(BotEvent(
                    self.name,
                    self.id,
                    "info",
                    f"Bot '{bot.name}' removed from Botman",
                    {"bot_name": bot.name, "bot_id": str(bot.id)}
                ))

    def run_bot(self, bot: Bot):
        """
        Run a single bot in a separate thread.
        
        Args:
            bot: The Bot instance to run
            
        Returns:
            Future object representing the pending execution
        """
        GLOBAL_EVENT_MANAGER.publish(BotEvent(
            self.name,
            self.id,
            "debug",
            f"Running bot '{bot.name}'",
            {"bot_name": bot.name, "bot_id": str(bot.id)}
        ))
        
        future = self._executor.submit(bot.run)
        return future

    def run_all_bots(self):
        """Run all bots in the order they were added."""
        GLOBAL_EVENT_MANAGER.publish(BotEvent(
            self.name,
            self.id,
            "info",
            "Running all bots",
            {"bot_count": len(self.bots)}
        ))
        
        for bot in self.bots:
            self.run_bot(bot)

    def _loop(self):
        """Main scheduling loop that checks for due bots and runs them."""
        while self.running:
            now = datetime.datetime.now()
            next_times = []
            bots_to_run = []
            
            with self._lock:
                for bot in self.bots:
                    if bot.metrics.state == BotState.RUNNING:
                        continue
                    
                    if bot.is_in_timeout():
                        if bot.timeout_until:
                            next_times.append(bot.timeout_until)
                        continue
                        
                    if bot.is_due(False):
                        bots_to_run.append(bot)
                        GLOBAL_EVENT_MANAGER.publish(BotEvent(
                            self.name,
                            self.id,
                            "debug",
                            f"Bot '{bot.name}' is scheduled to run",
                            {"bot_name": bot.name, "bot_id": str(bot.id), "scheduled_time": str(now)}
                        ))
                    else:
                        next_times.append(bot.get_next_run())
            
            for bot in bots_to_run:
                self.run_bot(bot)
            
            sleep_time = 5
            if next_times:
                min_next_time = min(next_times)
                sleep_time = max(0.5, min((min_next_time - now).total_seconds(), 120))
            
            if not self.running:
                break
                
            time.sleep(sleep_time)
    
    def start(self):
        """Start the bot manager and begin the scheduling loop."""
        with self._lock:
            if self.running:
                return
            self.running = True
            
            GLOBAL_EVENT_MANAGER.publish(BotEvent(
                self.name,
                self.id,
                "info",
                "Botman started",
                {"bot_count": len(self.bots)}
            ))
        
        self._executor.submit(self._loop)

    def stop(self):
        """Stop the bot manager and clean up resources."""
        with self._lock:
            if not self.running:
                return
                
            self.running = False
            
            GLOBAL_EVENT_MANAGER.publish(BotEvent(
                self.name,
                self.id,
                "info",
                "Botman stopping",
                {"bot_count": len(self.bots)}
            ))
            
        self._executor.shutdown(wait=True)
        
        GLOBAL_EVENT_MANAGER.publish(BotEvent(
            self.name,
            self.id,
            "info", 
            "Botman stopped",
            {"shutdown_time": str(datetime.datetime.now())}
        ))

    def get_bot_metrics(self) -> list[BotMetrics]:
        """
        Get metrics for all managed bots.
        
        Returns:
            List of BotMetrics objects for all bots
        """
        with self._lock:
            return [copy.deepcopy(bot.metrics) for bot in self.bots]
    
    def get_bot_metrics_by_name(self, name: str) -> BotMetrics:
        """
        Get metrics for a specific bot by name.
        
        Args:
            name: Name of the bot to get metrics for
            
        Returns:
            BotMetrics for the specified bot or None if not found
        """
        with self._lock:
            for bot in self.bots:
                if bot.name == name:
                    return copy.deepcopy(bot.metrics)
        return None
        
    def set_name(self, name: str):
        """
        Set a custom name for this Botman instance.
        
        Args:
            name: New name for the Botman instance
        """
        self.name = name
        
    def __del__(self):
        """Ensure everything is cleaned up when Botman is destroyed."""
        self.stop()