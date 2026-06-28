"""
RAG Semantic Cache model.

Stores query-answer pairs keyed by embedding vector for semantic
similarity lookup. Avoids redundant LLM calls for semantically
similar queries.
"""
from datetime import datetime

from app.extensions import db


class RagSemanticCache(db.Model):
    """Semantic cache for RAG query-answer pairs."""

    __tablename__ = 'rag_semantic_cache'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    query = db.Column(db.Text, nullable=False, comment='原始查询文本')
    query_embedding = db.Column(
        db.Text, nullable=False,
        comment='查询 embedding (JSON float array)',
    )
    answer = db.Column(db.Text, nullable=True, comment='缓存答案')
    results_json = db.Column(db.Text, nullable=True, comment='检索结果 JSON')
    metadata_json = db.Column(db.Text, nullable=True, comment='元数据 JSON')
    hit_count = db.Column(
        db.Integer, default=0,
        comment='命中次数（统计用）',
    )
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow,
        comment='创建时间',
    )
    last_hit_at = db.Column(
        db.DateTime, nullable=True,
        comment='最后命中时间',
    )
    expires_at = db.Column(
        db.DateTime, nullable=False,
        comment='过期时间',
    )

    @classmethod
    def cleanup_expired(cls):
        """Remove expired cache entries."""
        cls.query.filter(cls.expires_at < datetime.utcnow()).delete()
        db.session.commit()

    @classmethod
    def enforce_max_entries(cls, max_entries: int):
        """Remove oldest entries if cache exceeds max_entries."""
        count = cls.query.count()
        if count > max_entries:
            over = count - max_entries
            oldest = (
                cls.query
                .order_by(cls.created_at.asc())
                .limit(over)
                .all()
            )
            for entry in oldest:
                db.session.delete(entry)
            db.session.commit()

    @classmethod
    def get_all_valid(cls):
        """Get all non-expired cache entries."""
        return cls.query.filter(cls.expires_at >= datetime.utcnow()).all()

    def record_hit(self):
        """Record a cache hit for statistics."""
        self.hit_count += 1
        self.last_hit_at = datetime.utcnow()
        db.session.commit()
