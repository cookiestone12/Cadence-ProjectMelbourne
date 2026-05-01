from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, case
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
from difflib import SequenceMatcher
from collections import defaultdict
import csv
import io
import json
import logging

from ..models import (
    get_db, User, OrganizationMember, Song, Work, Release, Creator,
    Contract, ContractAsset, RightsSplit,
    RoyaltyStatement, RoyaltyTransaction,
    RoyaltyStatementLine, RoyaltyProcessingRun, RoyaltyLedgerEntry,
    Payee, Advance, PayoutBatch, PayoutItem,
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

router = APIRouter(prefix="/api/royalty-processing", tags=["Royalty Processing"])


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

@router.get(
    "/{org_id}/statements/{statement_id}/lines",
    summary='List the parsed line items on a royalty statement',
    description='Returns the per-track/per-territory rows that were extracted when the statement file was uploaded. This is the workhorse list view for the matching/reconciliation UI.\n\n**Path parameters:** `org_id` — Organization ID; `statement_id` — RoyaltyStatement id.\n**Query:** `status` (`unmatched|matched|confirmed|ignored`), `q` (substring on title/artist/ISRC), `min_amount`, `max_amount`, `limit` (default 100), `offset`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ total, limit, offset, lines: [{id, track_title, artist, isrc, period, territory, amount_cents, currency, status, song_id, work_id, release_id, match_confidence}] }`.',
)
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

    line_count_check = db.query(func.count(RoyaltyStatementLine.id)).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.statement_id == statement_id,
    ).scalar() or 0

    if line_count_check == 0:
        tx_query = db.query(RoyaltyTransaction).filter(
            RoyaltyTransaction.statement_id == statement_id,
            RoyaltyTransaction.organization_id == org_id,
        )
        if match_status:
            tx_query = tx_query.filter(RoyaltyTransaction.match_status == match_status)
        if search:
            search_term = f"%{search}%"
            tx_query = tx_query.filter(
                or_(
                    RoyaltyTransaction.original_track_title.ilike(search_term),
                    RoyaltyTransaction.original_artist.ilike(search_term),
                    RoyaltyTransaction.original_isrc.ilike(search_term),
                )
            )
        total = tx_query.count()
        txs = tx_query.order_by(RoyaltyTransaction.id).offset(offset).limit(limit).all()
        results = []
        for tx in txs:
            song_title = None
            if tx.song_id:
                song = db.query(Song).filter(Song.id == tx.song_id).first()
                if song:
                    song_title = song.title
            results.append({
                "id": tx.id,
                "statement_id": tx.statement_id,
                "isrc": tx.original_isrc,
                "upc": tx.original_upc,
                "iswc": None,
                "track_title_raw": tx.original_track_title,
                "artist_name_raw": tx.original_artist,
                "release_title_raw": None,
                "label_raw": None,
                "territory": tx.territory,
                "store": tx.platform,
                "revenue_type": tx.revenue_type,
                "unit_count": tx.quantity,
                "gross_amount": None,
                "net_amount": tx.revenue_cents / 100.0 if tx.revenue_cents else 0.0,
                "currency": tx.currency,
                "net_amount_statement_currency": tx.revenue_cents / 100.0 if tx.revenue_cents else 0.0,
                "matched_song_id": tx.song_id,
                "matched_song_title": song_title,
                "matched_work_id": None,
                "matched_release_id": None,
                "match_status": tx.match_status or "UNMATCHED",
                "match_confidence": tx.match_confidence,
                "match_method": None,
                "matched_at": None,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
                "source": "transaction_fallback",
            })
        return {"total": total, "offset": offset, "limit": limit, "lines": results}

    query = db.query(RoyaltyStatementLine).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.statement_id == statement_id,
    )
    if match_status:
        if match_status == "MATCHED":
            query = query.filter(RoyaltyStatementLine.match_status.in_(["MATCHED", "AUTO_MATCHED"]))
        else:
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


