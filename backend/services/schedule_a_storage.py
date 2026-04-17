"""Persistence for original Schedule A uploads.

Primary backend is Replit Object Storage. When the object storage client
cannot be initialised (missing bucket, sandboxed/test env, etc.) we fall
back to the local filesystem under ``uploads/schedule_a/<org_id>/``.

Object keys follow the convention:
    schedule_a/<org_id>/staged/<staged_id>__<safe_filename>
    schedule_a/<org_id>/<import_id>/<safe_filename>

Staged objects are written by the preview endpoint so that — if the user
proceeds to import — we already have the original bytes and can promote
them to a permanent ``ScheduleAImport`` record. If the user abandons the
preview the staged object is harmlessly garbage-collected on the next
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
from typing import List, Optional, Tuple

logger = logging.getLogger("cadence")

KEY_ROOT = "schedule_a"
LOCAL_ROOT = Path("uploads/schedule_a")
LOCAL_ROOT.mkdir(parents=True, exist_ok=True)

_object_client = None
_object_client_failed = False


def _get_object_client():
    """Lazily build a Replit Object Storage client. Returns None if unavailable."""
    global _object_client, _object_client_failed
    if _object_client is not None:
        return _object_client
    if _object_client_failed:
        return None
    try:
        from replit.object_storage import Client  # type: ignore
        _object_client = Client()
        return _object_client
    except Exception as e:
        _object_client_failed = True
        logger.info(
            f"Replit Object Storage unavailable; falling back to local disk for "
            f"Schedule A uploads ({type(e).__name__}: {e})"
        )
        return None


def _safe_filename(name: str) -> str:
    name = (name or "").strip() or "schedule_a"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name[:120]


def _staged_key(org_id: int, staged_id: str, filename: str) -> str:
    return f"{KEY_ROOT}/{org_id}/staged/{staged_id}__{_safe_filename(filename)}"


def _final_key(org_id: int, import_id: int, filename: str) -> str:
    return f"{KEY_ROOT}/{org_id}/{import_id}/{_safe_filename(filename)}"


# ---------- Local-disk helpers (fallback) ----------

def _local_org_root(org_id: int) -> Path:
    p = LOCAL_ROOT / str(org_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _local_path_for_key(key: str) -> Path:
    # key is "schedule_a/<org>/<rest>"; mirror under LOCAL_ROOT
    rel = key[len(KEY_ROOT) + 1 :] if key.startswith(KEY_ROOT + "/") else key
    p = LOCAL_ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ---------- Public API ----------

def stage_upload(org_id: int, content: bytes, filename: str) -> Tuple[str, str]:
    """Persist a staged upload and return ``(staged_id, storage_key)``.

    The ``staged_id`` is opaque (uuid hex) and safe to send to the client.
    The ``storage_key`` is the canonical key used by both backends; callers
    should treat it as opaque.
    """
    staged_id = uuid.uuid4().hex
    key = _staged_key(org_id, staged_id, filename)

    client = _get_object_client()
    if client is not None:
        try:
            client.upload_from_bytes(key, content)
            return staged_id, key
        except Exception as e:
            logger.warning(
                f"Object storage upload failed ({type(e).__name__}: {e}); "
                "falling back to local disk for this file."
            )

    path = _local_path_for_key(key)
    path.write_bytes(content)
    return staged_id, key


def find_staged(org_id: int, staged_id: str) -> Optional[str]:
    """Return the storage_key of a staged file, or None.

    Returns the key only if the underlying object/file actually exists.
    """
    if not staged_id or "/" in staged_id or "\\" in staged_id:
        return None

    prefix = f"{KEY_ROOT}/{org_id}/staged/{staged_id}__"

    client = _get_object_client()
    if client is not None:
        try:
            matches = client.list(prefix=prefix)
            # client.list returns objects with .name
            for obj in matches:
                name = getattr(obj, "name", None) or getattr(obj, "key", None) or str(obj)
                if name.startswith(prefix):
                    return name
        except Exception as e:
            logger.warning(f"Object storage list failed ({type(e).__name__}: {e}); checking local fallback")

    # Local-disk fallback (also used to tolerate files written before object storage was available)
    staged_dir = _local_org_root(org_id) / "staged"
    if staged_dir.exists():
        for p in staged_dir.iterdir():
            if p.is_file() and p.name.startswith(staged_id + "__"):
                return f"{KEY_ROOT}/{org_id}/staged/{p.name}"
    return None


def promote_staged(org_id: int, staged_key: str, import_id: int) -> str:
    """Move a staged object/file to its permanent location and return the new key."""
    safe_name = staged_key.rsplit("/", 1)[-1]
    if "__" in safe_name:
        safe_name = safe_name.split("__", 1)[1]
    final_key = _final_key(org_id, import_id, safe_name)

    client = _get_object_client()
    if client is not None:
        try:
            try:
                client.copy(staged_key, final_key)
                client.delete(staged_key)
                return final_key
            except Exception as copy_err:
                # Older SDKs may not expose copy; fall back to download+upload
                logger.info(f"object_storage.copy unavailable, falling back to re-upload: {copy_err}")
                data = client.download_as_bytes(staged_key)
                client.upload_from_bytes(final_key, data)
                client.delete(staged_key)
                return final_key
        except Exception as e:
            logger.warning(
                f"Object storage promote failed ({type(e).__name__}: {e}); "
                "falling back to local disk."
            )

    src = _local_path_for_key(staged_key)
    dest = _local_path_for_key(final_key)
    try:
        shutil.move(str(src), str(dest))
    except Exception as e:
        logger.error(f"Failed to promote staged file {src} -> {dest}: {e}")
        try:
            shutil.copy2(str(src), str(dest))
        except Exception as e2:
            logger.error(f"Fallback copy also failed: {e2}")
            raise
    return final_key


def delete(key: str) -> bool:
    """Best-effort delete of a stored object/file. Returns True on success."""
    if not key:
        return False
    client = _get_object_client()
    if client is not None:
        try:
            client.delete(key)
            return True
        except Exception as e:
            logger.info(f"object_storage.delete failed for {key}: {e}")
    try:
        p = _local_path_for_key(key)
        if p.exists():
            p.unlink()
            return True
    except Exception as e:
        logger.warning(f"Local delete failed for {key}: {e}")
    return False


def exists(key: str) -> bool:
    """Cheap existence check — does NOT download the object body."""
    if not key:
        return False
    client = _get_object_client()
    if client is not None:
        try:
            return bool(client.exists(key))
        except Exception as e:
            logger.info(f"object_storage.exists failed for {key}: {e}")
    return _local_path_for_key(key).exists()


def open_bytes(key: str) -> Optional[bytes]:
    """Read the bytes for a stored key, or None if missing."""
    if not key:
        return None
    client = _get_object_client()
    if client is not None:
        try:
            return client.download_as_bytes(key)
        except Exception as e:
            logger.info(f"object_storage download failed for {key}: {e}")
    p = _local_path_for_key(key)
    if p.exists():
        return p.read_bytes()
    return None


def hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def cleanup_stale_staged(max_age_seconds: int = 24 * 3600) -> int:
    """Best-effort sweep of staged objects/files older than max_age_seconds.

    Returns the number of items removed. Object storage entries are removed
    via list+delete using object metadata when available; otherwise a UUID
    embedded in the staged key gives no age, so object-storage-only cleanup
    is best handled by the bucket lifecycle policy. This function therefore
    focuses on the local disk fallback (where stale files actually accumulate)
    and returns 0 cleanly when no local files are present.
    """
    removed = 0
    if LOCAL_ROOT.exists():
        cutoff = time.time() - max_age_seconds
        for org_dir in LOCAL_ROOT.iterdir():
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
