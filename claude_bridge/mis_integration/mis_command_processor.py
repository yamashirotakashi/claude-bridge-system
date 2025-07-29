"""
Claude Bridge System - MIS Command Processor
MIS特殊プロンプトの統合処理とコマンド実行
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import asdict
from datetime import datetime

from .mis_prompt_handler import MISPromptHandler, MISPromptType, MISPromptResult
from .mis_memory_bridge import MISMemoryBridge, MISMemoryQuery

logger = logging.getLogger(__name__)


class MISCommandProcessor:
    """MIS特殊プロンプト統合処理システム"""
    
    def __init__(self, memory_bridge: Optional[MISMemoryBridge] = None):
        """
        初期化
        
        Args:
            memory_bridge: MIS記憶ブリッジ（省略時は自動作成）
        """
        self.prompt_handler = MISPromptHandler()
        self.memory_bridge = memory_bridge or MISMemoryBridge()
        self.processing_history: List[Dict[str, Any]] = []
        
        logger.info("MISCommandProcessor initialized")
    
    def process_conversation(self, conversation_text: str, project_id: str = None) -> Dict[str, Any]:
        """
        会話テキストからMIS特殊プロンプトを検出し、統合処理を実行
        
        Args:
            conversation_text: 会話テキスト
            project_id: プロジェクトID
            
        Returns:
            処理結果の詳細
        """
        try:
            # MIS特殊プロンプトを検出
            detected_prompts = self.prompt_handler.detect_mis_prompts(conversation_text)
            
            if not detected_prompts:
                return {
                    "status": "no_mis_prompts",
                    "message": "MIS特殊プロンプトが検出されませんでした",
                    "detected_prompts": 0,
                    "processed_prompts": 0
                }
            
            logger.info(f"Detected {len(detected_prompts)} MIS prompts")
            
            # 各プロンプトを処理
            processing_results = []
            for prompt_type, content in detected_prompts:
                result = self._process_single_prompt(prompt_type, content, project_id)
                processing_results.append(result)
            
            # 結果を統合
            return self._consolidate_results(processing_results, conversation_text)
            
        except Exception as e:
            logger.error(f"Error processing conversation: {e}")
            return {
                "status": "error",
                "message": f"処理中にエラーが発生しました: {e}",
                "error": str(e)
            }
    
    def _process_single_prompt(self, prompt_type: MISPromptType, content: str, project_id: str = None) -> Dict[str, Any]:
        """
        単一のMIS特殊プロンプトを処理
        
        Args:
            prompt_type: プロンプト種別
            content: プロンプト内容
            project_id: プロジェクトID
            
        Returns:
            処理結果
        """
        try:
            # プロンプトハンドラーで処理
            prompt_result = self.prompt_handler.process_prompt(prompt_type, content)
            
            # 記憶操作の実行
            memory_result = None
            if prompt_type == MISPromptType.MEMORY_SAVE:
                memory_result = self._execute_memory_save(content, project_id)
            elif prompt_type == MISPromptType.MEMORY_RECALL:
                memory_result = self._execute_memory_recall(content, project_id)
            
            # 結果を統合
            result = {
                "prompt_type": prompt_type.value,
                "content": content,
                "prompt_processing": asdict(prompt_result),
                "memory_operation": memory_result,
                "timestamp": datetime.now().isoformat(),
                "project_id": project_id
            }
            
            # 処理履歴に追加
            self.processing_history.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing single prompt: {e}")
            return {
                "prompt_type": prompt_type.value,
                "content": content,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "project_id": project_id
            }
    
    def _execute_memory_save(self, content: str, project_id: str = None) -> Dict[str, Any]:
        """
        記憶保存操作を実行
        
        Args:
            content: 保存内容
            project_id: プロジェクトID
            
        Returns:
            実行結果
        """
        try:
            # タグを自動抽出
            tags = self._extract_tags_from_content(content)
            
            # 記憶を保存
            memory_id = self.memory_bridge.save_memory(
                content=content,
                tags=tags,
                project_id=project_id,
                entry_type="mis_prompt_save"
            )
            
            return {
                "operation": "save",
                "success": True,
                "memory_id": memory_id,
                "tags": tags,
                "content_length": len(content)
            }
            
        except Exception as e:
            logger.error(f"Error executing memory save: {e}")
            return {
                "operation": "save",
                "success": False,
                "error": str(e)
            }
    
    def _execute_memory_recall(self, query: str, project_id: str = None) -> Dict[str, Any]:
        """
        記憶呼び出し操作を実行
        
        Args:
            query: 検索クエリ
            project_id: プロジェクトID
            
        Returns:
            実行結果
        """
        try:
            # 検索クエリを構築（エントリータイプ制限なしで幅広く検索）
            memory_query = MISMemoryQuery(
                query=query,
                max_results=10,
                project_id=project_id,
                entry_types=None  # 全てのエントリータイプを対象とする
            )
            
            # 記憶を検索
            memories = self.memory_bridge.recall_memory(memory_query)
            
            return {
                "operation": "recall",
                "success": True,
                "query": query,
                "results_count": len(memories),
                "memories": [
                    {
                        "id": memory.id,
                        "content": memory.content[:200] + "..." if len(memory.content) > 200 else memory.content,
                        "timestamp": memory.timestamp,
                        "tags": memory.tags,
                        "project_id": memory.project_id
                    }
                    for memory in memories
                ]
            }
            
        except Exception as e:
            logger.error(f"Error executing memory recall: {e}")
            return {
                "operation": "recall",
                "success": False,
                "error": str(e)
            }
    
    def _consolidate_results(self, processing_results: List[Dict[str, Any]], original_text: str) -> Dict[str, Any]:
        """
        処理結果を統合
        
        Args:
            processing_results: 個別処理結果のリスト
            original_text: 元の会話テキスト
            
        Returns:
            統合結果
        """
        successful_operations = [r for r in processing_results if not r.get("error")]
        failed_operations = [r for r in processing_results if r.get("error")]
        
        # Desktop向けアクションを抽出
        desktop_actions = []
        for result in successful_operations:
            prompt_result = result.get("prompt_processing", {})
            if prompt_result.get("desktop_action"):
                desktop_actions.append(prompt_result["desktop_action"])
        
        return {
            "status": "success" if not failed_operations else "partial_success",
            "message": f"処理完了: 成功 {len(successful_operations)}, 失敗 {len(failed_operations)}",
            "detected_prompts": len(processing_results),
            "processed_prompts": len(successful_operations),
            "failed_prompts": len(failed_operations),
            "processing_results": processing_results,
            "desktop_actions": desktop_actions,
            "original_text_length": len(original_text),
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_tags_from_content(self, content: str) -> List[str]:
        """
        コンテンツからタグを自動抽出
        
        Args:
            content: 分析対象コンテンツ
            
        Returns:
            抽出されたタグのリスト
        """
        tags = []
        content_lower = content.lower()
        
        # キーワードベースのタグ抽出
        tag_keywords = {
            "仕様": ["仕様", "要件", "requirements", "spec"],
            "実装": ["実装", "コード", "implementation", "code"],
            "バグ": ["バグ", "エラー", "bug", "error", "問題"],
            "設計": ["設計", "design", "architecture", "アーキテクチャ"],
            "テスト": ["テスト", "test", "testing", "検証"],
            "ドキュメント": ["ドキュメント", "document", "doc", "文書"],
            "学習": ["学習", "learning", "勉強", "理解"],
            "アイデア": ["アイデア", "idea", "提案", "suggestion"]
        }
        
        for tag, keywords in tag_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                tags.append(tag)
        
        # 長さベースのタグ
        if len(content) > 1000:
            tags.append("長文")
        elif len(content) < 100:
            tags.append("短文")
        
        return tags or ["general"]
    
    def get_processing_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        処理履歴を取得
        
        Args:
            limit: 取得件数制限
            
        Returns:
            処理履歴のリスト
        """
        return self.processing_history[-limit:]
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """
        記憶統計情報を取得
        
        Returns:
            統計情報
        """
        try:
            memory_stats = self.memory_bridge.get_memory_stats()
            
            # 処理履歴の統計を追加
            processing_stats = {
                "total_processed": len(self.processing_history),
                "successful_operations": len([h for h in self.processing_history if not h.get("error")]),
                "failed_operations": len([h for h in self.processing_history if h.get("error")])
            }
            
            # プロンプト種別の統計
            prompt_type_stats = {}
            for history in self.processing_history:
                prompt_type = history.get("prompt_type", "unknown")
                prompt_type_stats[prompt_type] = prompt_type_stats.get(prompt_type, 0) + 1
            
            return {
                "memory_stats": memory_stats,
                "processing_stats": processing_stats,
                "prompt_type_distribution": prompt_type_stats,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting memory statistics: {e}")
            return {"error": str(e)}
    
    def export_processing_history(self, output_path: Path, format: str = "json") -> bool:
        """
        処理履歴をエクスポート
        
        Args:
            output_path: 出力パス
            format: 出力形式（json, csv）
            
        Returns:
            エクスポート成功可否
        """
        try:
            if format == "json":
                # JSON serializable形式に変換（再帰的に処理）
                serializable_history = []
                for entry in self.processing_history:
                    serializable_entry = self._make_json_serializable(entry)
                    serializable_history.append(serializable_entry)
                
                data = {
                    "export_info": {
                        "timestamp": datetime.now().isoformat(),
                        "total_records": len(serializable_history),
                        "version": "1.0"
                    },
                    "processing_history": serializable_history
                }
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                return True
                
            elif format == "csv":
                import csv
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Timestamp', 'Prompt Type', 'Content', 'Project ID', 'Success', 'Error'])
                    
                    for record in self.processing_history:
                        prompt_type_value = record.get('prompt_type', '')
                        if hasattr(prompt_type_value, 'value'):
                            prompt_type_value = prompt_type_value.value
                        
                        content = record.get('content', '')
                        content_display = content[:100] + "..." if len(content) > 100 else content
                        
                        writer.writerow([
                            record.get('timestamp', ''),
                            prompt_type_value,
                            content_display,
                            record.get('project_id', ''),
                            'Yes' if not record.get('error') else 'No',
                            record.get('error', '')
                        ])
                
                return True
                
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
                
        except Exception as e:
            logger.error(f"Error exporting processing history: {e}")
            return False
    
    def _make_json_serializable(self, obj):
        """
        オブジェクトをJSON serializableに変換（再帰的）
        
        Args:
            obj: 変換対象オブジェクト
            
        Returns:
            JSON serializable オブジェクト
        """
        if hasattr(obj, 'value'):  # MISPromptType等のEnum
            return obj.value
        elif isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        else:
            return obj
    
    async def process_desktop_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Desktop向けアクションを処理（非同期）
        
        Args:
            action: 実行するアクション
            
        Returns:
            実行結果
        """
        try:
            action_type = action.get("type")
            payload = action.get("payload", {})
            
            if action_type == "memory_save":
                # Desktop側でのメモリ保存処理をシミュレート
                await asyncio.sleep(0.1)  # 非同期処理をシミュレート
                return {
                    "action_type": action_type,
                    "success": True,
                    "message": "Memory saved to Desktop session",
                    "payload": payload
                }
                
            elif action_type == "memory_recall":
                # Desktop側での記憶呼び出し処理をシミュレート
                await asyncio.sleep(0.2)  # 非同期処理をシミュレート
                return {
                    "action_type": action_type,
                    "success": True,
                    "message": "Memory recalled from Desktop session",
                    "payload": payload
                }
                
            elif action_type == "context_share":
                # Desktop側でのコンテキスト共有処理をシミュレート
                await asyncio.sleep(0.1)  # 非同期処理をシミュレート
                return {
                    "action_type": action_type,
                    "success": True,
                    "message": "Context shared with Desktop session",
                    "payload": payload
                }
                
            else:
                return {
                    "action_type": action_type,
                    "success": False,
                    "message": f"Unknown action type: {action_type}"
                }
                
        except Exception as e:
            logger.error(f"Error processing desktop action: {e}")
            return {
                "action_type": action.get("type", "unknown"),
                "success": False,
                "error": str(e)
            }