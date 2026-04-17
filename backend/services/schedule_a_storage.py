"""Persistence for original Schedule A uploads.

Files are written to ``uploads/schedule_a/<org_id>/<staged|<import_id>>/``.

Staged files are written by the preview endpoint so that — if the user
proceeds to import — we already have the original bytes and can promote
them to a permanent ``ScheduleAImport`` record. If the user abandons the
preview the staged file is harmlessly garbage-collected on the next
``cleanup_stale_staged`` sweep.
"""
from __future__ import annotations

import hashlib
import logging
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("cadence")

ROOT = Path("uploads/schedule_a")
ROOT.mkdir(parents=True, exist_ok=True)


def _safe_filename(name: str) -> str:
    name = name.strip() or "schedule_a"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name[:120]


def _org_root(org_id: int) -> Path:
    p = ROOT / str(org_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def stage_upload(org_id: int, content: bytes, filename: str) -> Tuple[str, str]:
    """Write the upload to a staged location and return (staged_id, full_path).

    The staged_id is opaque (uuid.hex) and safe to send to the client.
    """
    staged_dir = _org_root(org_id) / "staged"
    staged_dir.mkdir(parents=True, exist_ok=True)
    staged_id = uuid.uuid4().hex
    safe = _safe_filename(filename)
    full = staged_dir / f"{staged_id}__{safe}"
    full.write_bytes(content)
    return staged_id, str(full)


def find_staged(org_id: int, staged_id: str) -> Optional[Path]:
    if not staged_id or "/" in staged_id or "\\" in staged_id:
        return None
    staged_dir = _org_root(org_id) / "staged"
    if not staged_dir.exists():
        return None
    for p in staged_dir.iterdir():
        if p.is_file() and p.name.startswith(staged_id + "__"):
            return p
    return None


def promote_staged(org_id: int, staged_path: str, import_id: int) -> str:
    """Move a staged file under a permanent ``<import_id>/`` directory and
    return the new absolute path string.
    """
    src = Path(staged_path)
    dest_dir = _org_root(org_id) / str(import_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Strip the staged uuid prefix from the filename for the permanent copy.
    safe_name = src.name.split("__", 1)[-1] if "__" in src.name else src.name
    dest = dest_dir / safe_name
    try:
        shutil.move(str(src), str(dest))
    except Exception as e:
        logger.error(f"Failed to promote staged file {src} -> {dest}: {e}")
        # Fall back to copy + leave staged in place rather than losing data.
        try:
            shutil.copy2(str(src), str(dest))
        except Exception as e2:
            logger.error(f"Fallback copy also failed: {e2}")
            raise
    return str(dest)


def hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def cleanup_stale_staged(max_age_seconds: int = 24 * 3600) -> int:
    """Best-effort sweep of staged files older than max_age_seconds.

    Safe to call from a periodic job. Returns the number of files removed.
    """
    if not ROOT.exists():
        return 0
    cutoff = time.time() - max_age_seconds
    removed = 0
    for org_dir in ROOT.iterdir():
        staged = org_dir / "staged"
        if not staged.exists():
            continue
        for f in staged.iterdir():
            try:
                if f.is_file() and f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1
            except Exception as e:
                logger.warning(f"Could not remove stale staged file {f}: {e}")
    return removed
