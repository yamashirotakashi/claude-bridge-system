d to read previous checksums: {e}")
        
        # 新しいチェックサムを保存
        try:
            with open(checksums_file, 'w') as f:
                json.dump(current_checksums, f, indent=2)
        except Exception as e:
            self.security_logger.error(f"Failed to save checksums: {e}")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "changes": changes,
            "files_verified": len(current_checksums)
        }
```

#### 4.2 アクセス制御
```python
# security/access_control.py
import os
import stat
from pathlib import Path
from typing import List

class AccessController:
    def __init__(self):
        self.allowed_extensions = {'.py', '.md', '.txt', '.json', '.yaml', '.yml'}
        self.forbidden_dirs = {'/etc', '/usr', '/system', '/windows'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
    
    def validate_file_path(self, file_path: str) -> bool:
        """ファイルパスの妥当性検証"""
        path = Path(file_path).resolve()
        
        # 禁止ディレクトリのチェック
        for forbidden_dir in self.forbidden_dirs:
            if str(path).lower().startswith(forbidden_dir.lower()):
                raise SecurityError(f"Access to forbidden directory: {forbidden_dir}")
        
        # ディレクトリトラバーサルのチェック
        if '..' in str(path):
            raise SecurityError("Directory traversal attempt detected")
        
        # 拡張子のチェック
        if path.suffix and path.suffix not in self.allowed_extensions:
            raise SecurityError(f"File extension not allowed: {path.suffix}")
        
        return True
    
    def validate_file_size(self, file_path: Path) -> bool:
        """ファイルサイズの検証"""
        if file_path.exists() and file_path.stat().st_size > self.max_file_size:
            raise SecurityError(f"File too large: {file_path}")
        return True
    
    def set_secure_permissions(self, file_path: Path):
        """セキュアなファイル権限の設定"""
        if file_path.exists():
            # ファイルはオーナーのみ読み書き可能
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)

class SecurityError(Exception):
    """セキュリティ関連のエラー"""
    pass
```

### 5. パフォーマンス最適化

#### 5.1 キャッシュ管理
```python
# performance/cache_manager.py
import json
import time
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timedelta

