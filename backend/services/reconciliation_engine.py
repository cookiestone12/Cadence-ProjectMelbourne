import logging
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import (
    RoyaltyStatement, RoyaltyStatementLine,
    RoyaltyLedgerEntry, RoyaltyProcessingRun,
)

logger = logging.getLogger(__name__)


def run_control_totals(db: Session, statement_id: int, org_id: int) -> dict:
    statement = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not statement:
        return {"error": "Statement not found"}

    line_aggs = db.query(
        func.coalesce(func.sum(RoyaltyStatementLine.gross_amount), 0).label("sum_gross"),
        func.coalesce(func.sum(RoyaltyStatementLine.deductions_amount), 0).label("sum_deductions"),
        func.coalesce(func.sum(RoyaltyStatementLine.net_amount), 0).label("sum_net"),
        func.count(RoyaltyStatementLine.id).label("line_count"),
    ).filter(
        RoyaltyStatementLine.statement_id == statement_id,
        RoyaltyStatementLine.org_id == org_id,
    ).first()

    computed_gross = float(line_aggs.sum_gross) if line_aggs.sum_gross else 0.0
    computed_deductions = float(line_aggs.sum_deductions) if line_aggs.sum_deductions else 0.0
    computed_net = float(line_aggs.sum_net) if line_aggs.sum_net else 0.0
    line_count = line_aggs.line_count or 0

    checks = []

    if statement.reported_gross is not None:
        diff = abs(computed_gross - statement.reported_gross)
        checks.append({
            "check": "gross_payable",
            "reported": statement.reported_gross,
            "computed": round(computed_gross, 2),
            "difference": round(diff, 2),
            "status": "PASS" if diff < 0.02 else ("WARN" if diff < 1.0 else "FAIL"),
        })

    if statement.reported_withholding is not None:
        diff = abs(computed_deductions - statement.reported_withholding)
        checks.append({
            "check": "withholding_tax",
            "reported": statement.reported_withholding,
            "computed": round(computed_deductions, 2),
            "difference": round(diff, 2),
            "status": "PASS" if diff < 0.02 else ("WARN" if diff < 1.0 else "FAIL"),
        })

    if statement.reported_net is not None:
        diff = abs(computed_net - statement.reported_net)
        checks.append({
            "check": "net_payable",
            "reported": statement.reported_net,
            "computed": round(computed_net, 2),
            "difference": round(diff, 2),
            "status": "PASS" if diff < 0.02 else ("WARN" if diff < 1.0 else "FAIL"),
        })

    if not checks:
        if computed_gross != 0 and computed_net != 0:
            implied_deductions = computed_gross - computed_net
            diff = abs(implied_deductions - computed_deductions) if computed_deductions else 0
            checks.append({
                "check": "internal_consistency",
                "description": "gross - deductions == net",
                "computed_gross": round(computed_gross, 2),
                "computed_deductions": round(computed_deductions, 2),
                "computed_net": round(computed_net, 2),
                "implied_deductions": round(implied_deductions, 2),
                "difference": round(diff, 2),
                "status": "PASS" if diff < 0.02 else "WARN",
            })

    overall = "PASS"
    for c in checks:
        if c["status"] == "FAIL":
            overall = "FAIL"
            break
        if c["status"] == "WARN":
            overall = "WARN"

    result = {
        "statement_id": statement_id,
        "line_count": line_count,
        "computed_totals": {
            "gross": round(computed_gross, 2),
            "deductions": round(computed_deductions, 2),
            "net": round(computed_net, 2),
        },
        "checks": checks,
        "overall_status": overall,
    }

    statement.reconciliation_result = result
    db.flush()

    return result


def get_classification_breakdown(db: Session, statement_id: int, org_id: int) -> dict:
    by_right = db.query(
        RoyaltyStatementLine.canonical_right_category,
        func.sum(RoyaltyStatementLine.net_amount).label("total_net"),
        func.count(RoyaltyStatementLine.id).label("count"),
    ).filter(
        RoyaltyStatementLine.statement_id == statement_id,
        RoyaltyStatementLine.org_id == org_id,
    ).group_by(RoyaltyStatementLine.canonical_right_category).all()

    by_channel = db.query(
        RoyaltyStatementLine.canonical_channel,
        func.sum(RoyaltyStatementLine.net_amount).label("total_net"),
        func.count(RoyaltyStatementLine.id).label("count"),
    ).filter(
        RoyaltyStatementLine.statement_id == statement_id,
        RoyaltyStatementLine.org_id == org_id,
    ).group_by(RoyaltyStatementLine.canonical_channel).all()

    by_territory = db.query(
        RoyaltyStatementLine.territory_iso2,
        func.sum(RoyaltyStatementLine.net_amount).label("total_net"),
        func.count(RoyaltyStatementLine.id).label("count"),
    ).filter(
        RoyaltyStatementLine.statement_id == statement_id,
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.territory_iso2.isnot(None),
    ).group_by(RoyaltyStatementLine.territory_iso2).order_by(
        func.sum(RoyaltyStatementLine.net_amount).desc()
    ).limit(20).all()

    return {
        "by_right_category": [
            {"category": r.canonical_right_category or "unclassified", "net_total": round(float(r.total_net or 0), 2), "line_count": r.count}
            for r in by_right
        ],
        "by_channel": [
            {"channel": r.canonical_channel or "unclassified", "net_total": round(float(r.total_net or 0), 2), "line_count": r.count}
            for r in by_channel
        ],
        "by_territory": [
            {"territory": r.territory_iso2 or "unknown", "net_total": round(float(r.total_net or 0), 2), "line_count": r.count}
            for r in by_territory
        ],
    }


def get_match_summary(db: Session, statement_id: int, org_id: int) -> dict:
    statuses = db.query(
        RoyaltyStatementLine.match_status,
        func.count(RoyaltyStatementLine.id).label("count"),
        func.sum(RoyaltyStatementLine.net_amount).label("total_net"),
    ).filter(
        RoyaltyStatementLine.statement_id == statement_id,
        RoyaltyStatementLine.org_id == org_id,
    ).group_by(RoyaltyStatementLine.match_status).all()

    return {
        "match_summary": [
            {"status": s.match_status, "count": s.count, "net_total": round(float(s.total_net or 0), 2)}
            for s in statuses
        ]
    }
