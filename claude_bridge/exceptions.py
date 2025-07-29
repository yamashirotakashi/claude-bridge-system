"""
Claude Bridge System - 例外クラス定義
統一されたエラーハンドリングのための例外クラス群
"""

from typing import Optional


class BridgeException(Exception):
    """Claude Bridge System基底例外クラス"""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class FileSystemError(BridgeException):
    """ファイルシステム関連エラー"""
    pass


class ProjectNotFoundError(BridgeException):
    """プロジェクトが見つからない場合のエラー"""
    pass


class ConfigurationError(BridgeException):
    """設定ファイル関連エラー"""
    pass


class ValidationError(BridgeException):
    """データ検証エラー"""
    pass


class TaskGenerationError(BridgeException):
    """タスク生成関連エラー"""
    pass


class PermissionError(BridgeException):
    """権限関連エラー"""
    pass