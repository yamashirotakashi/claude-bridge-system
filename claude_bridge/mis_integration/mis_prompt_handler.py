"""
Claude Bridge System - MIS Prompt Handler
MIS特殊プロンプトの検出と処理を担当
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MISPromptType(Enum):
    """MIS特殊プロンプトの種類"""
    MEMORY_SAVE = "mis_memory_save"          # [MISに記憶]
    MEMORY_RECALL = "mis_memory_recall"      # [MIS記憶呼び出し]
    SPEC_UPDATE = "mis_spec_update"          # [MIS仕様更新]
    SPEC_CHECK = "mis_spec_check"            # [MIS仕様確認]
    PHASE_ADVANCE = "mis_phase_advance"      # [MISフェーズ進行]
    STATUS_SYNC = "mis_status_sync"          # [MIS状態同期]
    CONTEXT_SHARE = "mis_context_share"      # [MISコンテキスト共有]


@dataclass
class MISPromptResult:
    """MIS特殊プロンプト処理結果"""
    prompt_type: MISPromptType
    content: str
    metadata: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None
    desktop_action: Optional[str] = None  # Desktop側で実行すべきアクション


class MISPromptHandler:
    """MIS特殊プロンプトハンドラー"""
    
    def __init__(self):
        """初期化"""
        self.prompt_patterns = {
            MISPromptType.MEMORY_SAVE: [
                r'\[MISに記憶\](.+)',
                r'\[MIS記憶\](.+)',
                r'\[記憶\](.+)'
            ],
            MISPromptType.MEMORY_RECALL: [
                r'\[MIS記憶呼び出し\](.+)',
                r'\[MIS呼び出し\](.+)', 
                r'\[呼び出し\](.+)'
            ],
            MISPromptType.SPEC_UPDATE: [
                r'\[MIS仕様更新\](.+)',
                r'\[仕様更新\](.+)'
            ],
            MISPromptType.SPEC_CHECK: [
                r'\[MIS仕様確認\](.+)',
                r'\[仕様確認\](.+)'
            ],
            MISPromptType.PHASE_ADVANCE: [
                r'\[MISフェーズ進行\](.+)',
                r'\[フェーズ進行\](.+)'
            ],
            MISPromptType.STATUS_SYNC: [
                r'\[MIS状態同期\](.+)',
                r'\[状態同期\](.+)'
            ],
            MISPromptType.CONTEXT_SHARE: [
                r'\[MISコンテキスト共有\](.+)',
                r'\[コンテキスト共有\](.+)'
            ]
        }
        
        logger.info("MISPromptHandler initialized")
    
    def detect_mis_prompts(self, text: str) -> List[Tuple[MISPromptType, str]]:
        """
        テキストからMIS特殊プロンプトを検出
        
        Args:
            text: 検索対象テキスト
            
        Returns:
            検出されたプロンプトのリスト (プロンプト種別, 内容)
        """
        detected_prompts = []
        
        for prompt_type, patterns in self.prompt_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    content = match.strip()
                    if content:
                        detected_prompts.append((prompt_type, content))
                        logger.debug(f"Detected MIS prompt: {prompt_type.value} - {content[:50]}...")
        
        return detected_prompts
    
    def process_memory_save(self, content: str) -> MISPromptResult:
        """
        [MISに記憶] プロンプトの処理
        
        Args:
            content: 記憶する内容
            
        Returns:
            処理結果
        """
        try:
            # 記憶内容を構造化
            metadata = {
                "operation": "save",
                "timestamp": self._get_timestamp(),
                "content_length": len(content),
                "content_type": self._classify_content(content)
            }
            
            # Desktop側で実行すべきアクションを定義
            desktop_action = {
                "type": "memory_save",
                "payload": {
                    "content": content,
                    "metadata": metadata,
                    "storage_type": "mis_memory"
                }
            }
            
            return MISPromptResult(
                prompt_type=MISPromptType.MEMORY_SAVE,
                content=content,
                metadata=metadata,
                success=True,
                desktop_action=desktop_action
            )
            
        except Exception as e:
            logger.error(f"Error processing memory save: {e}")
            return MISPromptResult(
                prompt_type=MISPromptType.MEMORY_SAVE,
                content=content,
                metadata={},
                success=False,
                error_message=str(e)
            )
    
    def process_memory_recall(self, query: str) -> MISPromptResult:
        """
        [MIS記憶呼び出し] プロンプトの処理
        
        Args:
            query: 検索クエリ
            
        Returns:
            処理結果
        """
        try:
            metadata = {
                "operation": "recall",
                "query": query,
                "timestamp": self._get_timestamp(),
                "search_type": self._classify_query(query)
            }
            
            desktop_action = {
                "type": "memory_recall",
                "payload": {
                    "query": query,
                    "metadata": metadata,
                    "max_results": 10
                }
            }
            
            return MISPromptResult(
                prompt_type=MISPromptType.MEMORY_RECALL,
                content=query,
                metadata=metadata,
                success=True,
                desktop_action=desktop_action
            )
            
        except Exception as e:
            logger.error(f"Error processing memory recall: {e}")
            return MISPromptResult(
                prompt_type=MISPromptType.MEMORY_RECALL,
                content=query,
                metadata={},
                success=False,
                error_message=str(e)
            )
    
    def process_spec_update(self, spec_content: str) -> MISPromptResult:
        """
        [MIS仕様更新] プロンプトの処理
        
        Args:
            spec_content: 仕様更新内容
            
        Returns:
            処理結果
        """
        try:
            metadata = {
                "operation": "spec_update",
                "timestamp": self._get_timestamp(),
                "spec_type": self._classify_spec_content(spec_content),
                "update_size": len(spec_content)
            }
            
            desktop_action = {
                "type": "spec_update",
                "payload": {
                    "content": spec_content,
                    "metadata": metadata,
                    "validation_required": True
                }
            }
            
            return MISPromptResult(
                prompt_type=MISPromptType.SPEC_UPDATE,
                content=spec_content,
                metadata=metadata,
                success=True,
                desktop_action=desktop_action
            )
            
        except Exception as e:
            logger.error(f"Error processing spec update: {e}")
            return MISPromptResult(
                prompt_type=MISPromptType.SPEC_UPDATE,
                content=spec_content,
                metadata={},
                success=False,
                error_message=str(e)
            )
    
    def process_context_share(self, context_data: str) -> MISPromptResult:
        """
        [MISコンテキスト共有] プロンプトの処理
        
        Args:
            context_data: 共有するコンテキストデータ
            
        Returns:
            処理結果
        """
        try:
            metadata = {
                "operation": "context_share",
                "timestamp": self._get_timestamp(),
                "context_size": len(context_data),
                "context_type": self._classify_context(context_data)
            }
            
            desktop_action = {
                "type": "context_share",
                "payload": {
                    "context": context_data,
                    "metadata": metadata,
                    "share_scope": "desktop_session"
                }
            }
            
            return MISPromptResult(
                prompt_type=MISPromptType.CONTEXT_SHARE,
                content=context_data,
                metadata=metadata,
                success=True,
                desktop_action=desktop_action
            )
            
        except Exception as e:
            logger.error(f"Error processing context share: {e}")
            return MISPromptResult(
                prompt_type=MISPromptType.CONTEXT_SHARE,
                content=context_data,
                metadata={},
                success=False,
                error_message=str(e)
            )
    
    def process_prompt(self, prompt_type: MISPromptType, content: str) -> MISPromptResult:
        """
        MIS特殊プロンプトの統一処理エントリーポイント
        
        Args:
            prompt_type: プロンプト種別
            content: プロンプト内容
            
        Returns:
            処理結果
        """
        processor_map = {
            MISPromptType.MEMORY_SAVE: self.process_memory_save,
            MISPromptType.MEMORY_RECALL: self.process_memory_recall,
            MISPromptType.SPEC_UPDATE: self.process_spec_update,
            MISPromptType.SPEC_CHECK: self._process_spec_check,
            MISPromptType.PHASE_ADVANCE: self._process_phase_advance,
            MISPromptType.STATUS_SYNC: self._process_status_sync,
            MISPromptType.CONTEXT_SHARE: self.process_context_share
        }
        
        processor = processor_map.get(prompt_type)
        if processor:
            return processor(content)
        else:
            logger.warning(f"Unknown prompt type: {prompt_type}")
            return MISPromptResult(
                prompt_type=prompt_type,
                content=content,
                metadata={},
                success=False,
                error_message=f"Unknown prompt type: {prompt_type}"
            )
    
    def _process_spec_check(self, query: str) -> MISPromptResult:
        """仕様確認の処理"""
        metadata = {
            "operation": "spec_check",
            "query": query,
            "timestamp": self._get_timestamp()
        }
        
        desktop_action = {
            "type": "spec_check",
            "payload": {
                "query": query,
                "metadata": metadata
            }
        }
        
        return MISPromptResult(
            prompt_type=MISPromptType.SPEC_CHECK,
            content=query,
            metadata=metadata,
            success=True,
            desktop_action=desktop_action
        )
    
    def _process_phase_advance(self, phase_info: str) -> MISPromptResult:
        """フェーズ進行の処理"""
        metadata = {
            "operation": "phase_advance", 
            "phase_info": phase_info,
            "timestamp": self._get_timestamp()
        }
        
        desktop_action = {
            "type": "phase_advance",
            "payload": {
                "phase_info": phase_info,
                "metadata": metadata
            }
        }
        
        return MISPromptResult(
            prompt_type=MISPromptType.PHASE_ADVANCE,
            content=phase_info,
            metadata=metadata,
            success=True,
            desktop_action=desktop_action
        )
    
    def _process_status_sync(self, status_data: str) -> MISPromptResult:
        """状態同期の処理"""
        metadata = {
            "operation": "status_sync",
            "status_data": status_data,
            "timestamp": self._get_timestamp()
        }
        
        desktop_action = {
            "type": "status_sync",
            "payload": {
                "status_data": status_data,
                "metadata": metadata
            }
        }
        
        return MISPromptResult(
            prompt_type=MISPromptType.STATUS_SYNC,
            content=status_data,
            metadata=metadata,
            success=True,
            desktop_action=desktop_action
        )
    
    def _get_timestamp(self) -> str:
        """現在のタイムスタンプを取得"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _classify_content(self, content: str) -> str:
        """コンテンツの種類を分類"""
        if len(content) > 1000:
            return "long_text"
        elif any(keyword in content.lower() for keyword in ["仕様", "要件", "設計"]):
            return "specification"
        elif any(keyword in content.lower() for keyword in ["実装", "コード", "関数"]):
            return "implementation"
        elif any(keyword in content.lower() for keyword in ["バグ", "エラー", "問題"]):
            return "issue"
        else:
            return "general"
    
    def _classify_query(self, query: str) -> str:
        """クエリの種類を分類"""
        if any(keyword in query.lower() for keyword in ["いつ", "when", "時期"]):
            return "temporal"
        elif any(keyword in query.lower() for keyword in ["どこ", "where", "場所"]):
            return "location"
        elif any(keyword in query.lower() for keyword in ["なぜ", "why", "理由"]):
            return "reason"
        elif any(keyword in query.lower() for keyword in ["どうやって", "how", "方法"]):
            return "method"
        else:
            return "general"
    
    def _classify_spec_content(self, content: str) -> str:
        """仕様コンテンツの種類を分類"""
        if "requirements.md" in content.lower():
            return "requirements"
        elif "design.md" in content.lower():
            return "design"
        elif "api" in content.lower():
            return "api_spec"
        else:
            return "general_spec"
    
    def _classify_context(self, content: str) -> str:
        """コンテキストの種類を分類"""
        if any(keyword in content.lower() for keyword in ["プロジェクト", "project"]):
            return "project_context"
        elif any(keyword in content.lower() for keyword in ["セッション", "session"]):
            return "session_context"
        elif any(keyword in content.lower() for keyword in ["タスク", "task", "作業"]):
            return "task_context"
        else:
            return "general_context"