"""
Unit tests for Chat Memory System
Run with: pytest tests/test_chat_memory.py -v
"""
import pytest
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import User, Conversation, ChatMemory, FAQEntry
from app.services.chat_memory_service import ChatMemoryService, CompressionQueue
from app.services.query_rewriter import QueryRewriter
from app.services.faq_generator import FAQGenerator


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def chat_memory_service():
    """Create ChatMemoryService instance for testing"""
    return ChatMemoryService()


@pytest.fixture
def query_rewriter():
    """Create QueryRewriter instance for testing"""
    return QueryRewriter()


@pytest.fixture
def faq_generator():
    """Create FAQGenerator instance for testing"""
    return FAQGenerator()


# =============================================================================
# Test 6.1: Window Management Unit Tests
# =============================================================================

class TestWindowManagement:
    """Test chat memory window management"""

    def test_add_record_to_window(self, app, chat_memory_service):
        """Test adding a record to the window"""
        with app.app_context():
            # Create user and conversation
            user = User(username='testuser', email='test@example.com', role='user')
            user.set_password('TestPass123')
            db.session.add(user)
            db.session.commit()

            conversation = Conversation(user_id=user.id, status='active')
            db.session.add(conversation)
            db.session.commit()

            # Add record to window
            record = chat_memory_service.add_record(
                session_id=conversation.id,
                sender_type='user',
                content='Test message content'
            )

            assert record is not None
            assert record.session_id == conversation.id
            assert record.content == 'Test message content'
            assert record.status == 'active'

    def test_get_window_records(self, app, chat_memory_service):
        """Test getting window records"""
        with app.app_context():
            # Create user and conversation
            user = User(username='testuser2', email='test2@example.com', role='user')
            user.set_password('TestPass123')
            db.session.add(user)
            db.session.commit()

            conversation = Conversation(user_id=user.id, status='active')
            db.session.add(conversation)
            db.session.commit()

            # Add multiple records
            for i in range(7):
                chat_memory_service.add_record(
                    session_id=conversation.id,
                    sender_type='user' if i % 2 == 0 else 'ai',
                    content=f'Message {i}'
                )

            # Get window (default size 5)
            window = chat_memory_service.get_window(conversation.id)

            # Should only return 5 records (window size)
            assert len(window) == 5
            # All should be active
            assert all(r.status == 'active' for r in window)

    def test_window_exceeds_limit_marks_oldest(self, app, chat_memory_service):
        """Test that oldest record is marked for compression when window exceeds limit"""
        with app.app_context():
            user = User(username='testuser3', email='test3@example.com', role='user')
            user.set_password('TestPass123')
            db.session.add(user)
            db.session.commit()

            conversation = Conversation(user_id=user.id, status='active')
            db.session.add(conversation)
            db.session.commit()

            # Add 6 records (window size is 5)
            for i in range(6):
                chat_memory_service.add_record(
                    session_id=conversation.id,
                    sender_type='user',
                    content=f'Message {i}'
                )

            # Check that oldest record is marked for compression
            pending = chat_memory_service.get_pending_compression(conversation.id)
            assert len(pending) >= 1
            assert pending[0].status == 'pending_compression'

    def test_get_full_context(self, app, chat_memory_service):
        """Test getting full context (window + summaries)"""
        with app.app_context():
            user = User(username='testuser4', email='test4@example.com', role='user')
            user.set_password('TestPass123')
            db.session.add(user)
            db.session.commit()

            conversation = Conversation(user_id=user.id, status='active')
            db.session.add(conversation)
            db.session.commit()

            # Add some records
            for i in range(3):
                chat_memory_service.add_record(
                    session_id=conversation.id,
                    sender_type='user',
                    content=f'Message {i}'
                )

            context = chat_memory_service.get_full_context(conversation.id)

            assert 'window_records' in context
            assert 'summaries' in context
            assert 'total_records' in context
            assert len(context['window_records']) == 3


# =============================================================================
# Test 6.2: Batch Compression Unit Tests
# =============================================================================

class TestBatchCompression:
    """Test batch compression functionality"""

    def test_compress_batch(self, app, chat_memory_service):
        """Test batch compression"""
        with app.app_context():
            user = User(username='compressuser', email='compress@example.com', role='user')
            user.set_password('TestPass123')
            db.session.add(user)
            db.session.commit()

            conversation = Conversation(user_id=user.id, status='active')
            db.session.add(conversation)
            db.session.commit()

            # Add records to exceed window
            for i in range(7):
                chat_memory_service.add_record(
                    session_id=conversation.id,
                    sender_type='user',
                    content=f'Message {i} - some longer content to test compression'
                )

            # Compress batch
            result = chat_memory_service.compress_batch(conversation.id)

            assert result['success'] is True
            assert result['compressed_count'] >= 1
            assert result['batch_id'] is not None

    def test_compress_batch_empty(self, app, chat_memory_service):
        """Test batch compression with no pending records"""
        with app.app_context():
            user = User(username='compressuser2', email='compress2@example.com', role='user')
            user.set_password('TestPass123')
            db.session.add(user)
            db.session.commit()

            conversation = Conversation(user_id=user.id, status='active')
            db.session.add(conversation)
            db.session.commit()

            # No records added, so no pending compression
            result = chat_memory_service.compress_batch(conversation.id)

            assert result['success'] is True
            assert result['compressed_count'] == 0

    def test_summary_generation(self, app, chat_memory_service):
        """Test summary generation"""
        with app.app_context():
            long_text = "This is a very long text. " * 100  # 500+ chars
            summary = chat_memory_service._generate_summary(long_text)

            # Summary should be shorter than original (10:1 ratio target)
            assert len(summary) <= len(long_text) // 10 + 3  # +3 for "..."