@router.get(
    "/{org_id}/statements/{statement_id}/lines/stats",
    summary="Get aggregate counts and totals for a statement's lines",
    description='Returns the breakdown the matching dashboard renders along the top of the page: how many lines fall in each status bucket and what they sum to. Used to drive the progress bars and KPIs.\n\n**Path parameters:** `org_id`, `statement_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ total_lines, total_amount, by_status: { unmatched, suggested, confirmed, ignored } }` where each entry is `{ count, amount_cents }`.',
)
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

    line_exists = db.query(func.count(RoyaltyStatementLine.id)).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.statement_id == statement_id,
    ).scalar() or 0

    if line_exists == 0:
        status_counts = db.query(
            RoyaltyTransaction.match_status,
            func.count(RoyaltyTransaction.id),
            func.coalesce(func.sum(RoyaltyTransaction.revenue_cents), 0),
        ).filter(
            RoyaltyTransaction.statement_id == statement_id,
            RoyaltyTransaction.organization_id == org_id,
        ).group_by(RoyaltyTransaction.match_status).all()

        counts = {}
        total_amount = 0.0
        total_lines = 0
        for status, count, amount_cents in status_counts:
            amount_dollars = float(amount_cents) / 100.0
            display_status = "MATCHED" if status == "AUTO_MATCHED" else (status or "UNMATCHED")
            if display_status in counts:
                counts[display_status]["count"] += count
                counts[display_status]["total_amount"] += amount_dollars
            else:
                counts[display_status] = {"count": count, "total_amount": amount_dollars}
            total_amount += amount_dollars
            total_lines += count

        return {
            "total_lines": total_lines,
            "total_amount": total_amount,
            "by_status": counts,
        }

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
        display_status = "MATCHED" if status == "AUTO_MATCHED" else status
        if display_status in counts:
            counts[display_status]["count"] += count
            counts[display_status]["total_amount"] += float(amount)
        else:
            counts[display_status] = {"count": count, "total_amount": float(amount)}
        total_amount += float(amount)
        total_lines += count

    return {
        "total_lines": total_lines,
        "total_amount": total_amount,
        "by_status": counts,
    }


# --- Matching ---

@router.post(
    "/{org_id}/statements/{statement_id}/auto-match",
    summary='Run the auto-matcher across every line on a statement',
    description="Kicks off the auto-matching engine which fingerprints every unmatched line against the org's catalog (ISRC > exact title+artist > fuzzy title) and writes a suggested `song_id`/`work_id` plus a confidence score to each row. Lines already in `confirmed` or `ignored` are skipped. Synchronous.\n\n**Path parameters:** `org_id`, `statement_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ success: true, status, stats: { matched, high_confidence, low_confidence, unmatched } }`.",
)
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

    stmt.matched_transactions = total_matched + total_review
    stmt.unmatched_transactions = total_unmatched

    if stmt.status != "PROCESSED":
        if total_unmatched == 0 and total_review == 0:
            stmt.status = "FULLY_MATCHED"
        elif total_unmatched == 0:
            stmt.status = "REVIEW_REQUIRED"
        else:
            stmt.status = "PARTIALLY_MATCHED"

    db.commit()
    return {"success": True, "stats": stats, "status": stmt.status}


@router.post(
    "/{org_id}/lines/{line_id}/confirm-match",
    summary='Confirm a suggested match (or attach an explicit one) to a line',
    description="Locks in the song/work/release a statement line should pay out to. If the body specifies `song_id` it overrides whatever the auto-matcher suggested. Sets the line's status to `confirmed` and clears any pending suggestion.\n\n**Path parameters:** `org_id`, `line_id` — RoyaltyStatementLine id.\n**Body (`ConfirmMatchRequest`):** `song_id` (required), `work_id?`, `release_id?`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ success: true }`.",
)
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


@router.post(
    "/{org_id}/lines/{line_id}/reject-match",
    summary="Reject the auto-matcher's suggestion on a line",
    description='Clears the suggested song/work/release on a line and returns it to `unmatched` so a human can resolve it. Does **not** mark the line as ignored; use `/ignore` for that.\n\n**Path parameters:** `org_id`, `line_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ success: true }`.',
)
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


@router.post(
    "/{org_id}/lines/{line_id}/ignore",
    summary='Mark a statement line as intentionally unallocated',
    description="Sets the line's status to `ignored` so it stops appearing in the unmatched queue and is excluded from allocation. Useful for tax adjustments, recoupments already handled elsewhere, or garbage rows from the source file.\n\n**Path parameters:** `org_id`, `line_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ success: true }`.",
)
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


@router.post(
    "/{org_id}/statements/{statement_id}/bulk-confirm",
    summary='Bulk-confirm every high-confidence suggestion on a statement',
    description='Walks every line on the statement that has a `match_confidence` at or above the supplied threshold and confirms it in one shot. Designed to clear out the easy wins so reviewers can focus on the long tail.\n\n**Path parameters:** `org_id`, `statement_id`.\n**Body (`BulkConfirmRequest`):** `threshold` (0–100, default 85).\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ success: true, confirmed_count }`.',
)
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


