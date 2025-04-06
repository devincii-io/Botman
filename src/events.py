from typing import Literal, Optional
import queue
import threading
import time

EventType = Literal["error", "info", "warning", "debug"]

class BotEvent:
    """Event object containing information about a bot event."""
    def __init__(self, bot_name: str, bot_id: str, type: EventType, description: str, data: dict):
        self.bot_name = bot_name
        self.bot_id = bot_id
        self.type = type
        self.description = description
        self.data = data

class EventManager:
    """Manages event subscriptions and publishing for bots."""
    def __init__(self):
        self.subscriptions = {}
        self._queue = queue.Queue()
        self._running = False
        self._lock = threading.Lock()
        self._worker_thread = None
    
    def subscribe(self, bot_name: str, callback: callable, event_type: Optional[EventType] = None):
        """
        Subscribe to events from a bot.
        
        Args:
            bot_name: Name of the bot to subscribe to
            callback: Function to call when an event occurs
            event_type: Specific event type to subscribe to (None for all types)
        """
        with self._lock:
            if bot_name not in self.subscriptions:
                self.subscriptions[bot_name] = {}
            
            if event_type is None:
                if "all" not in self.subscriptions[bot_name]:
                    self.subscriptions[bot_name]["all"] = []
                self.subscriptions[bot_name]["all"].append(callback)
            else:
                if event_type not in self.subscriptions[bot_name]:
                    self.subscriptions[bot_name][event_type] = []
                self.subscriptions[bot_name][event_type].append(callback)

    def publish(self, event: BotEvent):
        """Add an event to the queue for processing."""
        self._queue.put(event)
    
    def _process_queue(self):
        """Process events in FIFO order (first in, first out)"""
        while self._running:
            try:
                event = self._queue.get(block=True, timeout=1.0)
                
                with self._lock:
                    if event.bot_name in self.subscriptions:
                        if event.type in self.subscriptions[event.bot_name]:
                            for callback in self.subscriptions[event.bot_name][event.type]:
                                try:
                                    callback(event)
                                except Exception as e:
                                    print(f"Error in event callback: {e}")
                        
                        if "all" in self.subscriptions[event.bot_name]:
                            for callback in self.subscriptions[event.bot_name]["all"]:
                                try:
                                    callback(event)
                                except Exception as e:
                                    print(f"Error in 'all' event callback: {e}")
                
                self._queue.task_done()
            except queue.Empty:
                pass
    
    def start(self):
        """Start the event processing thread"""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._process_queue,
                name="EventManager",
                daemon=True
            )
            self._worker_thread.start()
    
    def stop(self):
        """Stop the event processing thread"""
        with self._lock:
            self._running = False
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
    
    def get_queue_size(self):
        """Get the current number of events in the queue"""
        return self._queue.qsize()
    
    def wait_until_empty(self, timeout=None):
        """Wait until all events have been processed"""
        try:
            self._queue.join()
        except Exception:
            pass
    
    def unsubscribe(self, bot_name: str, callback: callable = None, event_type: Optional[EventType] = None):
        """
        Unsubscribe from events.
        
        Args:
            bot_name: Name of the bot to unsubscribe from
            callback: Specific callback to remove (None to remove all)
            event_type: Specific event type to unsubscribe from (None for all types)
        """
        with self._lock:
            if bot_name not in self.subscriptions:
                return
                
            if callback is None and event_type is None:
                del self.subscriptions[bot_name]
                return
                
            if event_type is not None:
                if event_type in self.subscriptions[bot_name]:
                    if callback is None:
                        del self.subscriptions[bot_name][event_type]
                    else:
                        self.subscriptions[bot_name][event_type] = [
                            cb for cb in self.subscriptions[bot_name][event_type] 
                            if cb != callback
                        ]
            else:
                for event_type in list(self.subscriptions[bot_name].keys()):
                    self.subscriptions[bot_name][event_type] = [
                        cb for cb in self.subscriptions[bot_name][event_type] 
                        if cb != callback
                    ]
                    if not self.subscriptions[bot_name][event_type]:
                        del self.subscriptions[bot_name][event_type]
                
            if not self.subscriptions[bot_name]:
                del self.subscriptions[bot_name]


GLOBAL_EVENT_MANAGER = EventManager()
GLOBAL_EVENT_MANAGER.start()

import atexit

def cleanup():
    """Stop the global event manager at program exit."""
    GLOBAL_EVENT_MANAGER.stop()

atexit.register(cleanup)

