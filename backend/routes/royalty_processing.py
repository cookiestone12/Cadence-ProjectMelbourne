from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
from difflib import SequenceMatcher
import csv
import io
import json
import logging

from ..models import (
    get_db, User, OrganizationMember, Song, Work, Release, Creator,
    Contract, ContractAsset, RightsSplit,
    RoyaltyStatement, RoyaltyTransaction,
    RoyaltyStatementLine, RoyaltyProcessingRun, RoyaltyLedgerEntry,
    Payee, AdvanceV2, PayoutBatch, PayoutItem,
)
from ..utils.auth import get_current_user
from ..services.royalty_processing_engine import (
    parse_statement_to_lines,
    auto_match_lines,
    confirm_match,
    reject_match,
    ignore_line,
    bulk_confirm_high_confidence,
    get_allocation_preview,
    process_statement,
    reprocess_statement,
    get_payee_balance,
    record_payment_ledger,
    generate_statement_action_items,
    generate_reprocess_action_item,
)
from ..services.reconciliation_engine import (
    run_control_totals,
    get_classification_breakdown,
    get_match_summary,
)
from ..services.decay_analytics_engine import (
    get_portfolio_analytics,
    get_song_analytics,
    build_time_series,
    fit_exponential_decay,
    compute_cagr,
)
from .royalties import parse_uploaded_file, suggest_column_mapping, detect_pro_source

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/royalty-processing", tags=["royalty-processing"])


def verify_org_access(user: User, org_id: int, db: Session):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


class ConfirmMatchRequest(BaseModel):
    song_id: int
    work_id: Optional[int] = None
    release_id: Optional[int] = None


class BulkConfirmRequest(BaseModel):
    threshold: float = 85.0


class ReprocessRequest(BaseModel):
    reason: str


class PayeeCreateRequest(BaseModel):
    payee_type: str
    creator_id: Optional[int] = None
    company_name: Optional[str] = None
    contact_email: Optional[str] = None


class AdvanceCreateRequest(BaseModel):
    contract_id: Optional[int] = None
    payee_id: Optional[int] = None
    advance_name: str
    advance_date: Optional[date] = None
    currency: str = "USD"
    principal_amount_cents: int
    recoupable: bool = True
    recoupment_pool: str
    recoupment_priority: int = 1
    cross_collateralize: bool = False
    start_recouping_on: Optional[date] = None
    end_recouping_on: Optional[date] = None
    notes: Optional[str] = None


class AdvanceUpdateRequest(BaseModel):
    contract_id: Optional[int] = None
    advance_name: Optional[str] = None
    advance_date: Optional[date] = None
    currency: Optional[str] = None
    principal_amount_cents: Optional[int] = None
    recoupable: Optional[bool] = None
    recoupment_pool: Optional[str] = None
    recoupment_priority: Optional[int] = None
    cross_collateralize: Optional[bool] = None
    start_recouping_on: Optional[date] = None
    end_recouping_on: Optional[date] = None
    notes: Optional[str] = None


class PayoutBatchCreateRequest(BaseModel):
    name: str
    currency: str = "USD"


class PayoutItemCreateRequest(BaseModel):
    payee_id: int
    amount_cents: int
    memo: Optional[str] = None


class PayoutBatchStatusUpdate(BaseModel):
    status: str


# --- Statement Lines ---

