"""Captures the current deploy / boot fingerprint at process startup.

Stored in-memory once and also persisted to the deploy_event table so
the /internal/dashboard "Deploy Status" panel can show the running git
SHA, boot time, runtime versions, and a short history."""
from __future__ import annotations

import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("cadence")

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class DeployInfo:
    booted_at: str
    git_sha: Optional[str]
    git_short: Optional[str]
    git_message: Optional[str]
    git_author: Optional[str]
    git_committed_at: Optional[str]
    app_env: str
    build_version: str
    python_version: str
    node_version: Optional[str]
    hostname: str

    def to_dict(self) -> dict:
        return asdict(self)


_current: Optional[DeployInfo] = None


def _git(*args: str) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except Exception:
        return None
    return None


def _node_version() -> Optional[str]:
    if not shutil.which("node"):
        return None
    try:
        out = subprocess.run(
            ["node", "--version"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        return None
    return None


def capture() -> DeployInfo:
    """Compute the deploy fingerprint (idempotent — stores once)."""
    global _current
    if _current is not None:
        return _current

    git_sha = _git("rev-parse", "HEAD")
    info = DeployInfo(
        booted_at=datetime.utcnow().isoformat(),
        git_sha=git_sha,
        git_short=(git_sha[:12] if git_sha else None) or _git("rev-parse", "--short=12", "HEAD"),
        git_message=_git("log", "-1", "--format=%s"),
        git_author=_git("log", "-1", "--format=%an"),
        git_committed_at=_git("log", "-1", "--format=%cI"),
        app_env=os.getenv("APP_ENV", "development"),
        build_version=os.getenv("BUILD_VERSION", "1.0.0"),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        node_version=_node_version(),
        hostname=socket.gethostname(),
    )
    _current = info
    return info


def current() -> Optional[DeployInfo]:
    return _current


def record_boot() -> None:
    """Persist the captured boot fingerprint to deploy_event. Trims to
    the most recent 20 rows so the table never grows unbounded."""
    info = capture()
    try:
        from ..models.database import SessionLocal
        from ..models.models import DeployEvent
        db = SessionLocal()
        try:
            committed_at: Optional[datetime] = None
            if info.git_committed_at:
                try:
                    committed_at = datetime.fromisoformat(
                        info.git_committed_at.replace("Z", "+00:00")
                    )
                except Exception:
                    committed_at = None
            db.add(DeployEvent(
                git_sha=info.git_sha,
                git_short=info.git_short,
                git_message=info.git_message,
                git_author=info.git_author,
                git_committed_at=committed_at,
                app_env=info.app_env,
                build_version=info.build_version,
                python_version=info.python_version,
                node_version=info.node_version,
                hostname=info.hostname,
            ))
            db.commit()
            # Trim — keep only the most recent 20.
            keep_ids = [
                row[0] for row in db.query(DeployEvent.id)
                .order_by(DeployEvent.id.desc())
                .limit(20).all()
            ]
            if keep_ids:
                db.query(DeployEvent).filter(
                    ~DeployEvent.id.in_(keep_ids)
                ).delete(synchronize_session=False)
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to persist deploy_event: {e}")
