import multiprocessing
import os

# Gunicorn configuration for high-performance Flask apps
bind = f"0.0.0.0:{os.getenv('PORT', '5001')}"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"  # Standard for Flask, change to gevent/eventlet for high I/O
threads = 2
timeout = 60
keepalive = 2

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