@router.get("/{org_id}/statements/{statement_id}/lines")
def list_statement_lines(
    org_id: int,
    statement_id: int,
    match_status: Optional[str] = None,
    search: Optional[str] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    query = db.query(RoyaltyStatementLine).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.statement_id == statement_id,
    )
    if match_status:
        query = query.filter(RoyaltyStatementLine.match_status == match_status)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                RoyaltyStatementLine.track_title_raw.ilike(search_term),
                RoyaltyStatementLine.artist_name_raw.ilike(search_term),
                RoyaltyStatementLine.isrc.ilike(search_term),
            )
        )

    total = query.count()
    lines = query.order_by(RoyaltyStatementLine.id).offset(offset).limit(limit).all()

    results = []
    for line in lines:
        song_title = None
        if line.matched_song_id:
            song = db.query(Song).filter(Song.id == line.matched_song_id).first()
            if song:
                song_title = song.title
        results.append({
            "id": line.id,
            "statement_id": line.statement_id,
            "isrc": line.isrc,
            "upc": line.upc,
            "iswc": line.iswc,
            "track_title_raw": line.track_title_raw,
            "artist_name_raw": line.artist_name_raw,
            "release_title_raw": line.release_title_raw,
            "label_raw": line.label_raw,
            "territory": line.territory,
            "store": line.store,
            "revenue_type": line.revenue_type,
            "unit_count": line.unit_count,
            "gross_amount": line.gross_amount,
            "net_amount": line.net_amount,
            "currency": line.currency,
            "net_amount_statement_currency": line.net_amount_statement_currency,
            "matched_song_id": line.matched_song_id,
            "matched_song_title": song_title,
            "matched_work_id": line.matched_work_id,
            "matched_release_id": line.matched_release_id,
            "match_status": line.match_status,
            "match_confidence": line.match_confidence,
            "match_method": line.match_method,
            "matched_at": line.matched_at.isoformat() if line.matched_at else None,
            "created_at": line.created_at.isoformat() if line.created_at else None,
        })

    return {"total": total, "offset": offset, "limit": limit, "lines": results}


@router.get("/{org_id}/statements/{statement_id}/lines/stats")
def get_statement_line_stats(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    status_counts = db.query(
        RoyaltyStatementLine.match_status,
        func.count(RoyaltyStatementLine.id),
        func.coalesce(func.sum(RoyaltyStatementLine.net_amount), 0),
    ).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.statement_id == statement_id,
    ).group_by(RoyaltyStatementLine.match_status).all()

    counts = {}
    total_amount = 0.0
    total_lines = 0
    for status, count, amount in status_counts:
        counts[status] = {"count": count, "total_amount": float(amount)}
        total_amount += float(amount)
        total_lines += count

    return {
        "total_lines": total_lines,
        "total_amount": total_amount,
        "by_status": counts,
    }


# --- Matching ---

