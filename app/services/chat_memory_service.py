"""
Chat Memory Service for SupportPilot

Handles window management, compression queue, and batch compression.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import threading

from ..extensions import db
from ..models.chat_memory import ChatMemory
from ..models.conversation import Conversation
from ..config import get_config

logger = logging.getLogger(__name__)


class ChatMemoryService:
    """
    Service for managing chat memory with window and compression support.

    Features:
    - Sliding window: retains most recent N records in full text
    - Pending compression queue: marks old records for batch compression
    - Batch compression: compresses multiple records at once to save tokens
    """

    def __init__(self):
        self.config = get_config()
        self.window_size = getattr(self.config, 'CHAT_MEMORY_WINDOW_SIZE', 5)
        self.idle_threshold_seconds = getattr(self.config, 'CHAT_MEMORY_IDLE_THRESHOLD_SECONDS', 30)
        self.compression_batch_size = getattr(self.config, 'CHAT_MEMORY_COMPRESSION_BATCH_SIZE', 5)

    def get_window(self, session_id: int, limit: int = None) -> List[ChatMemory]:
        """
        Get the most recent chat records within the window.

        Args:
            session_id: Conversation session ID
            limit: Optional override for window size

        Returns:
            List of ChatMemory records within the window (ordered by created_at desc)
        """
        if limit is None:
            limit = self.window_size

        return ChatMemory.query.filter_by(
            session_id=session_id,
            status='active'
        ).order_by(ChatMemory.created_at.desc()).limit(limit).all()

    def add_record(self, session_id: int, sender_type: str, content: str) -> ChatMemory:
        """
        Add a new chat record to the session.

        If the window is full, marks the oldest record for compression.

        Args:
            session_id: Conversation session ID
            sender_type: Type of sender ('user', 'ai', 'tech_support')
            content: Message content

        Returns:
            The newly created ChatMemory record
        """
        # Create new record
        new_record = ChatMemory(
            session_id=session_id,
            sender_type=sender_type,
            content=content,
            status='active'
        )
        db.session.add(new_record)
        db.session.flush()  # Get the ID

        # Check if we need to mark oldest record for compression
        self._check_and_mark_for_compression(session_id)

        db.session.commit()
        logger.info(f'Added chat memory record {new_record.id} for session {session_id}')

        return new_record

    def _check_and_mark_for_compression(self, session_id: int):
        """
        Check if window is full and mark oldest record for compression.

        Args:
            session_id: Conversation session ID
        """
        # Count active records in this session
        active_count = ChatMemory.query.filter_by(
            session_id=session_id,
            status='active'
        ).count()

        # If we exceed window size, mark the oldest as pending_compression
        if active_count > self.window_size:
            oldest = ChatMemory.query.filter_by(
                session_id=session_id,
                status='active'
            ).order_by(ChatMemory.created_at.asc()).first()

            if oldest:
                oldest.mark_for_compression()
                logger.info(f'Marked record {oldest.id} for compression (session {session_id})')

    def get_pending_compression(self, session_id: int) -> List[ChatMemory]:
        """
        Get records pending compression for a session.

        Args:
            session_id: Conversation session ID

        Returns:
            List of ChatMemory records with status='pending_compression'
        """
        return ChatMemory.query.filter_by(
            session_id=session_id,
            status='pending_compression'
        ).order_by(ChatMemory.created_at.asc()).all()

    def mark_for_compression(self, record_id: int):
        """
        Mark a specific record for compression.

        Args:
            record_id: ChatMemory record ID
        """
        record = ChatMemory.query.get(record_id)
        if record and record.status == 'active':
            record.mark_for_compression()
            db.session.commit()
            logger.info(f'Marked record {record_id} for compression')

    def compress_batch(self, session_id: int, batch_size: int = None) -> Dict:
        """
        Compress a batch of pending records for a session.

        Args:
            session_id: Conversation session ID
            batch_size: Number of records to compress (default: compression_batch_size)

        Returns:
            Dict with compression result:
            {
                'success': bool,
                'compressed_count': int,
                'batch_id': str,
                'summaries': list of summaries generated
            }
        """
        if batch_size is None:
            batch_size = self.compression_batch_size

        # Get pending records
        pending = self.get_pending_compression(session_id)
        if not pending:
            return {'success': True, 'compressed_count': 0, 'batch_id': None, 'summaries': []}

        # Limit batch size
        records_to_compress = pending[:batch_size]
        batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{session_id}"
        summaries = []

        # Generate summary for the batch (combine all records)
        combined_text = "\n\n".join([r.content for r in records_to_compress])
        summary = self._generate_summary(combined_text)

        # Mark all records as compressed with the summary
        for record in records_to_compress:
            record.mark_compressed(summary=summary, batch_id=batch_id)

        db.session.commit()

        logger.info(f'Compressed {len(records_to_compress)} records for session {session_id} (batch_id: {batch_id})')

        return {
            'success': True,
            'compressed_count': len(records_to_compress),
            'batch_id': batch_id,
            'summaries': summaries
        }

    def _generate_summary(self, text: str) -> str:
        """
        Generate a summary of the given text.

        Args:
            text: Text to summarize

        Returns:
            Summarized text (target: 10:1 compression ratio)
        """
        # TODO: Integrate with LLM API for actual summarization
        # For now, return a simple truncation as placeholder
        max_summary_length = len(text) // 10
        if len(text) <= max_summary_length:
            return text

        # Simple truncation with ellipsis (placeholder)
        return text[:max_summary_length] + "..."

    def get_session_summaries(self, session_id: int, start_date: datetime = None, end_date: datetime = None) -> List[ChatMemory]:
        """
        Get compressed summaries for a session.

        Args:
            session_id: Conversation session ID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of ChatMemory records with status='compressed'
        """
        query = ChatMemory.query.filter_by(
            session_id=session_id,
            status='compressed'
        )

        if start_date:
            query = query.filter(ChatMemory.created_at >= start_date)
        if end_date:
            query = query.filter(ChatMemory.created_at <= end_date)

        return query.order_by(ChatMemory.compressed_at.asc()).all()

    def get_full_context(self, session_id: int) -> Dict:
        """
        Get full context for a session (window + summaries).

        Args:
            session_id: Conversation session ID

        Returns:
            Dict with:
            {
                'window_records': List[ChatMemory],
                'summaries': List[str],
                'total_records': int
            }
        """
        window_records = self.get_window(session_id)
        summaries = self.get_session_summaries(session_id)

        return {
            'window_records': window_records,
            'summaries': [s.summary for s in summaries if s.summary],
            'total_records': len(window_records) + len(summaries)
        }

    def schedule_compression_if_idle(self, session_id: int, delay: int = None):
        """
        Schedule compression for a session if it becomes idle.

        Args:
            session_id: Conversation session ID
            delay: Delay in seconds before triggering compression (default: idle_threshold_seconds)
        """
        if delay is None:
            delay = self.idle_threshold_seconds

        def trigger_if_idle():
            import time
            time.sleep(delay)

            # Check if session is still idle (no new records added)
            pending = self.get_pending_compression(session_id)
            if pending:
                # Check if no new active records were added
                active_count = ChatMemory.query.filter_by(
                    session_id=session_id,
                    status='active'
                ).count()

                if active_count <= self.window_size:
                    # Session is idle, trigger compression
                    logger.info(f'Scheduled compression triggered for session {session_id}')
                    self.compress_batch(session_id)

        # Run in background thread
        thread = threading.Thread(target=trigger_if_idle, daemon=True)
        thread.start()


# Global instance
chat_memory_service = ChatMemoryService()