class CacheManager:
    def __init__(self, cache_dir=None, default_ttl=3600):
        self.cache_dir = Path(cache_dir or Path.home() / ".claude_bridge" / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self.memory_cache = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """キャッシュから値を取得"""
        # メモリキャッシュを先にチェック
        cache_key = f"{namespace}:{key}"
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if entry["expires_at"] > time.time():
                self.cache_stats["hits"] += 1
                return entry["data"]
            else:
                del self.memory_cache[cache_key]
        
        # ディスクキャッシュをチェック
        cache_file = self.cache_dir / namespace / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    entry = json.load(f)
                
                if entry["expires_at"] > time.time():
                    # メモリキャッシュにも保存
                    self.memory_cache[cache_key] = entry
                    self.cache_stats["hits"] += 1
                    return entry["data"]
                else:
                    cache_file.unlink()  # 期限切れファイルを削除
            except Exception:
                pass
        
        self.cache_stats["misses"] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = "default"):
        """キャッシュに値を設定"""
        if ttl is None:
            ttl = self.default_ttl
        
        expires_at = time.time() + ttl
        entry = {
            "data": value,
            "created_at": time.time(),
            "expires_at": expires_at,
            "ttl": ttl
        }
        
        # メモリキャッシュに保存
        cache_key = f"{namespace}:{key}"
        self.memory_cache[cache_key] = entry
        
        # ディスクキャッシュに保存
        cache_dir = self.cache_dir / namespace
        cache_dir.mkdir(exist_ok=True)
        
        cache_file = cache_dir / f"{key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(entry, f)
        except Exception as e:
            logging.getLogger('claude_bridge.cache').error(f"Failed to save cache: {e}")
    
    def delete(self, key: str, namespace: str = "default"):
        """キャッシュから値を削除"""
        cache_key = f"{namespace}:{key}"
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
        
        cache_file = self.cache_dir / namespace / f"{key}.json"
        if cache_file.exists():
            cache_file.unlink()
    
    def clear_namespace(self, namespace: str):
        """名前空間のキャッシュをクリア"""
        # メモリキャッシュから削除
        keys_to_delete = [k for k in self.memory_cache.keys() if k.startswith(f"{namespace}:")]
        for key in keys_to_delete:
            del self.memory_cache[key]
        
        # ディスクキャッシュから削除
        cache_dir = self.cache_dir / namespace
        if cache_dir.exists():
            for cache_file in cache_dir.glob("*.json"):
                cache_file.unlink()
    
    def cleanup_expired(self):
        """期限切れキャッシュのクリーンアップ"""
        current_time = time.time()
        
        # メモリキャッシュのクリーンアップ
        expired_keys = [k for k, v in self.memory_cache.items() 
                       if v["expires_at"] <= current_time]
        for key in expired_keys:
            del self.memory_cache[key]
            self.cache_stats["evictions"] += 1
        
        # ディスクキャッシュのクリーンアップ
        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    entry = json.load(f)
                if entry.get("expires_at", 0) <= current_time:
                    cache_file.unlink()
                    self.cache_stats["evictions"] += 1
            except Exception:
                continue
    
    def get_stats(self) -> dict:
        """キャッシュ統計を取得"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hit_rate_percent": hit_rate,
            "total_hits": self.cache_stats["hits"],
            "total_misses": self.cache_stats["misses"],
            "total_evictions": self.cache_stats["evictions"],
            "memory_cache_size": len(self.memory_cache),
            "disk_cache_files": len(list(self.cache_dir.rglob("*.json")))
        }
```

#### 5.2 非同期処理管理
```python
# performance/async_manager.py
import asyncio
import concurrent.futures
from typing import List, Callable, Any

class AsyncTaskManager:
    def __init__(self, max_workers=3):
        self.max_workers = max_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks = []
    
    def submit_task(self, func: Callable, *args, **kwargs) -> concurrent.futures.Future:
        """非同期タスクの投入"""
        future = self.executor.submit(func, *args, **kwargs)
        self.active_tasks.append(future)
        
        # 完了したタスクの削除
        self.active_tasks = [task for task in self.active_tasks if not task.done()]
        
        return future
    
    def submit_multiple_tasks(self, tasks: List[tuple]) -> List[concurrent.futures.Future]:
        """複数タスクの並列実行"""
        futures = []
        for func, args, kwargs in tasks:
            future = self.submit_task(func, *args, **kwargs)
            futures.append(future)
        return futures
    
    def wait_for_completion(self, futures: List[concurrent.futures.Future], timeout=None):
        """タスク完了の待機"""
        return concurrent.futures.as_completed(futures, timeout=timeout)
    
    def shutdown(self, wait=True):
        """タスクマネージャーの終了"""
        self.executor.shutdown(wait=wait)
```

### 6. 問題対応

#### 6.1 エラー復旧手順
```python
# troubleshooting/recovery_manager.py
import json
import shutil
from pathlib import Path
from datetime import datetime

class RecoveryManager:
    def __init__(self, bridge_root=None):
        self.bridge_root = Path(bridge_root or Path.home() / ".claude_bridge")
        self.recovery_log = []
    
    def diagnose_issues(self) -> dict:
        """システム問題の診断"""
        issues = []
        
        # 必須ディレクトリの確認
        required_dirs = [
            "config", "tasks/pending", "tasks/processing", 
            "tasks/completed", "results/success", "results/errors",
            "cache", "logs"
        ]
        
        missing_dirs = []
        for dir_name in required_dirs:
            if not (self.bridge_root / dir_name).exists():
                missing_dirs.append(dir_name)
        
        if missing_dirs:
            issues.append({
                "type": "missing_directories",
                "severity": "high",
                "details": missing_dirs,
                "auto_fixable": True
            })
        
        # 設定ファイルの確認
        config_file = self.bridge_root / "config" / "projects.json"
        if not config_file.exists():
            issues.append({
                "type": "missing_config",
                "severity": "critical",
                "details": "projects.json not found",
                "auto_fixable": True
            })
        elif config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    json.load(f)
            except json.JSONDecodeError:
                issues.append({
                    "type": "corrupted_config",
                    "severity": "critical",
                    "details": "projects.json is corrupted",
                    "auto_fixable": True
                })
        
        # 権限の確認
        if not os.access(self.bridge_root, os.R_OK | os.W_OK):
            issues.append({
                "type": "permission_issue",
                "severity": "critical",
                "details": "Insufficient permissions on bridge directory",
                "auto_fixable": False
            })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "issues": issues,
            "total_issues": len(issues),
            "critical_issues": len([i for i in issues if i["severity"] == "critical"])
        }
    
    def auto_fix_issues(self, diagnosis: dict) -> dict:
        """自動修復の実行"""
        fixed_issues = []
        failed_fixes = []
        
        for issue in diagnosis["issues"]:
            if not issue.get("auto_fixable", False):
                continue
            
            try:
                if issue["type"] == "missing_directories":
                    self._fix_missing_directories(issue["details"])
                    fixed_issues.append(issue["type"])
                
                elif issue["type"] == "missing_config":
                    self._fix_missing_config()
                    fixed_issues.append(issue["type"])
                
                elif issue["type"] == "corrupted_config":
                    self._fix_corrupted_config()
                    fixed_issues.append(issue["type"])
                
                self.recovery_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "action": f"fixed_{issue['type']}",
                    "status": "success"
                })
            
            except Exception as e:
                failed_fixes.append({
                    "issue_type": issue["type"],
                    "error": str(e)
                })
                
                self.recovery_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "action": f"fix_{issue['type']}",
                    "status": "failed",
                    "error": str(e)
                })
        
        return {
            "fixed_issues": fixed_issues,
            "failed_fixes": failed_fixes,
            "recovery_log": self.recovery_log
        }
    
    def _fix_missing_directories(self, missing_dirs: List[str]):
        """欠損ディレクトリの修復"""
        for dir_name in missing_dirs:
            dir_path = self.bridge_root / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _fix_missing_config(self):
        """欠損設定ファイルの修復"""
        config_dir = self.bridge_root / "config"
        config_dir.mkdir(exist_ok=True)
        
        default_config = {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "projects": {},
            "global_settings": {
                "auto_load_context": True,
                "max_context_size": 5000,
                "cache_duration": 3600,
                "default_analysis_depth": "detailed"
            }
        }
        
        config_file = config_dir / "projects.json"
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
    
    def _fix_corrupted_config(self):
        """破損設定ファイルの修復"""
        config_file = self.bridge_root / "config" / "projects.json"
        
        # バックアップを作成
        backup_file = config_file.with_suffix('.backup')
        shutil.copy2(config_file, backup_file)
        
        # デフォルト設定で置き換え
        self._fix_missing_config()
    
    def create_recovery_report(self) -> str:
        """復旧レポートの生成"""
        report = [
            "# Claude Bridge System Recovery Report",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Issues Diagnosed and Fixed",
            ""
        ]
        
        for entry in self.recovery_log:
            status_icon = "✅" if entry["status"] == "success" else "❌"
            report.append(f"- {status_icon} {entry['action']} ({entry['timestamp']})")
            if entry.get("error"):
                report.append(f"  Error: {entry['error']}")
        
        report.extend([
            "",
            "## Recommendations",
            "- Create regular backups using the backup manager",
            "- Monitor system health using the health checker",
            "- Review logs regularly for early issue detection",
            ""
        ])
        
        return "\n".join(report)
```

#### 6.2 トラブルシューティングガイド
```python
# troubleshooting/troubleshooting_guide.py
class TroubleshootingGuide:
    def __init__(self):
        self.solutions = {
            "project_not_detected": {
                "symptoms": ["ショートカットが認識されない", "プロジェクト情報が読み込まれない"],
                "causes": ["設定ファイルの問題", "ショートカット形式の間違い", "権限問題"],
                "solutions": [
                    "projects.jsonでプロジェクト設定を確認",
                    "ショートカット形式が [project_name] になっているか確認",
                    "ファイル権限を確認 (chmod 644 projects.json)",
                    "RecoveryManager.diagnose_issues() を実行"
                ]
            },
            "claude_md_not_found": {
                "symptoms": ["Claude.mdが見つからないエラー", "プロジェクトコンテキストが空"],
                "causes": ["ファイルパスの間違い", "ファイルが移動/削除された"],
                "solutions": [
                    "projects.jsonのclaude_mdパスを確認",
                    "ファイルが実際に存在するか確認",
                    "相対パスを絶対パスに変更",
                    "Claude.mdファイルを再作成"
                ]
            },
            "task_not_executing": {
                "symptoms": ["タスクファイルが作成されても実行されない", "結果ファイルが生成されない"],
                "causes": ["Claude Codeが動作していない", "ファイル監視の問題", "権限問題"],
                "solutions": [
                    "Claude Codeが起動しているか確認",
                    "タスクファイルの形式を確認",
                    "tasks/pendingディレクトリの権限を確認",
                    "ファイル監視プロセスを再起動"
                ]
            },
            "performance_degradation": {
                "symptoms": ["応答時間が遅い", "メモリ使用量が多い", "ディスク容量不足"],
                "causes": ["キャッシュの肥大化", "ログファイルの蓄積", "メモリリーク"],
                "solutions": [
                    "CacheManager.cleanup_expired() を実行",
                    "古いログファイルを削除",
                    "システム再起動",
                    "PerformanceMonitor で詳細分析"
                ]
            }
        }
    
    def get_solution(self, problem_type: str) -> dict:
        """問題タイプに対するソリューションを取得"""
        return self.solutions.get(problem_type, {
            "symptoms": ["Unknown problem"],
            "causes": ["Unknown cause"],
            "solutions": ["Contact support or check documentation"]
        })
    
    def diagnose_from_symptoms(self, symptoms: List[str]) -> List[str]:
        """症状から問題タイプを推定"""
        matches = []
        
        for problem_type, info in self.solutions.items():
            for symptom in symptoms:
                for known_symptom in info["symptoms"]:
                    if symptom.lower() in known_symptom.lower() or known_symptom.lower() in symptom.lower():
                        matches.append(problem_type)
                        break
        
        return list(set(matches))  # 重複を除去
```

### 7. 運用手順書

#### 7.1 日常運用手順
```markdown
# Claude Bridge System 日常運用手順

## 毎日の確認項目

### 1. システム稼働確認
```bash
# ヘルスチェック実行
python -m claude_bridge.monitoring.system_health check

# ログの確認
tail -n 50 ~/.claude_bridge/logs/claude_bridge.log
```

### 2. パフォーマンス確認
```bash
# パフォーマンス統計の確認
python -m claude_bridge.monitoring.performance_monitor summary

# キャッシュ統計の確認
python -m claude_bridge.performance.cache_manager stats
```

### 3. セキュリティ確認
```bash
# セキュリティ監査の実行
python -m claude_bridge.security.security_auditor audit

# ファイル権限の確認
python -m claude_bridge.security.security_auditor permissions
```

## 週次作業

### 1. バックアップ確認
```bash
# バックアップ一覧の確認
python -m claude_bridge.backup.backup_manager list

# 手動バックアップの作成（必要に応じて）
python -m claude_bridge.backup.backup_manager create_full
```

### 2. ログ分析
```bash
# エラーパターンの分析
python -m claude_bridge.tools.log_analyzer errors --days 7

# パフォーマンストレンドの分析
python -m claude_bridge.tools.log_analyzer performance --days 7
```

### 3. クリーンアップ作業
```bash
# 期限切れキャッシュのクリーンアップ
python -m claude_bridge.performance.cache_manager cleanup

# 古いタスクファイルのアーカイブ
python -m claude_bridge.core.bridge_filesystem cleanup --days 30
```

## 月次作業

### 1. 設定ファイルのレビュー
- プロジェクト設定の最新性確認
- 不要なプロジェクトの削除
- パフォーマンス設定の調整

### 2. セキュリティレビュー
- 機密データの検索・除去
- ファイル権限の再設定
- アクセスログの確認

### 3. システム最適化
- ディスク使用量の最適化
- パフォーマンス設定の調整
- 不要なファイルの削除
```

#### 7.2 緊急時対応手順
```markdown
# 緊急時対応手順

## レベル1: 軽微な問題
### 症状
- 一部のプロジェクトが認識されない
- レスポンスが若干遅い
- 一部のログにWARNINGが出力される

### 対応手順
1. システムヘルスチェックの実行
2. 設定ファイルの確認・修正
3. キャッシュのクリアと再起動

```bash
python -m claude_bridge.troubleshooting.recovery_manager diagnose
python -m claude_bridge.troubleshooting.recovery_manager auto_fix
```

## レベル2: 中程度の問題
### 症状
- システムが正常に動作しない
- 複数のプロジェクトが認識されない
- タスクが実行されない

### 対応手順
1. エラーログの詳細確認
2. バックアップからの設定復元
3. システムの再初期化

```bash
# バックアップから復元
python -m claude_bridge.backup.backup_manager restore --config-only

# システム再初期化
python -m claude_bridge.core.bridge_filesystem initialize
```

## レベル3: 重大な問題
### 症状
- システムが起動しない
- データが破損している
- セキュリティ侵害の疑い

### 対応手順
1. システム停止
2. フルバックアップから復元
3. セキュリティ監査の実行
4. 必要に応じて再セットアップ

```bash
# 完全バックアップから復元
python -m claude_bridge.backup.backup_manager restore --full

# セキュリティ監査
python -m claude_bridge.security.security_auditor full_audit

# 必要に応じてシステム再構築
python -m claude_bridge setup --force-reinstall
```
```

この運用設計により、Claude Bridge Systemの安定稼働と継続的な品質向上を実現します。特にVIBEcodingの実践環境では、システムの透明性と信頼性が重要であり、これらの運用プロセスがその要求を満たします。
