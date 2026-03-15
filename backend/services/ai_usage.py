import logging
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger("cadence")

COST_PER_1K_INPUT = 0.015
COST_PER_1K_OUTPUT = 0.060


def log_ai_usage(
    db: Session,
    feature: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    org_id: int = None,
):
    from ..models.models import AIUsageLog

    total_tokens = input_tokens + output_tokens
    cost_dollars = (input_tokens / 1000.0) * COST_PER_1K_INPUT + (output_tokens / 1000.0) * COST_PER_1K_OUTPUT
    cost_cents = int(round(cost_dollars * 100, 0))

    try:
        entry = AIUsageLog(
            org_id=org_id,
            feature=feature,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_cents=cost_cents,
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log AI usage for {feature}: {e}")
        db.rollback()


def log_ai_usage_standalone(
    feature: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    org_id: int = None,
):
    from ..models.database import SessionLocal

    db = SessionLocal()
    try:
        log_ai_usage(db, feature, model, input_tokens, output_tokens, org_id)
    finally:
        db.close()
