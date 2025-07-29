# データベース設計書
## Claude Bridge System データ構造設計

### 1. 概要

Claude Bridge Systemは主にファイルベースのデータ管理を採用していますが、構造化されたデータ形式を使用します。この文書では、JSON形式での設定ファイル、キャッシュデータ、ログデータの設計を定義します。

### 2. 主要データストア

#### 2.1 Projects Registry (projects.json)

**ファイルパス**: `~/.claude_bridge/config/projects.json`

**データ構造**:
```json
{
  "version": "1.0.0",
  "last_updated": "2025-07-29T12:00:00Z",
  "projects": {
    "tech": {
      "shortcut": "[tech]",
      "name": "メインテックプロジェクト",
      "path": "~/projects/tech",
      "claude_md": "~/projects/tech/Claude.md",
      "description": "メインのテクノロジープロジェクト",
      "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
      "dependencies": ["common-lib"],
      "related_projects": ["techzip"],
      "integration_points": [
        "共通認証システム",
        "データベース共有",
        "API エンドポイント統合"
      ],
      "metadata": {
        "created_at": "2025-07-01T00:00:00Z",
        "last_updated": "2025-07-29T12:00:00Z",
        "last_accessed": "2025-07-29T11:45:00Z",
        "access_count": 15,
        "auto_load_context": true,
        "max_context_size": 5000
      }
    }
  },
  "global_settings": {
    "auto_load_context": true,
    "max_context_size": 5000,
    "cache_duration": 3600,
    "default_analysis_depth": "detailed",
    "task_timeout": 300,
    "cleanup_days": 7,
    "log_level": "INFO"
  }
}
```

