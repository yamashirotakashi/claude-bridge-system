"""
Claude Bridge System - MVP実装
Claude DesktopとClaude Codeの有機的連携システム

Version: 1.0.0
Author: Claude Bridge Development Team
"""

__version__ = "1.0.0"
__author__ = "Claude Bridge Development Team"

from .core.bridge_filesystem import BridgeFileSystem
from .core.project_registry import ProjectRegistry
from .core.project_context_loader import ProjectContextLoader
from .core.task_generator import TaskGenerator
from .desktop_api.desktop_connector import DesktopConnector
from .desktop_api.sync_engine import SyncEngine
from .desktop_api.bridge_protocol import BridgeProtocol, MessageType, BridgeMessage

__all__ = [
    "BridgeFileSystem",
    "ProjectRegistry",
    "ProjectContextLoader", 
    "TaskGenerator",
    "DesktopConnector",
    "SyncEngine", 
    "BridgeProtocol",
    "MessageType",
    "BridgeMessage"
]