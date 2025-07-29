# API設計書
## Claude Bridge System API仕様

### 1. 概要

Claude Bridge SystemのAPI設計書です。主にPythonクラス・メソッドのインターフェース定義を含みます。

### 2. Core APIs

#### 2.1 ProjectContextLoader API

```python
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

class ProjectContextLoader:
    """プロジェクトコンテキストの検出・読み込みを担当するメインクラス"""
    
    def __init__(self, config_path: str = "~/.claude_bridge/config/projects.json"):
        """
        Args:
            config_path: プロジェクト設定ファイルのパス
        """
        pass
    
    def detect_project_shortcuts(self, message: str) -> List[str]:
        """
        メッセージからプロジェクトショートカットを検出
        
        Args:
            message: ユーザーからの入力メッセージ
            
        Returns:
            検出されたプロジェクトIDのリスト
            
        Example:
            >>> loader.detect_project_shortcuts("[tech]と[techzip]の連携")
            ['tech', 'techzip']
        """
        pass
    
    def load_project_context(self, project_id: str) -> Dict:
        """
        指定されたプロジェクトの詳細コンテキストを読み込み
        
        Args:
            project_id: プロジェクトID
            
        Returns:
            プロジェクトコンテキスト辞書
            {
                "basic_info": {...},
                "claude_md_content": "...",
                "project_structure": {...},
                "related_projects": {...}
            }
            
        Raises:
            ProjectNotFoundError: プロジェクトが見つからない場合
            FileAccessError: ファイルアクセスに失敗した場合
        """
        pass
    
    def generate_context_summary(self, project_ids: List[str]) -> str:
        """
        複数プロジェクトの統合コンテキストサマリを生成
        
        Args:
            project_ids: プロジェクトIDのリスト
            
        Returns:
            マークダウン形式のコンテキストサマリ
        """
        pass
    
    def get_related_contexts(self, project_ids: List[str]) -> Dict:
        """
        関連プロジェクトの情報を取得
        
        Args:
            project_ids: ベースプロジェクトIDのリスト
            
        Returns:
            関連プロジェクトの情報辞書
        """
        pass
    
    def refresh_cache(self, project_id: Optional[str] = None) -> None:
        """
        キャッシュを更新
        
        Args:
            project_id: 特定プロジェクトのみ更新する場合のID（Noneで全更新）
        """
        pass
```

#### 2.2 TaskGenerator API

```python
from enum import Enum
from dataclasses import dataclass

class TaskType(Enum):
    IMPLEMENT = "implement"
    ANALYZE = "analyze"
    TEST = "test"
    REFACTOR = "refactor"
    DOCUMENT = "document"

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class Task:
    task_id: str
    task_type: TaskType
    project_id: str
    title: str
    description: str
    target_files: List[str]
    code_snippets: List[str]
    priority: Priority
    dependencies: List[str]
    metadata: Dict

class TaskGenerator:
    """設計情報から実装タスクを生成するクラス"""
    
    def analyze_conversation(self, content: str, project_context: Dict) -> 'TaskAnalysis':
        """
        会話内容を分析してタスクの抽出準備
        
        Args:
            content: 会話内容
            project_context: プロジェクトコンテキスト
            
        Returns:
            TaskAnalysis: 分析結果
        """
        pass
    
    def extract_implementation_tasks(self, analysis: 'TaskAnalysis') -> List[Task]:
        """
        分析結果から実装タスクを抽出
        
        Args:
            analysis: 会話分析結果
            
        Returns:
            抽出されたタスクのリスト
        """
        pass
    
    def format_as_claude_task(self, task: Task) -> str:
        """
        タスクをClaude Code用マークダウン形式に変換
        
        Args:
            task: タスクオブジェクト
            
        Returns:
            マークダウン形式のタスク文字列
        """
        pass
    
    def save_task_file(self, task_content: str, project_id: str) -> Path:
        """
        タスクファイルを保存
        
        Args:
            task_content: タスクのマークダウン内容
            project_id: プロジェクトID
            
        Returns:
            保存されたファイルのパス
        """
        pass
```

#### 2.3 BridgeFileSystem API

```python
class BridgeFileSystem:
    """Claude Bridge のファイルシステム管理クラス"""
    
    def __init__(self, bridge_root: str = "~/.claude_bridge"):
        """
        Args:
            bridge_root: Bridge システムのルートディレクトリ
        """
        pass
    
    def initialize_structure(self) -> None:
        """
        必要なディレクトリ構造を初期化
        
        Creates:
            ~/.claude_bridge/
            ├── config/
            ├── tasks/pending/
            ├── tasks/processing/
            ├── tasks/completed/
            ├── results/success/
            ├── results/errors/
            ├── cache/
            └── logs/
        """
        pass
    
    def get_task_queue_path(self, status: str = "pending") -> Path:
        """
        タスクキューのパスを取得
        
        Args:
            status: "pending", "processing", "completed"
            
        Returns:
            タスクキューディレクトリのパス
        """
        pass
    
    def get_result_path(self, result_type: str = "success") -> Path:
        """
        結果ファイルのパスを取得
        
        Args:
            result_type: "success", "errors"
            
        Returns:
            結果ディレクトリのパス
        """
        pass
    
    def cleanup_old_files(self, days: int = 7) -> None:
        """
        古いファイルをクリーンアップ
        
        Args:
            days: 保持日数
        """
        pass
```

