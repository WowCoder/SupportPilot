"""
JWT Token Utilities for SupportPilot

Provides create_access_token, create_refresh_token, and verify_token
functions for JWT-based API authentication.
"""
import jwt
from datetime import datetime, timedelta, timezone
from flask import current_app


def _get_secret_key():
    """Get JWT secret key from Flask app config, with fallback."""
    try:
        return current_app.config.get(
            'JWT_SECRET_KEY',
            current_app.config['SECRET_KEY']
        )
    except RuntimeError:
        # Outside of request context — use os.environ
        import os
        return os.environ.get('JWT_SECRET_KEY', os.environ.get('SECRET_KEY', 'dev-secret-change-me'))


def create_access_token(user_id: int, role: str) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: The user's database ID
        role: The user's role (e.g., 'user', 'tech_support')

    Returns:
        Encoded JWT string valid for 15 minutes
    """
    now = datetime.now(timezone.utc)
    payload = {
        'sub': user_id,
        'role': role,
        'type': 'access',
        'iat': now,
        'exp': now + timedelta(minutes=15),
    }
    return jwt.encode(payload, _get_secret_key(), algorithm='HS256')


def create_refresh_token(user_id: int) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: The user's database ID

    Returns:
        Encoded JWT string valid for 7 days
    """
    now = datetime.now(timezone.utc)
    payload = {
        'sub': user_id,
        'type': 'refresh',
        'iat': now,
        'exp': now + timedelta(days=7),
    }
    return jwt.encode(payload, _get_secret_key(), algorithm='HS256')


def verify_token(token: str, expected_type: str = 'access') -> dict:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token string
        expected_type: Expected token type ('access' or 'refresh')

    Returns:
        Decoded token payload as dict

    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is invalid
        ValueError: Token type mismatch
    """
    payload = jwt.decode(
        token,
        _get_secret_key(),
        algorithms=['HS256'],
        options={'require': ['exp', 'sub', 'type']},
    )

    if payload.get('type') != expected_type:
        raise ValueError(f'Expected {expected_type} token, got {payload.get("type")}')

    return payload
