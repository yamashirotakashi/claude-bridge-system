"""
Claude Bridge System - Desktop Context Collector
Claude Desktopでの会話コンテキストを収集・分析してMISに保存
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

from .mis_memory_bridge import MISMemoryBridge
from .mis_prompt_handler import MISPromptHandler, MISPromptType

logger = logging.getLogger(__name__)


@dataclass
class DesktopConversation:
    """Desktop会話コンテキスト"""
    session_id: str
    timestamp: str
    user_messages: List[str]
    assistant_messages: List[str]
    detected_projects: List[str]
    key_topics: List[str]
    action_items: List[str]
    code_snippets: List[Dict[str, str]]  # {"language": "python", "code": "..."}
    file_references: List[str]
    importance_score: float
    summary: str


@dataclass
class ContextTransferRequest:
    """コンテキスト転送リクエスト"""
    conversation_id: str
    target_environment: str  # "claude_code"
    project_mapping: Optional[str] = None
    transfer_type: str = "full"  # "full", "summary", "code_only"
    include_history: bool = True


class DesktopContextCollector:
    """Desktop会話コンテキスト収集システム"""
    
    def __init__(self, memory_bridge: Optional[MISMemoryBridge] = None):
        """
        初期化
        
        Args:
            memory_bridge: MIS記憶ブリッジ
        """
        self.memory_bridge = memory_bridge or MISMemoryBridge()
        self.prompt_handler = MISPromptHandler()
        self.active_conversations: Dict[str, DesktopConversation] = {}
        self.context_patterns = self._initialize_context_patterns()
        
        logger.info("DesktopContextCollector initialized")
    
    def _initialize_context_patterns(self) -> Dict[str, List[str]]:
        """コンテキスト分析用パターンを初期化"""
        return {
            "project_indicators": [
                r"プロジェクト\s*[：:]\s*([^\s\n]+)",
                r"working\s+on\s+([^\s\n]+)",
                r"\[([a-zA-Z0-9_]+)\]",  # [narou], [tech] など
                r"([a-zA-Z0-9_]+)プロジェクト",
                r"([a-zA-Z0-9_]+)\.py",  # ファイル名から推測
                r"cd\s+([^\s\n]+)"  # ディレクトリ変更
            ],
            "code_patterns": [
                r"```(\w+)?\n(.*?)```",  # コードブロック
                r"`([^`]+)`",  # インラインコード
                r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)",  # 関数定義
                r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)",  # クラス定義
                r"import\s+([a-zA-Z0-9_.]+)",  # インポート文
                r"from\s+([a-zA-Z0-9_.]+)"  # from import文
            ],
            "action_patterns": [
                r"(実装|追加|修正|削除|変更|更新|作成|生成).*?([する]|[だ])",
                r"(fix|add|update|create|implement|remove|delete|modify)",
                r"TODO[：:]?\s*(.+)",
                r"FIXME[：:]?\s*(.+)",
                r"BUG[：:]?\s*(.+)"
            ],
            "file_patterns": [
                r"([a-zA-Z0-9_]+\.(py|js|ts|json|md|txt|yml|yaml|toml))",
                r"([a-zA-Z0-9_/]+/[a-zA-Z0-9_/]+\.[a-zA-Z0-9]+)",
                r"[Ff]ile[：:]?\s*([^\s\n]+)"
            ],
            "importance_indicators": [
                r"(重要|critical|urgent|必須|essential|important)",
                r"(エラー|error|バグ|bug|問題|issue|failure)",
                r"(完了|完成|finished|completed|done)",
                r"(決定|decided|確定|final|approved)",
                r"(締切|deadline|期限|due)"
            ]
        }
    
    def start_conversation_tracking(self, session_id: str) -> str:
        """
        会話トラッキングを開始
        
        Args:
            session_id: セッションID
            
        Returns:
            生成された会話ID
        """
        conversation_id = f"desktop_conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{session_id[:8]}"
        
        self.active_conversations[conversation_id] = DesktopConversation(
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            user_messages=[],
            assistant_messages=[],
            detected_projects=[],
            key_topics=[],
            action_items=[],
            code_snippets=[],
            file_references=[],
            importance_score=0.0,
            summary=""
        )
        
        logger.info(f"Started conversation tracking: {conversation_id}")
        return conversation_id
    
    def add_message(self, conversation_id: str, message: str, is_user: bool = True) -> None:
        """
        メッセージを会話に追加
        
        Args:
            conversation_id: 会話ID
            message: メッセージ内容
            is_user: ユーザーメッセージかどうか
        """
        if conversation_id not in self.active_conversations:
            logger.warning(f"Conversation not found: {conversation_id}")
            return
        
        conversation = self.active_conversations[conversation_id]
        
        if is_user:
            conversation.user_messages.append(message)
        else:
            conversation.assistant_messages.append(message)
        
        # メッセージをリアルタイム分析
        self._analyze_message(conversation, message)
        
        logger.debug(f"Added message to conversation {conversation_id}: {len(message)} chars")
    
    def _analyze_message(self, conversation: DesktopConversation, message: str) -> None:
        """
        メッセージを分析してコンテキスト情報を抽出
        
        Args:
            conversation: 会話オブジェクト
            message: 分析するメッセージ
        """
        # プロジェクト検出
        for pattern in self.context_patterns["project_indicators"]:
            matches = re.findall(pattern, message, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                if match and match not in conversation.detected_projects:
                    conversation.detected_projects.append(match)
        
        # コードスニペット抽出
        for pattern in self.context_patterns["code_patterns"]:
            matches = re.findall(pattern, message, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    language = match[0] if match[0] else "text"
                    code = match[1] if len(match) > 1 else match[0]
                else:
                    language = "text"
                    code = match
                
                if code and len(code.strip()) > 10:  # 短すぎるコードは除外
                    conversation.code_snippets.append({
                        "language": language,
                        "code": code.strip(),
                        "extracted_at": datetime.now().isoformat()
                    })
        
        # アクションアイテム抽出
        for pattern in self.context_patterns["action_patterns"]:
            matches = re.findall(pattern, message, re.IGNORECASE)
            for match in matches:
                action_text = match if isinstance(match, str) else " ".join(match)
                if action_text and action_text not in conversation.action_items:
                    conversation.action_items.append(action_text)
        
        # ファイル参照抽出
        for pattern in self.context_patterns["file_patterns"]:
            matches = re.findall(pattern, message, re.IGNORECASE)
            for match in matches:
                if match and match not in conversation.file_references:
                    conversation.file_references.append(match)
        
        # 重要度スコア更新
        importance_boost = 0.0
        for pattern in self.context_patterns["importance_indicators"]:
            matches = re.findall(pattern, message, re.IGNORECASE)
            importance_boost += len(matches) * 0.1
        
        conversation.importance_score += importance_boost
        
        # メッセージ長による重要度調整
        if len(message) > 1000:
            conversation.importance_score += 0.05
        
        # コードが含まれている場合の重要度調整
        if conversation.code_snippets:
            conversation.importance_score += 0.1
    
    def finalize_conversation(self, conversation_id: str) -> Optional[DesktopConversation]:
        """
        会話を終了し、最終分析を実行
        
        Args:
            conversation_id: 会話ID
            
        Returns:
            完了した会話オブジェクト
        """
        if conversation_id not in self.active_conversations:
            logger.warning(f"Conversation not found: {conversation_id}")
            return None
        
        conversation = self.active_conversations[conversation_id]
        
        # 最終サマリー生成
        conversation.summary = self._generate_conversation_summary(conversation)
        
        # キートピック抽出
        conversation.key_topics = self._extract_key_topics(conversation)
        
        # 重要度の最終調整
        self._calculate_final_importance(conversation)
        
        # MISに保存
        self._save_to_mis(conversation)
        
        # アクティブ会話から削除
        completed_conversation = self.active_conversations.pop(conversation_id)
        
        logger.info(f"Finalized conversation {conversation_id}: importance={completed_conversation.importance_score:.2f}")
        return completed_conversation
    
    def _generate_conversation_summary(self, conversation: DesktopConversation) -> str:
        """
        会話のサマリーを生成
        
        Args:
            conversation: 会話オブジェクト
            
        Returns:
            サマリーテキスト
        """
        summary_parts = []
        
        # プロジェクト情報
        if conversation.detected_projects:
            summary_parts.append(f"関連プロジェクト: {', '.join(conversation.detected_projects[:3])}")
        
        # メッセージ数
        total_messages = len(conversation.user_messages) + len(conversation.assistant_messages)
        summary_parts.append(f"メッセージ数: {total_messages}")
        
        # コードスニペット
        if conversation.code_snippets:
            languages = set(snippet["language"] for snippet in conversation.code_snippets)
            summary_parts.append(f"コード言語: {', '.join(languages)}")
        
        # アクションアイテム
        if conversation.action_items:
            summary_parts.append(f"アクション項目: {len(conversation.action_items)}件")
        
        # ファイル参照
        if conversation.file_references:
            summary_parts.append(f"参照ファイル: {len(conversation.file_references)}件")
        
        # 重要度
        importance_level = "高" if conversation.importance_score > 0.5 else "中" if conversation.importance_score > 0.2 else "低"
        summary_parts.append(f"重要度: {importance_level}")
        
        return " | ".join(summary_parts)
    
    def _extract_key_topics(self, conversation: DesktopConversation) -> List[str]:
        """
        キートピックを抽出
        
        Args:
            conversation: 会話オブジェクト
            
        Returns:
            キートピックのリスト
        """
        topics = set()
        
        # プロジェクト名をトピックに追加
        topics.update(conversation.detected_projects)
        
        # アクションアイテムからキーワード抽出
        for action in conversation.action_items:
            # 簡単なキーワード抽出（実装、修正、追加など）
            if "実装" in action or "implement" in action.lower():
                topics.add("実装")
            if "修正" in action or "fix" in action.lower():
                topics.add("バグ修正")
            if "追加" in action or "add" in action.lower():
                topics.add("機能追加")
            if "設計" in action or "design" in action.lower():
                topics.add("設計")
            if "テスト" in action or "test" in action.lower():
                topics.add("テスト")
        
        # コード言語をトピックに追加
        for snippet in conversation.code_snippets:
            if snippet["language"] and snippet["language"] != "text":
                topics.add(snippet["language"])
        
        return list(topics)[:10]  # 最大10個
    
    def _calculate_final_importance(self, conversation: DesktopConversation) -> None:
        """
        最終重要度を計算
        
        Args:
            conversation: 会話オブジェクト
        """
        # メッセージ数による調整
        message_count = len(conversation.user_messages) + len(conversation.assistant_messages)
        if message_count > 20:
            conversation.importance_score += 0.1
        elif message_count > 10:
            conversation.importance_score += 0.05
        
        # プロジェクト検出による調整
        if conversation.detected_projects:
            conversation.importance_score += 0.1
        
        # コードスニペット数による調整
        if len(conversation.code_snippets) > 5:
            conversation.importance_score += 0.2
        elif len(conversation.code_snippets) > 0:
            conversation.importance_score += 0.1
        
        # アクションアイテム数による調整
        if len(conversation.action_items) > 3:
            conversation.importance_score += 0.15
        elif len(conversation.action_items) > 0:
            conversation.importance_score += 0.05
        
        # 最大値を1.0に制限
        conversation.importance_score = min(conversation.importance_score, 1.0)
    
    def _save_to_mis(self, conversation: DesktopConversation) -> None:
        """
        会話をMISに保存
        
        Args:
            conversation: 会話オブジェクト
        """
        try:
            # メイン会話記録を保存
            main_content = f"""## Desktop会話記録

