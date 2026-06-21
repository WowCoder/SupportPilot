"""
SupportPilot Application Factory

This module creates and configures the Flask application instance.
Pure API server — all page rendering is handled by the Vue SPA frontend.
"""
from flask import Flask
import os
import logging
from logging.handlers import RotatingFileHandler

from flask_cors import CORS

from .extensions import db


def setup_logging(app: Flask) -> None:
    """
    Configure logging for the application

    Args:
        app: Flask application instance
    """
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # File handler with rotation
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    console_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application startup')


def create_app(config_class=None) -> Flask:
    """
    Application factory for creating Flask app instance

    Args:
        config_class: Configuration class or config name string

    Returns:
        Configured Flask application instance (API-only)
    """
    app = Flask(__name__)

    # Load configuration
    if config_class is None:
        from .config import DevelopmentConfig
        config_object = DevelopmentConfig()
    elif isinstance(config_class, str):
        from .config import get_config
        config_object = get_config(config_class)
    else:
        config_object = config_class()

    app.config.from_object(config_object)

    # Setup CORS for SPA frontend
    if app.config.get('DEBUG'):
        # Development: allow Vue dev server
        CORS(app, resources={
            r"/api/*": {
                "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
                "allow_headers": ["Authorization", "Content-Type"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            }
        })
    else:
        # Production: same-origin (frontend served by same Nginx)
        CORS(app)

    # Setup logging
    setup_logging(app)

    # Create uploads directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize database
    db.init_app(app)

    # Register API blueprints (JWT-based, no CSRF needed)
    from .api.routes import api_bp
    from .api.chat import chat_memory_bp
    from .api.tickets import ticket_bp
    from .api.faq import faq_bp
    from .api.rag_dashboard import rag_dash_bp
    from .api.auth import auth_bp as auth_api_bp
    from .api.v1.chat import chat_v1_bp
    from .api.v1.faq import faq_v1_bp
    from .api.v1.documents import doc_v1_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(chat_memory_bp)
    app.register_blueprint(ticket_bp)
    app.register_blueprint(faq_bp)
    app.register_blueprint(rag_dash_bp)
    app.register_blueprint(auth_api_bp)
    app.register_blueprint(chat_v1_bp)
    app.register_blueprint(faq_v1_bp)
    app.register_blueprint(doc_v1_bp)

    # Create database tables
    with app.app_context():
        db.create_all()

        # Create default tech support account (development only)
        if app.config.get('DEBUG'):
            from .models import User

            tech_user = User.query.filter_by(username='tech_support').first()
            if tech_user:
                tech_user.set_password('tech123')
                db.session.commit()
                app.logger.info('tech_support password reset to default')
            else:
                tech_support = User(
                    username='tech_support',
                    email='tech@example.com',
                    role='tech_support'
                )
                tech_support.set_password('tech123')
                db.session.add(tech_support)
                db.session.commit()
                app.logger.info('Default tech_support account created with password: tech123')

    return app
