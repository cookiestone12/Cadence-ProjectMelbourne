import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv('WEB_CONCURRENCY', '2'))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
graceful_timeout = 30
preload_app = True