**セッションID**: {conversation.session_id}
**日時**: {conversation.timestamp}
**サマリー**: {conversation.summary}

### 検出されたプロジェクト
{', '.join(conversation.detected_projects) if conversation.detected_projects else 'なし'}

### キートピック
{', '.join(conversation.key_topics) if conversation.key_topics else 'なし'}

### アクションアイテム
{chr(10).join(f'- {item}' for item in conversation.action_items) if conversation.action_items else 'なし'}

### 参照ファイル
{chr(10).join(f'- {file}' for file in conversation.file_references) if conversation.file_references else 'なし'}

### 会話内容（抜粋）
"""
            
            # 最初と最後のメッセージを抜粋
            if conversation.user_messages:
                main_content += f"\n**最初のユーザーメッセージ**:\n{conversation.user_messages[0][:200]}{'...' if len(conversation.user_messages[0]) > 200 else ''}\n"
            
            if len(conversation.user_messages) > 1:
                main_content += f"\n**最後のユーザーメッセージ**:\n{conversation.user_messages[-1][:200]}{'...' if len(conversation.user_messages[-1]) > 200 else ''}\n"
            
            # タグを生成
            tags = ["desktop_context", "conversation"] + conversation.key_topics[:5]
            
            # 重要度に基づいてタグを追加
            if conversation.importance_score > 0.5:
                tags.append("高重要度")
            elif conversation.importance_score > 0.2:
                tags.append("中重要度")
            
            # MISに保存
            memory_id = self.memory_bridge.save_memory(
                content=main_content,
                tags=tags,
                project_id=conversation.detected_projects[0] if conversation.detected_projects else None,
                entry_type="desktop_conversation",
                metadata={
                    "session_id": conversation.session_id,
                    "message_count": len(conversation.user_messages) + len(conversation.assistant_messages),
                    "code_snippets_count": len(conversation.code_snippets),
                    "action_items_count": len(conversation.action_items),
                    "importance_score": conversation.importance_score,
                    "detected_projects": conversation.detected_projects,
                    "file_references": conversation.file_references
                }
            )
            
            # コードスニペットを個別に保存
            for i, snippet in enumerate(conversation.code_snippets):
                if len(snippet["code"]) > 50:  # 短すぎるコードは保存しない
                    code_content = f"""## Desktop会話のコードスニペット

