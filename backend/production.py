"""Production ASGI entry point with instant health check response.

Serves frontend static files and health checks immediately while the
full FastAPI application loads in a background thread.
"""
import json
import mimetypes
import threading
from pathlib import Path

_app = None
_app_loaded = threading.Event()

HEALTH_BODY = b'{"status":"healthy","service":"Rythm Catalog Intelligence"}'
DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"
_index_cache = None


def _get_index_html():
    global _index_cache
    if _index_cache is None:
        index_path = DIST_DIR / "index.html"
        if index_path.exists():
            _index_cache = index_path.read_bytes()
    return _index_cache


def _load_app():
    global _app
    try:
        from backend.main import app
        _app = app
    except Exception as e:
        import sys
        print(f"FATAL: Failed to load app: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
    finally:
        _app_loaded.set()


_loader = threading.Thread(target=_load_app, daemon=True)
_loader.start()


def _try_serve_static(path: str):
    """Try to resolve a static file from frontend/dist."""
    if not DIST_DIR.exists():
        return None, None
    clean = path.lstrip("/")
    if not clean:
        return _get_index_html(), b"text/html; charset=utf-8"
    file_path = (DIST_DIR / clean).resolve()
    if not file_path.is_relative_to(DIST_DIR.resolve()):
        return None, None
    if file_path.is_file():
        ct = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        return file_path.read_bytes(), ct.encode()
    return None, None


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

    if _app_loaded.is_set() and _app is not None:
        await _app(scope, receive, send)
        return

    if path == "/api/health":
        await _send(send, 200, b"application/json", HEALTH_BODY)
        return

    if path == "/":
        html = _get_index_html()
        if html:
            await _send(send, 200, b"text/html; charset=utf-8", html)
        else:
            await _send(send, 200, b"application/json", HEALTH_BODY)
        return

    if not path.startswith("/api/"):
        body, ct = _try_serve_static(path)
        if body is not None:
            cache = b"public, max-age=31536000, immutable" if path.startswith("/assets/") else b"no-cache"
            await _send_with_cache(send, 200, ct, body, cache)
            return

    _app_loaded.wait(timeout=30)
    if _app is not None:
        await _app(scope, receive, send)
    else:
        await _send(send, 503, b"application/json",
                    b'{"error":"Application failed to load"}')


async def _send(send, status, content_type, body):
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [[b"content-type", content_type]],
    })
    await send({"type": "http.response.body", "body": body})


async def _send_with_cache(send, status, content_type, body, cache_control):
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            [b"content-type", content_type],
            [b"cache-control", cache_control],
        ],
    })
    await send({"type": "http.response.body", "body": body})