**スキーマ定義**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "version": {"type": "string"},
    "last_updated": {"type": "string", "format": "date-time"},
    "projects": {
      "type": "object",
      "patternProperties": {
        "^[a-zA-Z0-9_-]+$": {
          "type": "object",
          "properties": {
            "shortcut": {"type": "string", "pattern": "^\\[[a-zA-Z0-9_-]+\\]$"},
            "name": {"type": "string", "minLength": 1},
            "path": {"type": "string"},
            "claude_md": {"type": "string"},
            "description": {"type": "string"},
            "tech_stack": {
              "type": "array",
              "items": {"type": "string"}
            },
            "dependencies": {
              "type": "array",
              "items": {"type": "string"}
            },
            "related_projects": {
              "type": "array",
              "items": {"type": "string"}
            },
            "integration_points": {
              "type": "array",
              "items": {"type": "string"}
            },
            "metadata": {
              "type": "object",
              "properties": {
                "created_at": {"type": "string", "format": "date-time"},
                "last_updated": {"type": "string", "format": "date-time"},
                "last_accessed": {"type": "string", "format": "date-time"},
                "access_count": {"type": "integer", "minimum": 0},
                "auto_load_context": {"type": "boolean"},
                "max_context_size": {"type": "integer", "minimum": 1000}
              }
            }
          },
          "required": ["shortcut", "name", "path"]
        }
      }
    },
    "global_settings": {
      "type": "object",
      "properties": {
        "auto_load_context": {"type": "boolean"},
        "max_context_size": {"type": "integer", "minimum": 1000},
        "cache_duration": {"type": "integer", "minimum": 60},
        "default_analysis_depth": {"enum": ["basic", "detailed", "comprehensive"]},
        "task_timeout": {"type": "integer", "minimum": 30},
        "cleanup_days": {"type": "integer", "minimum": 1},
        "log_level": {"enum": ["DEBUG", "INFO", "WARNING", "ERROR"]}
      }
    }
  },
  "required": ["version", "projects", "global_settings"]
}
```

#### 2.2 User Settings (user_settings.json)

**ファイルパス**: `~/.claude_bridge/config/user_settings.json`

**データ構造**:
```json
{
  "user": {
    "name": "Developer Name",
    "email": "developer@example.com",
    "timezone": "Asia/Tokyo",
    "preferences": {
      "default_task_priority": "medium",
      "auto_execute_tasks": false,
      "notification_enabled": true,
      "theme": "dark",
      "language": "ja"
    }
  },
  "claude_desktop": {
    "integration_enabled": true,
    "auto_context_injection": true,
    "max_projects_per_context": 3,
    "context_format": "detailed"
  },
  "claude_code": {
    "integration_enabled": true,
    "auto_task_execution": false,
    "result_notification": true,
    "backup_before_execution": true
  },
  "paths": {
    "projects_root": "~/projects",
    "backup_directory": "~/backups/claude_bridge",
    "temp_directory": "/tmp/claude_bridge"
  },
  "security": {
    "allowed_file_extensions": [".py", ".md", ".txt", ".json", ".yaml", ".yml"],
    "forbidden_directories": ["/etc", "/usr", "/system"],
    "max_file_size_mb": 10
  }
}
```

#### 2.3 Cache Data Structure

**キャッシュディレクトリ**: `~/.claude_bridge/cache/`

##### 2.3.1 Project Context Cache
**ファイル形式**: `project_contexts/{project_id}.json`

```json
{
  "project_id": "tech",
  "cached_at": "2025-07-29T12:00:00Z",
  "expires_at": "2025-07-29T13:00:00Z",
  "data": {
    "basic_info": {
      "shortcut": "[tech]",
      "name": "メインテックプロジェクト",
      "description": "...",
      "tech_stack": ["Python", "FastAPI"]
    },
    "claude_md_content": "# Tech Project\\n\\nThis is...",
    "claude_md_summary": "プロジェクトの概要: ...",
    "project_structure": {
      "total_files": 45,
      "python_files": 32,
      "directories": ["src", "tests", "docs"],
      "main_files": ["README.md", "requirements.txt"],
      "entry_points": ["main.py", "app.py"]
    },
    "related_projects": {
      "techzip": {
        "name": "ZIP処理ライブラリ",
        "relationship": "dependency",
        "integration_points": ["file processing module"]
      }
    }
  },
  "metadata": {
    "load_time_ms": 250,
    "file_sizes": {
      "claude_md": 1500,
      "total_project": 2500000
    },
    "last_modified": {
      "claude_md": "2025-07-28T15:30:00Z",
      "project_root": "2025-07-29T10:20:00Z"
    }
  }
}
```

##### 2.3.2 Analysis Cache
**ファイル形式**: `analysis/{analysis_id}.json`

```json
{
  "analysis_id": "uuid4-string",
  "created_at": "2025-07-29T12:00:00Z",
  "input": {
    "message": "[tech]プロジェクトと[techzip]プロジェクトの連携について",
    "projects": ["tech", "techzip"],
    "context_size": 5000
  },
  "result": {
    "task_type": "analyze",
    "complexity": "medium",
    "estimated_effort_minutes": 30,
    "key_requirements": [
      "プロジェクト間の依存関係分析",
      "統合ポイントの特定",
      "実装方針の策定"
    ],
    "suggested_approach": "段階的統合アプローチを推奨",
    "potential_issues": [
      "依存関係の循環参照の可能性",
      "APIバージョンの不整合"
    ]
  }
}
```

### 3. Task Management Data

#### 3.1 Task Queue Structure

**ディレクトリ**: `~/.claude_bridge/tasks/`

##### 3.1.1 Task File Format
**ファイル名**: `{project_id}_{timestamp}_{task_id}.md`

```markdown
## CLAUDE_TASK: implement
### Project
tech

### Context
新しい認証システムを実装する必要がある。
現在のシステムは基本的なパスワード認証のみで、
MFA（多要素認証）を追加したい。

### Task
1. MFA対応の認証クラスを実装
2. TOTP（Time-based One-Time Password）のサポート
3. 既存のログイン処理を拡張

### Files
- src/auth/mfa.py (新規作成)
- src/auth/login.py (修正)
- tests/test_mfa.py (新規作成)

### Code
```python
class MFAAuthenticator:
    def __init__(self, secret_key):
        self.secret_key = secret_key
    
    def generate_qr_code(self, user_email):
        # QRコード生成ロジック
        pass
    
    def verify_totp(self, token):
        # TOTP検証ロジック
        pass
```

