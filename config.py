import os
import secrets
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class ProductionConfig:
    """Production configuration"""
    TESTING = False
    DEBUG = False

    def __init__(self):
        self.SECRET_KEY = os.environ.get('SECRET_KEY')
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY environment variable must be set in production")

        self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False

        self.QWEN_API_KEY = os.environ.get('QWEN_API_KEY')
        if not self.QWEN_API_KEY:
            raise ValueError("QWEN_API_KEY environment variable must be set in production")

        self.UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
        self.ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
        self.MAX_CONTENT_LENGTH = 16 * 1024 * 1024

        # Security
        self.WTF_CSRF_ENABLED = True
        self.SESSION_COOKIE_SECURE = True
        self.SESSION_COOKIE_HTTPONLY = True
        self.SESSION_COOKIE_SAMESITE = 'Lax'

        # Logging
        self.LOG_LEVEL = logging.INFO


class DevelopmentConfig:
    """Development configuration"""
    TESTING = False
    DEBUG = True

    def __init__(self):
        self.SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
        self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False

        self.QWEN_API_KEY = os.environ.get('QWEN_API_KEY')
        if not self.QWEN_API_KEY:
            raise ValueError("QWEN_API_KEY environment variable must be set")

        self.UPLOAD_FOLDER = 'uploads'
        self.ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
        self.MAX_CONTENT_LENGTH = 16 * 1024 * 1024

        # CSRF protection
        self.WTF_CSRF_ENABLED = True


class TestingConfig:
    """Testing configuration"""
    TESTING = True
    DEBUG = False

    def __init__(self):
        self.SECRET_KEY = 'test-secret-key-for-testing'
        self.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.QWEN_API_KEY = 'test-api-key'

        self.UPLOAD_FOLDER = 'test_uploads'
        self.ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
        self.MAX_CONTENT_LENGTH = 16 * 1024 * 1024

        # Disable CSRF for testing
        self.WTF_CSRF_ENABLED = False


def get_config(config_name='default'):
    """Get configuration class by name"""
    config_map = {
        'production': ProductionConfig,
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'default': DevelopmentConfig
    }
    config_class = config_map.get(config_name, DevelopmentConfig)
    return config_class()


config = {
    'production': ProductionConfig,
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
