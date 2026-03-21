"""
User model for SupportPilot
"""
from datetime import datetime
from typing import Tuple, List
from flask_login import UserMixin
import hashlib
import os

from ..extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id: str) -> 'User':
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    """User model for authentication and authorization"""

    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='user')  # 'user' or 'tech_support'

    # Relationships
    conversations = db.relationship('Conversation', backref='user', lazy='dynamic')
    documents = db.relationship('Document', backref='user', lazy='dynamic')

    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """
        Validate password strength

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if len(password) > 128:
            return False, "Password must be less than 128 characters"
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        return True, "Password is strong enough"

    def set_password(self, password: str) -> None:
        """
        Hash and store password

        Args:
            password: Plain text password
        """
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        self.password_hash = salt.hex() + key.hex()

    def check_password(self, password: str) -> bool:
        """
        Verify password against hash

        Args:
            password: Plain text password to verify

        Returns:
            True if password matches, False otherwise
        """
        salt = bytes.fromhex(self.password_hash[:64])
        key = bytes.fromhex(self.password_hash[64:])
        new_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return new_key == key

    def __repr__(self) -> str:
        return f'<User {self.username}>'