### 3. Configuration APIs

#### 3.1 ProjectRegistry API

```python
@dataclass
class ProjectConfig:
    project_id: str
    shortcut: str
    name: str
    path: str
    claude_md: str
    description: str
    tech_stack: List[str]
    dependencies: List[str]
    related_projects: List[str]
    integration_points: List[str]
    last_updated: datetime

class ProjectRegistry:
    """プロジェクト設定の管理クラス"""
    
    def load_config(self, config_path: str) -> Dict:
        """設定ファイルを読み込み"""
        pass
    
    def save_config(self, config: Dict, config_path: str) -> None:
        """設定ファイルを保存"""
        pass
    
    def add_project(self, project_config: ProjectConfig) -> None:
        """新しいプロジェクトを追加"""
        pass
    
    def update_project(self, project_id: str, updates: Dict) -> None:
        """プロジェクト設定を更新"""
        pass
    
    def remove_project(self, project_id: str) -> None:
        """プロジェクトを削除"""
        pass
    
    def get_project(self, project_id: str) -> Optional[ProjectConfig]:
        """プロジェクト設定を取得"""
        pass
    
    def list_projects(self) -> List[ProjectConfig]:
        """全プロジェクトのリストを取得"""
        pass
    
    def validate_config(self, config: Dict) -> List[str]:
        """
        設定の妥当性をチェック
        
        Returns:
            エラーメッセージのリスト（空の場合は妥当）
        """
        pass
```

### 4. Monitoring APIs

#### 4.1 TaskMonitor API

```python
from watchdog.events import FileSystemEventHandler

class TaskMonitor(FileSystemEventHandler):
    """タスクファイルの監視クラス"""
    
    def __init__(self, watch_dir: Path, callback: callable):
        """
        Args:
            watch_dir: 監視対象ディレクトリ
            callback: ファイル検出時のコールバック関数
        """
        pass
    
    def start_monitoring(self) -> None:
        """監視を開始"""
        pass
    
    def stop_monitoring(self) -> None:
        """監視を停止"""
        pass
    
    def on_created(self, event) -> None:
        """ファイル作成イベントのハンドラ"""
        pass
    
    def parse_task_file(self, task_file: Path) -> Task:
        """
        タスクファイルを解析
        
        Args:
            task_file: タスクファイルのパス
            
        Returns:
            解析されたTaskオブジェクト
            
        Raises:
            TaskParseError: 解析に失敗した場合
        """
        pass
    
    def validate_task_format(self, content: str) -> bool:
        """
        タスクファイルの形式を検証
        
        Args:
            content: ファイル内容
            
        Returns:
            形式が正しい場合True
        """
        pass
```

### 5. Execution APIs (Claude Code側)

#### 5.1 ExecutionEngine API

```python
@dataclass
class ExecutionResult:
    task_id: str
    status: str  # "success", "error", "partial"
    summary: str
    changes: List[str]
    output: str
    issues: List[str]
    next_steps: List[str]
    execution_time: float
    metadata: Dict

class ExecutionEngine:
    """タスク実行エンジン"""
    
    def execute_task(self, task: Task) -> ExecutionResult:
        """
        タスクを実行
        
        Args:
            task: 実行するタスク
            
        Returns:
            実行結果
        """
        pass
    
    def handle_errors(self, error: Exception, task: Task) -> 'ErrorReport':
        """
        エラーハンドリング
        
        Args:
            error: 発生した例外
            task: 実行中のタスク
            
        Returns:
            エラーレポート
        """
        pass
    
    def generate_result_report(self, result: ExecutionResult) -> str:
        """
        実行結果をマークダウン形式でフォーマット
        
        Args:
            result: 実行結果
            
        Returns:
            マークダウン形式のレポート
        """
        pass
    
    def save_result_file(self, report: str, task_id: str) -> Path:
        """
        結果ファイルを保存
        
        Args:
            report: 結果レポート
            task_id: タスクID
            
        Returns:
            保存されたファイルのパス
        """
        pass
```

### 6. Utility APIs

#### 6.1 Logger API

```python
import logging
from typing import Union

class BridgeLogger:
    """Claude Bridge専用ロガー"""
    
    def __init__(self, name: str, log_file: str = None):
        """
        Args:
            name: ロガー名
            log_file: ログファイルパス（Noneの場合はコンソールのみ）
        """
        pass
    
    def info(self, message: str, extra: Dict = None) -> None:
        """情報ログ"""
        pass
    
    def warning(self, message: str, extra: Dict = None) -> None:
        """警告ログ"""
        pass
    
    def error(self, message: str, extra: Dict = None) -> None:
        """エラーログ"""
        pass
    
    def debug(self, message: str, extra: Dict = None) -> None:
        """デバッグログ"""
        pass
    
    def log_task_execution(self, task: Task, result: ExecutionResult) -> None:
        """タスク実行のログ"""
        pass
    
    def log_project_context_load(self, project_id: str, load_time: float) -> None:
        """プロジェクトコンテキスト読み込みのログ"""
        pass
```

