# システム設計書
## Claude Bridge System アーキテクチャ設計

### 1. システム概要

Claude Bridge Systemは、Claude DesktopとClaude Code間の情報連携を自動化し、統一されたプロジェクト管理環境を提供するシステムです。

### 2. アーキテクチャ概要

```
┌─────────────────┐    ┌─────────────────┐
│  Claude Desktop │    │   Claude Code   │
│                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Project     │ │    │ │ Project     │ │
│ │ Context     │ │    │ │ Execution   │ │
│ │ Loader      │ │    │ │ Engine      │ │
│ └─────────────┘ │    │ └─────────────┘ │
└─────────┬───────┘    └───────┬─────────┘
          │                    │
          └────────┬───────────┘
                   │
         ┌─────────▼─────────┐
         │  Claude Bridge    │
         │  File System      │
         │                   │
         │ ┌───────────────┐ │
         │ │ Projects      │ │
         │ │ Registry      │ │
         │ ├───────────────┤ │
         │ │ Task Queue    │ │
         │ ├───────────────┤ │
         │ │ Result Store  │ │
         │ └───────────────┘ │
         └───────────────────┘
```

### 3. コンポーネント設計

#### 3.1 Claude Desktop側コンポーネント

##### 3.1.1 Project Context Loader
**責務**: プロジェクト情報の検出・読み込み・整理

**主要機能**:
- ショートカット検出 (`[project_name]` パターン)
- Claude.mdファイル読み込み
- プロジェクト構造分析
- 関連プロジェクト情報収集

**インターフェース**:
```python
class ProjectContextLoader:
    def detect_project_shortcuts(message: str) -> List[str]
    def load_project_context(project_id: str) -> Dict
    def generate_context_summary(project_ids: List[str]) -> str
    def get_related_contexts(project_ids: List[str]) -> Dict
```

##### 3.1.2 Task Generator
**責務**: 設計情報から実装タスクの生成

**主要機能**:
- 会話内容の分析
- 実装タスクの抽出
- 構造化マークダウン形式での出力
- 優先度・依存関係の設定

**インターフェース**:
```python
class TaskGenerator:
    def analyze_conversation(content: str) -> TaskAnalysis
    def extract_implementation_tasks(analysis: TaskAnalysis) -> List[Task]
    def format_as_claude_task(task: Task) -> str
    def save_task_file(task: str, project_id: str) -> Path
```

#### 3.2 Claude Code側コンポーネント

##### 3.2.1 Task Monitor
**責務**: タスクファイルの監視・検出

**主要機能**:
- ファイルシステム監視
- 新規タスクの検出
- タスクファイルの解析
- 実行キューへの追加

**インターフェース**:
```python
class TaskMonitor:
    def start_monitoring(watch_dir: Path) -> None
    def on_task_created(task_file: Path) -> None
    def parse_task_file(task_file: Path) -> Task
    def queue_task(task: Task) -> None
```

##### 3.2.2 Execution Engine
**責務**: タスクの実行・結果収集

**主要機能**:
- タスク実行
- エラーハンドリング
- 実行ログ収集
- 結果フォーマット

**インターフェース**:
```python
class ExecutionEngine:
    def execute_task(task: Task) -> ExecutionResult
    def handle_errors(error: Exception, task: Task) -> ErrorReport
    def generate_result_report(result: ExecutionResult) -> str
    def save_result_file(report: str, task_id: str) -> Path
```

#### 3.3 共有コンポーネント

##### 3.3.1 Projects Registry
**責務**: プロジェクト情報の管理

**データ構造**:
```json
{
  "projects": {
    "project_id": {
      "shortcut": "[shortcut]",
      "name": "Project Name",
      "path": "/path/to/project",
      "claude_md": "/path/to/Claude.md",
      "tech_stack": ["Python", "FastAPI"],
      "dependencies": ["other_project"],
      "related_projects": ["related_project"],
      "integration_points": ["description"],
      "last_updated": "2025-07-29T12:00:00Z"
    }
  },
  "global_settings": {
    "auto_load_context": true,
    "max_context_size": 5000,
    "cache_duration": 3600
  }
}
```

##### 3.3.2 Bridge File System
**責務**: ツール間のファイルベース通信

**ディレクトリ構造**:
```
~/.claude_bridge/
├── config/
│   ├── projects.json          # プロジェクト設定
│   └── user_settings.json     # ユーザー設定
├── tasks/
│   ├── pending/               # 未実行タスク
│   ├── processing/            # 実行中タスク
│   └── completed/             # 完了タスク
├── results/
│   ├── success/               # 成功結果
│   └── errors/                # エラー結果
├── cache/
│   └── project_contexts/      # プロジェクト情報キャッシュ
└── logs/
    ├── desktop.log            # Desktop側ログ
    └── code.log               # Code側ログ
```

