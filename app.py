from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_class=None):
    app = Flask(__name__)

    if config_class is None:
        from config import Config
        config_class = Config

    app.config.from_object(config_class)

    # Create uploads directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    # Register blueprints
    from routes import main_bp
    app.register_blueprint(main_bp)

    # Create database tables
    with app.app_context():
        db.create_all()
        # Create default tech support account
        from models import User
        if not User.query.filter_by(username='tech_support').first():
            tech_support = User(username='tech_support', email='tech@example.com', role='tech_support')
            # Generate a secure random password
            import secrets
            default_password = secrets.token_urlsafe(16)
            tech_support.set_password(default_password)
            db.session.add(tech_support)
            db.session.commit()
            print(f"[INFO] Default tech_support account created with password: {default_password}")
            print("[INFO] Please change the password immediately after first login!")

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
