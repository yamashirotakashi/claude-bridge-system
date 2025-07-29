"""
Claude Bridge System - Task Generator
会話分析とタスク生成機能
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from .project_context_loader import ProjectContextLoader
from .project_registry import ProjectRegistry
from .bridge_filesystem import BridgeFileSystem
from ..exceptions import TaskGenerationError, ValidationError

logger = logging.getLogger(__name__)


class TaskGenerator:
    """タスク生成クラス
    
    Claude Desktopでの会話内容を分析し、Claude Code向けの
    実行可能なタスクファイルを自動生成する。
    """
    
    def __init__(self, 
                 context_loader: Optional[ProjectContextLoader] = None,
                 bridge_fs: Optional[BridgeFileSystem] = None):
        """
        初期化
        
        Args:
            context_loader: プロジェクトコンテキストローダー
            bridge_fs: ブリッジファイルシステム
        """
        self.context_loader = context_loader if context_loader else ProjectContextLoader()
        self.bridge_fs = bridge_fs if bridge_fs else BridgeFileSystem()
        
        # タスク生成ルールの初期化
        self._init_task_patterns()
        
        logger.info("TaskGenerator initialized")
    
    def _init_task_patterns(self) -> None:
        """タスク生成パターンの初期化"""
        self.task_patterns = {
            # 実装系タスク
            "implementation": {
                "patterns": [
                    r"(.+)を実装",
                    r"(.+)機能を追加",
                    r"(.+)を作成",
                    r"(.+)を開発",
                    r"(.+)システムを構築"
                ],
                "priority": "high",
                "type": "implementation"
            },
            
            # 修正系タスク
            "fix": {
                "patterns": [
                    r"(.+)を修正",
                    r"(.+)バグを直",
                    r"(.+)エラーを解決",
                    r"(.+)問題を修正",
                    r"(.+)を改修"
                ],
                "priority": "high",
                "type": "bugfix"
            },
            
            # 改善系タスク
            "improvement": {
                "patterns": [
                    r"(.+)を改善",
                    r"(.+)を最適化",
                    r"(.+)を強化",
                    r"(.+)を向上",
                    r"(.+)のパフォーマンスを"
                ],
                "priority": "medium",
                "type": "improvement"
            },
            
            # 分析系タスク
            "analysis": {
                "patterns": [
                    r"(.+)を分析",
                    r"(.+)を調査",
                    r"(.+)を検証",
                    r"(.+)をチェック",
                    r"(.+)を確認"
                ],
                "priority": "low",
                "type": "analysis"
            },
            
            # リファクタリング系
            "refactor": {
                "patterns": [
                    r"(.+)をリファクタリング",
                    r"(.+)を整理",
                    r"(.+)を再構築",
                    r"(.+)を統一",
                    r"(.+)を再設計"
                ],
                "priority": "medium",
                "type": "refactor"
            }
        }
    
    def analyze_conversation(self, conversation_content: str, 
                           context_projects: Optional[List[str]] = None) -> Dict:
        """
        会話内容を分析してタスク生成可能性を評価
        
        Args:
            conversation_content: 会話の内容
            context_projects: コンテキストに含むプロジェクト
            
        Returns:
            分析結果の辞書
        """
        analysis = {
            "status": "success",
            "detected_projects": [],
            "task_candidates": [],
            "action_items": [],
            "complexity_score": 0,
            "confidence": 0.0,
            "recommendations": [],
            "error": None
        }
        
        try:
            # プロジェクト検出
            detected_projects = self.context_loader.detect_project_shortcuts(conversation_content)
            analysis["detected_projects"] = detected_projects
            
            # タスク候補の抽出
            task_candidates = self._extract_task_candidates(conversation_content)
            analysis["task_candidates"] = task_candidates
            
            # アクションアイテムの特定
            action_items = self._identify_action_items(conversation_content, detected_projects)
            analysis["action_items"] = action_items
            
            # 複雑度スコアの計算
            complexity_score = self._calculate_complexity(conversation_content, task_candidates)
            analysis["complexity_score"] = complexity_score
            
            # 信頼度の計算
            confidence = self._calculate_confidence(task_candidates, detected_projects)
            analysis["confidence"] = confidence
            
            # 推奨事項の生成
            recommendations = self._generate_recommendations(
                task_candidates, detected_projects, complexity_score
            )
            analysis["recommendations"] = recommendations
            
            logger.info(f"Conversation analysis completed: {len(task_candidates)} candidates found")
            
        except Exception as e:
            analysis["status"] = "error"
            analysis["error"] = str(e)
            logger.error(f"Conversation analysis failed: {e}")
        
        return analysis
    
    def _extract_task_candidates(self, content: str) -> List[Dict]:
        """会話からタスク候補を抽出"""
        candidates = []
        
        for category, config in self.task_patterns.items():
            for pattern in config["patterns"]:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                
                for match in matches:
                    candidate = {
                        "category": category,
                        "type": config["type"],
                        "priority": config["priority"],
                        "description": match.group(0),
                        "extracted_content": match.group(1) if match.groups() else match.group(0),
                        "position": match.span(),
                        "confidence": self._calculate_pattern_confidence(match.group(0))
                    }
                    candidates.append(candidate)
        
        # 重複除去と信頼度順ソート
        unique_candidates = self._deduplicate_candidates(candidates)
        return sorted(unique_candidates, key=lambda x: x["confidence"], reverse=True)
    
    def _calculate_pattern_confidence(self, matched_text: str) -> float:
        """パターンマッチの信頼度を計算"""
        base_confidence = 0.7
        
        # 具体的なキーワードがある場合は信頼度向上
        technical_keywords = [
            "API", "データベース", "認証", "テスト", "UI", "バックエンド", 
            "フロントエンド", "セキュリティ", "パフォーマンス", "ログ"
        ]
        
        keyword_bonus = sum(0.05 for keyword in technical_keywords 
                           if keyword.lower() in matched_text.lower())
        
        # 長さによる調整
        length_factor = min(len(matched_text) / 50, 1.0) * 0.1
        
        return min(base_confidence + keyword_bonus + length_factor, 1.0)
    
    def _deduplicate_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """タスク候補の重複を除去"""
        seen_descriptions = set()
        unique_candidates = []
        
        for candidate in candidates:
            desc_key = candidate["extracted_content"].lower().strip()
            if desc_key not in seen_descriptions:
                seen_descriptions.add(desc_key)
                unique_candidates.append(candidate)
        
        return unique_candidates
    
    def _identify_action_items(self, content: str, projects: List[str]) -> List[Dict]:
        """具体的なアクションアイテムを特定"""
        action_patterns = [
            r"(?:する|やる|実行|対応)(?:必要|べき)",
            r"(?:作成|実装|修正|改善)(?:して|を)",
            r"(?:確認|チェック|検証)(?:して|を)",
            r"(?:対応|処理|実行)(?:すべき|が必要)"
        ]
        
        action_items = []
        sentences = content.split('。')
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            for pattern in action_patterns:
                if re.search(pattern, sentence):
                    # プロジェクト関連性をチェック
                    related_project = None
                    for project in projects:
                        if f"[{project}]" in sentence or project in sentence:
                            related_project = project
                            break
                    
                    action_item = {
                        "description": sentence,
                        "related_project": related_project,
                        "urgency": self._assess_urgency(sentence),
                        "actionable": self._assess_actionability(sentence)
                    }
                    action_items.append(action_item)
                    break
        
        return action_items
    
    def _assess_urgency(self, text: str) -> str:
        """文の緊急度を評価"""
        high_urgency_keywords = ["緊急", "至急", "すぐに", "即座に", "重要", "クリティカル"]
        medium_urgency_keywords = ["早めに", "優先", "必要", "すべき"]
        
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in high_urgency_keywords):
            return "high"
        elif any(keyword in text_lower for keyword in medium_urgency_keywords):
            return "medium"
        else:
            return "low"
    
    def _assess_actionability(self, text: str) -> float:
        """文の実行可能性を評価（0.0-1.0）"""
        actionable_indicators = [
            "実装", "作成", "修正", "追加", "削除", "更新", "設定", "構築"
        ]
        vague_indicators = [
            "検討", "考える", "思う", "かもしれない", "だろう", "可能性"
        ]
        
        text_lower = text.lower()
        
        actionable_score = sum(0.2 for indicator in actionable_indicators 
                              if indicator in text_lower)
        vague_penalty = sum(0.15 for indicator in vague_indicators 
                           if indicator in text_lower)
        
        return max(0.0, min(1.0, 0.5 + actionable_score - vague_penalty))
    
    def _calculate_complexity(self, content: str, candidates: List[Dict]) -> int:
        """タスクの複雑度を計算（1-10スケール）"""
        base_complexity = len(candidates)
        
        # 複雑度を上げる要因
        complexity_indicators = [
            ("複数のファイル", 2),
            ("データベース", 2),
            ("API", 1),
            ("テスト", 1),
            ("リファクタリング", 3),
            ("統合", 2),
            ("セキュリティ", 2),
            ("パフォーマンス", 2)
        ]
        
        content_lower = content.lower()
        complexity_boost = sum(weight for keyword, weight in complexity_indicators 
                              if keyword.lower() in content_lower)
        
        return min(10, max(1, base_complexity + complexity_boost))
    
    def _calculate_confidence(self, candidates: List[Dict], projects: List[str]) -> float:
        """タスク生成の全体的信頼度を計算"""
        if not candidates:
            return 0.0
        
        # 候補の平均信頼度
        avg_candidate_confidence = sum(c["confidence"] for c in candidates) / len(candidates)
        
        # プロジェクト検出による信頼度向上
        project_bonus = min(len(projects) * 0.1, 0.3)
        
        # 高信頼度候補の存在による向上
        high_conf_bonus = 0.1 if any(c["confidence"] > 0.8 for c in candidates) else 0.0
        
        return min(1.0, avg_candidate_confidence + project_bonus + high_conf_bonus)
    
    def _generate_recommendations(self, candidates: List[Dict], 
                                projects: List[str], complexity: int) -> List[str]:
        """推奨事項を生成"""
        recommendations = []
        
        if not candidates:
            recommendations.append("明確なタスクが検出されませんでした。より具体的な指示を含めることをお勧めします。")
            return recommendations
        
        if not projects:
            recommendations.append("プロジェクトショートカット([project]形式)を使用すると、より正確なタスク生成が可能です。")
        
        if complexity > 7:
            recommendations.append("複雑度が高いタスクです。段階的な実装を検討することをお勧めします。")
        
        high_priority_count = sum(1 for c in candidates if c["priority"] == "high")
        if high_priority_count > 3:
            recommendations.append(f"{high_priority_count}個の高優先度タスクが検出されました。優先順位の調整を検討してください。")
        
        implementation_count = sum(1 for c in candidates if c["type"] == "implementation")
        if implementation_count > 0:
            recommendations.append(f"{implementation_count}個の実装タスクが検出されました。事前のテスト設計を推奨します。")
        
        return recommendations
    
    def generate_task_file(self, conversation_content: str, 
                          project_ids: Optional[List[str]] = None,
                          task_metadata: Optional[Dict] = None) -> Path:
        """
        会話内容からタスクファイルを生成
        
        Args:
            conversation_content: 会話内容
            project_ids: 対象プロジェクト
            task_metadata: 追加メタデータ
            
        Returns:
            生成されたタスクファイルのパス
            
        Raises:
            TaskGenerationError: タスク生成に失敗した場合
        """
        try:
            # 会話分析
            analysis = self.analyze_conversation(conversation_content, project_ids)
            
            if analysis["status"] == "error":
                raise TaskGenerationError(f"Conversation analysis failed: {analysis['error']}")
            
            # プロジェクトコンテキストの読み込み
            project_contexts = {}
            detected_projects = analysis["detected_projects"]
            
            for project_id in detected_projects:
                try:
                    context = self.context_loader.load_project_context(project_id)
                    project_contexts[project_id] = context
                except Exception as e:
                    logger.warning(f"Failed to load context for project {project_id}: {e}")
            
            # タスクファイル内容の生成
            task_content = self._generate_task_markdown(
                conversation_content, analysis, project_contexts, task_metadata
            )
            
            # ファイル保存
            primary_project = detected_projects[0] if detected_projects else "general"
            task_file = self.bridge_fs.save_task_file(
                task_content, primary_project, "auto_generated"
            )
            
            logger.info(f"Task file generated: {task_file}")
            return task_file
            
        except Exception as e:
            error_msg = f"Task generation failed: {str(e)}"
            logger.error(error_msg)
            raise TaskGenerationError(error_msg, str(e))
    
    def _generate_task_markdown(self, conversation: str, analysis: Dict,
                               contexts: Dict, metadata: Optional[Dict]) -> str:
        """タスクファイルのMarkdown内容を生成"""
        
        # ヘッダー情報
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        projects_str = ", ".join(analysis["detected_projects"]) if analysis["detected_projects"] else "N/A"
        
        content_parts = [
            "# Claude Bridge Auto-Generated Task",
            "",
            f"**Generated At**: {timestamp}",
            f"**Target Projects**: {projects_str}",
            f"**Complexity Score**: {analysis['complexity_score']}/10",
            f"**Confidence**: {analysis['confidence']:.2f}",
            "",
            "## 📋 Original Conversation",
            "",
            "```",
            conversation.strip(),
            "```",
            "",
            "## 🎯 Detected Task Candidates",
            ""
        ]
        
        # タスク候補の一覧
        for i, candidate in enumerate(analysis["task_candidates"], 1):
            content_parts.extend([
                f"### {i}. {candidate['description']}",
                f"- **Type**: {candidate['type']}",
                f"- **Priority**: {candidate['priority']}",
                f"- **Confidence**: {candidate['confidence']:.2f}",
                f"- **Category**: {candidate['category']}",
                ""
            ])
        
        # アクションアイテム
        if analysis["action_items"]:
            content_parts.extend([
                "## ⚡ Action Items",
                ""
            ])
            
            for i, item in enumerate(analysis["action_items"], 1):
                content_parts.extend([
                    f"### {i}. {item['description']}",
                    f"- **Related Project**: {item['related_project'] or 'N/A'}",
                    f"- **Urgency**: {item['urgency']}",
                    f"- **Actionability**: {item['actionable']:.2f}",
                    ""
                ])
        
        # プロジェクトコンテキスト
        if contexts:
            content_parts.extend([
                "## 📁 Project Context",
                ""
            ])
            
            for project_id, context in contexts.items():
                basic_info = context.get("basic_info", {})
                content_parts.extend([
                    f"### {basic_info.get('name', project_id)}",
                    f"- **Shortcut**: {basic_info.get('shortcut', 'N/A')}",
                    f"- **Description**: {basic_info.get('description', 'N/A')}",
                    f"- **Tech Stack**: {', '.join(basic_info.get('tech_stack', []))}",
                    f"- **Path**: {basic_info.get('path', 'N/A')}",
                    ""
                ])
        
        # 推奨事項
        if analysis["recommendations"]:
            content_parts.extend([
                "## 💡 Recommendations",
                ""
            ])
            
            for i, rec in enumerate(analysis["recommendations"], 1):
                content_parts.append(f"{i}. {rec}")
            
            content_parts.append("")
        
        # メタデータ
        if metadata:
            content_parts.extend([
                "## 📊 Metadata",
                "",
                "```json",
                json.dumps(metadata, ensure_ascii=False, indent=2),
                "```",
                ""
            ])
        
        # フッター
        content_parts.extend([
            "---",
            "",
            "*Generated by Claude Bridge System TaskGenerator*",
            f"*Analysis ID: {datetime.now().strftime('%Y%m%d_%H%M%S')}*"
        ])
        
        return "\n".join(content_parts)
    
    def batch_generate_tasks(self, conversations: List[Dict]) -> List[Dict]:
        """
        複数の会話からバッチでタスクを生成
        
        Args:
            conversations: 会話データのリスト
            
        Returns:
            生成結果のリスト
        """
        results = []
        
        for i, conv_data in enumerate(conversations):
            try:
                result = {
                    "index": i,
                    "status": "success",
                    "conversation_id": conv_data.get("id"),
                    "task_file": None,
                    "analysis": None,
                    "error": None
                }
                
                # タスク生成
                task_file = self.generate_task_file(
                    conv_data["content"],
                    conv_data.get("projects"),
                    conv_data.get("metadata")
                )
                
                result["task_file"] = str(task_file)
                result["analysis"] = self.analyze_conversation(
                    conv_data["content"], 
                    conv_data.get("projects")
                )
                
            except Exception as e:
                result = {
                    "index": i,
                    "status": "error",
                    "conversation_id": conv_data.get("id"),
                    "task_file": None,
                    "analysis": None,
                    "error": str(e)
                }
                logger.error(f"Batch task generation failed for conversation {i}: {e}")
            
            results.append(result)
        
        logger.info(f"Batch task generation completed: {len(results)} conversations processed")
        return results
    
    def get_generation_stats(self) -> Dict:
        """タスク生成統計情報を取得"""
        try:
            # ブリッジファイルシステムの統計
            fs_stats = self.bridge_fs.get_system_stats()
            
            # キャッシュ統計
            cache_stats = self.context_loader.get_cache_stats()
            
            stats = {
                "filesystem": fs_stats,
                "cache": cache_stats,
                "task_patterns": len(self.task_patterns),
                "last_updated": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get generation stats: {e}")
            return {"error": str(e)}