"""
Claude Bridge System - Context Bridge System
Desktop ↔ Code間でのコンテキスト橋渡しとMIS統合管理
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

from .mis_memory_bridge import MISMemoryBridge, MISMemoryQuery
from .desktop_context_collector import DesktopContextCollector, DesktopConversation, ContextTransferRequest
from .code_development_tracker import CodeDevelopmentTracker, DevelopmentSession, ProjectStatus

logger = logging.getLogger(__name__)


@dataclass
class ContextTransferResult:
    """コンテキスト転送結果"""
    transfer_id: str
    source_environment: str
    target_environment: str
    transfer_type: str
    success: bool
    transferred_items: List[str]
    error_message: Optional[str] = None
    timestamp: str = None


@dataclass
class CrossPlatformContext:
    """クロスプラットフォームコンテキスト"""
    context_id: str
    desktop_conversations: List[str]  # 会話ID
    code_sessions: List[str]  # セッションID
    shared_projects: List[str]
    context_flow: List[Dict[str, str]]  # 環境間の流れ
    last_sync: str
    sync_status: str


class ContextBridgeSystem:
    """Desktop ↔ Code コンテキスト橋渡しシステム"""
    
    def __init__(self, memory_bridge: Optional[MISMemoryBridge] = None):
        """
        初期化
        
        Args:
            memory_bridge: MIS記憶ブリッジ
        """
        self.memory_bridge = memory_bridge or MISMemoryBridge()
        self.desktop_collector = DesktopContextCollector(memory_bridge)
        self.code_tracker = CodeDevelopmentTracker(memory_bridge)
        
        self.active_transfers: Dict[str, ContextTransferRequest] = {}
        self.cross_platform_contexts: Dict[str, CrossPlatformContext] = {}
        
        logger.info("ContextBridgeSystem initialized")
    
    def transfer_desktop_to_code(
        self, 
        conversation_content: str, 
        target_project: str,
        include_code_snippets: bool = True,
        include_context_history: bool = True
    ) -> ContextTransferResult:
        """
        Desktop会話コンテキストをCode環境に転送
        
        Args:
            conversation_content: Desktop会話内容
            target_project: 転送先プロジェクト
            include_code_snippets: コードスニペットを含めるか
            include_context_history: 履歴を含めるか
            
        Returns:
            転送結果
        """
        transfer_id = f"desktop_to_code_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # 会話を分析
            conversation_id = self.desktop_collector.start_conversation_tracking("manual_transfer")
            self.desktop_collector.add_message(conversation_id, conversation_content, is_user=True)
            
            # 会話を完了
            completed_conversation = self.desktop_collector.finalize_conversation(conversation_id)
            
            if not completed_conversation:
                return ContextTransferResult(
                    transfer_id=transfer_id,
                    source_environment="desktop",
                    target_environment="code",
                    transfer_type="conversation",
                    success=False,
                    transferred_items=[],
                    error_message="Failed to process conversation",
                    timestamp=datetime.now().isoformat()
                )
            
            # Code環境用のコンテキストを構築
            transferred_items = []
            
            # 1. 基本会話コンテキスト
            basic_context = self._create_code_context_from_conversation(
                completed_conversation, target_project
            )
            basic_memory_id = self.memory_bridge.save_memory(
                content=basic_context,
                tags=["context_transfer", "desktop_to_code", target_project],
                project_id=target_project,
                entry_type="transferred_context"
            )
            transferred_items.append(f"基本コンテキスト: {basic_memory_id}")
            
            # 2. コードスニペット（オプション）
            if include_code_snippets and completed_conversation.code_snippets:
                for i, snippet in enumerate(completed_conversation.code_snippets):
                    code_context = self._create_code_snippet_context(snippet, target_project)
                    code_memory_id = self.memory_bridge.save_memory(
                        content=code_context,
                        tags=["context_transfer", "code_snippet", target_project, snippet["language"]],
                        project_id=target_project,
                        entry_type="transferred_code"
                    )
                    transferred_items.append(f"コードスニペット {i+1}: {code_memory_id}")
            
            # 3. アクションアイテム
            if completed_conversation.action_items:
                action_context = self._create_action_items_context(
                    completed_conversation.action_items, target_project
                )
                action_memory_id = self.memory_bridge.save_memory(
                    content=action_context,
                    tags=["context_transfer", "action_items", target_project],
                    project_id=target_project,
                    entry_type="transferred_actions"
                )
                transferred_items.append(f"アクションアイテム: {action_memory_id}")
            
            # 4. 関連履歴（オプション）
            if include_context_history:
                history_context = self._get_related_history_for_project(target_project)
                if history_context:
                    history_memory_id = self.memory_bridge.save_memory(
                        content=history_context,
                        tags=["context_transfer", "project_history", target_project],
                        project_id=target_project,
                        entry_type="project_history"
                    )
                    transferred_items.append(f"関連履歴: {history_memory_id}")
            
            return ContextTransferResult(
                transfer_id=transfer_id,
                source_environment="desktop",
                target_environment="code",
                transfer_type="conversation",
                success=True,
                transferred_items=transferred_items,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to transfer desktop context to code: {e}")
            return ContextTransferResult(
                transfer_id=transfer_id,
                source_environment="desktop",
                target_environment="code",
                transfer_type="conversation",
                success=False,
                transferred_items=[],
                error_message=str(e),
                timestamp=datetime.now().isoformat()
            )
    
    def transfer_code_to_desktop(
        self, 
        project_id: str,
        include_recent_sessions: bool = True,
        include_project_status: bool = True,
        session_id: Optional[str] = None
    ) -> ContextTransferResult:
        """
        Code開発状況をDesktop環境に転送
        
        Args:
            project_id: プロジェクトID
            include_recent_sessions: 最近のセッションを含めるか
            include_project_status: プロジェクト状況を含めるか
            session_id: 特定のセッションID（指定時はそのセッションのみ）
            
        Returns:
            転送結果
        """
        transfer_id = f"code_to_desktop_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            transferred_items = []
            
            # 1. プロジェクト状況分析
            if include_project_status:
                project_status = self.code_tracker.analyze_project_status(project_id)
                status_context = self._create_desktop_context_from_project_status(project_status)
                
                status_memory_id = self.memory_bridge.save_memory(
                    content=status_context,
                    tags=["context_transfer", "code_to_desktop", "project_status", project_id],
                    project_id=project_id,
                    entry_type="project_status_for_desktop"
                )
                transferred_items.append(f"プロジェクト状況: {status_memory_id}")
            
            # 2. 開発セッション情報
            if session_id:
                # 特定のセッション
                session_status = self.code_tracker.get_session_status(session_id)
                if session_status:
                    session_context = self._create_desktop_context_from_session(session_status, project_id)
                    session_memory_id = self.memory_bridge.save_memory(
                        content=session_context,
                        tags=["context_transfer", "code_to_desktop", "session", project_id],
                        project_id=project_id,
                        entry_type="session_for_desktop"
                    )
                    transferred_items.append(f"開発セッション: {session_memory_id}")
            elif include_recent_sessions:
                # 最近のセッション情報を取得
                recent_sessions_context = self._get_recent_sessions_context(project_id)
                if recent_sessions_context:
                    sessions_memory_id = self.memory_bridge.save_memory(
                        content=recent_sessions_context,
                        tags=["context_transfer", "code_to_desktop", "recent_sessions", project_id],
                        project_id=project_id,
                        entry_type="recent_sessions_for_desktop"
                    )
                    transferred_items.append(f"最近のセッション: {sessions_memory_id}")
            
            # 3. 開発状況サマリー
            summary_context = self._create_development_summary_for_desktop(project_id)
            summary_memory_id = self.memory_bridge.save_memory(
                content=summary_context,
                tags=["context_transfer", "code_to_desktop", "summary", project_id],
                project_id=project_id,
                entry_type="dev_summary_for_desktop"
            )
            transferred_items.append(f"開発サマリー: {summary_memory_id}")
            
            return ContextTransferResult(
                transfer_id=transfer_id,
                source_environment="code",
                target_environment="desktop",
                transfer_type="development_status",
                success=True,
                transferred_items=transferred_items,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to transfer code context to desktop: {e}")
            return ContextTransferResult(
                transfer_id=transfer_id,
                source_environment="code",
                target_environment="desktop",
                transfer_type="development_status",
                success=False,
                transferred_items=[],
                error_message=str(e),
                timestamp=datetime.now().isoformat()
            )
    
    def get_context_for_code_session(
        self, 
        project_id: str, 
        context_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Code環境でのセッション開始時に関連コンテキストを取得
        
        Args:
            project_id: プロジェクトID
            context_types: 取得するコンテキスト種別
            
        Returns:
            コンテキスト情報
        """
        if not context_types:
            context_types = ["desktop_conversations", "project_history", "action_items"]
        
        context = {
            "project_id": project_id,
            "timestamp": datetime.now().isoformat(),
            "available_contexts": {}
        }
        
        try:
            # Desktop会話履歴
            if "desktop_conversations" in context_types:
                query = MISMemoryQuery(
                    query="",
                    max_results=5,
                    project_id=project_id,
                    entry_types=["desktop_conversation", "transferred_context"]
                )
                memories = self.memory_bridge.recall_memory(query)
                context["available_contexts"]["desktop_conversations"] = [
                    {
                        "id": memory.id,
                        "summary": memory.content[:200] + "..." if len(memory.content) > 200 else memory.content,
                        "timestamp": memory.timestamp,
                        "tags": memory.tags
                    }
                    for memory in memories
                ]
            
            # プロジェクト履歴
            if "project_history" in context_types:
                query = MISMemoryQuery(
                    query="",
                    max_results=10,
                    project_id=project_id,
                    entry_types=["project_status", "dev_session_complete"]
                )
                memories = self.memory_bridge.recall_memory(query)
                context["available_contexts"]["project_history"] = [
                    {
                        "id": memory.id,
                        "summary": memory.content[:150] + "..." if len(memory.content) > 150 else memory.content,
                        "timestamp": memory.timestamp,
                        "entry_type": memory.entry_type
                    }
                    for memory in memories
                ]
            
            # アクションアイテム
            if "action_items" in context_types:
                query = MISMemoryQuery(
                    query="TODO アクション 実装 修正",
                    max_results=5,
                    project_id=project_id,
                    tags=["action_items"]
                )
                memories = self.memory_bridge.recall_memory(query)
                context["available_contexts"]["action_items"] = [
                    {
                        "id": memory.id,
                        "content": memory.content,
                        "timestamp": memory.timestamp
                    }
                    for memory in memories
                ]
            
        except Exception as e:
            logger.error(f"Failed to get context for code session: {e}")
            context["error"] = str(e)
        
        return context
    
    def get_context_for_desktop_session(
        self, 
        project_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Desktop環境でのセッション開始時に関連コンテキストを取得
        
        Args:
            project_hint: プロジェクトヒント
            
        Returns:
            コンテキスト情報
        """
        context = {
            "timestamp": datetime.now().isoformat(),
            "available_contexts": {}
        }
        
        try:
            # 最近の開発状況
            query = MISMemoryQuery(
                query="",
                max_results=5,
                project_id=project_hint,
                entry_types=["project_status", "dev_summary_for_desktop"]
            )
            memories = self.memory_bridge.recall_memory(query)
            context["available_contexts"]["recent_development"] = [
                {
                    "id": memory.id,
                    "project": memory.project_id,
                    "summary": memory.content[:200] + "..." if len(memory.content) > 200 else memory.content,
                    "timestamp": memory.timestamp
                }
                for memory in memories
            ]
            
            # 最近の問題・課題
            query = MISMemoryQuery(
                query="問題 バグ エラー TODO",
                max_results=5,
                tags=["問題あり", "バグ修正"]
            )
            memories = self.memory_bridge.recall_memory(query)
            context["available_contexts"]["recent_issues"] = [
                {
                    "id": memory.id,
                    "project": memory.project_id,
                    "content": memory.content[:150] + "..." if len(memory.content) > 150 else memory.content,
                    "timestamp": memory.timestamp
                }
                for memory in memories
            ]
            
            # アクティブなプロジェクト
            query = MISMemoryQuery(
                query="プロジェクト 開発中",
                max_results=3,
                entry_types=["project_status"]
            )
            memories = self.memory_bridge.recall_memory(query)
            active_projects = set()
            for memory in memories:
                if memory.project_id:
                    active_projects.add(memory.project_id)
            
            context["available_contexts"]["active_projects"] = list(active_projects)
            
        except Exception as e:
            logger.error(f"Failed to get context for desktop session: {e}")
            context["error"] = str(e)
        
        return context
    
    def _create_code_context_from_conversation(
        self, 
        conversation: DesktopConversation, 
        target_project: str
    ) -> str:
        """Desktop会話からCode用コンテキストを作成"""
        return f"""## Desktop会話からのコンテキスト転送

**転送日時**: {datetime.now().isoformat()}
**対象プロジェクト**: {target_project}
**元セッション**: {conversation.session_id}

### 会話サマリー
{conversation.summary}

### 検出されたプロジェクト
{', '.join(conversation.detected_projects) if conversation.detected_projects else 'なし'}

### キートピック
{', '.join(conversation.key_topics) if conversation.key_topics else 'なし'}

### 参照ファイル
{chr(10).join(f'- {file}' for file in conversation.file_references) if conversation.file_references else '- なし'}

### Desktop側でのアクションアイテム
{chr(10).join(f'- {action}' for action in conversation.action_items) if conversation.action_items else '- なし'}

### 重要度
スコア: {conversation.importance_score:.2f}

---
*このコンテキストはClaude Desktopでの会話から自動転送されました。*
*Code環境での作業時に参考にしてください。*
"""
    
    def _create_code_snippet_context(self, snippet: Dict[str, str], target_project: str) -> str:
        """コードスニペット用コンテキストを作成"""
        return f"""## Desktop会話のコードスニペット

**転送日時**: {datetime.now().isoformat()}
**対象プロジェクト**: {target_project}
**言語**: {snippet["language"]}

### コード内容
```{snippet["language"]}
{snippet["code"]}
```

---
*このコードはClaude Desktopでの会話から抽出されました。*
*実装時の参考にしてください。*
"""
    
    def _create_action_items_context(self, action_items: List[str], target_project: str) -> str:
        """アクションアイテム用コンテキストを作成"""
        return f"""## Desktop会話のアクションアイテム

**転送日時**: {datetime.now().isoformat()}
**対象プロジェクト**: {target_project}

### 実行すべきアクション
{chr(10).join(f'- [ ] {action}' for action in action_items)}

---
*これらのアクションアイテムはClaude Desktopでの会話から抽出されました。*
*Code環境での作業時に実行してください。*
"""
    
    def _create_desktop_context_from_project_status(self, status: ProjectStatus) -> str:
        """プロジェクト状況からDesktop用コンテキストを作成"""
        return f"""## Code開発状況レポート

**プロジェクト**: {status.project_name} ({status.project_id})
**更新日時**: {status.last_updated}

### 📊 現在の状況
- **フェーズ**: {status.current_phase}
- **完了率**: {status.completion_percentage:.1f}%
- **ヘルススコア**: {status.health_score:.2f}/1.0
- **最終活動**: {status.last_activity}

### 📁 アクティブファイル ({len(status.active_files)}件)
{chr(10).join(f'- {file}' for file in status.active_files[:5]) if status.active_files else '- なし'}
{('- ... (他' + str(len(status.active_files) - 5) + '件)') if len(status.active_files) > 5 else ''}

### 📝 最近のコミット
{chr(10).join(f'- {commit["hash"]}: {commit["message"]}' for commit in status.recent_commits[:3]) if status.recent_commits else '- なし'}

### ❗ 未解決問題 ({len(status.open_issues)}件)
{chr(10).join(f'- {issue}' for issue in status.open_issues[:3]) if status.open_issues else '- なし'}
{('- ... (他' + str(len(status.open_issues) - 3) + '件)') if len(status.open_issues) > 3 else ''}

### 📋 次のタスク ({len(status.next_tasks)}件)
{chr(10).join(f'- [ ] {task}' for task in status.next_tasks) if status.next_tasks else '- なし'}

### 🔗 主要依存関係
{', '.join(status.dependencies[:5]) if status.dependencies else 'なし'}

---
*このレポートはClaude Code環境から自動生成されました。*
*Desktop環境での議論時に参考にしてください。*
"""
    
    def _create_desktop_context_from_session(self, session_status: Dict[str, Any], project_id: str) -> str:
        """開発セッションからDesktop用コンテキストを作成"""
        return f"""## Code開発セッション状況

**プロジェクト**: {project_id}
**セッションID**: {session_status["session_id"]}
**開始時刻**: {session_status["start_time"]}
**作業ディレクトリ**: {session_status["working_directory"]}
**Gitブランチ**: {session_status.get("git_branch", "N/A")}

### 📊 活動統計
- **変更ファイル数**: {session_status["files_modified_count"]}
- **実行コマンド数**: {session_status["commands_executed_count"]}
- **進捗メモ数**: {session_status["progress_notes_count"]}
- **問題発生数**: {session_status["issues_encountered_count"]}

### 📈 ステータス
**完了状況**: {session_status["completion_status"]}

---
*このセッション情報はClaude Code環境から取得されました。*
*Desktop環境での相談時に参考にしてください。*
"""
    
    def _get_related_history_for_project(self, project_id: str) -> Optional[str]:
        """プロジェクトの関連履歴を取得"""
        try:
            query = MISMemoryQuery(
                query="",
                max_results=3,
                project_id=project_id,
                entry_types=["desktop_conversation", "project_status"]
            )
            memories = self.memory_bridge.recall_memory(query)
            
            if not memories:
                return None
            
            history_content = f"""## {project_id} プロジェクト関連履歴

**取得日時**: {datetime.now().isoformat()}

### 最近の活動履歴
"""
            
            for i, memory in enumerate(memories, 1):
                history_content += f"""
#### {i}. {memory.entry_type} ({memory.timestamp})
{memory.content[:300] + "..." if len(memory.content) > 300 else memory.content}
"""
            
            return history_content
            
        except Exception as e:
            logger.error(f"Failed to get related history: {e}")
            return None
    
    def _get_recent_sessions_context(self, project_id: str) -> Optional[str]:
        """最近のセッション情報を取得"""
        try:
            query = MISMemoryQuery(
                query="",
                max_results=3,
                project_id=project_id,
                entry_types=["dev_session_complete"]
            )
            memories = self.memory_bridge.recall_memory(query)
            
            if not memories:
                return None
            
            sessions_content = f"""## {project_id} 最近の開発セッション

**取得日時**: {datetime.now().isoformat()}

### 最近完了したセッション
"""
            
            for i, memory in enumerate(memories, 1):
                sessions_content += f"""
#### セッション {i} ({memory.timestamp})
{memory.content[:400] + "..." if len(memory.content) > 400 else memory.content}
"""
            
            return sessions_content
            
        except Exception as e:
            logger.error(f"Failed to get recent sessions context: {e}")
            return None
    
    def _create_development_summary_for_desktop(self, project_id: str) -> str:
        """Desktop向け開発サマリーを作成"""
        try:
            # プロジェクト関連の記憶を取得
            query = MISMemoryQuery(
                query="",
                max_results=10,
                project_id=project_id
            )
            memories = self.memory_bridge.recall_memory(query)
            
            # エントリータイプ別に分類
            by_type = {}
            for memory in memories:
                entry_type = memory.entry_type
                if entry_type not in by_type:
                    by_type[entry_type] = []
                by_type[entry_type].append(memory)
            
            summary = f"""## {project_id} 開発状況サマリー

**生成日時**: {datetime.now().isoformat()}
**総記憶数**: {len(memories)}

### 📊 活動分析
"""
            
            # 各タイプの記憶数を報告
            for entry_type, type_memories in by_type.items():
                summary += f"- **{entry_type}**: {len(type_memories)}件\n"
            
            # 最新の活動
            if memories:
                latest_memory = max(memories, key=lambda m: m.timestamp)
                summary += f"""
### 🕒 最新活動
**日時**: {latest_memory.timestamp}
**種別**: {latest_memory.entry_type}
**内容**: {latest_memory.content[:200] + "..." if len(latest_memory.content) > 200 else latest_memory.content}
"""
            
            # タグ分析
            all_tags = []
            for memory in memories:
                all_tags.extend(memory.tags)
            
            tag_counts = {}
            for tag in all_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            if tag_counts:
                top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                summary += f"""
### 🏷️ 主要トピック
{chr(10).join(f'- {tag}: {count}回' for tag, count in top_tags)}
"""
            
            summary += """
---
*この開発サマリーはClaude Code環境の記録から自動生成されました。*
*Desktop環境での議論時に参考にしてください。*
"""
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to create development summary: {e}")
            return f"""## {project_id} 開発状況サマリー

**生成日時**: {datetime.now().isoformat()}
**エラー**: サマリー生成に失敗しました: {e}
"""