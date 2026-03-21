# Gunicorn configuration file
import os
import multiprocessing

# Server socket
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')

# Worker processes
workers = os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1)
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', 'logs/gunicorn_access.log')
errorlog = os.environ.get('GUNICORN_ERROR_LOG', 'logs/gunicorn_error.log')
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')

# Process naming
proc_name = 'supportpilot'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (configure if needed)
# keyfile = None
# certfile = None
