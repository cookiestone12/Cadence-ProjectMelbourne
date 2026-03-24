import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 180
keepalive = 5
max_requests = 0
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
graceful_timeout = 30
preload_app = True