**言語**: {snippet["language"]}
**抽出日時**: {snippet["extracted_at"]}
**元会話**: {conversation.session_id}

```{snippet["language"]}
{snippet["code"]}
```
"""
                    
                    code_tags = ["desktop_context", "code", snippet["language"]] + conversation.key_topics[:3]
                    
                    self.memory_bridge.save_memory(
                        content=code_content,
                        tags=code_tags,
                        project_id=conversation.detected_projects[0] if conversation.detected_projects else None,
                        entry_type="code_snippet",
                        metadata={
                            "parent_conversation": memory_id,
                            "language": snippet["language"],
                            "code_length": len(snippet["code"])
                        }
                    )
            
            logger.info(f"Saved conversation to MIS: {memory_id}")
            
        except Exception as e:
            logger.error(f"Failed to save conversation to MIS: {e}")
    
    def create_context_transfer_request(
        self, 
        conversation_id: str, 
        target_project: Optional[str] = None,
        transfer_type: str = "full"
    ) -> Optional[ContextTransferRequest]:
        """
        コンテキスト転送リクエストを作成
        
        Args:
            conversation_id: 会話ID
            target_project: 転送先プロジェクト
            transfer_type: 転送タイプ
            
        Returns:
            転送リクエスト
        """
        if conversation_id not in self.active_conversations:
            logger.warning(f"Conversation not found: {conversation_id}")
            return None
        
        conversation = self.active_conversations[conversation_id]
        
        # プロジェクトマッピングを決定
        project_mapping = target_project
        if not project_mapping and conversation.detected_projects:
            project_mapping = conversation.detected_projects[0]
        
        request = ContextTransferRequest(
            conversation_id=conversation_id,
            target_environment="claude_code",
            project_mapping=project_mapping,
            transfer_type=transfer_type,
            include_history=True
        )
        
        logger.info(f"Created context transfer request: {conversation_id} -> {project_mapping}")
        return request
    
    def get_conversation_status(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        会話の状態を取得
        
        Args:
            conversation_id: 会話ID
            
        Returns:
            会話状態情報
        """
        if conversation_id not in self.active_conversations:
            return None
        
        conversation = self.active_conversations[conversation_id]
        
        return {
            "conversation_id": conversation_id,
            "session_id": conversation.session_id,
            "start_time": conversation.timestamp,
            "message_count": len(conversation.user_messages) + len(conversation.assistant_messages),
            "detected_projects": conversation.detected_projects,
            "key_topics": conversation.key_topics,
            "importance_score": conversation.importance_score,
            "code_snippets_count": len(conversation.code_snippets),
            "action_items_count": len(conversation.action_items),
            "file_references_count": len(conversation.file_references)
        }
    
    def list_active_conversations(self) -> List[Dict[str, Any]]:
        """
        アクティブな会話一覧を取得
        
        Returns:
            アクティブ会話のリスト
        """
        return [
            self.get_conversation_status(conv_id) 
            for conv_id in self.active_conversations.keys()
        ]