#### 6.2 Cache API

```python
from typing import Any
import time

class ProjectCache:
    """プロジェクト情報のキャッシュ管理"""
    
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        """
        Args:
            max_size: 最大キャッシュサイズ
            ttl: Time To Live (秒)
        """
        pass
    
    def get(self, key: str) -> Any:
        """
        キャッシュから値を取得
        
        Args:
            key: キャッシュキー
            
        Returns:
            キャッシュされた値（期限切れまたは存在しない場合はNone）
        """
        pass
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """
        キャッシュに値を設定
        
        Args:
            key: キャッシュキー
            value: キャッシュする値
            ttl: 個別のTTL設定（Noneの場合はデフォルト使用）
        """
        pass
    
    def delete(self, key: str) -> None:
        """キャッシュから値を削除"""
        pass
    
    def clear(self) -> None:
        """全キャッシュをクリア"""
        pass
    
    def cleanup_expired(self) -> None:
        """期限切れのキャッシュを削除"""
        pass
```

### 7. Exception Classes

```python
class ClaudeBridgeError(Exception):
    """Claude Bridge システムの基底例外クラス"""
    pass

class ProjectNotFoundError(ClaudeBridgeError):
    """プロジェクトが見つからない場合の例外"""
    pass

class FileAccessError(ClaudeBridgeError):
    """ファイルアクセスに失敗した場合の例外"""
    pass

class TaskParseError(ClaudeBridgeError):
    """タスクファイルの解析に失敗した場合の例外"""
    pass

class ConfigurationError(ClaudeBridgeError):
    """設定に問題がある場合の例外"""
    pass

class ExecutionError(ClaudeBridgeError):
    """タスク実行に失敗した場合の例外"""
    pass
```

### 8. Data Models

```python
from typing import Optional
from datetime import datetime
from enum import Enum

@dataclass
class ProjectInfo:
    """プロジェクト基本情報"""
    project_id: str
    name: str
    shortcut: str
    description: str
    path: str
    claude_md_path: str
    tech_stack: List[str]
    last_updated: datetime

@dataclass
class ProjectContext:
    """プロジェクトの完全なコンテキスト"""
    info: ProjectInfo
    claude_md_content: str
    structure: Dict
    related_projects: List[ProjectInfo]
    integration_points: List[str]
    loaded_at: datetime

@dataclass
class TaskAnalysis:
    """会話分析の結果"""
    mentioned_projects: List[str]
    task_type: TaskType
    complexity: str  # "simple", "medium", "complex"
    estimated_effort: int  # minutes
    key_requirements: List[str]
    suggested_approach: str
```

### 9. Constants

```python
# ファイル形式定義
TASK_FILE_HEADER = "## CLAUDE_TASK:"
RESULT_FILE_HEADER = "## CLAUDE_RESULT:"

# ディレクトリ名
DIR_TASKS_PENDING = "tasks/pending"
DIR_TASKS_PROCESSING = "tasks/processing"
DIR_TASKS_COMPLETED = "tasks/completed"
DIR_RESULTS_SUCCESS = "results/success"
DIR_RESULTS_ERRORS = "results/errors"
DIR_CACHE = "cache"
DIR_LOGS = "logs"

# 設定デフォルト値
DEFAULT_CACHE_TTL = 3600  # 1 hour
DEFAULT_MAX_CACHE_SIZE = 100
DEFAULT_TASK_TIMEOUT = 300  # 5 minutes
DEFAULT_FILE_CLEANUP_DAYS = 7

# 正規表現パターン
PROJECT_SHORTCUT_PATTERN = r'\[(\w+)\]'
TASK_ID_PATTERN = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
```

### 10. API使用例

```python
# 基本的な使用例
from claude_bridge import ProjectContextLoader, TaskGenerator

# プロジェクトコンテキストの読み込み
loader = ProjectContextLoader()
message = "[tech]プロジェクトと[techzip]プロジェクトの連携について"

# ショートカット検出
projects = loader.detect_project_shortcuts(message)
print(projects)  # ['tech', 'techzip']

# コンテキスト生成
context = loader.generate_context_summary(projects)
print(context)  # マークダウン形式のコンテキスト

# タスク生成
generator = TaskGenerator()
analysis = generator.analyze_conversation(message, context)
tasks = generator.extract_implementation_tasks(analysis)

for task in tasks:
    task_md = generator.format_as_claude_task(task)
    file_path = generator.save_task_file(task_md, task.project_id)
    print(f"Task saved to: {file_path}")
```
