from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from difflib import SequenceMatcher
import csv
import io
import logging

from ..models import (
    get_db, User, OrganizationMember, Song, Creator,
    Contract, ContractAsset, RightsSplit,
    RoyaltyStatement, RoyaltyTransaction, RoyaltyAllocation, Payment,
)
from ..utils.auth import get_current_user

try:
    import openpyxl
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/royalties", tags=["royalties"])


def verify_org_access(user: User, org_id: int, db: Session):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


class PaymentCreate(BaseModel):
    payee_id: int
    contract_id: Optional[int] = None
    amount_cents: int
    currency: str = "USD"
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    payment_date: Optional[date] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    notes: Optional[str] = None


class ManualMatchRequest(BaseModel):
    song_id: int


COLUMN_HINTS = {
    "isrc": ["isrc"],
    "upc": ["upc", "barcode"],
    "track_title": ["title", "track", "song", "track_title", "song_title", "track name", "song name"],
    "artist": ["artist", "performer", "band", "artist name", "primary artist"],
    "revenue": ["revenue", "amount", "earnings", "net", "royalty", "payment", "gross", "total", "payout"],
    "quantity": ["quantity", "streams", "plays", "downloads", "units", "count"],
    "territory": ["territory", "country", "region", "market"],
    "platform": ["platform", "store", "service", "dsp", "source"],
    "revenue_type": ["type", "revenue_type", "sale type", "transaction type", "usage type"],
}


def suggest_column_mapping(headers: List[str]) -> Dict[str, Optional[str]]:
    mapping = {}
    used_headers = set()
    for field, hints in COLUMN_HINTS.items():
        best_match = None
        for header in headers:
            if header in used_headers:
                continue
            lower = header.lower().strip()
            for hint in hints:
                if hint == lower or hint in lower:
                    best_match = header
                    break
            if best_match:
                break
        mapping[field] = best_match
        if best_match:
            used_headers.add(best_match)
    return mapping


def parse_revenue_to_cents(value: Any) -> int:
    if value is None:
        return 0
    try:
        s = str(value).strip().replace(",", "").replace("$", "").replace("£", "").replace("€", "")
        if not s or s == "-":
            return 0
        return int(round(float(s) * 100))
    except (ValueError, TypeError):
        return 0


def parse_quantity(value: Any) -> int:
    if value is None:
        return 0
    try:
        s = str(value).strip().replace(",", "")
        if not s or s == "-":
            return 0
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def format_excel_cell(cell_value, number_format=None) -> str:
    if cell_value is None:
        return ""
    if isinstance(cell_value, (datetime, date)):
        return cell_value.strftime("%Y-%m-%d") if hasattr(cell_value, 'strftime') else str(cell_value)
    if isinstance(cell_value, (int, float)):
        if number_format and '%' in str(number_format):
            converted = cell_value * 100
            if converted == int(converted):
                return str(int(converted))
            return str(round(converted, 4))
        if isinstance(cell_value, float) and cell_value == int(cell_value):
            return str(int(cell_value))
        return str(cell_value)
    return str(cell_value).strip()


def parse_uploaded_file(content: bytes, filename: str) -> tuple:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext in ("xlsx", "xls"):
        if not EXCEL_SUPPORT:
            raise HTTPException(status_code=400, detail="Excel support not available")
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=False))
        if not all_rows:
            wb.close()
            raise HTTPException(status_code=400, detail="File has no data")
        header_idx = 0
        for idx, row in enumerate(all_rows[:10]):
            vals = [c.value for c in row]
            non_empty = sum(1 for v in vals if v is not None and str(v).strip())
            text_count = sum(1 for v in vals if isinstance(v, str) and not v.replace('.', '').replace('-', '').isdigit())
            if non_empty >= 2 and text_count >= 1:
                header_idx = idx
                break
        header_cells = all_rows[header_idx]
        headers = [str(c.value).strip() if c.value else f"Column_{i}" for i, c in enumerate(header_cells)]
        rows = []
        for row in all_rows[header_idx + 1:]:
            if any(c.value is not None for c in row):
                row_dict = {}
                for i, cell in enumerate(row):
                    if i < len(headers):
                        row_dict[headers[i]] = format_excel_cell(cell.value, cell.number_format)
                rows.append(row_dict)
        wb.close()
        return headers, rows
    else:
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = content.decode('latin-1')
            except Exception:
                raise HTTPException(status_code=400, detail="Unable to decode file")
        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames or []
        if not headers:
            raise HTTPException(status_code=400, detail="File has no headers")
        rows = list(reader)
        return headers, rows