@router.get(
    "/{org_id}/lines/{line_id}/suggestions",
    summary='Get ranked match candidates for a single statement line',
    description='Returns the top scoring catalog entries for a line so a human can pick the right one when the auto-matcher was uncertain. Combines ISRC/title/artist matching strategies.\n\n**Path parameters:** `org_id`, `line_id`.\n**Query:** `limit` (default 5).\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ line_id, suggestions: [{song_id, work_id, release_id, title, artist, isrc, confidence, reason}] }`.',
)
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

@router.get(
    "/{org_id}/statements/{statement_id}/allocation-preview",
    summary="Preview how a statement's revenue would split across rights-holders",
    description="Computes — without persisting — the per-payee allocation that `/process` would write to the ledger, by joining each confirmed line to its work's RightsSplits and applying advance recoupment rules. Use this to sanity-check before pulling the trigger.\n\n**Path parameters:** `org_id`, `statement_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ statement_id, is_processed, allocations: [{payee_id, payee_name, gross_cents, recouped_cents, net_cents, currency, lines: [...]}] }`.",
)
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

    result = get_allocation_preview(db, statement_id, org_id)
    return {
        "statement_id": statement_id,
        "allocations": result["allocations"],
        "is_processed": result["is_processed"],
    }


@router.post(
    "/{org_id}/statements/{statement_id}/process",
    summary='Process a statement: write ledger entries and recoup advances',
    description='Materializes the allocation preview into RoyaltyLedgerEntry rows for every payee, applies recoupment against any open advances in the configured pools, and marks the statement as `processed`. Idempotent on already-processed statements (use `/reprocess` to redo).\n\n**Path parameters:** `org_id`, `statement_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ success: true, processing_run: {id, started_at, completed_at, lines_processed, entries_written, advance_recoupments_cents} }`.',
)
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


@router.post(
    "/{org_id}/statements/{statement_id}/reprocess",
    summary='Reverse and re-run processing for an already-processed statement',
    description="Voids the prior RoyaltyProcessingRun's ledger entries (keeping an audit trail), then re-runs `/process` from scratch. Use when splits, advances, or matches have changed since the original processing.\n\n**Path parameters:** `org_id`, `statement_id`.\n**Body (`ReprocessRequest`):** `reason` — required free-text audit reason recorded on the new run.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ success: true, processing_run: {...} }`.",
)
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


@router.get(
    "/{org_id}/statements/{statement_id}/runs",
    summary='List every processing run for a statement',
    description='Returns the audit history of `/process` and `/reprocess` calls against a statement, newest first.\n\n**Path parameters:** `org_id`, `statement_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ runs: [{id, kind, started_at, completed_at, actor_user_id, reason, lines_processed, entries_written, voided_at, voided_by_run_id}] }` ordered by `started_at desc`.',
)
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


