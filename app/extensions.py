"""
Flask extensions module
This module defines extensions that need to be initialized with the app factory pattern
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
