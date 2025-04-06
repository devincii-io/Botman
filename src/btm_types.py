from enum import Enum
from dataclasses import dataclass, field
import datetime

class BotState(Enum):
    RUNNING = "running"
    IDLE = "idle"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class BotMetrics:
    runs: int
    errors: int
    last_run: datetime.datetime
    since: datetime.datetime = field(default_factory=datetime.datetime.now)
    state: BotState = field(default=BotState.IDLE)

