from typing import Callable
import datetime

class Bot:
    def __init__(self, name: str, schedule: Callable, function: Callable):
        self.name = name
        self.schedule = schedule
        self.function = function

    def run(self):
        self.function()