@router.get(
    "/{org_id}/reconciliation",
    summary="Org-wide royalty reconciliation report",
    description=(
        "Returns a per-statement reconciliation showing the variance between "
        "the statement header total, the sum of its line items, the ledger "
        "entries written by /process, and (if known) the PDF-stated grand "
        "total. Flags duplicates, $0-with-N-lines parser failures, missing "
        "periods, and statements marked PROCESSED that have no ledger.\n\n"
        "**Path parameter:** `org_id`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the org.\n\n"
        "**Response:** `{ totals: {...}, statements: [{id, file_name, header_total_cents, sum_of_lines_cents, ledger_total_cents, variance_cents, flags: [...]}], duplicate_groups: [...] }`."
    ),
)
def get_reconciliation_report(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    statements = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.organization_id == org_id,
    ).order_by(desc(RoyaltyStatement.id)).all()

    # Aggregate sum of lines + count of zero/non-zero lines per statement
    line_sums = dict(
        db.query(
            RoyaltyStatementLine.statement_id,
            func.coalesce(func.sum(RoyaltyStatementLine.net_amount), 0),
        )
        .filter(RoyaltyStatementLine.org_id == org_id)
        .group_by(RoyaltyStatementLine.statement_id)
        .all()
    )
    line_counts = {}
    for sid, n_total, n_zero in db.query(
        RoyaltyStatementLine.statement_id,
        func.count(RoyaltyStatementLine.id),
        func.sum(case((func.coalesce(RoyaltyStatementLine.net_amount, 0) == 0, 1), else_=0)),
    ).filter(RoyaltyStatementLine.org_id == org_id).group_by(RoyaltyStatementLine.statement_id).all():
        line_counts[sid] = (int(n_total or 0), int(n_zero or 0))

    ledger_sums = dict(
        db.query(
            RoyaltyLedgerEntry.statement_id,
            func.coalesce(func.sum(RoyaltyLedgerEntry.amount_cents), 0),
        )
        .filter(
            RoyaltyLedgerEntry.org_id == org_id,
            RoyaltyLedgerEntry.entry_type == "EARNING",
        )
        .group_by(RoyaltyLedgerEntry.statement_id)
        .all()
    )

    # Duplicate detection by file_name within the org
    dup_buckets = defaultdict(list)
    for s in statements:
        if s.file_name:
            dup_buckets[s.file_name].append(s.id)
    duplicate_ids = {
        sid for ids in dup_buckets.values() if len(ids) > 1 for sid in ids
    }
    duplicate_groups = [
        {"file_name": fn, "statement_ids": sorted(ids)}
        for fn, ids in dup_buckets.items() if len(ids) > 1
    ]

    rows = []
    grand_header = 0
    grand_lines_cents = 0
    grand_ledger = 0
    grand_assigned = 0
    grand_unassigned = 0
    flagged = 0
    for s in statements:
        header_cents = int(s.total_revenue_cents or 0)
        line_total_dollars = float(line_sums.get(s.id, 0) or 0)
        line_cents = int(round(line_total_dollars * 100))
        ledger_cents = int(ledger_sums.get(s.id, 0) or 0)
        n_total, n_zero = line_counts.get(s.id, (0, 0))

        # PDF cover-page grand total when the parser captured it on upload
        # (stored on RoyaltyStatement.reported_net / reported_gross, in dollars).
        pdf_grand_total_dollars = s.reported_net if s.reported_net is not None else s.reported_gross
        pdf_grand_total_cents = (
            int(round(float(pdf_grand_total_dollars) * 100))
            if pdf_grand_total_dollars is not None else None
        )

        flags = []
        if s.id in duplicate_ids:
            flags.append("DUPLICATE_FILE")
        if header_cents == 0 and n_total > 0:
            flags.append("ZERO_AMOUNT_HEADER")
        if n_total > 0 and n_zero == n_total:
            # Plan vocabulary alias — every line parsed as $0 means the parser
            # likely missed the amount column entirely.
            flags.append("ZERO_AMOUNT_LINES")
            flags.append("ALL_LINES_ZERO_AMOUNT")
        elif n_total > 0 and n_zero > 0:
            flags.append("SOME_LINES_ZERO_AMOUNT")
        if abs(header_cents - line_cents) > 1 and n_total > 0:
            flags.append("HEADER_VS_LINES_VARIANCE")
        # PDF cover-page total > sum-of-lines means the parser captured the
        # right header but missed individual line items (BMI 2023 case).
        if (
            pdf_grand_total_cents is not None
            and pdf_grand_total_cents > 0
            and abs(pdf_grand_total_cents - line_cents) > 1
            and pdf_grand_total_cents > line_cents
        ):
            flags.append("LINES_MISSING_AMOUNTS")
        if (s.status or "").upper() == "PROCESSED" and ledger_cents == 0 and header_cents > 0:
            # Plan vocabulary alias for the same condition.
            flags.append("LEDGER_MISSING")
            flags.append("PROCESSED_WITHOUT_LEDGER")
        if header_cents > 0 and ledger_cents > 0 and abs(header_cents - ledger_cents) > 1:
            flags.append("HEADER_VS_LEDGER_VARIANCE")
        if not s.period_start or not s.period_end:
            flags.append("PERIOD_MISSING")
        if s.creator_id is None:
            flags.append("UNASSIGNED")

        if flags:
            flagged += 1

        # Don't double-count duplicates in grand totals: keep the lowest id only
        is_dup_secondary = (
            s.id in duplicate_ids and s.file_name
            and s.id != min(dup_buckets[s.file_name])
        )

        if not is_dup_secondary:
            grand_header += header_cents
            grand_lines_cents += line_cents
            grand_ledger += ledger_cents
            if s.creator_id is not None:
                grand_assigned += header_cents
            else:
                grand_unassigned += header_cents

        rows.append({
            "id": s.id,
            "file_name": s.file_name,
            "source_name": s.source_name,
            "source_type": s.source_type,
            "status": s.status,
            "creator_id": s.creator_id,
            "uploaded_at": s.created_at.isoformat() if s.created_at else None,
            "period_start": s.period_start.isoformat() if s.period_start else None,
            "period_end": s.period_end.isoformat() if s.period_end else None,
            "header_total_cents": header_cents,
            "sum_of_lines_cents": line_cents,
            "ledger_total_cents": ledger_cents,
            "pdf_grand_total_cents": pdf_grand_total_cents,
            "variance_cents": header_cents - line_cents,
            "line_count": n_total,
            "zero_amount_line_count": n_zero,
            "flags": flags,
            "is_duplicate_secondary": is_dup_secondary,
        })

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "totals": {
            "statement_count": len(statements),
            "flagged_count": flagged,
            "duplicate_group_count": len(duplicate_groups),
            # Net of duplicate-secondaries — the figure that should match Reports.
            "header_total_cents_net_of_dupes": grand_header,
            "sum_of_lines_cents_net_of_dupes": grand_lines_cents,
            "ledger_total_cents_net_of_dupes": grand_ledger,
            "assigned_total_cents_net_of_dupes": grand_assigned,
            "unassigned_total_cents_net_of_dupes": grand_unassigned,
        },
        "statements": rows,
        "duplicate_groups": duplicate_groups,
    }


