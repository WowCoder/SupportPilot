"""
Application configuration module
"""
import os
import secrets
import logging
from dotenv import load_dotenv
from typing import Any, Dict, Optional

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration with common settings"""

    # Application
    SECRET_KEY: Optional[str] = None
    TESTING: bool = False
    DEBUG: bool = False
    HOST: str = '127.0.0.1'
    PORT: int = 5005

    # Database
    SQLALCHEMY_DATABASE_URI: str = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Qwen API
    QWEN_API_KEY: Optional[str] = None

    # File upload
    UPLOAD_FOLDER: str = 'uploads'
    ALLOWED_EXTENSIONS: set = {'txt', 'pdf', 'doc', 'docx'}
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB

    # CSRF protection
    WTF_CSRF_ENABLED: bool = True

    # Session security
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'

    # Logging
    LOG_LEVEL: int = logging.INFO

    # Chat Memory System
    CHAT_MEMORY_WINDOW_SIZE: int = 5
    CHAT_MEMORY_COMPRESSION_BATCH_SIZE: int = 5
    CHAT_MEMORY_IDLE_THRESHOLD_SECONDS: int = 30
    CHAT_MEMORY_COMPRESSION_MAX_DELAY_SECONDS: int = 120  # 2 minutes fallback
    CHAT_MEMORY_COMPRESSION_QUEUE_MAX: int = 10
    CHAT_MEMORY_QUERY_REWRITE_ENABLED: bool = True
    CHAT_MEMORY_QUERY_REWRITE_TIMEOUT_SECONDS: int = 5

    # FAQ
    FAQ_SIMILARITY_THRESHOLD: float = 0.9
    SUMMARY_COMPRESSION_RATIO_TARGET: int = 10

    # Human Handoff
    HANDOFF_ROUND_THRESHOLD: int = 3  # Show handoff button after 3 rounds


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

    def __init__(self):
        self.SECRET_KEY = os.environ.get('SECRET_KEY')
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY environment variable must be set in production")

        self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
        self.QWEN_API_KEY = os.environ.get('QWEN_API_KEY')
        if not self.QWEN_API_KEY:
            raise ValueError("QWEN_API_KEY environment variable must be set in production")

        # Production security settings
        self.SESSION_COOKIE_SECURE = True
        self.LOG_LEVEL = logging.INFO


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

    def __init__(self):
        self.SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
        self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
        self.QWEN_API_KEY = os.environ.get('QWEN_API_KEY')
        if not self.QWEN_API_KEY:
            raise ValueError("QWEN_API_KEY environment variable must be set")


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = False

    def __init__(self):
        self.SECRET_KEY = 'test-secret-key-for-testing'
        self.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        self.QWEN_API_KEY = 'test-api-key'
        self.UPLOAD_FOLDER = 'test_uploads'
        self.WTF_CSRF_ENABLED = False  # Disable CSRF for testing


# Configuration registry
config: Dict[str, Any] = {
    'production': ProductionConfig,
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str = 'default') -> Config:
    """Get configuration class by name"""
    config_class = config.get(config_name, DevelopmentConfig)
    return config_class()
