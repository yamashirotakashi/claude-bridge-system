"""
Claude Bridge System - Code Development Tracker
Claude Codeでの開発状況を追跡・分析してMISで共有
"""

import json
import logging
import os
import re
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

from .mis_memory_bridge import MISMemoryBridge

logger = logging.getLogger(__name__)


@dataclass
class DevelopmentSession:
    """開発セッション情報"""
    session_id: str
    project_id: str
    start_time: str
    end_time: Optional[str]
    working_directory: str
    git_branch: Optional[str]
    files_modified: List[str]
    commands_executed: List[str]
    test_results: Dict[str, Any]
    commit_messages: List[str]
    progress_notes: List[str]
    issues_encountered: List[str]
    completion_status: str  # "in_progress", "completed", "paused", "blocked"


@dataclass
class ProjectStatus:
    """プロジェクト状況"""
    project_id: str
    project_name: str
    current_phase: str
    last_activity: str
    completion_percentage: float
    active_files: List[str]
    recent_commits: List[Dict[str, str]]
    open_issues: List[str]
    next_tasks: List[str]
    dependencies: List[str]
    health_score: float
    last_updated: str


class CodeDevelopmentTracker:
    """Code開発状況追跡システム"""
    
    def __init__(self, memory_bridge: Optional[MISMemoryBridge] = None):
        """
        初期化
        
        Args:
            memory_bridge: MIS記憶ブリッジ
        """
        self.memory_bridge = memory_bridge or MISMemoryBridge()
        self.active_sessions: Dict[str, DevelopmentSession] = {}
        self.project_cache: Dict[str, ProjectStatus] = {}
        
        logger.info("CodeDevelopmentTracker initialized")
    
    def start_development_session(
        self, 
        project_id: str, 
        working_directory: str = None
    ) -> str:
        """
        開発セッションを開始
        
        Args:
            project_id: プロジェクトID
            working_directory: 作業ディレクトリ
            
        Returns:
            生成されたセッションID
        """
        session_id = f"dev_session_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 作業ディレクトリを自動検出
        if not working_directory:
            working_directory = os.getcwd()
        
        # Gitブランチ情報を取得
        git_branch = self._get_current_git_branch(working_directory)
        
        session = DevelopmentSession(
            session_id=session_id,
            project_id=project_id,
            start_time=datetime.now().isoformat(),
            end_time=None,
            working_directory=working_directory,
            git_branch=git_branch,
            files_modified=[],
            commands_executed=[],
            test_results={},
            commit_messages=[],
            progress_notes=[],
            issues_encountered=[],
            completion_status="in_progress"
        )
        
        self.active_sessions[session_id] = session
        
        # 開始ログをMISに記録
        self._log_session_start(session)
        
        logger.info(f"Started development session: {session_id} for project {project_id}")
        return session_id
    
    def _get_current_git_branch(self, directory: str) -> Optional[str]:
        """
        現在のGitブランチを取得
        
        Args:
            directory: 対象ディレクトリ
            
        Returns:
            ブランチ名
        """
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.debug(f"Failed to get git branch: {e}")
        
        return None
    
    def log_file_modification(self, session_id: str, file_path: str, operation: str = "modified") -> None:
        """
        ファイル変更をログ
        
        Args:
            session_id: セッションID
            file_path: ファイルパス
            operation: 操作種別
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return
        
        session = self.active_sessions[session_id]
        
        # 相対パスに変換
        try:
            relative_path = os.path.relpath(file_path, session.working_directory)
            file_entry = f"{operation}: {relative_path}"
            
            if file_entry not in session.files_modified:
                session.files_modified.append(file_entry)
                logger.debug(f"Logged file modification: {file_entry}")
        except Exception as e:
            logger.warning(f"Failed to log file modification: {e}")
    
    def log_command_execution(self, session_id: str, command: str, result: str = None) -> None:
        """
        コマンド実行をログ
        
        Args:
            session_id: セッションID
            command: 実行コマンド
            result: 実行結果
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return
        
        session = self.active_sessions[session_id]
        
        command_entry = {
            "command": command,
            "timestamp": datetime.now().isoformat(),
            "result": result[:200] + "..." if result and len(result) > 200 else result
        }
        
        session.commands_executed.append(json.dumps(command_entry))
        logger.debug(f"Logged command execution: {command}")
    
    def log_test_results(self, session_id: str, test_framework: str, results: Dict[str, Any]) -> None:
        """
        テスト結果をログ
        
        Args:
            session_id: セッションID
            test_framework: テストフレームワーク
            results: テスト結果
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return
        
        session = self.active_sessions[session_id]
        session.test_results[test_framework] = {
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        
        logger.debug(f"Logged test results for {test_framework}")
    
    def log_progress_note(self, session_id: str, note: str, note_type: str = "progress") -> None:
        """
        進捗メモをログ
        
        Args:
            session_id: セッションID
            note: メモ内容
            note_type: メモタイプ（progress, issue, completion）
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return
        
        session = self.active_sessions[session_id]
        
        note_entry = f"[{datetime.now().strftime('%H:%M')}] {note}"
        
        if note_type == "issue":
            session.issues_encountered.append(note_entry)
        else:
            session.progress_notes.append(note_entry)
        
        logger.debug(f"Logged {note_type} note: {note[:50]}...")
    
    def capture_git_commits(self, session_id: str, since_minutes: int = 60) -> None:
        """
        最近のGitコミットを取得
        
        Args:
            session_id: セッションID
            since_minutes: 取得対象期間（分）
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return
        
        session = self.active_sessions[session_id]
        
        try:
            # 指定時間以降のコミットを取得
            since_time = (datetime.now() - timedelta(minutes=since_minutes)).strftime('%Y-%m-%d %H:%M:%S')
            
            result = subprocess.run(
                ["git", "log", f"--since={since_time}", "--oneline", "--no-merges"],
                cwd=session.working_directory,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                commits = result.stdout.strip().split('\n')
                session.commit_messages.extend(commits)
                logger.debug(f"Captured {len(commits)} git commits")
        
        except Exception as e:
            logger.warning(f"Failed to capture git commits: {e}")
    
    def end_development_session(self, session_id: str, completion_status: str = "completed") -> Optional[DevelopmentSession]:
        """
        開発セッションを終了
        
        Args:
            session_id: セッションID
            completion_status: 完了ステータス
            
        Returns:
            完了したセッション
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return None
        
        session = self.active_sessions[session_id]
        session.end_time = datetime.now().isoformat()
        session.completion_status = completion_status
        
        # 最新のGitコミットを取得
        self.capture_git_commits(session_id, since_minutes=120)
        
        # セッション完了ログをMISに記録
        self._log_session_completion(session)
        
        # アクティブセッションから削除
        completed_session = self.active_sessions.pop(session_id)
        
        logger.info(f"Ended development session: {session_id} with status {completion_status}")
        return completed_session
    
    def analyze_project_status(self, project_id: str, project_path: str = None) -> ProjectStatus:
        """
        プロジェクト状況を分析
        
        Args:
            project_id: プロジェクトID
            project_path: プロジェクトパス
            
        Returns:
            プロジェクト状況
        """
        if not project_path:
            project_path = os.getcwd()
        
        project_path = Path(project_path)
        
        # プロジェクト名を取得
        project_name = project_path.name
        
        # 最終活動時刻を取得
        last_activity = self._get_last_activity_time(project_path)
        
        # アクティブファイルを分析
        active_files = self._analyze_active_files(project_path)
        
        # 最近のコミットを取得
        recent_commits = self._get_recent_commits(project_path)
        
        # 未解決問題を検索
        open_issues = self._find_open_issues(project_path)
        
        # 次のタスクを推測
        next_tasks = self._extract_next_tasks(project_path)
        
        # 依存関係を分析
        dependencies = self._analyze_dependencies(project_path)
        
        # プロジェクトフェーズを推測
        current_phase = self._estimate_project_phase(project_path, recent_commits, active_files)
        
        # 完了率を計算
        completion_percentage = self._calculate_completion_percentage(project_path, open_issues, next_tasks)
        
        # ヘルススコアを計算
        health_score = self._calculate_health_score(recent_commits, open_issues, active_files)
        
        status = ProjectStatus(
            project_id=project_id,
            project_name=project_name,
            current_phase=current_phase,
            last_activity=last_activity,
            completion_percentage=completion_percentage,
            active_files=active_files[:10],  # 最大10個
            recent_commits=recent_commits[:5],  # 最大5個
            open_issues=open_issues[:10],  # 最大10個
            next_tasks=next_tasks[:5],  # 最大5個
            dependencies=dependencies[:10],  # 最大10個
            health_score=health_score,
            last_updated=datetime.now().isoformat()
        )
        
        # キャッシュに保存
        self.project_cache[project_id] = status
        
        # MISに保存
        self._save_project_status_to_mis(status)
        
        logger.info(f"Analyzed project status for {project_id}: phase={current_phase}, completion={completion_percentage:.1f}%")
        return status
    
    def _get_last_activity_time(self, project_path: Path) -> str:
        """最終活動時刻を取得"""
        try:
            # Gitログから最後のコミット時刻を取得
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ci"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        
        # Gitが使えない場合はファイルの更新時刻を使用
        try:
            latest_time = 0
            for file_path in project_path.rglob("*.py"):
                if file_path.is_file():
                    mtime = file_path.stat().st_mtime
                    latest_time = max(latest_time, mtime)
            
            if latest_time > 0:
                return datetime.fromtimestamp(latest_time).isoformat()
        except Exception:
            pass
        
        return datetime.now().isoformat()
    
    def _analyze_active_files(self, project_path: Path) -> List[str]:
        """アクティブファイルを分析"""
        active_files = []
        
        try:
            # Gitステータスから変更されたファイルを取得
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        status = line[:2]
                        filename = line[3:].strip()
                        active_files.append(f"{status.strip()} {filename}")
        except Exception:
            pass
        
        # 最近変更されたファイルも追加
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            for file_path in project_path.rglob("*.py"):
                if file_path.is_file():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime > cutoff_time:
                        rel_path = file_path.relative_to(project_path)
                        if str(rel_path) not in [f.split(' ', 1)[1] for f in active_files]:
                            active_files.append(f"recent {rel_path}")
        except Exception:
            pass
        
        return active_files[:10]
    
    def _get_recent_commits(self, project_path: Path) -> List[Dict[str, str]]:
        """最近のコミットを取得"""
        commits = []
        
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-10", "--no-merges"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split(' ', 1)
                        if len(parts) == 2:
                            commits.append({
                                "hash": parts[0],
                                "message": parts[1]
                            })
        except Exception:
            pass
        
        return commits
    
    def _find_open_issues(self, project_path: Path) -> List[str]:
        """未解決問題を検索"""
        issues = []
        
        # コード内のTODO、FIXME、BUGコメントを検索
        patterns = [
            r"#\s*(TODO|FIXME|BUG|HACK)[:\s](.+)",
            r"//\s*(TODO|FIXME|BUG|HACK)[:\s](.+)",
            r"/\*\s*(TODO|FIXME|BUG|HACK)[:\s](.+)\*/"
        ]
        
        try:
            for file_path in project_path.rglob("*.py"):
                if file_path.is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        for pattern in patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            for match in matches:
                                issue_type = match[0].upper()
                                issue_text = match[1].strip()
                                rel_path = file_path.relative_to(project_path)
                                issues.append(f"{issue_type}: {issue_text} ({rel_path})")
                    except Exception:
                        continue
        except Exception:
            pass
        
        return issues[:10]
    
    def _extract_next_tasks(self, project_path: Path) -> List[str]:
        """次のタスクを推測"""
        tasks = []
        
        # README.mdやTODO.mdからタスクを抽出
        for readme_file in ["README.md", "TODO.md", "ROADMAP.md"]:
            readme_path = project_path / readme_file
            if readme_path.exists():
                try:
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # チェックボックス形式のTODOを抽出
                    todo_pattern = r'- \[ \] (.+)'
                    matches = re.findall(todo_pattern, content)
                    for match in matches[:5]:
                        tasks.append(f"TODO: {match.strip()}")
                        
                except Exception:
                    continue
        
        return tasks[:5]
    
    def _analyze_dependencies(self, project_path: Path) -> List[str]:
        """依存関係を分析"""
        dependencies = []
        
        # requirements.txtから依存関係を取得
        requirements_files = ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]
        
        for req_file in requirements_files:
            req_path = project_path / req_file
            if req_path.exists():
                try:
                    with open(req_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if req_file == "requirements.txt":
                        lines = content.split('\n')
                        for line in lines[:10]:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                dependencies.append(line.split('==')[0].split('>=')[0].split('<=')[0])
                    else:
                        # 他のファイル形式の場合は簡単な解析
                        import_pattern = r'([a-zA-Z0-9_-]+)'
                        matches = re.findall(import_pattern, content)
                        dependencies.extend(matches[:5])
                    
                    break  # 最初に見つかったファイルのみ処理
                        
                except Exception:
                    continue
        
        return list(set(dependencies))[:10]
    
    def _estimate_project_phase(self, project_path: Path, recent_commits: List, active_files: List) -> str:
        """プロジェクトフェーズを推測"""
        # ファイル構造からフェーズを推測
        has_tests = any(path.name.startswith('test_') or 'test' in path.name.lower() 
                       for path in project_path.rglob("*.py"))
        
        has_docs = any(path.suffix == '.md' and path.name.lower() in ['readme.md', 'docs.md']
                      for path in project_path.rglob("*"))
        
        has_setup = any(path.name in ['setup.py', 'pyproject.toml', 'requirements.txt']
                       for path in project_path.rglob("*"))
        
        # コミットメッセージから推測
        commit_messages = ' '.join([commit.get('message', '') for commit in recent_commits]).lower()
        
        if 'initial' in commit_messages or 'init' in commit_messages:
            return "初期化"
        elif 'implement' in commit_messages or 'add' in commit_messages:
            return "実装"
        elif 'test' in commit_messages or has_tests:
            return "テスト"
        elif 'fix' in commit_messages or 'bug' in commit_messages:
            return "バグ修正"
        elif 'refactor' in commit_messages:
            return "リファクタリング"
        elif 'doc' in commit_messages or has_docs:
            return "ドキュメント化"
        elif 'release' in commit_messages or 'deploy' in commit_messages:
            return "リリース準備"
        elif has_setup and has_tests and has_docs:
            return "完成"
        else:
            return "開発中"
    
    def _calculate_completion_percentage(self, project_path: Path, open_issues: List, next_tasks: List) -> float:
        """完了率を計算"""
        # ファイル数ベースの基本スコア
        total_files = len(list(project_path.rglob("*.py")))
        base_score = min(total_files * 10, 70)  # ファイル数 × 10, 最大70%
        
        # 未解決問題による減点
        issue_penalty = len(open_issues) * 5
        
        # 残タスクによる減点
        task_penalty = len(next_tasks) * 3
        
        # テストファイルの存在による加点
        test_files = len([path for path in project_path.rglob("*.py") 
                         if 'test' in path.name.lower()])
        test_bonus = min(test_files * 5, 20)
        
        # ドキュメントファイルの存在による加点
        doc_files = len(list(project_path.rglob("*.md")))
        doc_bonus = min(doc_files * 3, 10)
        
        completion = base_score + test_bonus + doc_bonus - issue_penalty - task_penalty
        return max(0, min(100, completion))
    
    def _calculate_health_score(self, recent_commits: List, open_issues: List, active_files: List) -> float:
        """ヘルススコアを計算"""
        score = 0.5  # ベーススコア
        
        # 最近のコミット活動による加点
        if len(recent_commits) > 0:
            score += 0.2
        if len(recent_commits) > 5:
            score += 0.1
        
        # 未解決問題による減点
        if len(open_issues) > 10:
            score -= 0.3
        elif len(open_issues) > 5:
            score -= 0.1
        
        # アクティブファイル数による調整
        if len(active_files) > 0:
            score += 0.1
        if len(active_files) > 5:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _log_session_start(self, session: DevelopmentSession) -> None:
        """セッション開始をMISに記録"""
        try:
            content = f"""## 開発セッション開始

**プロジェクト**: {session.project_id}
**セッションID**: {session.session_id}
**開始時刻**: {session.start_time}
**作業ディレクトリ**: {session.working_directory}
**Gitブランチ**: {session.git_branch or 'N/A'}

開発セッションが開始されました。
"""
            
            self.memory_bridge.save_memory(
                content=content,
                tags=["development", "session_start", session.project_id],
                project_id=session.project_id,
                entry_type="dev_session_start",
                metadata={
                    "session_id": session.session_id,
                    "working_directory": session.working_directory,
                    "git_branch": session.git_branch
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to log session start: {e}")
    
    def _log_session_completion(self, session: DevelopmentSession) -> None:
        """セッション完了をMISに記録"""
        try:
            # セッション時間を計算
            start_time = datetime.fromisoformat(session.start_time)
            end_time = datetime.fromisoformat(session.end_time)
            duration = end_time - start_time
            
            content = f"""## 開発セッション完了

**プロジェクト**: {session.project_id}
**セッションID**: {session.session_id}
**期間**: {session.start_time} ～ {session.end_time}
**継続時間**: {str(duration).split('.')[0]}
**完了ステータス**: {session.completion_status}

### 活動サマリー
- 変更ファイル数: {len(session.files_modified)}
- 実行コマンド数: {len(session.commands_executed)}
- 進捗メモ数: {len(session.progress_notes)}
- 問題発生数: {len(session.issues_encountered)}
- コミット数: {len(session.commit_messages)}

### 変更されたファイル
{chr(10).join(f'- {file}' for file in session.files_modified[:10]) if session.files_modified else '- なし'}

### 進捗メモ
{chr(10).join(f'- {note}' for note in session.progress_notes[-5:]) if session.progress_notes else '- なし'}

### 発生した問題
{chr(10).join(f'- {issue}' for issue in session.issues_encountered) if session.issues_encountered else '- なし'}

### 最近のコミット
{chr(10).join(f'- {commit}' for commit in session.commit_messages[-5:]) if session.commit_messages else '- なし'}
"""
            
            # タグを生成
            tags = ["development", "session_complete", session.project_id, session.completion_status]
            
            # 重要度による追加タグ
            if len(session.files_modified) > 10:
                tags.append("大規模変更")
            if len(session.issues_encountered) > 0:
                tags.append("問題あり")
            if len(session.commit_messages) > 0:
                tags.append("コミット実行")
            
            self.memory_bridge.save_memory(
                content=content,
                tags=tags,
                project_id=session.project_id,
                entry_type="dev_session_complete",
                metadata={
                    "session_id": session.session_id,
                    "duration_minutes": int(duration.total_seconds() / 60),
                    "files_modified_count": len(session.files_modified),
                    "commands_executed_count": len(session.commands_executed),
                    "issues_count": len(session.issues_encountered),
                    "commits_count": len(session.commit_messages),
                    "completion_status": session.completion_status
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to log session completion: {e}")
    
    def _save_project_status_to_mis(self, status: ProjectStatus) -> None:
        """プロジェクト状況をMISに保存"""
        try:
            content = f"""## プロジェクト開発状況

**プロジェクト**: {status.project_name} ({status.project_id})
**フェーズ**: {status.current_phase}
**完了率**: {status.completion_percentage:.1f}%
**ヘルススコア**: {status.health_score:.2f}
**最終活動**: {status.last_activity}
**更新日時**: {status.last_updated}

### アクティブファイル
{chr(10).join(f'- {file}' for file in status.active_files) if status.active_files else '- なし'}

### 最近のコミット
{chr(10).join(f'- {commit["hash"]}: {commit["message"]}' for commit in status.recent_commits) if status.recent_commits else '- なし'}

### 未解決問題
{chr(10).join(f'- {issue}' for issue in status.open_issues) if status.open_issues else '- なし'}

### 次のタスク
{chr(10).join(f'- {task}' for task in status.next_tasks) if status.next_tasks else '- なし'}

### 依存関係
{', '.join(status.dependencies) if status.dependencies else 'なし'}
"""
            
            # タグを生成
            tags = ["project_status", status.project_id, status.current_phase]
            
            # 完了率による追加タグ
            if status.completion_percentage >= 80:
                tags.append("完成間近")
            elif status.completion_percentage >= 50:
                tags.append("進行中")
            else:
                tags.append("初期段階")
            
            # ヘルススコアによる追加タグ
            if status.health_score >= 0.8:
                tags.append("健全")
            elif status.health_score >= 0.5:
                tags.append("要注意")
            else:
                tags.append("問題あり")
            
            self.memory_bridge.save_memory(
                content=content,
                tags=tags,
                project_id=status.project_id,
                entry_type="project_status",
                metadata={
                    "project_name": status.project_name,
                    "current_phase": status.current_phase,
                    "completion_percentage": status.completion_percentage,
                    "health_score": status.health_score,
                    "active_files_count": len(status.active_files),
                    "open_issues_count": len(status.open_issues),
                    "next_tasks_count": len(status.next_tasks)
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to save project status to MIS: {e}")
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        セッション状態を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            セッション状態情報
        """
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session.session_id,
            "project_id": session.project_id,
            "start_time": session.start_time,
            "working_directory": session.working_directory,
            "git_branch": session.git_branch,
            "files_modified_count": len(session.files_modified),
            "commands_executed_count": len(session.commands_executed),
            "progress_notes_count": len(session.progress_notes),
            "issues_encountered_count": len(session.issues_encountered),
            "completion_status": session.completion_status
        }
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """
        アクティブセッション一覧を取得
        
        Returns:
            アクティブセッションのリスト
        """
        return [
            self.get_session_status(session_id) 
            for session_id in self.active_sessions.keys()
        ]