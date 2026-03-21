"""
SupportPilot Application Entry Point (Backward Compatibility)

This file is kept for backward compatibility.
The application factory has been moved to app/__init__.py.
"""
from app import create_app

# For backward compatibility - direct execution
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