### 4. データフロー設計

#### 4.1 プロジェクト認識フロー
```
1. User Input: "[techzip]プロジェクトについて相談"
   ↓
2. ProjectContextLoader.detect_project_shortcuts()
   ↓
3. ProjectContextLoader.load_project_context("techzip")
   ↓
4. Claude.mdファイル読み込み + プロジェクト構造分析
   ↓
5. コンテキスト生成・会話への注入
```

#### 4.2 タスク実行フロー
```
1. Claude Desktop: タスク生成・ファイル保存
   ↓
2. TaskMonitor: 新規ファイル検出
   ↓
3. Task解析・実行キューへ追加
   ↓
4. ExecutionEngine: タスク実行
   ↓
5. 結果ファイル生成・保存
   ↓
6. Claude Desktop: 結果読み込み・フィードバック
```

### 5. インターフェース設計

#### 5.1 Task File Format
```markdown
## CLAUDE_TASK: [task_type]
### Project
project_id

### Context
Background information and requirements

### Task
Specific implementation instructions

### Files
- target/file/path.py
- another/file.py

### Code
```python
# Code snippets or examples
def example_function():
    pass
```

### Priority
high | medium | low

### Dependencies
- other_task_id

### Metadata
- created_at: 2025-07-29T12:00:00Z
- created_by: claude_desktop
- task_id: uuid4()
---
```

#### 5.2 Result File Format
```markdown
## CLAUDE_RESULT: [task_id]
### Status
success | error | partial

### Summary
Brief description of what was accomplished

### Changes
- Created: new_file.py
- Modified: existing_file.py
- Deleted: old_file.py

### Output
```
Console output or logs
```

### Code
```python
# Generated or modified code
```

### Issues
- Warning: potential issue description
- Error: error description with resolution

### Next Steps
- Suggested follow-up tasks
- Dependencies to resolve

### Metadata
- completed_at: 2025-07-29T12:30:00Z
- execution_time: 30.5s
- claude_code_version: 1.0.0
---
```

### 6. エラーハンドリング設計

#### 6.1 エラー分類
- **設定エラー**: プロジェクト設定ファイルの問題
- **ファイルアクセスエラー**: 権限・存在確認の問題
- **パース エラー**: タスクファイルの形式問題
- **実行エラー**: Claude Code側での実行失敗
- **通信エラー**: ファイルベース通信の問題

#### 6.2 リカバリ戦略
- **設定エラー**: デフォルト設定での継続 + 警告表示
- **ファイルアクセスエラー**: 代替パス試行 + ユーザー通知
- **パース エラー**: 部分解析 + エラー箇所の特定
- **実行エラー**: エラー詳細の収集 + 修正提案
- **通信エラー**: リトライ + 手動モードへのフォールバック

### 7. 拡張性設計

#### 7.1 プラグインアーキテクチャ
```python
class ProjectAnalyzer:
    def analyze_project(self, project_path: Path) -> AnalysisResult:
        pass

class CustomAnalyzer(ProjectAnalyzer):
    def analyze_project(self, project_path: Path) -> AnalysisResult:
        # カスタム分析ロジック
        pass
```

#### 7.2 設定拡張
```json
{
  "analyzers": [
    "builtin.python_analyzer",
    "custom.django_analyzer",
    "custom.fastapi_analyzer"
  ],
  "task_generators": [
    "builtin.markdown_generator",
    "custom.jira_generator"
  ]
}
```

### 8. セキュリティ設計

#### 8.1 アクセス制御
- プロジェクトパスの検証（ディレクトリトラバーサル防止）
- 実行可能ファイルの制限
- 機密ファイル（.env等）の除外

#### 8.2 データ保護
- 機密情報のマスキング
- ログレベルの調整
- 一時ファイルの自動削除

### 9. パフォーマンス設計

#### 9.1 キャッシュ戦略
- プロジェクト情報のメモリキャッシュ
- ファイル変更時のキャッシュ無効化
- LRU による自動リサイズ

#### 9.2 非同期処理
- ファイル監視の非同期実行
- 大きなプロジェクトの段階的読み込み
- バックグラウンドでの前処理

### 10. 運用設計

#### 10.1 ログ設計
```python
import logging

logger = logging.getLogger('claude_bridge')
logger.info(f"Project {project_id} context loaded successfully")
logger.warning(f"Claude.md not found for project {project_id}")
logger.error(f"Failed to execute task {task_id}: {error}")
```

#### 10.2 モニタリング
- タスク実行時間の追跡
- エラー率の監視
- ファイルサイズの監視
- メモリ使用量の追跡
