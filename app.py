from flask import Flask
from flask_wtf.csrf import CSRFProtect
import os
import logging
from logging.handlers import RotatingFileHandler

from extensions import db, login_manager, csrf


def setup_logging(app):
    """Configure logging for the application"""
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


def create_app(config_class=None):
    app = Flask(__name__)

    if config_class is None:
        from config import DevelopmentConfig
        config_object = DevelopmentConfig()
    elif isinstance(config_class, str):
        from config import get_config
        config_object = get_config(config_class)
    else:
        config_object = config_class()

    app.config.from_object(config_object)

    # Setup logging
    setup_logging(app)

    # Create uploads directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    csrf.init_app(app)

    # Register blueprints
    from routes import main_bp
    app.register_blueprint(main_bp)

    # Create database tables
    with app.app_context():
        db.create_all()
        # Create default tech support account (development only)
        if app.config.get('DEBUG'):
            from models import User
            if not User.query.filter_by(username='tech_support').first():
                tech_support = User(username='tech_support', email='tech@example.com', role='tech_support')
                # Generate a secure random password
                import secrets
                default_password = secrets.token_urlsafe(16)
                tech_support.set_password(default_password)
                db.session.add(tech_support)
                db.session.commit()
                app.logger.info(f'Default tech_support account created with password: {default_password}')
                app.logger.warning('Please change the password immediately after first login!')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
