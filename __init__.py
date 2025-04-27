"""
Botman - A Python framework for building and managing autonomous bots.

This package provides tools for creating, running, and monitoring bots.
"""

from .src.events import GLOBAL_EVENT_MANAGER, BotEvent, EventManager, SlackEventReceiver, ChimeEventReceiver, EventType
from .src.botman import Botman
from .src.bot import Bot 

__all__ = ["GLOBAL_EVENT_MANAGER", "BotEvent", "EventManager", "SlackEventReceiver", "ChimeEventReceiver", "EventType", "Botman", "Bot"]
