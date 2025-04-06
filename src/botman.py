import time
import threading
from .bot import Bot
from .btm_types import BotMetrics, BotState
from concurrent.futures import ThreadPoolExecutor
import datetime
import copy



class Botman:
    def __init__(self):
        self.bots: list[Bot] = []
        self._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="Botman")
        self.running = False
        self._lock = threading.Lock()  # Keep this for start/stop synchronization

    def add_bot(self, bot: Bot):
        with self._lock:
            self.bots.append(bot)
    
    def remove_bot(self, bot: Bot):
        with self._lock:
            self.bots.remove(bot)

    def run_bot(self, bot: Bot):
        future = self._executor.submit(bot.run)
        return future

    def run_all_bots(self):
        for bot in self.bots:
            self.run_bot(bot)

    def _loop(self):
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
        with self._lock:
            if self.running:
                return  # Already running
            self.running = True
            self._executor.submit(self._loop)

    def stop(self):
        with self._lock:
            self.running = False
        self._executor.shutdown(wait=True)

    def get_bot_metrics(self) -> list[BotMetrics]:
        with self._lock:
            return [copy.deepcopy(bot.metrics) for bot in self.bots]
    
    def get_bot_metrics_by_name(self, name: str) -> BotMetrics:
        with self._lock:
            for bot in self.bots:
                if bot.name == name:
                    return copy.deepcopy(bot.metrics)
        return None