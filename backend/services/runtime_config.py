"""Read-through cache + writer for the runtime_config table.

Call sites use `get(key, default)` to fetch a flag value cheaply
(in-memory dict, no DB round trip after warmup). `set(...)` updates
the row, refreshes the cache, and writes an audit entry."""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models.database import SessionLocal
from ..models.models import RuntimeConfig

logger = logging.getLogger("cadence")

_cache: dict[str, Any] = {}
_meta: dict[str, dict] = {}  # key -> {category, value_type, description}
_lock = threading.RLock()
_warmed = False


# Default flags — created if missing at first warmup so the editor UI
# always has something to show. Add new flags here; the seeder is
# additive and never overwrites existing values.
DEFAULTS: list[dict] = [
    # Feature flags
    {"key": "feature.brief_builder", "category": "Flags", "value_type": "bool",
     "value": True, "description": "Enable the AI Brief Builder page."},
    {"key": "feature.audio_analysis", "category": "Flags", "value_type": "bool",
     "value": True, "description": "Enable AI audio analysis pipeline."},
    {"key": "feature.client_portal", "category": "Flags", "value_type": "bool",
     "value": True, "description": "Enable the org-managed client portal."},
    {"key": "feature.public_signup", "category": "Flags", "value_type": "bool",
     "value": False, "description": "Allow self-serve signup (off in private beta)."},
    # AI knobs
    {"key": "ai.assistant_model", "category": "AI", "value_type": "string",
     "value": "gpt-4o-mini", "description": "OpenAI model for the floating assistant."},
    {"key": "ai.contract_parser_model", "category": "AI", "value_type": "string",
     "value": "gpt-4o", "description": "OpenAI model for contract parsing."},
    # Email / notifications
    {"key": "email.support_inbox", "category": "Email", "value_type": "string",
     "value": "support@cadence-ci.com", "description": "Where support tickets are forwarded."},
    {"key": "email.digest_enabled", "category": "Email", "value_type": "bool",
     "value": True, "description": "Send the daily email digest to opted-in users."},
    # Valuation
    {"key": "valuation.weight_streaming", "category": "Valuation", "value_type": "float",
     "value": 0.4, "description": "Weight for streaming-based valuation component."},
    {"key": "valuation.weight_sync", "category": "Valuation", "value_type": "float",
     "value": 0.3, "description": "Weight for sync placement valuation component."},
    {"key": "valuation.weight_blackbox", "category": "Valuation", "value_type": "float",
     "value": 0.3, "description": "Weight for the proprietary Black Box algorithm."},
    # Limits
    {"key": "limits.max_csv_rows", "category": "Limits", "value_type": "int",
     "value": 50000, "description": "Reject CSV imports with more rows than this."},
    {"key": "limits.audio_upload_mb", "category": "Limits", "value_type": "int",
     "value": 200, "description": "Max upload size for audio files (MB)."},
]


def _coerce(value: Any, value_type: str) -> Any:
    if value is None:
        return None
    if value_type == "bool":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "1", "yes", "on")
    if value_type == "int":
        return int(value)
    if value_type == "float":
        return float(value)
    if value_type == "json":
        return value
    return str(value)


def _warmup_unlocked() -> None:
    global _warmed
    db = SessionLocal()
    try:
        # Insert defaults that don't yet exist — additive only.
        existing_keys = {r[0] for r in db.query(RuntimeConfig.key).all()}
        added = 0
        for d in DEFAULTS:
            if d["key"] in existing_keys:
                continue
            db.add(RuntimeConfig(
                key=d["key"],
                category=d["category"],
                value_type=d["value_type"],
                value=d["value"],
                description=d["description"],
            ))
            added += 1
        if added:
            db.commit()
            logger.info(f"Seeded {added} default runtime_config keys")

        rows = db.query(RuntimeConfig).all()
        _cache.clear(); _meta.clear()
        for r in rows:
            _cache[r.key] = _coerce(r.value, r.value_type or "string")
            _meta[r.key] = {
                "category": r.category,
                "value_type": r.value_type,
                "description": r.description,
            }
        _warmed = True
    finally:
        db.close()


def warmup() -> None:
    with _lock:
        try:
            _warmup_unlocked()
        except Exception as e:
            logger.warning(f"runtime_config warmup failed: {e}")


def get(key: str, default: Any = None) -> Any:
    with _lock:
        if not _warmed:
            try:
                _warmup_unlocked()
            except Exception:
                return default
        return _cache.get(key, default)


def all_items() -> list[dict]:
    with _lock:
        if not _warmed:
            _warmup_unlocked()
        out: list[dict] = []
        for key, value in _cache.items():
            meta = _meta.get(key, {})
            out.append({
                "key": key,
                "value": value,
                "category": meta.get("category", "general"),
                "value_type": meta.get("value_type", "string"),
                "description": meta.get("description"),
            })
        out.sort(key=lambda x: (x["category"], x["key"]))
        return out


def set_value(db: Session, key: str, value: Any, updated_by: int) -> dict:
    row = db.query(RuntimeConfig).filter(RuntimeConfig.key == key).first()
    if row is None:
        raise KeyError(key)
    coerced = _coerce(value, row.value_type or "string")
    row.value = coerced
    row.updated_by = updated_by
    db.commit()
    with _lock:
        _cache[key] = coerced
    return {"key": key, "value": coerced, "value_type": row.value_type}