# --- Payees ---

@router.get(
    "/{org_id}/payees",
    summary="List the org's payees (creators and external companies)",
    description='Returns every Payee record — the abstraction that owns a royalty ledger balance. A payee is either backed by a Creator in the roster or an external `company` (label, sub-publisher, etc.).\n\n**Path parameter:** `org_id`.\n**Query:** `payee_type` (`creator|company`), `q` (name search).\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ payees: [{id, payee_type, creator_id, company_name, contact_email, balance_cents, currency, created_at}] }`.',
)
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


@router.post(
    "/{org_id}/payees",
    summary='Create a new payee (creator-backed or external company)',
    description='Adds a Payee that future allocations and payouts can post to. When `payee_type="creator"`, `creator_id` must reference a Creator in the org. When `payee_type="company"`, `company_name` must be supplied.\n\n**Path parameter:** `org_id`.\n**Body (`PayeeCreateRequest`):** `payee_type` (`creator|company`), `creator_id?`, `company_name?`, `contact_email?`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ id, payee_type, creator_id, company_name, contact_email, created_at }`.',
)
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


@router.get(
    "/{org_id}/payees/{payee_id}/ledger",
    summary="Get a payee's running royalty ledger",
    description='Returns every credit (allocation), debit (recoupment), and payout posted to the payee, chronological newest-first, with a running balance. This is the source of truth for what the org owes — or has paid — that payee.\n\n**Path parameters:** `org_id`, `payee_id`.\n**Query:** `limit` (default 100), `offset`, `start_date`, `end_date`, `entry_type` (`credit|debit|payout|advance`).\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ total, limit, offset, entries: [{id, posted_at, entry_type, amount_cents, running_balance_cents, currency, statement_id, processing_run_id, payout_item_id, advance_id, memo}] }`.',
)
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

