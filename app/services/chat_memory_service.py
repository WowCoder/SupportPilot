"""
Chat Memory Service for SupportPilot

Handles window management, compression queue, and batch compression.
"""
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import threading
import queue
import json
import os

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
        self.compression_batch_size = getattr(self.config, 'CHAT_MEMORY_COMPRESSION_BATCH_SIZE', 5)
        self.idle_threshold_seconds = getattr(self.config, 'CHAT_MEMORY_IDLE_THRESHOLD_SECONDS', 30)
        self.max_delay_seconds = getattr(self.config, 'CHAT_MEMORY_COMPRESSION_MAX_DELAY_SECONDS', 120)
        self.compression_queue_max = getattr(self.config, 'CHAT_MEMORY_COMPRESSION_QUEUE_MAX', 10)

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


class CompressionQueue:
    """
    Queue manager for compression tasks with persistence and recovery.

    Features:
    - Persistent queue storage in SQLite
    - Recovery on service restart
    - Idle-triggered compression
    - Max-delay fallback compression
    """

    def __init__(self, persist_path: str = "./compression_queue"):
        self.persist_path = persist_path
        self.db_path = os.path.join(persist_path, "compression_queue.db")
        self._lock = threading.Lock()
        self._scheduler_thread = None
        self._stop_scheduler = threading.Event()
        self._init_store()
        self._start_scheduler()

    def _init_store(self):
        """Initialize SQLite storage for queue persistence"""
        import sqlite3

        os.makedirs(self.persist_path, exist_ok=True)

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create queue table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS compression_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    record_id INTEGER NOT NULL,
                    marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE,
                    processed_at TIMESTAMP
                )
            """)

            # Create index for session lookup
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id
                ON compression_queue(session_id, processed)
            """)

            conn.commit()
            conn.close()

        logger.info(f'CompressionQueue initialized at {self.db_path}')

    def enqueue(self, session_id: int, record_id: int):
        """
        Add a record to the compression queue.

        Args:
            session_id: Conversation session ID
            record_id: ChatMemory record ID
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO compression_queue (session_id, record_id)
                VALUES (?, ?)
            """, (session_id, record_id))

            conn.commit()
            conn.close()

        logger.debug(f'Enqueued record {record_id} for session {session_id}')

    def dequeue_session(self, session_id: int) -> List[int]:
        """
        Get all unprocessed record IDs for a session.

        Args:
            session_id: Conversation session ID

        Returns:
            List of record IDs pending compression
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT record_id FROM compression_queue
                WHERE session_id = ? AND processed = FALSE
                ORDER BY marked_at ASC
            """, (session_id,))

            record_ids = [row[0] for row in cursor.fetchall()]
            conn.close()

        return record_ids

    def mark_processed(self, record_id: int):
        """
        Mark a record as processed.

        Args:
            record_id: ChatMemory record ID
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE compression_queue
                SET processed = TRUE, processed_at = CURRENT_TIMESTAMP
                WHERE record_id = ?
            """, (record_id,))

            conn.commit()
            conn.close()

    def get_queue_stats(self) -> Dict:
        """
        Get queue statistics.

        Returns:
            Dict with queue stats:
            {
                'total_pending': int,
                'sessions_pending': int,
                'oldest_pending': datetime
            }
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM compression_queue WHERE processed = FALSE")
            total_pending = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(DISTINCT session_id) FROM compression_queue
                WHERE processed = FALSE
            """)
            sessions_pending = cursor.fetchone()[0]

            cursor.execute("""
                SELECT MIN(marked_at) FROM compression_queue
                WHERE processed = FALSE
            """)
            oldest = cursor.fetchone()[0]

            conn.close()

        return {
            'total_pending': total_pending,
            'sessions_pending': sessions_pending,
            'oldest_pending': oldest
        }

    def recover(self, chat_memory_service: ChatMemoryService):
        """
        Recover queue state on service restart.

        Syncs queue with database records that are in pending_compression status.

        Args:
            chat_memory_service: ChatMemoryService instance
        """
        logger.info('Recovering compression queue state...')

        # Find all records in pending_compression status
        pending_records = ChatMemory.query.filter_by(status='pending_compression').all()

        for record in pending_records:
            self.enqueue(record.session_id, record.id)

        logger.info(f'Recovered {len(pending_records)} pending compression records')

    def _start_scheduler(self):
        """Start the background scheduler thread"""
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        logger.info('CompressionQueue scheduler started')

    def _scheduler_loop(self):
        """
        Background scheduler loop.

        Checks every 10 seconds for:
        - Sessions with queue >= batch_size
        - Sessions idle for > idle_threshold
        - Records pending for > max_delay
        """
        from ..services.chat_memory_service import chat_memory_service

        check_interval = 10  # seconds

        while not self._stop_scheduler.is_set():
            try:
                self._check_and_trigger_compression(chat_memory_service)
            except Exception as e:
                logger.error(f'Error in compression scheduler: {e}', exc_info=True)

            self._stop_scheduler.wait(check_interval)

    def _check_and_trigger_compression(self, service: ChatMemoryService):
        """
        Check and trigger compression for eligible sessions.

        Args:
            service: ChatMemoryService instance
        """
        stats = self.get_queue_stats()

        # Get all sessions with pending records
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT session_id, COUNT(*) as cnt, MIN(marked_at) as oldest
                FROM compression_queue
                WHERE processed = FALSE
                GROUP BY session_id
            """)

            sessions = cursor.fetchall()
            conn.close()

        for session_id, count, oldest_marked_at in sessions:
            should_compress = False

            # Check batch size threshold
            if count >= service.compression_batch_size:
                logger.info(f'Triggering compression for session {session_id}: batch size reached ({count})')
                should_compress = True

            # Check idle threshold
            elif self._is_session_idle(session_id, service.idle_threshold_seconds):
                logger.info(f'Triggering compression for session {session_id}: idle threshold reached')
                should_compress = True

            # Check max delay (兜底机制)
            elif self._exceeds_max_delay(oldest_marked_at, service.max_delay_seconds):
                logger.info(f'Triggering compression for session {session_id}: max delay reached')
                should_compress = True

            if should_compress:
                # Trigger compression
                result = service.compress_batch(session_id)
                if result['success']:
                    # Mark records as processed in queue
                    record_ids = self.dequeue_session(session_id)
                    for record_id in record_ids[:service.compression_batch_size]:
                        self.mark_processed(record_id)

    def _is_session_idle(self, session_id: int, idle_threshold: int) -> bool:
        """
        Check if a session has been idle for longer than threshold.

        Args:
            session_id: Conversation session ID
            idle_threshold: Idle threshold in seconds

        Returns:
            True if session is idle beyond threshold
        """
        last_message = ChatMemory.query.filter_by(session_id=session_id).order_by(
            ChatMemory.created_at.desc()
        ).first()

        if not last_message:
            return False

        idle_time = (datetime.utcnow() - last_message.created_at).total_seconds()
        return idle_time > idle_threshold

    def _exceeds_max_delay(self, oldest_marked_at: str, max_delay: int) -> bool:
        """
        Check if oldest pending record exceeds max delay.

        Args:
            oldest_marked_at: Timestamp of oldest pending record
            max_delay: Maximum delay in seconds

        Returns:
            True if max delay exceeded
        """
        if not oldest_marked_at:
            return False

        marked_time = datetime.strptime(oldest_marked_at, '%Y-%m-%d %H:%M:%S.%f') if '.' in oldest_marked_at else datetime.strptime(oldest_marked_at, '%Y-%m-%d %H:%M:%S')
        elapsed = (datetime.utcnow() - marked_time).total_seconds()
        return elapsed > max_delay

    def stop(self):
        """Stop the scheduler thread"""
        self._stop_scheduler.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info('CompressionQueue scheduler stopped')
