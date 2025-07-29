"""
Claude Bridge System - Core Module
システムのコア機能を提供するモジュール
"""

from .bridge_filesystem import BridgeFileSystem
from .project_registry import ProjectRegistry
from .project_context_loader import ProjectContextLoader

__all__ = [
    "BridgeFileSystem",
    "ProjectRegistry",
    "ProjectContextLoader"
]