### Priority
high

### Dependencies
- auth-base-update

### Metadata
created_at: 2025-07-29T12:00:00Z
created_by: claude_desktop
task_id: 550e8400-e29b-41d4-a716-446655440000
estimated_time: 45
complexity: medium
---
```

##### 3.1.2 Task Metadata (JSON)
**ファイル名**: `{task_id}.meta.json`

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_id": "tech",
  "status": "pending",
  "created_at": "2025-07-29T12:00:00Z",
  "updated_at": "2025-07-29T12:00:00Z",
  "created_by": "claude_desktop",
  "assigned_to": "claude_code",
  "priority": "high",
  "task_type": "implement",
  "estimated_time_minutes": 45,
  "complexity": "medium",
  "dependencies": ["auth-base-update"],
  "tags": ["authentication", "security", "mfa"],
  "file_references": [
    "src/auth/mfa.py",
    "src/auth/login.py",
    "tests/test_mfa.py"
  ],
  "status_history": [
    {
      "status": "pending",
      "timestamp": "2025-07-29T12:00:00Z",
      "note": "Task created"
    }
  ]
}
```

#### 3.2 Result Data Structure

##### 3.2.1 Result File Format
**ファイル名**: `{task_id}_result.md`

```markdown
## CLAUDE_RESULT: 550e8400-e29b-41d4-a716-446655440000
### Status
success

### Summary
MFA認証システムの実装が完了しました。
TOTP対応の認証クラスと既存ログイン処理の拡張を行いました。

### Changes
- Created: src/auth/mfa.py (180 lines)
- Modified: src/auth/login.py (added MFA integration, 45 lines)
- Created: tests/test_mfa.py (120 lines)
- Modified: requirements.txt (added pyotp dependency)

### Output
```
Tests passed: 15/15
Coverage: 95%
Linting: No issues found
Type checking: Passed
```

### Code
```python
# Generated MFAAuthenticator class
class MFAAuthenticator:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.totp = pyotp.TOTP(secret_key)
    
    def generate_qr_code(self, user_email: str) -> str:
        provisioning_uri = self.totp.provisioning_uri(
            name=user_email,
            issuer_name="TechApp"
        )
        return qrcode.make(provisioning_uri)
```

### Issues
- Warning: Consider implementing rate limiting for TOTP verification
- Info: Added dependency on pyotp library

### Next Steps
- Integration testing with existing auth system
- User interface for QR code display
- Backup codes implementation

### Metadata
completed_at: 2025-07-29T12:45:00Z
execution_time: 42.3
claude_code_version: 1.0.0
test_results: 15/15 passed
coverage_percent: 95
---
```

