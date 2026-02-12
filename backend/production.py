"""Production ASGI entry point with instant health check response.

Wraps the main FastAPI app to ensure health checks at / respond
immediately even while the full application is still loading.
"""
import asyncio
import os
import json
import threading
from pathlib import Path


_app = None
_app_loaded = threading.Event()
_app_error = None


def _load_app():
    global _app, _app_error
    try:
        from backend.main import app
        _app = app
        _app_loaded.set()
    except Exception as e:
        _app_error = str(e)
        _app_loaded.set()


_loader_thread = threading.Thread(target=_load_app, daemon=True)
_loader_thread.start()


HEALTH_RESPONSE_BODY = json.dumps({"status": "healthy", "service": "Rythm Catalog Intelligence"}).encode("utf-8")
HEALTH_HEADERS = [
    [b"content-type", b"application/json"],
    [b"cache-control", b"no-cache"],
]

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
index_html_path = frontend_dist / "index.html"


async def _send_health_json(send):
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": HEALTH_HEADERS,
    })
    await send({
        "type": "http.response.body",
        "body": HEALTH_RESPONSE_BODY,
    })


async def _send_index_html(send):
    try:
        body = index_html_path.read_bytes()
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/html; charset=utf-8"],
                [b"cache-control", b"no-cache, no-store, must-revalidate"],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
    except FileNotFoundError:
        await _send_health_json(send)


async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        if _app_loaded.is_set() and _app is not None:
            await _app(scope, receive, send)
        else:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            message = await receive()
            if message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
        return

    if scope["type"] == "http":
        path = scope.get("path", "/")

        if not _app_loaded.is_set():
            if path == "/" or path == "/api/health":
                if path == "/" and index_html_path.exists():
                    await _send_index_html(send)
                else:
                    await _send_health_json(send)
                return
            _app_loaded.wait(timeout=30)

        if _app is not None:
            await _app(scope, receive, send)
        else:
            error_body = json.dumps({"error": "Application failed to load", "detail": _app_error or "Unknown error"}).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 503,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": error_body,
            })
        return

    if _app_loaded.is_set() and _app is not None:
        await _app(scope, receive, send)
