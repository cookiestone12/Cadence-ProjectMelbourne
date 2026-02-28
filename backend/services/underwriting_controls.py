import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.models import RoyaltyStatement, RoyaltyStatementLine

logger = logging.getLogger("cadence")


def run_reconciliation_controls(db: Session, statement_id: int, org_id: int) -> dict:
    statement = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not statement:
        return {"error": "Statement not found"}

    line_aggs = db.query(
        func.sum(RoyaltyStatementLine.gross_amount),
        func.sum(RoyaltyStatementLine.deductions_amount),
        func.sum(RoyaltyStatementLine.net_amount),
        func.count(RoyaltyStatementLine.id),
    ).filter(
        RoyaltyStatementLine.statement_id == statement_id,
        RoyaltyStatementLine.org_id == org_id,
    ).first()

    sum_gross = float(line_aggs[0] or 0)
    sum_deductions = float(line_aggs[1] or 0)
    sum_net = float(line_aggs[2] or 0)
    line_count = line_aggs[3] or 0

    tolerance = 0.01

    checks = []

    if statement.reported_gross is not None:
        variance = abs(sum_gross - statement.reported_gross)
        checks.append({
            "check": "gross_control_total",
            "expected": statement.reported_gross,
            "actual": round(sum_gross, 2),
            "variance": round(variance, 2),
            "passed": variance <= tolerance,
        })

    if statement.reported_withholding is not None:
        variance = abs(sum_deductions - statement.reported_withholding)
        checks.append({
            "check": "withholding_control_total",
            "expected": statement.reported_withholding,
            "actual": round(sum_deductions, 2),
            "variance": round(variance, 2),
            "passed": variance <= tolerance,
        })

    if statement.reported_net is not None:
        variance = abs(sum_net - statement.reported_net)
        checks.append({
            "check": "net_control_total",
            "expected": statement.reported_net,
            "actual": round(sum_net, 2),
            "variance": round(variance, 2),
            "passed": variance <= tolerance,
        })

    if statement.opening_balance is not None and statement.closing_balance is not None:
        expected_closing = statement.opening_balance + sum_net
        variance = abs(statement.closing_balance - expected_closing)
        checks.append({
            "check": "balance_roll_forward",
            "opening_balance": statement.opening_balance,
            "earned_net": round(sum_net, 2),
            "expected_closing": round(expected_closing, 2),
            "reported_closing": statement.closing_balance,
            "variance": round(variance, 2),
            "passed": variance <= tolerance,
        })

    all_passed = all(c["passed"] for c in checks) if checks else None
    result = {
        "statement_id": statement_id,
        "line_count": line_count,
        "sum_gross": round(sum_gross, 2),
        "sum_deductions": round(sum_deductions, 2),
        "sum_net": round(sum_net, 2),
        "checks": checks,
        "all_passed": all_passed,
        "run_at": datetime.utcnow().isoformat(),
    }

    statement.reconciliation_details = result
    db.flush()

    return result
