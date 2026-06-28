"""RAG retrieval log and user feedback models for quality dashboard."""
from datetime import datetime, timezone
from ..extensions import db


class RagRetrievalLog(db.Model):
    __tablename__ = 'rag_retrieval_logs'

    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.Text, nullable=False)
    result_count = db.Column(db.Integer, default=0)
    top1_similarity = db.Column(db.Float, nullable=True)
    duration_ms = db.Column(db.Float, nullable=True)
    route_type = db.Column(db.String(20), default='simple')
    results_json = db.Column(db.Text, nullable=True)  # JSON string of full retrieval results
    # JSON string of full pipeline trace (node events, decisions)
    trace_json = db.Column(db.Text, nullable=True)
    sub_query_count = db.Column(db.Integer, default=0)
    retry_count = db.Column(db.Integer, default=0)
    faithfulness_score = db.Column(db.Float, nullable=True)
    # JSON: {"relevance":4,"completeness":3,"noise":2}
    judge_score = db.Column(db.Text, nullable=True)
    # LLM judge explanation
    judge_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    feedbacks = db.relationship('UserFeedback', backref='log', lazy='dynamic')


class UserFeedback(db.Model):
    __tablename__ = 'user_feedback'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'positive' or 'negative'
    retrieval_log_id = db.Column(db.Integer, db.ForeignKey('rag_retrieval_logs.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'message_id', name='uq_user_message_feedback'),
    )