def match_transaction_to_song(tx: RoyaltyTransaction, songs: List[Song]) -> tuple:
    if tx.original_isrc:
        isrc_clean = tx.original_isrc.strip().upper().replace("-", "")
        for song in songs:
            if song.isrc:
                song_isrc = song.isrc.strip().upper().replace("-", "")
                if song_isrc == isrc_clean:
                    return song.id, 1.0, "MATCHED"

    if tx.original_track_title:
        best_score = 0.0
        best_song_id = None
        tx_title = (tx.original_track_title or "").lower().strip()
        tx_artist = (tx.original_artist or "").lower().strip()

        for song in songs:
            song_title = (song.title or "").lower().strip()
            title_ratio = SequenceMatcher(None, tx_title, song_title).ratio()

            if tx_artist and song.primary_artist:
                song_artist = song.primary_artist.lower().strip()
                artist_ratio = SequenceMatcher(None, tx_artist, song_artist).ratio()
                combined = (title_ratio * 0.6) + (artist_ratio * 0.4)
            else:
                combined = title_ratio

            if combined > best_score:
                best_score = combined
                best_song_id = song.id

        if best_score >= 0.8 and best_song_id is not None:
            return best_song_id, best_score, "MATCHED"

    return None, None, "UNMATCHED"


@router.post("/statements/{org_id}/preview")
async def preview_statement(
    org_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    content = await file.read()
    headers, rows = parse_uploaded_file(content, file.filename or "data.csv")
    mapping = suggest_column_mapping(headers)
    preview = rows[:10]
    return {
        "headers": headers,
        "mapping": mapping,
        "preview_rows": preview,
        "row_count": len(rows),
        "success": True,
    }


@router.get("/statements/{org_id}")
def list_statements(
    org_id: int,
    status: Optional[str] = None,
    source: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(RoyaltyStatement).filter(RoyaltyStatement.organization_id == org_id)
    if status:
        query = query.filter(RoyaltyStatement.status == status)
    if source:
        query = query.filter(RoyaltyStatement.source_name.ilike(f"%{source}%"))
    total = query.count()
    statements = query.order_by(desc(RoyaltyStatement.created_at)).offset(skip).limit(limit).all()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "statements": [
            {
                "id": s.id,
                "source_name": s.source_name,
                "source_type": s.source_type,
                "period_start": s.period_start.isoformat() if s.period_start else None,
                "period_end": s.period_end.isoformat() if s.period_end else None,
                "currency": s.currency,
                "total_revenue_cents": s.total_revenue_cents,
                "total_revenue_dollars": s.total_revenue_cents / 100.0,
                "total_transactions": s.total_transactions,
                "matched_transactions": s.matched_transactions,
                "unmatched_transactions": s.unmatched_transactions,
                "status": s.status,
                "file_name": s.file_name,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in statements
        ],
    }


@router.get("/statements/{org_id}/{statement_id}")
def get_statement(
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

    alloc_total = db.query(func.coalesce(func.sum(RoyaltyAllocation.allocated_cents), 0)).join(
        RoyaltyTransaction, RoyaltyAllocation.transaction_id == RoyaltyTransaction.id
    ).filter(RoyaltyTransaction.statement_id == statement_id).scalar()

    return {
        "id": stmt.id,
        "organization_id": stmt.organization_id,
        "source_name": stmt.source_name,
        "source_type": stmt.source_type,
        "period_start": stmt.period_start.isoformat() if stmt.period_start else None,
        "period_end": stmt.period_end.isoformat() if stmt.period_end else None,
        "currency": stmt.currency,
        "exchange_rate": stmt.exchange_rate,
        "file_name": stmt.file_name,
        "total_revenue_cents": stmt.total_revenue_cents,
        "total_revenue_dollars": stmt.total_revenue_cents / 100.0,
        "total_transactions": stmt.total_transactions,
        "matched_transactions": stmt.matched_transactions,
        "unmatched_transactions": stmt.unmatched_transactions,
        "status": stmt.status,
        "processing_notes": stmt.processing_notes,
        "column_mapping": stmt.column_mapping,
        "total_allocated_cents": alloc_total,
        "total_allocated_dollars": alloc_total / 100.0,
        "total_unallocated_cents": stmt.total_revenue_cents - alloc_total,
        "total_unallocated_dollars": (stmt.total_revenue_cents - alloc_total) / 100.0,
        "created_at": stmt.created_at.isoformat() if stmt.created_at else None,
        "updated_at": stmt.updated_at.isoformat() if stmt.updated_at else None,
    }


@router.post("/statements/{org_id}/upload")
async def upload_statement(
    org_id: int,
    file: UploadFile = File(...),
    source_name: str = Form(...),
    source_type: Optional[str] = Form(None),
    period_start: Optional[str] = Form(None),
    period_end: Optional[str] = Form(None),
    currency: str = Form("USD"),
    column_mapping: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    content = await file.read()
    headers, rows = parse_uploaded_file(content, file.filename or "data.csv")

    if column_mapping:
        import json
        try:
            mapping = json.loads(column_mapping)
        except Exception:
            mapping = suggest_column_mapping(headers)
    else:
        mapping = suggest_column_mapping(headers)

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
    )
    db.add(statement)
    db.flush()

    org_songs = db.query(Song).filter(Song.organization_id == org_id).all()

    total_rev = 0
    matched_count = 0
    unmatched_count = 0
    transactions = []

    isrc_col = mapping.get("isrc")
    upc_col = mapping.get("upc")
    title_col = mapping.get("track_title")
    artist_col = mapping.get("artist")
    rev_col = mapping.get("revenue")
    qty_col = mapping.get("quantity")
    territory_col = mapping.get("territory")
    platform_col = mapping.get("platform")
    rev_type_col = mapping.get("revenue_type")

    for row in rows:
        rev_cents = parse_revenue_to_cents(row.get(rev_col) if rev_col else None)
        qty = parse_quantity(row.get(qty_col) if qty_col else None)

        tx = RoyaltyTransaction(
            statement_id=statement.id,
            organization_id=org_id,
            original_isrc=row.get(isrc_col, "").strip() if isrc_col else None,
            original_upc=row.get(upc_col, "").strip() if upc_col else None,
            original_track_title=row.get(title_col, "").strip() if title_col else None,
            original_artist=row.get(artist_col, "").strip() if artist_col else None,
            revenue_cents=rev_cents,
            currency=currency,
            quantity=qty,
            territory=row.get(territory_col, "").strip() if territory_col else None,
            platform=row.get(platform_col, "").strip() if platform_col else None,
            revenue_type=row.get(rev_type_col, "").strip() if rev_type_col else None,
            raw_data=row,
        )

        song_id, confidence, status = match_transaction_to_song(tx, org_songs)
        tx.song_id = song_id
        tx.match_confidence = confidence
        tx.match_status = status

        if status == "MATCHED":
            matched_count += 1
        else:
            unmatched_count += 1

        total_rev += rev_cents
        transactions.append(tx)

    db.add_all(transactions)

    statement.total_revenue_cents = total_rev
    statement.total_transactions = len(transactions)
    statement.matched_transactions = matched_count
    statement.unmatched_transactions = unmatched_count
    statement.status = "PROCESSED" if unmatched_count == 0 else "PARTIALLY_MATCHED"

    db.commit()
    db.refresh(statement)

    return {
        "id": statement.id,
        "status": statement.status,
        "total_transactions": statement.total_transactions,
        "matched_transactions": statement.matched_transactions,
        "unmatched_transactions": statement.unmatched_transactions,
        "total_revenue_cents": statement.total_revenue_cents,
        "total_revenue_dollars": statement.total_revenue_cents / 100.0,
    }


@router.delete("/statements/{org_id}/{statement_id}")
def delete_statement(
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
    db.delete(stmt)
    db.commit()
    return {"detail": "Statement deleted"}


@router.get("/statements/{org_id}/{statement_id}/transactions")
def list_transactions(
    org_id: int,
    statement_id: int,
    match_status: Optional[str] = None,
    skip: int = Query(0, ge=0),
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

    query = db.query(RoyaltyTransaction).filter(RoyaltyTransaction.statement_id == statement_id)
    if match_status:
        query = query.filter(RoyaltyTransaction.match_status == match_status)
    total = query.count()
    txs = query.order_by(RoyaltyTransaction.id).offset(skip).limit(limit).all()

    results = []
    for tx in txs:
        song_title = None
        song_artist = None
        if tx.song_id:
            song = db.query(Song).filter(Song.id == tx.song_id).first()
            if song:
                song_title = song.title
                song_artist = song.primary_artist
        results.append({
            "id": tx.id,
            "original_track_title": tx.original_track_title,
            "original_artist": tx.original_artist,
            "original_isrc": tx.original_isrc,
            "original_upc": tx.original_upc,
            "song_id": tx.song_id,
            "matched_song_title": song_title,
            "matched_song_artist": song_artist,
            "match_status": tx.match_status,
            "match_confidence": tx.match_confidence,
            "revenue_cents": tx.revenue_cents,
            "revenue_dollars": tx.revenue_cents / 100.0,
            "quantity": tx.quantity,
            "territory": tx.territory,
            "platform": tx.platform,
            "revenue_type": tx.revenue_type,
        })

    return {"total": total, "skip": skip, "limit": limit, "transactions": results}


@router.post("/statements/{org_id}/{statement_id}/match/{transaction_id}")
def manual_match(
    org_id: int,
    statement_id: int,
    transaction_id: int,
    body: ManualMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    tx = db.query(RoyaltyTransaction).filter(
        RoyaltyTransaction.id == transaction_id,
        RoyaltyTransaction.statement_id == statement_id,
        RoyaltyTransaction.organization_id == org_id,
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    song = db.query(Song).filter(Song.id == body.song_id, Song.organization_id == org_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found in this organization")

    was_unmatched = tx.match_status == "UNMATCHED"
    tx.song_id = song.id
    tx.match_status = "MANUAL"
    tx.match_confidence = 1.0

    stmt = db.query(RoyaltyStatement).filter(RoyaltyStatement.id == statement_id).first()
    if stmt and was_unmatched:
        stmt.matched_transactions = (stmt.matched_transactions or 0) + 1
        stmt.unmatched_transactions = max((stmt.unmatched_transactions or 0) - 1, 0)
        if stmt.unmatched_transactions == 0:
            stmt.status = "PROCESSED"

    db.commit()
    return {"detail": "Transaction matched", "song_id": song.id, "song_title": song.title}


@router.post("/statements/{org_id}/{statement_id}/rematch")
def rematch_transactions(
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

    unmatched = db.query(RoyaltyTransaction).filter(
        RoyaltyTransaction.statement_id == statement_id,
        RoyaltyTransaction.match_status == "UNMATCHED",
    ).all()

    org_songs = db.query(Song).filter(Song.organization_id == org_id).all()
    newly_matched = 0

    for tx in unmatched:
        song_id, confidence, status = match_transaction_to_song(tx, org_songs)
        if status == "MATCHED":
            tx.song_id = song_id
            tx.match_confidence = confidence
            tx.match_status = "MATCHED"
            newly_matched += 1

    stmt.matched_transactions = (stmt.matched_transactions or 0) + newly_matched
    stmt.unmatched_transactions = max((stmt.unmatched_transactions or 0) - newly_matched, 0)
    if stmt.unmatched_transactions == 0:
        stmt.status = "PROCESSED"
    elif newly_matched > 0:
        stmt.status = "PARTIALLY_MATCHED"

    db.commit()
    return {
        "newly_matched": newly_matched,
        "remaining_unmatched": stmt.unmatched_transactions,
        "status": stmt.status,
    }


@router.post("/calculate/{org_id}/{statement_id}")
def calculate_royalties(
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

    db.query(RoyaltyAllocation).filter(
        RoyaltyAllocation.transaction_id.in_(
            db.query(RoyaltyTransaction.id).filter(RoyaltyTransaction.statement_id == statement_id)
        )
    ).delete(synchronize_session=False)

    matched_txs = db.query(RoyaltyTransaction).filter(
        RoyaltyTransaction.statement_id == statement_id,
        RoyaltyTransaction.match_status.in_(["MATCHED", "MANUAL"]),
        RoyaltyTransaction.song_id.isnot(None),
    ).all()

    allocations_created = 0
    total_allocated = 0
    total_recouped = 0

    for tx in matched_txs:
        contract_assets = db.query(ContractAsset).filter(
            ContractAsset.asset_type == "SONG",
            ContractAsset.asset_id == tx.song_id,
        ).all()

        for ca in contract_assets:
            contract = db.query(Contract).filter(
                Contract.id == ca.contract_id,
                Contract.organization_id == org_id,
            ).first()
            if not contract:
                continue

            splits = db.query(RightsSplit).filter(
                RightsSplit.contract_asset_id == ca.id
            ).all()

            for split in splits:
                share_cents = int(round(tx.revenue_cents * (split.share_percentage / 100.0)))
                recouped_cents = 0
                is_recoupable = False

                if contract.advance_amount and contract.advance_amount > 0:
                    advance_cents = int(round(contract.advance_amount * 100))
                    recouped_so_far_cents = int(round((contract.advance_recouped or 0) * 100))
                    remaining = advance_cents - recouped_so_far_cents

                    if remaining > 0:
                        is_recoupable = True
                        recoup_amount = min(share_cents, remaining)
                        recouped_cents = recoup_amount
                        contract.advance_recouped = (contract.advance_recouped or 0) + (recoup_amount / 100.0)

                alloc = RoyaltyAllocation(
                    transaction_id=tx.id,
                    organization_id=org_id,
                    contract_id=contract.id,
                    rights_holder_id=split.rights_holder_id,
                    rights_type=split.rights_type,
                    share_percentage=split.share_percentage,
                    allocated_cents=share_cents,
                    is_recoupable=is_recoupable,
                    recouped_cents=recouped_cents,
                )
                db.add(alloc)
                allocations_created += 1
                total_allocated += share_cents
                total_recouped += recouped_cents

    db.commit()

    return {
        "statement_id": statement_id,
        "allocations_created": allocations_created,
        "total_allocated_cents": total_allocated,
        "total_allocated_dollars": total_allocated / 100.0,
        "total_recouped_cents": total_recouped,
        "total_recouped_dollars": total_recouped / 100.0,
    }


@router.get("/allocations/{org_id}")
def list_allocations(
    org_id: int,
    contract_id: Optional[int] = None,
    rights_holder_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(RoyaltyAllocation).filter(RoyaltyAllocation.organization_id == org_id)

    if contract_id:
        query = query.filter(RoyaltyAllocation.contract_id == contract_id)
    if rights_holder_id:
        query = query.filter(RoyaltyAllocation.rights_holder_id == rights_holder_id)
    if start_date:
        try:
            sd = date.fromisoformat(start_date)
            query = query.filter(RoyaltyAllocation.created_at >= datetime.combine(sd, datetime.min.time()))
        except ValueError:
            pass
    if end_date:
        try:
            ed = date.fromisoformat(end_date)
            query = query.filter(RoyaltyAllocation.created_at <= datetime.combine(ed, datetime.max.time()))
        except ValueError:
            pass

    total = query.count()
    allocs = query.order_by(desc(RoyaltyAllocation.created_at)).offset(skip).limit(limit).all()

    results = []
    for a in allocs:
        holder = db.query(Creator).filter(Creator.id == a.rights_holder_id).first()
        contract = db.query(Contract).filter(Contract.id == a.contract_id).first() if a.contract_id else None
        results.append({
            "id": a.id,
            "transaction_id": a.transaction_id,
            "contract_id": a.contract_id,
            "contract_title": contract.title if contract else None,
            "rights_holder_id": a.rights_holder_id,
            "rights_holder_name": holder.display_name if holder else None,
            "rights_type": a.rights_type,
            "share_percentage": a.share_percentage,
            "allocated_cents": a.allocated_cents,
            "allocated_dollars": a.allocated_cents / 100.0,
            "is_recoupable": a.is_recoupable,
            "recouped_cents": a.recouped_cents,
            "recouped_dollars": a.recouped_cents / 100.0,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })

    return {"total": total, "skip": skip, "limit": limit, "allocations": results}


@router.get("/dashboard/{org_id}")
def royalties_dashboard(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    total_revenue = db.query(func.coalesce(func.sum(RoyaltyStatement.total_revenue_cents), 0)).filter(
        RoyaltyStatement.organization_id == org_id
    ).scalar()

    total_allocated = db.query(func.coalesce(func.sum(RoyaltyAllocation.allocated_cents), 0)).filter(
        RoyaltyAllocation.organization_id == org_id
    ).scalar()

    total_unallocated = total_revenue - total_allocated

    top_tracks = db.query(
        Song.id, Song.title, Song.primary_artist,
        func.sum(RoyaltyTransaction.revenue_cents).label("total_cents"),
    ).join(
        RoyaltyTransaction, RoyaltyTransaction.song_id == Song.id
    ).filter(
        RoyaltyTransaction.organization_id == org_id,
    ).group_by(Song.id, Song.title, Song.primary_artist).order_by(
        desc("total_cents")
    ).limit(10).all()

    revenue_by_source = db.query(
        RoyaltyStatement.source_name,
        func.sum(RoyaltyStatement.total_revenue_cents).label("total_cents"),
    ).filter(
        RoyaltyStatement.organization_id == org_id
    ).group_by(RoyaltyStatement.source_name).all()

    revenue_by_period = db.query(
        RoyaltyStatement.period_start,
        RoyaltyStatement.period_end,
        RoyaltyStatement.source_name,
        RoyaltyStatement.total_revenue_cents,
    ).filter(
        RoyaltyStatement.organization_id == org_id
    ).order_by(RoyaltyStatement.period_start).all()

    contracts_with_advances = db.query(Contract).filter(
        Contract.organization_id == org_id,
        Contract.advance_amount > 0,
    ).all()

    recoupment_status = []
    for c in contracts_with_advances:
        advance = c.advance_amount or 0
        recouped = c.advance_recouped or 0
        recoupment_status.append({
            "contract_id": c.id,
            "contract_title": c.title,
            "advance_amount": advance,
            "advance_recouped": recouped,
            "remaining": max(advance - recouped, 0),
            "percentage_recouped": round((recouped / advance) * 100, 2) if advance > 0 else 0,
        })

    return {
        "total_revenue_cents": total_revenue,
        "total_revenue_dollars": total_revenue / 100.0,
        "total_allocated_cents": total_allocated,
        "total_allocated_dollars": total_allocated / 100.0,
        "total_unallocated_cents": total_unallocated,
        "total_unallocated_dollars": total_unallocated / 100.0,
        "top_earning_tracks": [
            {
                "song_id": t.id,
                "title": t.title,
                "artist": t.primary_artist,
                "total_revenue_cents": t.total_cents,
                "total_revenue_dollars": t.total_cents / 100.0,
            }
            for t in top_tracks
        ],
        "revenue_by_source": [
            {"source": r.source_name, "total_cents": r.total_cents, "total_dollars": r.total_cents / 100.0}
            for r in revenue_by_source
        ],
        "revenue_by_period": [
            {
                "period_start": r.period_start.isoformat() if r.period_start else None,
                "period_end": r.period_end.isoformat() if r.period_end else None,
                "source": r.source_name,
                "total_cents": r.total_revenue_cents,
                "total_dollars": r.total_revenue_cents / 100.0,
            }
            for r in revenue_by_period
        ],
        "recoupment_status": recoupment_status,
    }


@router.get("/earnings/{org_id}/by-holder")
def earnings_by_holder(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    results = db.query(
        Creator.id, Creator.display_name,
        func.sum(RoyaltyAllocation.allocated_cents).label("total_cents"),
        func.sum(RoyaltyAllocation.recouped_cents).label("total_recouped"),
    ).join(
        RoyaltyAllocation, RoyaltyAllocation.rights_holder_id == Creator.id
    ).filter(
        RoyaltyAllocation.organization_id == org_id,
    ).group_by(Creator.id, Creator.display_name).order_by(desc("total_cents")).all()

    return {
        "earnings": [
            {
                "rights_holder_id": r.id,
                "rights_holder_name": r.display_name,
                "total_allocated_cents": r.total_cents,
                "total_allocated_dollars": r.total_cents / 100.0,
                "total_recouped_cents": r.total_recouped,
                "total_recouped_dollars": r.total_recouped / 100.0,
                "net_earned_cents": r.total_cents - r.total_recouped,
                "net_earned_dollars": (r.total_cents - r.total_recouped) / 100.0,
            }
            for r in results
        ]
    }


@router.get("/earnings/{org_id}/by-contract")
def earnings_by_contract(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    results = db.query(
        Contract.id, Contract.title, Contract.advance_amount, Contract.advance_recouped,
        func.sum(RoyaltyAllocation.allocated_cents).label("total_cents"),
        func.sum(RoyaltyAllocation.recouped_cents).label("total_recouped"),
    ).join(
        RoyaltyAllocation, RoyaltyAllocation.contract_id == Contract.id
    ).filter(
        RoyaltyAllocation.organization_id == org_id,
    ).group_by(Contract.id, Contract.title, Contract.advance_amount, Contract.advance_recouped).order_by(desc("total_cents")).all()

    return {
        "earnings": [
            {
                "contract_id": r.id,
                "contract_title": r.title,
                "advance_amount": r.advance_amount or 0,
                "advance_recouped": r.advance_recouped or 0,
                "remaining_advance": max((r.advance_amount or 0) - (r.advance_recouped or 0), 0),
                "recoupment_percentage": round(((r.advance_recouped or 0) / r.advance_amount) * 100, 2) if r.advance_amount and r.advance_amount > 0 else 0,
                "total_allocated_cents": r.total_cents,
                "total_allocated_dollars": r.total_cents / 100.0,
                "total_recouped_cents": r.total_recouped,
                "net_earned_cents": r.total_cents - r.total_recouped,
                "net_earned_dollars": (r.total_cents - r.total_recouped) / 100.0,
            }
            for r in results
        ]
    }


@router.get("/earnings/{org_id}/by-track")
def earnings_by_track(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    results = db.query(
        Song.id, Song.title, Song.primary_artist, Song.isrc,
        func.sum(RoyaltyTransaction.revenue_cents).label("total_revenue_cents"),
        func.sum(RoyaltyTransaction.quantity).label("total_quantity"),
    ).join(
        RoyaltyTransaction, RoyaltyTransaction.song_id == Song.id
    ).filter(
        RoyaltyTransaction.organization_id == org_id,
    ).group_by(Song.id, Song.title, Song.primary_artist, Song.isrc).order_by(desc("total_revenue_cents")).all()

    return {
        "earnings": [
            {
                "song_id": r.id,
                "title": r.title,
                "artist": r.primary_artist,
                "isrc": r.isrc,
                "total_revenue_cents": r.total_revenue_cents,
                "total_revenue_dollars": r.total_revenue_cents / 100.0,
                "total_quantity": r.total_quantity,
            }
            for r in results
        ]
    }


@router.get("/payments/{org_id}")
def list_payments(
    org_id: int,
    status: Optional[str] = None,
    payee_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(Payment).filter(Payment.organization_id == org_id)
    if status:
        query = query.filter(Payment.status == status)
    if payee_id:
        query = query.filter(Payment.payee_id == payee_id)
    total = query.count()
    payments = query.order_by(desc(Payment.created_at)).offset(skip).limit(limit).all()

    results = []
    for p in payments:
        payee = db.query(Creator).filter(Creator.id == p.payee_id).first()
        contract = db.query(Contract).filter(Contract.id == p.contract_id).first() if p.contract_id else None
        results.append({
            "id": p.id,
            "payee_id": p.payee_id,
            "payee_name": payee.display_name if payee else None,
            "contract_id": p.contract_id,
            "contract_title": contract.title if contract else None,
            "amount_cents": p.amount_cents,
            "amount_dollars": p.amount_cents / 100.0,
            "currency": p.currency,
            "period_start": p.period_start.isoformat() if p.period_start else None,
            "period_end": p.period_end.isoformat() if p.period_end else None,
            "status": p.status,
            "payment_date": p.payment_date.isoformat() if p.payment_date else None,
            "payment_method": p.payment_method,
            "payment_reference": p.payment_reference,
            "notes": p.notes,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        })

    return {"total": total, "skip": skip, "limit": limit, "payments": results}


@router.post("/payments/{org_id}")
def create_payment(
    org_id: int,
    body: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    payee = db.query(Creator).filter(Creator.id == body.payee_id, Creator.organization_id == org_id).first()
    if not payee:
        raise HTTPException(status_code=404, detail="Payee not found in this organization")

    if body.contract_id:
        contract = db.query(Contract).filter(Contract.id == body.contract_id, Contract.organization_id == org_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found in this organization")

    payment = Payment(
        organization_id=org_id,
        payee_id=body.payee_id,
        contract_id=body.contract_id,
        amount_cents=body.amount_cents,
        currency=body.currency,
        period_start=body.period_start,
        period_end=body.period_end,
        status="PENDING",
        payment_method=body.payment_method,
        payment_reference=body.payment_reference,
        notes=body.notes,
        created_by_user_id=current_user.id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "id": payment.id,
        "status": payment.status,
        "amount_cents": payment.amount_cents,
        "amount_dollars": payment.amount_cents / 100.0,
    }


@router.patch("/payments/{org_id}/{payment_id}")
def update_payment(
    org_id: int,
    payment_id: int,
    body: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.organization_id == org_id,
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if body.status is not None:
        payment.status = body.status
    if body.payment_date is not None:
        payment.payment_date = body.payment_date
    if body.payment_method is not None:
        payment.payment_method = body.payment_method
    if body.payment_reference is not None:
        payment.payment_reference = body.payment_reference
    if body.notes is not None:
        payment.notes = body.notes

    db.commit()
    db.refresh(payment)

    return {
        "id": payment.id,
        "status": payment.status,
        "amount_cents": payment.amount_cents,
        "amount_dollars": payment.amount_cents / 100.0,
        "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
    }
