"""Production ASGI entry point with instant health check response."""
import json
import threading
from pathlib import Path

_app = None
_app_loaded = threading.Event()

HEALTH_BODY = b'{"status":"healthy","service":"Rythm Catalog Intelligence"}'
INDEX_PATH = Path(__file__).parent.parent / "frontend" / "dist" / "index.html"
_index_cache = None


def _get_index_html():
    global _index_cache
    if _index_cache is None and INDEX_PATH.exists():
        _index_cache = INDEX_PATH.read_bytes()
    return _index_cache


def _load_app():
    global _app
    try:
        from backend.main import app
        _app = app
    except Exception as e:
        import sys
        print(f"FATAL: Failed to load app: {e}", file=sys.stderr)
    finally:
        _app_loaded.set()


_loader = threading.Thread(target=_load_app, daemon=True)
_loader.start()


async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        msg = await receive()
        if msg["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        msg = await receive()
        if msg["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
        return

    if scope["type"] != "http":
        if _app_loaded.is_set() and _app:
            await _app(scope, receive, send)
        return

    path = scope.get("path", "/")

    if not _app_loaded.is_set():
        if path == "/" or path == "/api/health":
            await _respond_fast(path, send)
            return
        _app_loaded.wait(timeout=30)

    if _app is not None:
        await _app(scope, receive, send)
    else:
        await _send(send, 503, b"application/json",
                    b'{"error":"Application failed to load"}')


async def _respond_fast(path, send):
    if path == "/" and _get_index_html():
        await _send(send, 200, b"text/html; charset=utf-8", _get_index_html())
    else:
        await _send(send, 200, b"application/json", HEALTH_BODY)


async def _send(send, status, content_type, body):
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [[b"content-type", content_type]],
    })
    await send({"type": "http.response.body", "body": body})
