"""
Unit tests for SupportPilot application
Run with: pytest tests/test_app.py -v
"""
import pytest
from app import create_app, db
from models import User, Conversation, Message


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
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


class TestConfig:
    """Test configuration class"""

    def test_secret_key_required(self):
        """Test that SECRET_KEY is required for production"""
        import os
        # Save original value
        original = os.environ.get('SECRET_KEY')
        os.environ.pop('SECRET_KEY', None)

        try:
            with pytest.raises(ValueError):
                create_app('production')
        finally:
            # Restore original value
            if original:
                os.environ['SECRET_KEY'] = original

    def test_testing_config_loaded(self, app):
        """Test that testing config is loaded correctly"""
        assert app.config['TESTING'] is True
        assert app.config['WTF_CSRF_ENABLED'] is False


class TestPasswordValidation:
    """Test password strength validation"""

    def test_weak_password_too_short(self):
        """Test password that is too short"""
        is_valid, message = User.validate_password_strength('Abc1')
        assert is_valid is False
        assert 'at least 8 characters' in message

    def test_weak_password_no_uppercase(self):
        """Test password without uppercase"""
        is_valid, message = User.validate_password_strength('lowercase123')
        assert is_valid is False
        assert 'uppercase' in message

    def test_weak_password_no_lowercase(self):
        """Test password without lowercase"""
        is_valid, message = User.validate_password_strength('UPPERCASE123')
        assert is_valid is False
        assert 'lowercase' in message

    def test_weak_password_no_number(self):
        """Test password without number"""
        is_valid, message = User.validate_password_strength('NoNumbersHere')
        assert is_valid is False
        assert 'number' in message

    def test_strong_password(self):
        """Test strong password"""
        is_valid, message = User.validate_password_strength('StrongPass123')
        assert is_valid is True
        assert 'strong enough' in message.lower()


class TestInputSanitization:
    """Test input sanitization"""

    def test_sanitize_xss_script(self):
        """Test XSS script tag sanitization"""
        from utils import sanitize_input
        result = sanitize_input('<script>alert("xss")</script>')
        assert '<script>' not in result

    def test_sanitize_html_escape(self):
        """Test HTML escaping"""
        from utils import sanitize_input
        result = sanitize_input('<div>test</div>')
        assert '&lt;' in result
        assert '<div>' not in result

    def test_sanitize_empty_input(self):
        """Test empty input sanitization"""
        from utils import sanitize_input
        result = sanitize_input('')
        assert result == ''

    def test_sanitize_none_input(self):
        """Test None input sanitization"""
        from utils import sanitize_input
        result = sanitize_input(None)
        assert result == ''

    def test_sanitize_long_input(self):
        """Test long input truncation"""
        from utils import sanitize_input
        long_input = 'a' * 15000
        result = sanitize_input(long_input)
        assert len(result) <= 10000


class TestModels:
    """Test database models"""

    def test_user_creation(self, app):
        """Test user creation"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com', role='user')
            user.set_password('TestPass123')
            db.session.add(user)
            db.session.commit()

            # Verify user was created
            saved_user = User.query.filter_by(username='testuser').first()
            assert saved_user is not None
            assert saved_user.email == 'test@example.com'
            assert saved_user.check_password('TestPass123')
            assert saved_user.check_password('wrongpassword') is False

    def test_conversation_creation(self, app):
        """Test conversation creation"""
        with app.app_context():
            user = User(username='convouser', email='convo@example.com', role='user')
            user.set_password('TestPass123')
            db.session.add(user)
            db.session.commit()

            conversation = Conversation(user_id=user.id, status='active')
            db.session.add(conversation)
            db.session.commit()

            saved_conversation = Conversation.query.first()
            assert saved_conversation is not None
            assert saved_conversation.status == 'active'
            assert saved_conversation.user_id == user.id

    def test_message_creation(self, app):
        """Test message creation"""
        with app.app_context():
            user = User(username='msguser', email='msg@example.com', role='user')
            user.set_password('TestPass123')
            db.session.add(user)
            db.session.commit()

            conversation = Conversation(user_id=user.id, status='active')
            db.session.add(conversation)
            db.session.commit()

            message = Message(
                conversation_id=conversation.id,
                sender_type='user',
                content='Test message content'
            )
            db.session.add(message)
            db.session.commit()

            saved_message = Message.query.first()
            assert saved_message is not None
            assert saved_message.content == 'Test message content'
            assert saved_message.sender_type == 'user'
