"""
Flyin: A drone routing and simulation engine.

This package contains the core logic for parsing maps, planning multi-agent
drone routes, and managing simulation assets.
"""

__version__ = "0.1.0"

from .units import Hub, Connection, Drone, ZoneType
from .parser import MapParser
from .algorithm import DronePlanner
from .map_manager import MapFolderManager

__all__ = [
    "Hub",
    "Connection",
    "Drone",
    "ZoneType",
    "MapParser",
    "DronePlanner",
    "MapFolderManager",
]
