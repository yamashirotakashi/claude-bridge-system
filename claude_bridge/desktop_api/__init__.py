"""
Claude Bridge System - Desktop API Interface
Claude Desktopとの連携API
"""

from .desktop_connector import DesktopConnector
from .sync_engine import SyncEngine
from .bridge_protocol import BridgeProtocol, MessageType, BridgeMessage

__all__ = [
    "DesktopConnector",
    "SyncEngine", 
    "BridgeProtocol",
    "MessageType",
    "BridgeMessage"
]

__version__ = "1.0.0"