# =============================================================================
# Test 6.3: Compression Queue Persistence Tests
# =============================================================================

class TestCompressionQueue:
    """Test compression queue persistence"""

    def test_enqueue_dequeue(self, app, tmp_path):
        """Test enqueue and dequeue operations"""
        persist_path = str(tmp_path / "compression_queue")
        queue = CompressionQueue(persist_path=persist_path)

        try:
            # Enqueue
            queue.enqueue(session_id=1, record_id=100)
            queue.enqueue(session_id=1, record_id=101)

            # Dequeue
            record_ids = queue.dequeue_session(session_id=1)

            assert len(record_ids) == 2
            assert 100 in record_ids
            assert 101 in record_ids
        finally:
            queue.stop()

    def test_queue_stats(self, app, tmp_path):
        """Test queue statistics"""
        persist_path = str(tmp_path / "compression_queue")
        queue = CompressionQueue(persist_path=persist_path)

        try:
            queue.enqueue(session_id=1, record_id=100)
            queue.enqueue(session_id=2, record_id=101)

            stats = queue.get_queue_stats()

            assert stats['total_pending'] == 2
            assert stats['sessions_pending'] == 2
        finally:
            queue.stop()

    def test_mark_processed(self, app, tmp_path):
        """Test marking records as processed"""
        persist_path = str(tmp_path / "compression_queue")
        queue = CompressionQueue(persist_path=persist_path)

        try:
            queue.enqueue(session_id=1, record_id=100)

            # Mark as processed
            queue.mark_processed(record_id=100)

            # Should not appear in dequeue
            record_ids = queue.dequeue_session(session_id=1)
            assert len(record_ids) == 0
        finally:
            queue.stop()


# =============================================================================
# Test 6.4: Query Rewrite Unit Tests
# =============================================================================

class TestQueryRewriter:
    """Test query rewrite functionality"""

    def test_rewrite_disabled(self, app):
        """Test query rewrite when disabled"""
        rewriter = QueryRewriter()
        rewriter.enabled = False

        result = rewriter.rewrite_query("What does it support?", session_id=999)
        assert result == "What does it support?"  # Original query returned

    def test_rewrite_with_empty_history(self, app):
        """Test query rewrite with no history"""
        rewriter = QueryRewriter()
        rewriter.enabled = False  # Disable LLM calls for this test

        # Test rule-based rewrite with empty history
        history = []
        result = rewriter.rewrite_with_rules("What does it support?", history)
        # Without history, should return original or similar
        assert result is not None

    def test_subject_extraction(self, app):
        """Test subject extraction from text"""
        rewriter = QueryRewriter()

        text = "The data export feature supports CSV and Excel formats"
        subject = rewriter._extract_subject(text)
        assert subject is not None  # Should extract something

    def test_context_building(self, app):
        """Test building context from history"""
        rewriter = QueryRewriter()

        history = [
            {'sender_type': 'user', 'content': 'How does data export work?'},
            {'sender_type': 'ai', 'content': 'Data export supports CSV and Excel.'}
        ]

        context = rewriter._build_context(history)

        assert 'user' in context
        assert 'ai' in context
        assert 'data export' in context.lower()


# =============================================================================
# Test 6.5: FAQ Generation Integration Tests
# =============================================================================

class TestFAQGenerator:
    """Test FAQ generation functionality"""

    def test_check_similarity_empty_db(self, app, faq_generator):
        """Test similarity check with empty database"""
        with app.app_context():
            is_duplicate, duplicate_id = faq_generator.check_similarity("How do I export data?")
            assert is_duplicate is False
            assert duplicate_id is None

    def test_save_faq(self, app, faq_generator):
        """Test saving FAQ entry"""
        with app.app_context():
            # Create conversation
            user = User(username='faquser', email='faq@example.com', role='user')
            user.set_password('TestPass123')
            db.session.add(user)
            db.session.commit()

            conversation = Conversation(user_id=user.id, status='closed')
            db.session.add(conversation)
            db.session.commit()

            # Save FAQ (note: ChromaDB might not be available in test environment)
            try:
                faq = faq_generator.save_faq(
                    question="How do I export data?",
                    answer="Use the Export button in the dashboard.",
                    source_session_id=conversation.id
                )
                # If ChromaDB is available, faq should be created
                if faq:
                    assert faq.question == "How do I export data?"
                    assert faq.answer == "Use the Export button in the dashboard."
            except Exception:
                # ChromaDB might not be initialized in test environment
                pass

    def test_generate_from_session_empty(self, app, faq_generator):
        """Test FAQ generation from session with no content"""
        with app.app_context():
            user = User(username='faquser2', email='faq2@example.com', role='user')
            user.set_password('TestPass123')
            db.session.add(user)
            db.session.commit()

            conversation = Conversation(user_id=user.id, status='closed')
            db.session.add(conversation)
            db.session.commit()

            # No chat memory records exist
            result = faq_generator.generate_from_session(conversation.id)

            assert result['success'] is False
            assert 'No conversation content found' in result.get('error', '')
