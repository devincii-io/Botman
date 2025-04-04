from typing import Callable, List
from .utils import SoftError
from uuid import uuid4
from croniter import croniter
import datetime

class Bot:
    def __init__(self, name: str, schedule: List[str] | str, function: Callable, 
                 slack_webhook: List[str] | str = None, chime_webhook: List[str] | str = None,
                 raise_exceptions: bool = False):
        self.schedule = schedule if isinstance(schedule, list) else [schedule]
        self.name = name
        self.function = function
        self.last_run = None
        self.init_time = datetime.datetime.now()
        self.id = uuid4()
        self.slack_webhook = slack_webhook if isinstance(slack_webhook, list) else [slack_webhook]
        self.chime_webhook = chime_webhook if isinstance(chime_webhook, list) else [chime_webhook]
        self.metrics = {
            "errors": 0,
            "runs": 0
        }
        self.raise_exceptions = raise_exceptions

    def run(self):
        try:
            self.metrics["runs"] += 1
            self.function()
        except Exception as e:
            self.metrics["errors"] += 1
            if self.raise_exceptions:
                raise e
            else:
                return SoftError(self.name, self.id, str(e))
                            
    def add_schedule(self, schedule: str):
        self.schedule.append(schedule)

    def remove_schedule(self, schedule: str):
        self.schedule.remove(schedule)

    def get_next_run(self):
        runs = []
        if self.last_run is None:
            for schedule in self.schedule:
                cron = croniter(schedule, self.init_time)
                next_run = cron.get_next(datetime.datetime)
                runs.append(next_run)
        else:
            for schedule in self.schedule:
                cron = croniter(schedule, self.last_run)
                next_run = cron.get_next(datetime.datetime)
                runs.append(next_run)
        return min(runs)

    def is_due(self, set_last_run: bool = True):
        now = datetime.datetime.now()
        next_run = self.get_next_run()
        if set_last_run:
            self.set_last_run(now)
        return next_run <= now

    def set_last_run(self, last_run: datetime.datetime):
        self.last_run = last_run