@router.get(
    "/{org_id}/payables",
    summary='List current outstanding amounts owed to each payee',
    description='Returns the rolled-up `balance_cents` per payee — i.e. what would be paid out if a batch were cut today, after recoupment. Drives the "Payables" dashboard and the payout-batch builder.\n\n**Path parameter:** `org_id`.\n**Query:** `min_balance_cents` (default 0), `currency`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ payables: [{payee_id, payee_name, payee_type, balance_cents, currency, last_credit_at}] }` sorted by balance desc.',
)
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

        outstanding_advances = db.query(Advance).filter(
            Advance.org_id == org_id,
            Advance.payee_id == p.id,
            Advance.recoupable == True,
            Advance.outstanding_balance_cents > 0,
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

@router.get(
    "/{org_id}/advances",
    summary='List all advances (recoupable and non-recoupable) in the org',
    description='Returns every Advance record — the principal balances that future royalty allocations will recoup against, including their current recoupment status.\n\n**Path parameter:** `org_id`.\n**Query:** `payee_id`, `contract_id`, `recouped` (bool — only fully/partially recouped), `pool` (recoupment pool name).\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ advances: [{id, advance_name, advance_date, principal_amount_cents, recouped_amount_cents, outstanding_cents, currency, recoupment_pool, recoupment_priority, cross_collateralize, payee_id, contract_id, recoupable, start_recouping_on, end_recouping_on}] }`.',
)
def list_advances(
    org_id: int,
    contract_id: Optional[int] = None,
    payee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(Advance).filter(Advance.org_id == org_id)
    if contract_id:
        query = query.filter(Advance.contract_id == contract_id)
    if payee_id:
        query = query.filter(Advance.payee_id == payee_id)

    advances = query.order_by(desc(Advance.created_at)).all()
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


@router.post(
    "/{org_id}/advances",
    summary='Create a new advance against a payee or contract',
    description="Records an advance that will be recouped from future royalties in the given `recoupment_pool`. Set `cross_collateralize=true` to allow recoupment across all of the payee's pools.\n\n**Path parameter:** `org_id`.\n**Body (`AdvanceCreateRequest`):** `advance_name`, `principal_amount_cents`, `recoupment_pool`, `recoupment_priority` (default 1), `currency` (default USD), `recoupable` (default true), `cross_collateralize` (default false), `payee_id?`, `contract_id?`, `advance_date?`, `start_recouping_on?`, `end_recouping_on?`, `notes?`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** the created advance object.",
)
def create_advance(
    org_id: int,
    body: AdvanceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    advance = Advance(
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


@router.put(
    "/{org_id}/advances/{advance_id}",
    summary="Update an advance's metadata",
    description='Patches editable fields on an advance. Changing `principal_amount_cents` does **not** retroactively rewrite ledger entries — re-run `/reprocess` on affected statements if you need that.\n\n**Path parameters:** `org_id`, `advance_id`.\n**Body (`AdvanceUpdateRequest`):** any subset of writable fields from create.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** the updated advance object.',
)
def update_advance(
    org_id: int,
    advance_id: int,
    body: AdvanceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    advance = db.query(Advance).filter(
        Advance.id == advance_id,
        Advance.org_id == org_id,
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


@router.get(
    "/{org_id}/advances/{advance_id}",
    summary='Get a single advance with its recoupment history',
    description='Returns the advance plus the per-statement history of how much was recouped against it and when.\n\n**Path parameters:** `org_id`, `advance_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** the full advance object plus `recoupment_history: [{processing_run_id, statement_id, recouped_at, amount_cents}]`.',
)
def get_advance_detail(
    org_id: int,
    advance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    advance = db.query(Advance).filter(
        Advance.id == advance_id,
        Advance.org_id == org_id,
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

@router.get(
    "/{org_id}/payout-batches",
    summary='List payout batches for the organization',
    description='Returns all PayoutBatch records (drafts, approved, paid) with their total amount and item count. Used to render the payouts page.\n\n**Path parameter:** `org_id`.\n**Query:** `status` (`draft|approved|paid|cancelled`).\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ batches: [{id, name, status, currency, total_cents, item_count, created_at, paid_at}] }`.',
)
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


@router.post(
    "/{org_id}/payout-batches",
    summary='Create a new (empty) payout batch',
    description='Creates a draft PayoutBatch that line items can be added to via `/items`. Status starts as `draft`; cut over to `approved` and then `paid` via `/status`.\n\n**Path parameter:** `org_id`.\n**Body (`PayoutBatchCreateRequest`):** `name`, `currency` (default USD).\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** the created batch object.',
)
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


@router.post(
    "/{org_id}/payout-batches/{batch_id}/items",
    summary='Add a payout item to a draft batch',
    description="Appends a single payee/amount line to a draft PayoutBatch and debits the payee's ledger when the batch is later marked paid. Only allowed while the batch is `draft`.\n\n**Path parameters:** `org_id`, `batch_id`.\n**Body (`PayoutItemCreateRequest`):** `payee_id`, `amount_cents`, `memo?`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** the created PayoutItem `{id, payee_id, amount_cents, memo, created_at}`.",
)
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


@router.put(
    "/{org_id}/payout-batches/{batch_id}/status",
    summary='Move a payout batch through its status lifecycle',
    description='Transitions the batch — `draft → approved → paid` (or `cancelled` from any non-paid state). Marking a batch `paid` writes a debit ledger entry for every item against its payee.\n\n**Path parameters:** `org_id`, `batch_id`.\n**Body (`PayoutBatchStatusUpdate`):** `status` (`draft|approved|paid|cancelled`).\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** the updated batch object.',
)
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

@router.get(
    "/{org_id}/inbox",
    summary='Get the royalty-processing action-item inbox',
    description='Returns the prioritized list of things a royalty operator needs to do — statements waiting to be processed, statements with low-confidence matches, statements that re-need processing after splits changed, etc. Each item includes a deep link.\n\n**Path parameter:** `org_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ items: [{id, kind, severity, statement_id, title, description, created_at, link}] }`.',
)
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

@router.get(
    "/{org_id}/statements/{statement_id}/export/unmatched",
    summary='Download the unmatched lines on a statement as CSV',
    description='Streams a CSV of every line whose status is `unmatched` so an operator can resolve them in a spreadsheet (or hand them off to a contractor).\n\n**Path parameters:** `org_id`, `statement_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `text/csv` download — columns: `line_id, track_title, artist, isrc, period, territory, amount_cents, currency, suggested_song_id, suggested_title, confidence`.',
)
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


@router.get(
    "/{org_id}/statements/{statement_id}/export/allocation",
    summary='Download the per-payee allocation preview as CSV',
    description='Streams the rows from `/allocation-preview` as a CSV — one row per payee with their gross, recouped and net amounts.\n\n**Path parameters:** `org_id`, `statement_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `text/csv` download — columns: `payee_id, payee_name, gross_cents, recouped_cents, net_cents, currency`.',
)
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

    result = get_allocation_preview(db, statement_id, org_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Payee ID", "Payee Name", "Payee Type", "Earnings (cents)", "Fees (cents)", "Recoupment (cents)", "Payable (cents)"])
    for row in result["allocations"]:
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


@router.get(
    "/{org_id}/statements/{statement_id}/export/payables",
    summary='Download the payables report for a processed statement as CSV',
    description='Like the allocation export but only for **processed** statements: shows the actual ledger postings written by the processing run plus updated payee balances.\n\n**Path parameters:** `org_id`, `statement_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `text/csv` download — columns: `payee_id, payee_name, posted_amount_cents, balance_cents, currency, processing_run_id`.',
)
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

@router.post(
    "/{org_id}/statements/upload",
    summary='Upload a royalty statement file and parse it into lines',
    description='Accepts a CSV/XLSX statement file (Spotify, Apple, ASCAP, BMI, etc.), auto-detects the source format, suggests column mappings, and creates a RoyaltyStatement with parsed RoyaltyStatementLine rows. Run `/auto-match` next.\n\n**Path parameter:** `org_id`.\n**Body (multipart/form-data):** `file` (the statement), `source` (PRO/DSP slug, optional — auto-detected when omitted), `period_start`, `period_end` (optional ISO dates), `column_mapping` (optional JSON overrides).\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ statement_id, source_detected, lines_created, suggested_mapping, warnings }`.',
)
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
    auto_match: Optional[str] = Query("true"),
    force: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    from .royalties import normalize_source_name
    from ..config.statement_formats import (
        canonical_source_type,
        StatementSourceType,
    )

    # Validate source_type at the API boundary against the canonical
    # StatementSourceType enum. Empty / omitted is allowed (we'll
    # auto-detect). A non-empty string that doesn't match any
    # registered alias is a 400 — surfaces typos early instead of
    # silently writing garbage into ``RoyaltyStatement.source_type``.
    if source_type:
        canonical = canonical_source_type(source_type)
        if not canonical:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_source_type",
                    "message": (
                        f"Unknown source_type {source_type!r}. "
                        f"Accepted values: {sorted(v.value for v in StatementSourceType)}"
                    ),
                    "accepted_values": sorted(v.value for v in StatementSourceType),
                },
            )
        source_type = canonical

    source_name = normalize_source_name(source_name)
    content = await file.read()

    # Duplicate detection (mirrors /api/royalties/statements/{org_id}/upload):
    # same org + same file_name = same upload. 409 unless caller passes force=true.
    if file.filename and not force:
        existing_dup = db.query(RoyaltyStatement).filter(
            RoyaltyStatement.organization_id == org_id,
            RoyaltyStatement.file_name == file.filename,
        ).first()
        if existing_dup is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "duplicate_statement",
                    "message": (
                        f"A statement with file name '{file.filename}' was already "
                        f"uploaded (id={existing_dup.id}, status={existing_dup.status}). "
                        f"Re-submit with force=true to override."
                    ),
                    "existing_statement_id": existing_dup.id,
                    "existing_status": existing_dup.status,
                    "existing_uploaded_at": existing_dup.created_at.isoformat() if existing_dup.created_at else None,
                },
            )

    # Single-call orchestrator: parse file → detect source-type →
    # suggest column mapping (registry-aware, biased by the canonical
    # source-type the user explicitly selected so per-source
    # extra_hints win over the generic baseline).
    try:
        from ..services.statement_parser import parse_statement_file
        parsed = parse_statement_file(
            content,
            file.filename or "data.csv",
            source_name=source_name or "",
            source_type=source_type,
            org_id=org_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File parsing crashed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    headers = parsed.headers
    rows = parsed.rows
    pdf_metadata = parsed.pdf_metadata
    if parsed.resolved_source_type and not source_type:
        source_type = parsed.resolved_source_type

    # Caller-supplied column_mapping JSON overrides the orchestrator's
    # suggestion; PDF parser hints (already folded into
    # parsed.suggested_mapping) otherwise win; baseline registry
    # suggestion is the fallback.
    if column_mapping:
        try:
            mapping = json.loads(column_mapping)
        except Exception:
            mapping = parsed.suggested_mapping
    else:
        mapping = parsed.suggested_mapping

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

    # Auto-extract period from PDF header when not supplied (BMI/ASCAP/publisher).
    if (p_start is None or p_end is None) and (file.filename or "").lower().endswith(".pdf"):
        try:
            from ..utils.pdf_statement_parser import parse_period_from_pdf
            auto_start, auto_end = parse_period_from_pdf(content, file_name=file.filename)
            if p_start is None and auto_start is not None:
                p_start = auto_start
            if p_end is None and auto_end is not None:
                p_end = auto_end
            if auto_start or auto_end:
                logger.info(f"upload_and_parse_statement: auto-parsed period {auto_start} - {auto_end} from PDF header")
        except Exception as e:
            logger.warning(f"upload_and_parse_statement: period auto-parse failed: {e}")

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
    else:
        statement.matched_transactions = 0
        statement.unmatched_transactions = line_count

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


@router.get(
    "/{org_id}/statements/{statement_id}/reconciliation",
    summary='Run control totals against a statement',
    description="Compares the sum of parsed line amounts against the source file's reported totals (when supplied) to flag parsing/import errors. Used as a sanity check before processing.\n\n**Path parameters:** `org_id`, `statement_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ reported_total_cents, parsed_total_cents, delta_cents, in_balance, by_currency: [...] }`.",
)
def get_reconciliation(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    result = run_control_totals(db, statement_id, org_id)
    return result


@router.get(
    "/{org_id}/statements/{statement_id}/classification",
    summary="Break down a statement's lines by revenue classification",
    description='Returns the buckets the reconciliation engine assigned to each line — mechanical, performance, sync, neighboring rights, streaming, etc. — with counts and totals per bucket. Drives the "composition" pie chart on the statement page.\n\n**Path parameters:** `org_id`, `statement_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ classifications: [{bucket, count, amount_cents, currency, pct_of_total}] }`.',
)
def get_statement_classification(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    return get_classification_breakdown(db, statement_id, org_id)


@router.get(
    "/{org_id}/statements/{statement_id}/match-summary",
    summary='Summarize match coverage for a statement',
    description="Reports how much of the statement's value has been matched, by match strategy (ISRC, exact, fuzzy, manual) — useful for spotting brittle data sources.\n\n**Path parameters:** `org_id`, `statement_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ total_amount_cents, matched_amount_cents, unmatched_amount_cents, coverage_pct, by_strategy: [{strategy, count, amount_cents}] }`.",
)
def get_statement_match_summary(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    return get_match_summary(db, statement_id, org_id)


@router.post(
    "/{org_id}/statements/{statement_id}/set-reported-totals",
    summary='Manually record the reported totals from the source file',
    description="Stores the totals printed on the cover page of the original PRO/DSP statement so reconciliation has something to compare the parsed sum against. Use when the parser couldn't auto-extract them.\n\n**Path parameters:** `org_id`, `statement_id`.\n**Body:** `{ reported_total_cents: int, currency: str, totals_by_bucket?: { mechanical?, performance?, ... } }`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ success: true }`.",
)
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


@router.get(
    "/{org_id}/analytics/portfolio",
    summary='Portfolio-level decay/earnings analytics for the org',
    description='Returns the org-wide decay analytics dashboard data: aggregate earnings curves, CAGR, top earners, and projected lifetime value across the catalog.\n\n**Path parameter:** `org_id`.\n**Query:** `start_date`, `end_date`, `currency`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ totals_by_period: [...], cagr, decay_fit: {a, k, r2}, top_songs: [...], projections: [...] }`.',
)
def get_portfolio_analytics_endpoint(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    return get_portfolio_analytics(db, org_id)


@router.get(
    "/{org_id}/analytics/song/{song_id}",
    summary='Per-song decay/earnings analytics',
    description='The song-level version of `/analytics/portfolio`: time series, exponential decay fit, CAGR, and projection for a single song based on its historical royalty postings.\n\n**Path parameters:** `org_id`, `song_id`.\n**Query:** `start_date`, `end_date`, `currency`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ song_id, time_series: [{period, amount_cents}], cagr, decay_fit: {a, k, r2}, projection: [...] }`.',
)
def get_song_analytics_endpoint(
    org_id: int,
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    return get_song_analytics(db, org_id, song_id)


@router.get(
    "/{org_id}/analytics/time-series",
    summary='Aggregate royalty earnings as a time series',
    description='Returns a flexible time series of royalty postings, optionally grouped by source, classification, payee, or song. Powers custom analytics widgets.\n\n**Path parameter:** `org_id`.\n**Query:** `start_date`, `end_date`, `granularity` (`month|quarter|year`), `group_by` (`source|classification|payee|song`), `currency`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ series: [{key, points: [{period, amount_cents}]}] }`.',
)
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
