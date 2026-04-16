"""
Parent Document Store for Small-to-Big Retrieval

Stores large chunks (parent documents) for retrieval context.
Uses SQLite for lightweight, reliable persistence.
"""
import sqlite3
import os
import json
import logging
import threading

logger = logging.getLogger(__name__)


class ParentDocumentStore:
    """存储父文档（大块），支持 key-value 查询

    用于 Small-to-Big 检索策略：
    - 小块索引到向量库（高精度检索）
    - 大块存储到 ParentDocumentStore（完整上下文）
    - 检索时：小块匹配 → 查映射表 → 返回大块
    """

    _lock = threading.Lock()

    def __init__(self, persist_path: str = "./parent_store"):
        """初始化父文档存储

        Args:
            persist_path: 存储路径，SQLite 数据库文件位置
        """
        self.store_path = persist_path
        self.db_path = os.path.join(persist_path, "parent_docs.db")
        self._init_store()

    def _init_store(self):
        """初始化 SQLite 数据库"""
        # 确保目录存在
        os.makedirs(self.store_path, exist_ok=True)

        with ParentDocumentStore._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 创建表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parent_documents (
                    doc_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引以加速 source 查询
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_source
                ON parent_documents(json_extract(metadata, '$.source'))
            """)

            conn.commit()
            conn.close()

        logger.info(f'ParentDocumentStore initialized at {self.db_path}')

    def put(self, doc_id: str, content: str, metadata: dict = None):
        """存储父文档

        Args:
            doc_id: 文档唯一标识
            content: 文档内容
            metadata: 元数据（如 source, page 等）
        """
        with ParentDocumentStore._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            metadata_json = json.dumps(metadata or {})

            cursor.execute("""
                INSERT OR REPLACE INTO parent_documents (doc_id, content, metadata)
                VALUES (?, ?, ?)
            """, (doc_id, content, metadata_json))

            conn.commit()
            conn.close()

        logger.debug(f'Stored parent document: {doc_id}')

    def get(self, doc_id: str) -> dict:
        """获取父文档

        Args:
            doc_id: 文档唯一标识

        Returns:
            dict: {'content': str, 'metadata': dict} 或 None
        """
        with ParentDocumentStore._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT content, metadata FROM parent_documents WHERE doc_id = ?
            """, (doc_id,))

            row = cursor.fetchone()
            conn.close()

        if row:
            return {
                'content': row[0],
                'metadata': json.loads(row[1]) if row[1] else {}
            }
        return None

    def delete(self, doc_id: str):
        """删除单个父文档

        Args:
            doc_id: 文档唯一标识
        """
        with ParentDocumentStore._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM parent_documents WHERE doc_id = ?", (doc_id,))

            conn.commit()
            conn.close()

        logger.debug(f'Deleted parent document: {doc_id}')

    def delete_by_source(self, source: str):
        """删除指定来源的所有父文档

        Args:
            source: 文档来源文件名
        """
        with ParentDocumentStore._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 使用 JSON 提取查询
            cursor.execute("""
                DELETE FROM parent_documents
                WHERE json_extract(metadata, '$.source') = ?
            """, (source,))

            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

        logger.info(f'Deleted {deleted_count} parent documents from source: {source}')
        return deleted_count

    def get_all_ids(self) -> list:
        """获取所有父文档 ID

        Returns:
            list: 所有 doc_id 列表
        """
        with ParentDocumentStore._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT doc_id FROM parent_documents")
            ids = [row[0] for row in cursor.fetchall()]
            conn.close()

        return ids

    def count(self) -> int:
        """获取父文档总数

        Returns:
            int: 文档总数
        """
        with ParentDocumentStore._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM parent_documents")
            count = cursor.fetchone()[0]
            conn.close()

        return count

    def clear(self):
        """清空所有父文档"""
        with ParentDocumentStore._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM parent_documents")
            conn.commit()
            conn.close()

        logger.info('Cleared all parent documents')


# 全局实例
parent_store = ParentDocumentStore()