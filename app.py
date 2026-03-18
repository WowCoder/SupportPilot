from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
import os

app = Flask(__name__)
app.config.from_object(Config)

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

from routes import *
from models import *

# Create database tables
with app.app_context():
    db.create_all()
    # Create default tech support account
    from models import User
    if not User.query.filter_by(username='tech_support').first():
        tech_support = User(username='tech_support', email='tech@example.com', role='tech_support')
        tech_support.set_password('password123')
        db.session.add(tech_support)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
