"""
JWT Authentication Decorator for SupportPilot

Provides @jwt_required decorator that replaces Flask-Login's @login_required
for API endpoints. Extracts and validates JWT from Authorization header.
"""
import logging
from functools import wraps
from flask import request, jsonify, g

from ..models import User
from .jwt import verify_token

logger = logging.getLogger(__name__)


def jwt_required(f):
    """
    Decorator: require a valid JWT access token for the endpoint.

    Extracts token from `Authorization: Bearer <token>` header,
    verifies it, and injects `current_user` into Flask's `g` object.

    Usage:
        @jwt_required
        def protected_route():
            user = g.current_user  # User model instance
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return jsonify({
                'code': 401,
                'data': None,
                'message': 'Authentication required',
            }), 401

        token = auth_header[7:]  # Strip 'Bearer ' prefix

        try:
            payload = verify_token(token, expected_type='access')
        except Exception as e:
            error_name = type(e).__name__
            logger.warning(f'JWT verification failed: {error_name} - {e}')
            return jsonify({
                'code': 401,
                'data': None,
                'message': 'Token expired or invalid',
            }), 401

        user_id = payload['sub']
        user = User.query.get(user_id)

        if user is None:
            return jsonify({
                'code': 401,
                'data': None,
                'message': 'User not found',
            }), 401

        g.current_user = user
        return f(*args, **kwargs)

    return decorated_function


def jwt_optional(f):
    """
    Decorator: optionally authenticate via JWT.

    If a valid token is present, injects `current_user` into `g`.
    If no token or invalid, `g.current_user` is None.

    Usage:
        @jwt_optional
        def public_or_private_route():
            user = g.get('current_user')  # None if not authenticated
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.current_user = None

        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            try:
                payload = verify_token(token, expected_type='access')
                user_id = payload['sub']
                g.current_user = User.query.get(user_id)
            except Exception:
                pass  # Silent fail for optional auth

        return f(*args, **kwargs)

    return decorated_function
