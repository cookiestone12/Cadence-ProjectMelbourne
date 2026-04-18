"""Structured logging + in-process ring buffer.

Adds:
  * a ContextFilter that pulls request_id / user_id / org_id / route
    from the request-scoped ContextVars onto every LogRecord
  * an extended JSONFormatter that emits those fields plus duration_ms
    when present
  * a bounded RingBufferHandler that keeps the most recent N records
    in memory so the /internal/logs page (Task #76) can tail them
    without an external log shipper
"""
import logging
import json
import sys
import os
import traceback as _traceback
from collections import deque
from datetime import datetime, timezone
from threading import RLock
from typing import Optional

from .request_context import (
    request_id_var,
    user_id_var,
    org_id_var,
    route_var,
)


class ContextFilter(logging.Filter):
    """Copies request-scoped ContextVars onto every LogRecord so the
    formatter can include them. Cheap; runs on every log call."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            rid = request_id_var.get()
            if rid is not None:
                record.request_id = rid
        if not hasattr(record, "user_id"):
            uid = user_id_var.get()
            if uid is not None:
                record.user_id = uid
        if not hasattr(record, "org_id"):
            oid = org_id_var.get()
            if oid is not None:
                record.org_id = oid
        if not hasattr(record, "route"):
            rt = route_var.get()
            if rt is not None:
                record.route = rt
        return True


class JSONFormatter(logging.Formatter):
    """Emits one JSON object per log line. Extra context fields are
    attached opportunistically — absent fields are simply omitted."""

    _CORE_FIELDS = {
        "request_id",
        "user_id",
        "org_id",
        "route",
        "duration_ms",
        "method",
        "path",
        "status_code",
    }

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)
        for field in self._CORE_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                log_data[field] = value
        return json.dumps(log_data, default=str)


class RingBufferHandler(logging.Handler):
    """Keeps the most recent ``capacity`` records in memory as plain
    dicts so an HTTP endpoint can stream them back. Thread-safe."""

    def __init__(self, capacity: int = 10_000):
        super().__init__()
        self._buffer: deque[dict] = deque(maxlen=capacity)
        self._lock = RLock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            if record.exc_info and record.exc_info[0]:
                # logging.Handler has no formatException; use the
                # traceback module directly so we don't drop records
                # exactly when something has gone wrong.
                entry["exception"] = "".join(
                    _traceback.format_exception(*record.exc_info)
                )
            for field in JSONFormatter._CORE_FIELDS:
                value = getattr(record, field, None)
                if value is not None:
                    entry[field] = value
            with self._lock:
                self._buffer.append(entry)
        except Exception:
            self.handleError(record)

    def snapshot(self) -> list[dict]:
        with self._lock:
            return list(self._buffer)


_ring_handler: Optional[RingBufferHandler] = None


def get_ring_handler() -> Optional[RingBufferHandler]:
    return _ring_handler


def tail_logs(
    level: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = 200,
    until: Optional[datetime] = None,
) -> list[dict]:
    """Return the most recent log entries from the in-process ring
    buffer, newest last. ``level`` filters by minimum severity (e.g.
    ``"WARNING"`` returns warnings + errors + critical). ``since`` is
    a timezone-aware datetime; entries strictly older are dropped."""
    if _ring_handler is None:
        return []
    entries = _ring_handler.snapshot()
    if level:
        wanted = logging.getLevelName(level.upper())
        if isinstance(wanted, int):
            entries = [
                e for e in entries
                if logging.getLevelName(e.get("level", "INFO")) >= wanted  # type: ignore[operator]
            ]
    if since is not None:
        cutoff = since.isoformat()
        entries = [e for e in entries if e.get("timestamp", "") >= cutoff]
    if until is not None:
        upper = until.isoformat()
        entries = [e for e in entries if e.get("timestamp", "") <= upper]
    if limit and len(entries) > limit:
        entries = entries[-limit:]
    return entries


def setup_logging() -> logging.Logger:
    global _ring_handler

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    use_json = os.getenv("LOG_FORMAT", "text").lower() == "json"

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    context_filter = ContextFilter()

    handler = logging.StreamHandler(sys.stdout)
    if use_json:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
    handler.addFilter(context_filter)
    root_logger.addHandler(handler)

    ring_capacity = int(os.getenv("LOG_RING_CAPACITY", "10000"))
    _ring_handler = RingBufferHandler(capacity=ring_capacity)
    _ring_handler.addFilter(context_filter)
    _ring_handler.setLevel(log_level)
    root_logger.addHandler(_ring_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if os.getenv("SQL_DEBUG") == "true" else logging.WARNING
    )

    return logging.getLogger("cadence")


logger = setup_logging()