##### 3.2.2 Result Metadata (JSON)
**ファイル名**: `{task_id}_result.meta.json`

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "result_id": "uuid4-result-string",
  "status": "success",
  "completed_at": "2025-07-29T12:45:00Z",
  "execution_time_seconds": 42.3,
  "claude_code_version": "1.0.0",
  "summary": "MFA認証システムの実装が完了",
  "changes": {
    "files_created": [
      {
        "path": "src/auth/mfa.py",
        "lines": 180,
        "size_bytes": 5420
      },
      {
        "path": "tests/test_mfa.py", 
        "lines": 120,
        "size_bytes": 3200
      }
    ],
    "files_modified": [
      {
        "path": "src/auth/login.py",
        "lines_added": 45,
        "lines_removed": 5
      }
    ],
    "files_deleted": []
  },
  "test_results": {
    "total_tests": 15,
    "passed": 15,
    "failed": 0,
    "coverage_percent": 95.0,
    "execution_time": 2.8
  },
  "issues": [
    {
      "type": "warning",
      "message": "Consider implementing rate limiting for TOTP verification",
      "file": "src/auth/mfa.py",
      "line": 45
    }
  ],
  "next_steps": [
    "Integration testing with existing auth system",
    "User interface for QR code display",
    "Backup codes implementation"
  ]
}
```

### 4. Logging Data Structure

#### 4.1 Application Logs
**ファイル**: `~/.claude_bridge/logs/claude_bridge.log`

**フォーマット**: JSON Lines format

```json
{"timestamp": "2025-07-29T12:00:00.123Z", "level": "INFO", "component": "ProjectContextLoader", "action": "load_project_context", "project_id": "tech", "duration_ms": 250, "message": "Project context loaded successfully"}
{"timestamp": "2025-07-29T12:00:05.456Z", "level": "WARNING", "component": "ProjectContextLoader", "action": "load_claude_md", "project_id": "tech", "file_path": "~/projects/tech/Claude.md", "message": "Claude.md file not found, using default context"}
{"timestamp": "2025-07-29T12:01:00.789Z", "level": "ERROR", "component": "TaskGenerator", "action": "save_task_file", "error": "Permission denied", "file_path": "/restricted/path", "message": "Failed to save task file"}
```

#### 4.2 Performance Logs
**ファイル**: `~/.claude_bridge/logs/performance.log`

```json
{"timestamp": "2025-07-29T12:00:00Z", "metric": "project_context_load_time", "project_id": "tech", "value_ms": 250, "cache_hit": false}
{"timestamp": "2025-07-29T12:00:05Z", "metric": "shortcut_detection_time", "message_length": 45, "shortcuts_found": 2, "value_ms": 15}
{"timestamp": "2025-07-29T12:01:00Z", "metric": "task_execution_time", "task_id": "550e8400-e29b-41d4-a716-446655440000", "value_seconds": 42.3, "success": true}
```

### 5. Data Relationships

#### 5.1 Entity Relationship Diagram

```
Projects Registry
├── Projects (1:N)
│   ├── Project Contexts (1:1)
│   ├── Tasks (1:N)
│   └── Results (1:N via Tasks)
├── Global Settings (1:1)
└── User Settings (1:1)

Tasks
├── Task Metadata (1:1)
├── Results (1:1)
└── Dependencies (N:N with other Tasks)

Cache
├── Project Context Cache (N:1 with Projects)
└── Analysis Cache (independent)

Logs
├── Application Logs (references all entities)
└── Performance Logs (references all entities)
```

#### 5.2 データの整合性ルール

1. **Project ID Uniqueness**: プロジェクトIDは全体で一意
2. **Shortcut Uniqueness**: ショートカットは全体で一意
3. **File Path Validation**: 全てのファイルパスは存在確認が必要
4. **Task Dependencies**: 循環依存の禁止
5. **Cache Expiration**: キャッシュは必ず有効期限を持つ
6. **Log Rotation**: ログファイルは自動ローテーション

### 6. データマイグレーション

#### 6.1 バージョン管理

各データファイルには `version` フィールドを含め、必要に応じてマイグレーションを実行：

```python
MIGRATION_HANDLERS = {
    "1.0.0": migrate_from_legacy,
    "1.1.0": migrate_to_enhanced_metadata,
    "2.0.0": migrate_to_new_schema
}

def migrate_data(current_version: str, target_version: str):
    """データマイグレーションの実行"""
    pass
```

#### 6.2 バックアップ戦略

- 設定変更前の自動バックアップ
- 日次バックアップのローテーション
- 重要なタスク実行前のスナップショット

### 7. パフォーマンス最適化

#### 7.1 インデックス戦略

```json
{
  "indexes": {
    "projects_by_shortcut": {
      "type": "hash_map",
      "field": "shortcut",
      "unique": true
    },
    "tasks_by_status": {
      "type": "btree", 
      "field": "status",
      "unique": false
    },
    "results_by_completion_time": {
      "type": "btree",
      "field": "completed_at",
      "unique": false
    }
  }
}
```

#### 7.2 キャッシュ戦略

- **Project Context**: 1時間キャッシュ
- **Analysis Results**: 30分キャッシュ
- **File Metadata**: ファイル更新まで永続
- **LRU Policy**: 最大100エントリ

これらのデータ構造により、効率的で拡張可能なClaude Bridge Systemを実現します。
