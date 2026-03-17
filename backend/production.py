"""Production ASGI entry point.

Returns 200 for health checks immediately while loading the full app
in a background thread. Once loaded, all requests go to the real app.
"""
import mimetypes
import threading
from pathlib import Path

_real_app = None
_loaded = threading.Event()

DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"
HEALTH_JSON = b'{"status":"healthy","service":"Cadence Catalog Intelligence"}'


def _load():
    global _real_app
    try:
        from backend.main import app as real
        _real_app = real
    except Exception as e:
        import sys, traceback
        print(f"FATAL: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    finally:
        _loaded.set()


threading.Thread(target=_load, daemon=True).start()


async def _drain(receive):
    while True:
        msg = await receive()
        if msg.get("type") == "http.request":
            if not msg.get("more_body", False):
                break


async def _reply(send, status, ctype, body, extra_headers=None):
    headers = [[b"content-type", ctype]]
    if extra_headers:
        headers.extend(extra_headers)
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


def _static(path):
    if not DIST_DIR.exists():
        return None, None
    fp = (DIST_DIR / path.lstrip("/")).resolve()
    if not fp.is_relative_to(DIST_DIR.resolve()) or not fp.is_file():
        return None, None
    ct = (mimetypes.guess_type(str(fp))[0] or "application/octet-stream").encode()
    return fp.read_bytes(), ct


async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        _loaded.wait(timeout=60)
        if _real_app is not None:
            await _real_app(scope, receive, send)
        else:
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            msg = await receive()
            if msg["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
        return

    if scope["type"] != "http":
        if _loaded.is_set() and _real_app:
            await _real_app(scope, receive, send)
        return

    path = scope.get("path", "/")

    if _loaded.is_set() and _real_app is not None:
        await _real_app(scope, receive, send)
        return

    await _drain(receive)

    if path == "/api/health" or path == "/":
        if path == "/" and DIST_DIR.exists():
            idx = DIST_DIR / "index.html"
            if idx.exists():
                await _reply(send, 200, b"text/html; charset=utf-8", idx.read_bytes(),
                             [[b"cache-control", b"no-cache"]])
                return
        await _reply(send, 200, b"application/json", HEALTH_JSON)
        return

    if not path.startswith("/api/"):
        body, ct = _static(path)
        if body is not None:
            cc = b"public, max-age=31536000, immutable" if "/assets/" in path else b"no-cache"
            await _reply(send, 200, ct, body, [[b"cache-control", cc]])
            return

    _loaded.wait(timeout=30)
    if _real_app is not None:
        await _real_app(scope, receive, send)
    else:
        await _reply(send, 503, b"application/json", b'{"error":"app failed to load"}')
