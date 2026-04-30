import logging
from sqlalchemy.orm import Session

logger = logging.getLogger("cadence")


def log_action(
    db: Session,
    organization_id: int,
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: int = None,
    entity_name: str = None,
    details: dict = None,
):
    from ..models.models import AuditLog
    try:
        entry = AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=details,
        )
        db.add(entry)
    except Exception as e:
        logger.error(f"Failed to log audit action: {e}")


def make_diff(before: dict, after: dict) -> dict:
    """Return a `{field: {"old": x, "new": y}}` map of changed values.

    Fields present only in one side are still emitted (the missing side is
    serialized as ``None``). Used by Task #161 audit hooks so the audit-log
    viewer can render exact split / share deltas instead of opaque snapshots.
    """
    before = before or {}
    after = after or {}
    keys = sorted(set(before.keys()) | set(after.keys()), key=str)
    diff: dict = {}
    for key in keys:
        old_val = before.get(key)
        new_val = after.get(key)
        if old_val != new_val:
            diff[key] = {"old": old_val, "new": new_val}
    return diff
