"""
WSGI Entry Point for SupportPilot

Usage:
    gunicorn wsgi:app
    python wsgi.py  (development server on port 5001)
"""
import os

# Disable CoreML for ONNX Runtime (fixes macOS CoreML errors)
os.environ['ORT_DISABLE_COREML'] = '1'
os.environ['ONNXRUNTIME_DISABLE_CPU'] = '0'

from app import create_app
from app.config import get_config

app = create_app()

if __name__ == '__main__':
    config = get_config()
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)  # Development server on port 5005
