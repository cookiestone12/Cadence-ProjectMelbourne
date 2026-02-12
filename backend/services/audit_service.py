import logging
from sqlalchemy.orm import Session

logger = logging.getLogger("rythm")


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