@router.post("/{org_id}/statements/{statement_id}/auto-match")
def trigger_auto_match(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    stats = auto_match_lines(db, statement_id, org_id)

    status_counts = dict(
        db.query(RoyaltyStatementLine.match_status, func.count(RoyaltyStatementLine.id))
        .filter(
            RoyaltyStatementLine.org_id == org_id,
            RoyaltyStatementLine.statement_id == statement_id,
        )
        .group_by(RoyaltyStatementLine.match_status)
        .all()
    )

    total_matched = sum(status_counts.get(s, 0) for s in ("MATCHED", "CONFIRMED", "AUTO_MATCHED"))
    total_review = status_counts.get("REVIEW_REQUIRED", 0)
    total_unmatched = status_counts.get("UNMATCHED", 0)

    if total_unmatched == 0 and total_review == 0:
        stmt.status = "FULLY_MATCHED"
    elif total_unmatched == 0:
        stmt.status = "REVIEW_REQUIRED"
    else:
        stmt.status = "PARTIALLY_MATCHED"

    stmt.matched_transactions = total_matched + total_review
    stmt.unmatched_transactions = total_unmatched

    db.commit()
    return {"success": True, "stats": stats, "status": stmt.status}


@router.post("/{org_id}/lines/{line_id}/confirm-match")
def confirm_line_match(
    org_id: int,
    line_id: int,
    body: ConfirmMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    try:
        confirm_match(db, line_id, org_id, body.song_id, current_user.id, body.work_id, body.release_id)
        db.commit()
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{org_id}/lines/{line_id}/reject-match")
def reject_line_match(
    org_id: int,
    line_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    try:
        reject_match(db, line_id, org_id)
        db.commit()
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{org_id}/lines/{line_id}/ignore")
def ignore_statement_line(
    org_id: int,
    line_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    try:
        ignore_line(db, line_id, org_id)
        db.commit()
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{org_id}/statements/{statement_id}/bulk-confirm")
def bulk_confirm_matches(
    org_id: int,
    statement_id: int,
    body: BulkConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    count = bulk_confirm_high_confidence(db, statement_id, org_id, body.threshold, current_user.id)
    db.commit()
    return {"success": True, "confirmed_count": count}


@router.get("/{org_id}/lines/{line_id}/suggestions")
def get_match_suggestions(
    org_id: int,
    line_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    line = db.query(RoyaltyStatementLine).filter(
        RoyaltyStatementLine.id == line_id,
        RoyaltyStatementLine.org_id == org_id,
    ).first()
    if not line:
        raise HTTPException(status_code=404, detail="Statement line not found")

    org_songs = db.query(Song).filter(Song.organization_id == org_id).all()
    candidates = []

    for song in org_songs:
        score = 0.0

        if line.isrc and song.isrc:
            clean_line_isrc = line.isrc.strip().upper().replace("-", "")
            clean_song_isrc = song.isrc.strip().upper().replace("-", "")
            if clean_line_isrc == clean_song_isrc:
                score = 100.0
                candidates.append({
                    "song_id": song.id,
                    "title": song.title,
                    "primary_artist": song.primary_artist,
                    "isrc": song.isrc,
                    "confidence": score,
                    "match_method": "ISRC",
                })
                continue

        title_score = 0.0
        if line.track_title_raw and song.title:
            title_score = SequenceMatcher(None, line.track_title_raw.lower().strip(), song.title.lower().strip()).ratio()

        artist_score = 0.0
        if line.artist_name_raw and song.primary_artist:
            artist_score = SequenceMatcher(None, line.artist_name_raw.lower().strip(), song.primary_artist.lower().strip()).ratio()

        if title_score > 0 or artist_score > 0:
            if artist_score > 0:
                score = (title_score * 0.6 + artist_score * 0.4) * 100.0
            else:
                score = title_score * 100.0

        if score >= 30.0:
            candidates.append({
                "song_id": song.id,
                "title": song.title,
                "primary_artist": song.primary_artist,
                "isrc": song.isrc,
                "confidence": round(score, 2),
                "match_method": "FUZZY",
            })

    candidates.sort(key=lambda x: x["confidence"], reverse=True)
    return {"line_id": line_id, "suggestions": candidates[:10]}


# --- Processing ---

@router.get("/{org_id}/statements/{statement_id}/allocation-preview")
def get_statement_allocation_preview(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    preview = get_allocation_preview(db, statement_id, org_id)
    return {"statement_id": statement_id, "allocations": preview}


@router.post("/{org_id}/statements/{statement_id}/process")
def process_statement_endpoint(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    try:
        run_id = process_statement(db, statement_id, org_id, current_user.id)
        try:
            generate_statement_action_items(db, statement_id, org_id)
        except Exception:
            pass
        db.commit()
        run = db.query(RoyaltyProcessingRun).filter(RoyaltyProcessingRun.id == run_id).first()
        return {
            "success": True,
            "processing_run": {
                "id": run.id,
                "run_version": run.run_version,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "summary": run.summary_json,
            } if run else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{org_id}/statements/{statement_id}/reprocess")
def reprocess_statement_endpoint(
    org_id: int,
    statement_id: int,
    body: ReprocessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    try:
        run_id = reprocess_statement(db, statement_id, org_id, current_user.id, body.reason)
        try:
            generate_reprocess_action_item(db, statement_id, org_id, run_id)
        except Exception:
            pass
        db.commit()
        run = db.query(RoyaltyProcessingRun).filter(RoyaltyProcessingRun.id == run_id).first()
        return {
            "success": True,
            "processing_run": {
                "id": run.id,
                "run_version": run.run_version,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "summary": run.summary_json,
            } if run else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{org_id}/statements/{statement_id}/runs")
def list_processing_runs(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    runs = db.query(RoyaltyProcessingRun).filter(
        RoyaltyProcessingRun.org_id == org_id,
        RoyaltyProcessingRun.statement_id == statement_id,
    ).order_by(desc(RoyaltyProcessingRun.run_version)).all()

    return {
        "runs": [
            {
                "id": r.id,
                "run_version": r.run_version,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "started_by_user_id": r.started_by_user_id,
                "notes": r.notes,
                "summary": r.summary_json,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ]
    }


# --- Payees ---

@router.get("/{org_id}/payees")
def list_payees(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    payees = db.query(Payee).filter(Payee.org_id == org_id).all()

    results = []
    for p in payees:
        balance = get_payee_balance(db, p.id, org_id)
        creator_name = None
        if p.creator_id:
            creator = db.query(Creator).filter(Creator.id == p.creator_id).first()
            if creator:
                creator_name = creator.display_name
        results.append({
            "id": p.id,
            "payee_type": p.payee_type,
            "creator_id": p.creator_id,
            "creator_name": creator_name,
            "company_name": p.company_name,
            "contact_email": p.contact_email,
            "balance": balance,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return {"payees": results}


@router.post("/{org_id}/payees")
def create_payee(
    org_id: int,
    body: PayeeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    payee = Payee(
        org_id=org_id,
        payee_type=body.payee_type,
        creator_id=body.creator_id,
        company_name=body.company_name,
        contact_email=body.contact_email,
    )
    db.add(payee)
    db.commit()
    db.refresh(payee)
    return {
        "id": payee.id,
        "payee_type": payee.payee_type,
        "creator_id": payee.creator_id,
        "company_name": payee.company_name,
        "contact_email": payee.contact_email,
        "created_at": payee.created_at.isoformat() if payee.created_at else None,
    }


@router.get("/{org_id}/payees/{payee_id}/ledger")
def get_payee_ledger(
    org_id: int,
    payee_id: int,
    entry_type: Optional[str] = None,
    statement_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(RoyaltyLedgerEntry).filter(
        RoyaltyLedgerEntry.org_id == org_id,
        RoyaltyLedgerEntry.payee_id == payee_id,
    )
    if entry_type:
        query = query.filter(RoyaltyLedgerEntry.entry_type == entry_type)
    if statement_id:
        query = query.filter(RoyaltyLedgerEntry.statement_id == statement_id)
    if date_from:
        try:
            query = query.filter(RoyaltyLedgerEntry.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(RoyaltyLedgerEntry.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    total = query.count()
    entries = query.order_by(desc(RoyaltyLedgerEntry.created_at)).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "entries": [
            {
                "id": e.id,
                "statement_id": e.statement_id,
                "statement_line_id": e.statement_line_id,
                "processing_run_id": e.processing_run_id,
                "song_id": e.song_id,
                "work_id": e.work_id,
                "release_id": e.release_id,
                "contract_id": e.contract_id,
                "payee_id": e.payee_id,
                "entry_type": e.entry_type,
                "revenue_type": e.revenue_type,
                "source": e.source,
                "amount_cents": e.amount_cents,
                "amount_dollars": e.amount_cents / 100.0,
                "advance_id": e.advance_id,
                "recoupment_pool": e.recoupment_pool,
                "memo": e.memo,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
    }


# --- Payables ---

@router.get("/{org_id}/payables")
def list_payables(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    payees = db.query(Payee).filter(Payee.org_id == org_id).all()

    results = []
    for p in payees:
        balance = get_payee_balance(db, p.id, org_id)
        if balance["current_balance_cents"] <= 0:
            continue

        creator_name = None
        if p.creator_id:
            creator = db.query(Creator).filter(Creator.id == p.creator_id).first()
            if creator:
                creator_name = creator.display_name

        outstanding_advances = db.query(AdvanceV2).filter(
            AdvanceV2.org_id == org_id,
            AdvanceV2.payee_id == p.id,
            AdvanceV2.recoupable == True,
            AdvanceV2.outstanding_balance_cents > 0,
        ).all()

        last_statement_entry = db.query(RoyaltyLedgerEntry).filter(
            RoyaltyLedgerEntry.org_id == org_id,
            RoyaltyLedgerEntry.payee_id == p.id,
        ).order_by(desc(RoyaltyLedgerEntry.created_at)).first()

        last_statement_info = None
        if last_statement_entry and last_statement_entry.statement_id:
            stmt = db.query(RoyaltyStatement).filter(
                RoyaltyStatement.id == last_statement_entry.statement_id
            ).first()
            if stmt:
                last_statement_info = {
                    "id": stmt.id,
                    "source_name": stmt.source_name,
                    "period_end": stmt.period_end.isoformat() if stmt.period_end else None,
                }

        results.append({
            "payee_id": p.id,
            "payee_type": p.payee_type,
            "creator_id": p.creator_id,
            "creator_name": creator_name,
            "company_name": p.company_name,
            "contact_email": p.contact_email,
            "balance": balance,
            "outstanding_advances": [
                {
                    "id": a.id,
                    "advance_name": a.advance_name,
                    "principal_amount_cents": a.principal_amount_cents,
                    "outstanding_balance_cents": a.outstanding_balance_cents,
                }
                for a in outstanding_advances
            ],
            "last_statement": last_statement_info,
        })

    return {"payables": results}


# --- Advances ---

@router.get("/{org_id}/advances")
def list_advances(
    org_id: int,
    contract_id: Optional[int] = None,
    payee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(AdvanceV2).filter(AdvanceV2.org_id == org_id)
    if contract_id:
        query = query.filter(AdvanceV2.contract_id == contract_id)
    if payee_id:
        query = query.filter(AdvanceV2.payee_id == payee_id)

    advances = query.order_by(desc(AdvanceV2.created_at)).all()
    return {
        "advances": [
            {
                "id": a.id,
                "contract_id": a.contract_id,
                "payee_id": a.payee_id,
                "advance_name": a.advance_name,
                "advance_date": a.advance_date.isoformat() if a.advance_date else None,
                "currency": a.currency,
                "principal_amount_cents": a.principal_amount_cents,
                "outstanding_balance_cents": a.outstanding_balance_cents,
                "recoupable": a.recoupable,
                "recoupment_pool": a.recoupment_pool,
                "recoupment_priority": a.recoupment_priority,
                "cross_collateralize": a.cross_collateralize,
                "start_recouping_on": a.start_recouping_on.isoformat() if a.start_recouping_on else None,
                "end_recouping_on": a.end_recouping_on.isoformat() if a.end_recouping_on else None,
                "notes": a.notes,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in advances
        ]
    }


@router.post("/{org_id}/advances")
def create_advance(
    org_id: int,
    body: AdvanceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    advance = AdvanceV2(
        org_id=org_id,
        contract_id=body.contract_id,
        payee_id=body.payee_id,
        advance_name=body.advance_name,
        advance_date=body.advance_date,
        currency=body.currency,
        principal_amount_cents=body.principal_amount_cents,
        outstanding_balance_cents=body.principal_amount_cents,
        recoupable=body.recoupable,
        recoupment_pool=body.recoupment_pool,
        recoupment_priority=body.recoupment_priority,
        cross_collateralize=body.cross_collateralize,
        start_recouping_on=body.start_recouping_on,
        end_recouping_on=body.end_recouping_on,
        notes=body.notes,
        created_by_user_id=current_user.id,
    )
    db.add(advance)
    db.commit()
    db.refresh(advance)
    return {
        "id": advance.id,
        "advance_name": advance.advance_name,
        "principal_amount_cents": advance.principal_amount_cents,
        "outstanding_balance_cents": advance.outstanding_balance_cents,
        "created_at": advance.created_at.isoformat() if advance.created_at else None,
    }


@router.put("/{org_id}/advances/{advance_id}")
def update_advance(
    org_id: int,
    advance_id: int,
    body: AdvanceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    advance = db.query(AdvanceV2).filter(
        AdvanceV2.id == advance_id,
        AdvanceV2.org_id == org_id,
    ).first()
    if not advance:
        raise HTTPException(status_code=404, detail="Advance not found")

    has_recoupment = db.query(RoyaltyLedgerEntry).filter(
        RoyaltyLedgerEntry.org_id == org_id,
        RoyaltyLedgerEntry.advance_id == advance_id,
        RoyaltyLedgerEntry.entry_type == "RECOUPMENT_APPLIED",
    ).first()
    if has_recoupment:
        raise HTTPException(status_code=400, detail="Cannot update advance after recoupment has been applied")

    update_data = body.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(advance, field, value)

    if "principal_amount_cents" in update_data:
        advance.outstanding_balance_cents = update_data["principal_amount_cents"]

    db.commit()
    db.refresh(advance)
    return {
        "id": advance.id,
        "advance_name": advance.advance_name,
        "principal_amount_cents": advance.principal_amount_cents,
        "outstanding_balance_cents": advance.outstanding_balance_cents,
        "updated": True,
    }


@router.get("/{org_id}/advances/{advance_id}")
def get_advance_detail(
    org_id: int,
    advance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    advance = db.query(AdvanceV2).filter(
        AdvanceV2.id == advance_id,
        AdvanceV2.org_id == org_id,
    ).first()
    if not advance:
        raise HTTPException(status_code=404, detail="Advance not found")

    recoupment_entries = db.query(RoyaltyLedgerEntry).filter(
        RoyaltyLedgerEntry.org_id == org_id,
        RoyaltyLedgerEntry.advance_id == advance_id,
    ).order_by(desc(RoyaltyLedgerEntry.created_at)).all()

    return {
        "id": advance.id,
        "contract_id": advance.contract_id,
        "payee_id": advance.payee_id,
        "advance_name": advance.advance_name,
        "advance_date": advance.advance_date.isoformat() if advance.advance_date else None,
        "currency": advance.currency,
        "principal_amount_cents": advance.principal_amount_cents,
        "outstanding_balance_cents": advance.outstanding_balance_cents,
        "recoupable": advance.recoupable,
        "recoupment_pool": advance.recoupment_pool,
        "recoupment_priority": advance.recoupment_priority,
        "cross_collateralize": advance.cross_collateralize,
        "start_recouping_on": advance.start_recouping_on.isoformat() if advance.start_recouping_on else None,
        "end_recouping_on": advance.end_recouping_on.isoformat() if advance.end_recouping_on else None,
        "notes": advance.notes,
        "created_at": advance.created_at.isoformat() if advance.created_at else None,
        "recoupment_history": [
            {
                "id": e.id,
                "entry_type": e.entry_type,
                "amount_cents": e.amount_cents,
                "amount_dollars": e.amount_cents / 100.0,
                "memo": e.memo,
                "statement_id": e.statement_id,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in recoupment_entries
        ],
    }


# --- Payout Batches ---

@router.get("/{org_id}/payout-batches")
def list_payout_batches(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    batches = db.query(PayoutBatch).filter(
        PayoutBatch.org_id == org_id
    ).order_by(desc(PayoutBatch.created_at)).all()

    results = []
    for b in batches:
        item_count = db.query(func.count(PayoutItem.id)).filter(
            PayoutItem.batch_id == b.id,
            PayoutItem.org_id == org_id,
        ).scalar()
        total_cents = db.query(func.coalesce(func.sum(PayoutItem.amount_cents), 0)).filter(
            PayoutItem.batch_id == b.id,
            PayoutItem.org_id == org_id,
        ).scalar()
        results.append({
            "id": b.id,
            "name": b.name,
            "currency": b.currency,
            "status": b.status,
            "item_count": item_count,
            "total_cents": total_cents,
            "total_dollars": total_cents / 100.0,
            "created_by_user_id": b.created_by_user_id,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "updated_at": b.updated_at.isoformat() if b.updated_at else None,
        })

    return {"batches": results}


@router.post("/{org_id}/payout-batches")
def create_payout_batch(
    org_id: int,
    body: PayoutBatchCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    batch = PayoutBatch(
        org_id=org_id,
        name=body.name,
        currency=body.currency,
        status="DRAFT",
        created_by_user_id=current_user.id,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return {
        "id": batch.id,
        "name": batch.name,
        "currency": batch.currency,
        "status": batch.status,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
    }


@router.post("/{org_id}/payout-batches/{batch_id}/items")
def add_payout_item(
    org_id: int,
    batch_id: int,
    body: PayoutItemCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    batch = db.query(PayoutBatch).filter(
        PayoutBatch.id == batch_id,
        PayoutBatch.org_id == org_id,
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Payout batch not found")
    if batch.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Can only add items to DRAFT batches")

    item = PayoutItem(
        org_id=org_id,
        batch_id=batch_id,
        payee_id=body.payee_id,
        amount_cents=body.amount_cents,
        memo=body.memo,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "id": item.id,
        "batch_id": item.batch_id,
        "payee_id": item.payee_id,
        "amount_cents": item.amount_cents,
        "memo": item.memo,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.put("/{org_id}/payout-batches/{batch_id}/status")
def update_payout_batch_status(
    org_id: int,
    batch_id: int,
    body: PayoutBatchStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    batch = db.query(PayoutBatch).filter(
        PayoutBatch.id == batch_id,
        PayoutBatch.org_id == org_id,
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Payout batch not found")

    valid_transitions = {
        "DRAFT": ["APPROVED"],
        "APPROVED": ["PAID", "DRAFT"],
        "PAID": [],
    }
    allowed = valid_transitions.get(batch.status, [])
    if body.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {batch.status} to {body.status}",
        )

    batch.status = body.status

    if body.status == "PAID":
        items = db.query(PayoutItem).filter(
            PayoutItem.batch_id == batch_id,
            PayoutItem.org_id == org_id,
        ).all()
        for item in items:
            record_payment_ledger(db, item.id, org_id, current_user.id)

    db.commit()
    return {"success": True, "batch_id": batch_id, "status": batch.status}


# --- Processing Inbox ---

@router.get("/{org_id}/inbox")
def get_processing_inbox(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    status_counts = db.query(
        RoyaltyStatement.status,
        func.count(RoyaltyStatement.id),
    ).filter(
        RoyaltyStatement.organization_id == org_id,
    ).group_by(RoyaltyStatement.status).all()

    counts = {status: count for status, count in status_counts}
    total = sum(counts.values())
    return {"total_statements": total, "by_status": counts}


# --- Exports ---

@router.get("/{org_id}/statements/{statement_id}/export/unmatched")
def export_unmatched_lines(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    lines = db.query(RoyaltyStatementLine).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.statement_id == statement_id,
        RoyaltyStatementLine.match_status == "UNMATCHED",
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "ISRC", "UPC", "Track Title", "Artist", "Release", "Territory", "Store", "Revenue Type", "Net Amount", "Currency"])
    for line in lines:
        writer.writerow([
            line.id, line.isrc, line.upc, line.track_title_raw, line.artist_name_raw,
            line.release_title_raw, line.territory, line.store, line.revenue_type,
            line.net_amount, line.currency,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=unmatched_lines_{statement_id}.csv"},
    )


@router.get("/{org_id}/statements/{statement_id}/export/allocation")
def export_allocation_preview(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    preview = get_allocation_preview(db, statement_id, org_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Payee ID", "Payee Name", "Payee Type", "Earnings (cents)", "Fees (cents)", "Recoupment (cents)", "Payable (cents)"])
    for row in preview:
        writer.writerow([
            row["payee_id"], row["payee_name"], row["payee_type"],
            row["earnings_cents"], row["fees_cents"], row["recoupment_cents"], row["payable_cents"],
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=allocation_preview_{statement_id}.csv"},
    )


@router.get("/{org_id}/statements/{statement_id}/export/payables")
def export_payables_report(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    entries = db.query(RoyaltyLedgerEntry).filter(
        RoyaltyLedgerEntry.org_id == org_id,
        RoyaltyLedgerEntry.statement_id == statement_id,
        RoyaltyLedgerEntry.entry_type == "PAYABLE_CREATED",
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Entry ID", "Payee ID", "Song ID", "Amount (cents)", "Revenue Type", "Source", "Memo", "Created At"])
    for e in entries:
        writer.writerow([
            e.id, e.payee_id, e.song_id, e.amount_cents,
            e.revenue_type, e.source, e.memo,
            e.created_at.isoformat() if e.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=payables_report_{statement_id}.csv"},
    )


# --- Statement Upload Enhancement ---

@router.post("/{org_id}/statements/upload")
async def upload_and_parse_statement(
    org_id: int,
    file: UploadFile = File(...),
    source_name: str = Form(...),
    source_type: Optional[str] = Form(None),
    period_start: Optional[str] = Form(None),
    period_end: Optional[str] = Form(None),
    currency: str = Form("USD"),
    column_mapping: Optional[str] = Form(None),
    creator_id: Optional[int] = Form(None),
    auto_match: Optional[str] = Form("true"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    content = await file.read()
    try:
        headers, rows, pdf_metadata = parse_uploaded_file(content, file.filename or "data.csv", org_id=org_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File parsing crashed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    suggested = pdf_metadata.get("suggested_mapping") if pdf_metadata else None
    if suggested:
        mapping = suggested
    elif column_mapping:
        try:
            mapping = json.loads(column_mapping)
        except Exception:
            mapping = suggest_column_mapping(headers, source_name or "")
    else:
        detected_source = detect_pro_source(headers, source_name or "")
        mapping = suggest_column_mapping(headers, source_name or "")

    p_start = None
    p_end = None
    if period_start:
        try:
            p_start = date.fromisoformat(period_start)
        except ValueError:
            pass
    if period_end:
        try:
            p_end = date.fromisoformat(period_end)
        except ValueError:
            pass

    statement = RoyaltyStatement(
        organization_id=org_id,
        source_name=source_name,
        source_type=source_type,
        period_start=p_start,
        period_end=p_end,
        currency=currency,
        file_name=file.filename,
        status="PROCESSING",
        column_mapping=mapping,
        uploaded_by_user_id=current_user.id,
        creator_id=creator_id,
    )
    db.add(statement)
    db.flush()

    line_count = parse_statement_to_lines(db, statement.id, org_id, mapping, rows, pdf_metadata=pdf_metadata)

    statement.status = "UPLOADED"
    db.flush()

    should_auto_match = auto_match.lower() in ("true", "1", "yes")
    match_stats = {}

    if should_auto_match:
        match_stats = auto_match_lines(db, statement.id, org_id)

        matched = match_stats.get("auto_matched", 0)
        review = match_stats.get("review_required", 0)
        unmatched = match_stats.get("unmatched", 0)

        if unmatched == 0 and review == 0:
            statement.status = "FULLY_MATCHED"
        elif unmatched == 0:
            statement.status = "REVIEW_REQUIRED"
        else:
            statement.status = "PARTIALLY_MATCHED"

        statement.matched_transactions = matched + review
        statement.unmatched_transactions = unmatched

    try:
        generate_statement_action_items(db, statement.id, org_id)
    except Exception:
        pass

    db.commit()
    db.refresh(statement)

    return {
        "id": statement.id,
        "status": statement.status,
        "total_lines": line_count,
        "match_stats": match_stats,
        "column_mapping": mapping,
    }


@router.get("/{org_id}/statements/{statement_id}/reconciliation")
def get_reconciliation(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    result = run_control_totals(db, statement_id, org_id)
    return result


@router.get("/{org_id}/statements/{statement_id}/classification")
def get_statement_classification(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    return get_classification_breakdown(db, statement_id, org_id)


@router.get("/{org_id}/statements/{statement_id}/match-summary")
def get_statement_match_summary(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    return get_match_summary(db, statement_id, org_id)


@router.post("/{org_id}/statements/{statement_id}/set-reported-totals")
def set_reported_totals(
    org_id: int,
    statement_id: int,
    gross: Optional[float] = None,
    withholding: Optional[float] = None,
    net: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    statement = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    if gross is not None:
        statement.reported_gross = gross
    if withholding is not None:
        statement.reported_withholding = withholding
    if net is not None:
        statement.reported_net = net
    db.commit()
    return {"message": "Reported totals updated"}


@router.get("/{org_id}/analytics/portfolio")
def get_portfolio_analytics_endpoint(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    return get_portfolio_analytics(db, org_id)


@router.get("/{org_id}/analytics/song/{song_id}")
def get_song_analytics_endpoint(
    org_id: int,
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    return get_song_analytics(db, org_id, song_id)


@router.get("/{org_id}/analytics/time-series")
def get_time_series_endpoint(
    org_id: int,
    song_id: Optional[int] = Query(None),
    granularity: str = Query("quarter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    series = build_time_series(db, org_id, song_id=song_id, granularity=granularity)
    decay = fit_exponential_decay(series) if len(series) >= 3 else None
    cagr_result = compute_cagr(series) if len(series) >= 2 else None
    return {
        "time_series": series,
        "decay": decay,
        "cagr": cagr_result,
    }
