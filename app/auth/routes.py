"""
Authentication Blueprint for SupportPilot

Handles user registration, login, and logout.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_user, logout_user
import logging

from ..extensions import db
from ..models import User

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Validate username
        if len(username) < 3 or len(username) > 64:
            logger.warning(f'Registration failed: username {username} invalid length')
            flash('Username must be between 3 and 64 characters')
            return redirect(url_for('auth.register'))

        # Validate email
        if not email or '@' not in email:
            logger.warning(f'Registration failed: invalid email {email}')
            flash('Invalid email address')
            return redirect(url_for('auth.register'))

        # Validate password strength
        is_valid, message = User.validate_password_strength(password)
        if not is_valid:
            logger.warning(f'Registration failed: weak password for user {username}')
            flash(message)
            return redirect(url_for('auth.register'))

        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            logger.warning(f'Registration failed: username {username} already exists')
            flash('Username already exists')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            logger.warning(f'Registration failed: email {email} already exists')
            flash('Email already exists')
            return redirect(url_for('auth.register'))

        # Create new user
        user = User(username=username, email=email, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        logger.info(f'User registered successfully: {username}')
        flash('Registration successful!')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Log in a user"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            logger.info(f'User logged in: {username}')
            return redirect(url_for('main.index'))

        logger.warning(f'Login failed: invalid credentials for user {username}')
        flash('Invalid username or password')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Log out current user"""
    username = current_user.username
    logout_user()
    logger.info(f'User logged out: {username}')
    return redirect(url_for('auth.login'))
