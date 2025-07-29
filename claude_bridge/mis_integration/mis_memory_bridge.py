"""
Claude Bridge System - MIS Memory Bridge
MIS記憶システムとClaude Desktopの橋渡し
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MISMemoryEntry:
    """MIS記憶エントリー"""
    id: str
    content: str
    metadata: Dict[str, Any]
    timestamp: str
    tags: List[str]
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    entry_type: str = "general"
    

@dataclass
class MISMemoryQuery:
    """MIS記憶検索クエリ"""
    query: str
    max_results: int = 10
    tags: Optional[List[str]] = None
    project_id: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    entry_types: Optional[List[str]] = None


class MISMemoryBridge:
    """MIS記憶システムブリッジ"""
    
    def __init__(self, memory_file: Optional[Path] = None):
        """
        初期化
        
        Args:
            memory_file: 記憶ファイルのパス（省略時はデフォルト）
        """
        self.memory_file = memory_file or Path("bridge_data/mis_memory.json")
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 記憶データをロード
        self.memories: Dict[str, MISMemoryEntry] = {}
        self._load_memories()
        
        logger.info(f"MISMemoryBridge initialized with {len(self.memories)} memories")
    
    def save_memory(
        self, 
        content: str, 
        tags: List[str] = None, 
        project_id: str = None,
        session_id: str = None,
        entry_type: str = "general",
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        記憶を保存
        
        Args:
            content: 記憶する内容
            tags: タグリスト
            project_id: プロジェクトID
            session_id: セッションID
            entry_type: エントリータイプ
            metadata: 追加メタデータ
            
        Returns:
            記憶ID
        """
        try:
            # 記憶IDを生成
            memory_id = self._generate_memory_id()
            
            # 記憶エントリーを作成
            memory_entry = MISMemoryEntry(
                id=memory_id,
                content=content,
                metadata=metadata or {},
                timestamp=datetime.now().isoformat(),
                tags=tags or [],
                project_id=project_id,
                session_id=session_id,
                entry_type=entry_type
            )
            
            # 記憶を保存
            self.memories[memory_id] = memory_entry
            self._save_memories()
            
            logger.info(f"Memory saved: {memory_id} ({len(content)} chars)")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            raise
    
    def recall_memory(self, query: MISMemoryQuery) -> List[MISMemoryEntry]:
        """
        記憶を検索・呼び出し
        
        Args:
            query: 検索クエリ
            
        Returns:
            マッチした記憶エントリーのリスト
        """
        try:
            results = []
            query_lower = query.query.lower()
            
            for memory in self.memories.values():
                # コンテンツマッチング（より柔軟に）
                content_match = self._content_matches(query_lower, memory.content.lower())
                
                # タグマッチング
                tag_match = True
                if query.tags:
                    tag_match = any(tag in memory.tags for tag in query.tags)
                
                # プロジェクトマッチング
                project_match = True
                if query.project_id:
                    project_match = memory.project_id == query.project_id
                
                # 日付範囲マッチング
                date_match = True
                if query.date_from or query.date_to:
                    memory_date = datetime.fromisoformat(memory.timestamp)
                    if query.date_from:
                        date_match = memory_date >= datetime.fromisoformat(query.date_from)
                    if query.date_to and date_match:
                        date_match = memory_date <= datetime.fromisoformat(query.date_to)
                
                # エントリータイプマッチング
                type_match = True
                if query.entry_types:
                    type_match = memory.entry_type in query.entry_types
                
                # 全条件マッチング
                if content_match and tag_match and project_match and date_match and type_match:
                    results.append(memory)
            
            # 結果を時系列でソート（新しい順）
            results.sort(key=lambda x: x.timestamp, reverse=True)
            
            # 最大結果数で制限
            results = results[:query.max_results]
            
            logger.info(f"Memory recall: {len(results)} results for query '{query.query}'")
            return results
            
        except Exception as e:
            logger.error(f"Failed to recall memory: {e}")
            return []
    
    def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """
        記憶を更新
        
        Args:
            memory_id: 記憶ID
            updates: 更新内容
            
        Returns:
            更新成功可否
        """
        try:
            if memory_id not in self.memories:
                logger.warning(f"Memory not found: {memory_id}")
                return False
            
            memory = self.memories[memory_id]
            
            # 更新可能なフィールドのみ更新
            if "content" in updates:
                memory.content = updates["content"]
            if "tags" in updates:
                memory.tags = updates["tags"]
            if "metadata" in updates:
                memory.metadata.update(updates["metadata"])
            if "entry_type" in updates:
                memory.entry_type = updates["entry_type"]
            
            # 更新時刻を記録
            memory.metadata["last_updated"] = datetime.now().isoformat()
            
            self._save_memories()
            logger.info(f"Memory updated: {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            return False
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        記憶を削除
        
        Args:
            memory_id: 記憶ID
            
        Returns:
            削除成功可否
        """
        try:
            if memory_id not in self.memories:
                logger.warning(f"Memory not found: {memory_id}")
                return False
            
            del self.memories[memory_id]
            self._save_memories()
            
            logger.info(f"Memory deleted: {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        記憶統計情報を取得
        
        Returns:
            統計情報
        """
        try:
            total_memories = len(self.memories)
            
            # エントリータイプ別の統計
            type_stats = {}
            tag_stats = {}
            project_stats = {}
            
            for memory in self.memories.values():
                # タイプ別
                entry_type = memory.entry_type
                type_stats[entry_type] = type_stats.get(entry_type, 0) + 1
                
                # タグ別
                for tag in memory.tags:
                    tag_stats[tag] = tag_stats.get(tag, 0) + 1
                
                # プロジェクト別
                if memory.project_id:
                    project_stats[memory.project_id] = project_stats.get(memory.project_id, 0) + 1
            
            # 最新・最古の記憶
            timestamps = [memory.timestamp for memory in self.memories.values()]
            latest_memory = max(timestamps) if timestamps else None
            oldest_memory = min(timestamps) if timestamps else None
            
            return {
                "total_memories": total_memories,
                "type_distribution": type_stats,
                "tag_distribution": tag_stats,
                "project_distribution": project_stats,
                "latest_memory": latest_memory,
                "oldest_memory": oldest_memory,
                "memory_file_size": self.memory_file.stat().st_size if self.memory_file.exists() else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {}
    
    def export_memories(self, output_path: Path, format: str = "json") -> bool:
        """
        記憶をエクスポート
        
        Args:
            output_path: 出力パス
            format: 出力形式（json, csv, markdown）
            
        Returns:
            エクスポート成功可否
        """
        try:
            if format == "json":
                return self._export_json(output_path)
            elif format == "csv":
                return self._export_csv(output_path)
            elif format == "markdown":
                return self._export_markdown(output_path)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to export memories: {e}")
            return False
    
    def import_memories(self, input_path: Path, format: str = "json") -> int:
        """
        記憶をインポート
        
        Args:
            input_path: 入力パス
            format: 入力形式
            
        Returns:
            インポートした記憶数
        """
        try:
            if format == "json":
                return self._import_json(input_path)
            else:
                logger.error(f"Unsupported import format: {format}")
                return 0
                
        except Exception as e:
            logger.error(f"Failed to import memories: {e}")
            return 0
    
    def _load_memories(self) -> None:
        """記憶データをファイルからロード"""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for memory_data in data.get("memories", []):
                    memory = MISMemoryEntry(**memory_data)
                    self.memories[memory.id] = memory
                    
                logger.info(f"Loaded {len(self.memories)} memories from {self.memory_file}")
            else:
                logger.info("No existing memory file found, starting fresh")
                
        except Exception as e:
            logger.error(f"Failed to load memories: {e}")
            self.memories = {}
    
    def _save_memories(self) -> None:
        """記憶データをファイルに保存"""
        try:
            data = {
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "total_memories": len(self.memories),
                "memories": [asdict(memory) for memory in self.memories.values()]
            }
            
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"Saved {len(self.memories)} memories to {self.memory_file}")
            
        except Exception as e:
            logger.error(f"Failed to save memories: {e}")
    
    def _content_matches(self, query: str, content: str) -> bool:
        """
        コンテンツマッチングをより柔軟に行う
        
        Args:
            query: 検索クエリ（小文字）
            content: 記憶内容（小文字）
            
        Returns:
            マッチするかどうか
        """
        # 完全一致チェック
        if query in content:
            return True
        
        # 単語レベルでのマッチング
        query_words = query.split()
        for word in query_words:
            if len(word) > 1 and word in content:  # 1文字以上の単語のみ
                return True
        
        # キーワードの部分マッチング（3文字以上）
        for i in range(len(query) - 2):
            substring = query[i:i+3]
            if substring in content:
                return True
        
        return False
    
    def _generate_memory_id(self) -> str:
        """記憶IDを生成"""
        import uuid
        return f"mis_mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def _export_json(self, output_path: Path) -> bool:
        """JSON形式でエクスポート"""
        data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "total_memories": len(self.memories),
                "version": "1.0"
            },
            "memories": [asdict(memory) for memory in self.memories.values()]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    
    def _export_csv(self, output_path: Path) -> bool:
        """CSV形式でエクスポート"""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Content', 'Tags', 'Project', 'Type', 'Timestamp'])
            
            for memory in self.memories.values():
                writer.writerow([
                    memory.id,
                    memory.content[:100] + "..." if len(memory.content) > 100 else memory.content,
                    ",".join(memory.tags),
                    memory.project_id or "",
                    memory.entry_type,
                    memory.timestamp
                ])
        
        return True
    
    def _export_markdown(self, output_path: Path) -> bool:
        """Markdown形式でエクスポート"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# MIS Memory Export\n\n")
            f.write(f"Export Date: {datetime.now().isoformat()}\n")
            f.write(f"Total Memories: {len(self.memories)}\n\n")
            
            for memory in self.memories.values():
                f.write(f"## {memory.id}\n\n")
                f.write(f"**Type**: {memory.entry_type}\n")
                f.write(f"**Timestamp**: {memory.timestamp}\n")
                if memory.project_id:
                    f.write(f"**Project**: {memory.project_id}\n")
                if memory.tags:
                    f.write(f"**Tags**: {', '.join(memory.tags)}\n")
                f.write("\n")
                f.write(memory.content)
                f.write("\n\n---\n\n")
        
        return True
    
    def _import_json(self, input_path: Path) -> int:
        """JSON形式からインポート"""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        imported_count = 0
        for memory_data in data.get("memories", []):
            try:
                memory = MISMemoryEntry(**memory_data)
                # 重複チェック
                if memory.id not in self.memories:
                    self.memories[memory.id] = memory
                    imported_count += 1
            except Exception as e:
                logger.warning(f"Failed to import memory: {e}")
        
        if imported_count > 0:
            self._save_memories()
        
        return imported_count