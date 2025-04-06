from typing import Literal, Optional
import queue
import threading
import time

EventType = Literal["error", "info", "warning"]

class BotEvent:
    def __init__(self, bot_name: str, bot_id: str, type: EventType, description: str, data: dict):
        self.bot_name = bot_name
        self.bot_id = bot_id
        self.type = type
        self.description = description
        self.data = data

class EventManager:
    def __init__(self):
        # Structure: {bot_name: {event_type: [callbacks]}}
        self.subscriptions = {}
        # Use Queue which is a thread-safe FIFO queue
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
            # Initialize bot entry if it doesn't exist
            if bot_name not in self.subscriptions:
                self.subscriptions[bot_name] = {}
            
            # If event_type is None, we're subscribing to all event types
            if event_type is None:
                # Add this callback to the special "all" category
                if "all" not in self.subscriptions[bot_name]:
                    self.subscriptions[bot_name]["all"] = []
                self.subscriptions[bot_name]["all"].append(callback)
            else:
                # Add this callback to the specific event type
                if event_type not in self.subscriptions[bot_name]:
                    self.subscriptions[bot_name][event_type] = []
                self.subscriptions[bot_name][event_type].append(callback)

    def publish(self, event: BotEvent):
        # Add event to the FIFO queue
        self._queue.put(event)
    
    def _process_queue(self):
        """Process events in FIFO order (first in, first out)"""
        while self._running:
            try:
                # Get the oldest event from the queue (FIFO)
                event = self._queue.get(block=True, timeout=1.0)
                
                # Process this event
                with self._lock:
                    if event.bot_name in self.subscriptions:
                        # Call callbacks registered for this specific event type
                        if event.type in self.subscriptions[event.bot_name]:
                            for callback in self.subscriptions[event.bot_name][event.type]:
                                try:
                                    callback(event)
                                except Exception as e:
                                    print(f"Error in event callback: {e}")
                        
                        # Also call callbacks registered for all event types
                        if "all" in self.subscriptions[event.bot_name]:
                            for callback in self.subscriptions[event.bot_name]["all"]:
                                try:
                                    callback(event)
                                except Exception as e:
                                    print(f"Error in 'all' event callback: {e}")
                
                # Mark this task as done
                self._queue.task_done()
            except queue.Empty:
                # No events in queue, just continue waiting
                pass
    
    def start(self):
        """Start the event processing thread"""
        with self._lock:
            if self._running:
                return  # Already running
            
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
            # Handle potential timeout exception
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
                
            # If no specific callback or event type, remove all subscriptions for this bot
            if callback is None and event_type is None:
                del self.subscriptions[bot_name]
                return
                
            # If we have a specific event type
            if event_type is not None:
                if event_type in self.subscriptions[bot_name]:
                    if callback is None:
                        # Remove all callbacks for this event type
                        del self.subscriptions[bot_name][event_type]
                    else:
                        # Remove just this specific callback
                        self.subscriptions[bot_name][event_type] = [
                            cb for cb in self.subscriptions[bot_name][event_type] 
                            if cb != callback
                        ]
            else:
                # Remove this callback from all event types
                for event_type in list(self.subscriptions[bot_name].keys()):
                    self.subscriptions[bot_name][event_type] = [
                        cb for cb in self.subscriptions[bot_name][event_type] 
                        if cb != callback
                    ]
                    # Clean up empty lists
                    if not self.subscriptions[bot_name][event_type]:
                        del self.subscriptions[bot_name][event_type]
                
            # Clean up empty dictionaries
            if not self.subscriptions[bot_name]:
                del self.subscriptions[bot_name]
    


