"""
Utility functions for SupportPilot
"""
# Re-export from root utils module
import sys
import os

# Add parent directory to path for relative import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import sanitize_input

__all__ = ['sanitize_input']
