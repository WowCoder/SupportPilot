"""
Auth API Routes for SupportPilot

Provides REST API endpoints for authentication (login, register, token refresh)
using JWT tokens. Replaces Flask-Login session-based auth for the SPA frontend.
"""
import logging
from flask import Blueprint, request, jsonify

from ..models import User
from ..extensions import db
from ..utils.jwt import create_access_token, create_refresh_token, verify_token
from ..utils.auth import jwt_required

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth_api', __name__, url_prefix='/api/v1/auth')


def _user_to_dict(user: User) -> dict:
    """Convert a User model instance to a safe dictionary."""
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
    }


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT tokens.

    Request body:
        { "username": "...", "password": "..." }

    Returns:
        JSON with access_token, refresh_token, and user info
    """
    data = request.get_json(silent=True) or {}

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({
            'code': 400,
            'data': None,
            'message': 'Username and password are required',
        }), 400

    user = User.query.filter_by(username=username).first()

    if user is None or not user.check_password(password):
        logger.info(f'Failed login attempt for username: {username}')
        return jsonify({
            'code': 401,
            'data': None,
            'message': 'Invalid username or password',
        }), 401

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    logger.info(f'User {user.username} logged in successfully')

    return jsonify({
        'code': 200,
        'data': {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': _user_to_dict(user),
        },
        'message': 'Login successful',
    }), 200


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user and return JWT tokens.

    Request body:
        { "username": "...", "email": "...", "password": "..." }

    Returns:
        JSON with access_token, refresh_token, and user info
    """
    data = request.get_json(silent=True) or {}

    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    # Validate required fields
    if not username or not email or not password:
        return jsonify({
            'code': 400,
            'data': None,
            'message': 'Username, email, and password are required',
        }), 400

    # Validate username length
    if len(username) < 3 or len(username) > 64:
        return jsonify({
            'code': 400,
            'data': None,
            'message': 'Username must be between 3 and 64 characters',
        }), 400

    # Validate email format (basic)
    if '@' not in email or '.' not in email:
        return jsonify({
            'code': 400,
            'data': None,
            'message': 'Invalid email format',
        }), 400

    # Validate password strength
    is_valid, msg = User.validate_password_strength(password)
    if not is_valid:
        return jsonify({
            'code': 400,
            'data': None,
            'message': msg,
        }), 400

    # Check uniqueness
    if User.query.filter_by(username=username).first():
        return jsonify({
            'code': 409,
            'data': None,
            'message': 'Username already exists',
        }), 409

    if User.query.filter_by(email=email).first():
        return jsonify({
            'code': 409,
            'data': None,
            'message': 'Email already registered',
        }), 409

    # Create user
    user = User(username=username, email=email, role='user')
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # Generate tokens
    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    logger.info(f'New user registered: {username} ({email})')

    return jsonify({
        'code': 201,
        'data': {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': _user_to_dict(user),
        },
        'message': 'Registration successful',
    }), 201


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Refresh an expired access_token using a valid refresh_token.

    Request body:
        { "refresh_token": "<token>" }

    Returns:
        JSON with new access_token
    """
    data = request.get_json(silent=True) or {}

    refresh_token_str = data.get('refresh_token', '')

    if not refresh_token_str:
        return jsonify({
            'code': 400,
            'data': None,
            'message': 'Refresh token is required',
        }), 400

    try:
        payload = verify_token(refresh_token_str, expected_type='refresh')
    except Exception as e:
        error_name = type(e).__name__
        logger.warning(f'Refresh token verification failed: {error_name} - {e}')
        return jsonify({
            'code': 401,
            'data': None,
            'message': 'Invalid refresh token',
        }), 401

    user_id = payload['sub']
    user = User.query.get(user_id)

    if user is None:
        return jsonify({
            'code': 401,
            'data': None,
            'message': 'User not found',
        }), 401

    new_access_token = create_access_token(user.id, user.role)

    logger.debug(f'Token refreshed for user: {user.username}')

    return jsonify({
        'code': 200,
        'data': {
            'access_token': new_access_token,
        },
        'message': 'Token refreshed successfully',
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required
def me():
    """
    Return current authenticated user's profile.

    Requires valid JWT access token.

    Returns:
        JSON with user info
    """
    from flask import g
    user = g.current_user
    return jsonify({
        'code': 200,
        'data': _user_to_dict(user),
        'message': 'ok',
    }), 200
