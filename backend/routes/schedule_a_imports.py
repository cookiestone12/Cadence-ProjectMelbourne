"""Audit, download, and re-extract endpoints for saved Schedule A uploads."""
from __future__ import annotations

import logging
import mimetypes
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models import get_db, OrganizationMember, User
from ..models.models import ScheduleAImport
from ..utils.auth import get_current_user
from ..services import schedule_a_storage

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/schedule-a-imports", tags=["Schedule A"])


class ScheduleAImportSummary(BaseModel):
    id: int
    original_filename: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    sha256: Optional[str] = None
    extraction_method: Optional[str] = None
    songs_created: int
    songs_failed: int
    creator_id: Optional[int] = None
    creator_name: Optional[str] = None
    is_text_paste: bool = False
    created_at: str
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    file_available: bool = True


def _membership_or_403(db: Session, user: User, org_id: int) -> OrganizationMember:
    m = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id,
    ).first()
    if not m:
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")
    return m


def _admin_or_403(membership: OrganizationMember) -> None:
    role = (membership.role or "").upper()
    if role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Only OWNER or ADMIN may access Schedule A audit data")


def _file_available(rec: ScheduleAImport) -> bool:
    if not rec.stored_path:
        return False
    try:
        return schedule_a_storage.exists(rec.stored_path)
    except Exception:
        return False


@router.get(
    "/{org_id}",
    response_model=List[ScheduleAImportSummary],
    summary='List Schedule A imports for the organization',
    description='Returns every ScheduleAImport the org has run with summary metrics (rows imported, errors, original filename).\n\n**Path parameter:** `org_id`.\n**Query:** `status`, `limit`, `offset`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `List[ScheduleAImportSummary]`.',
)
async def list_schedule_a_imports(
    org_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = _membership_or_403(db, current_user, org_id)
    _admin_or_403(membership)

    rows = (
        db.query(ScheduleAImport)
        .filter(ScheduleAImport.organization_id == org_id)
        .order_by(ScheduleAImport.created_at.desc())
        .limit(min(max(limit, 1), 200))
        .all()
    )

    out: List[ScheduleAImportSummary] = []
    for r in rows:
        out.append(ScheduleAImportSummary(
            id=r.id,
            original_filename=r.original_filename,
            file_size=r.file_size,
            mime_type=r.mime_type,
            sha256=r.sha256,
            extraction_method=r.extraction_method,
            songs_created=r.songs_created or 0,
            songs_failed=r.songs_failed or 0,
            creator_id=r.creator_id,
            creator_name=r.creator_name,
            is_text_paste=bool(r.is_text_paste),
            created_at=r.created_at.isoformat() if r.created_at else "",
            user_id=r.user_id,
            user_email=r.user.email if r.user else None,
            file_available=_file_available(r),
        ))
    return out


@router.get(
    "/{org_id}/{import_id}/download",
    summary='Download the original Schedule A import file',
    description='Streams the original spreadsheet that was uploaded to create this import — useful for forensics when the import produced unexpected data.\n\n**Path parameters:** `org_id`, `import_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** the file with the appropriate `Content-Type`.',
)
async def download_schedule_a_import(
    org_id: int,
    import_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = _membership_or_403(db, current_user, org_id)
    _admin_or_403(membership)

    rec = db.query(ScheduleAImport).filter(
        ScheduleAImport.id == import_id,
        ScheduleAImport.organization_id == org_id,
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Import not found")

    data = schedule_a_storage.open_bytes(rec.stored_path) if rec.stored_path else None
    if data is None:
        raise HTTPException(status_code=410, detail="Original file is no longer available")

    media_type = rec.mime_type or mimetypes.guess_type(rec.original_filename)[0] or "application/octet-stream"
    safe_name = (rec.original_filename or f"schedule_a_{import_id}").replace('"', "_")
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


class ReExtractResult(BaseModel):
    success: bool
    extraction_method: Optional[str] = None
    preview_rows: List[Dict[str, Any]] = []
    row_count: int = 0
    creator_info: Dict[str, Any] = {}
    contract_terms: Dict[str, Any] = {}
    document_info: Dict[str, Any] = {}
    warnings: List[str] = []
    errors: List[str] = []
    is_text_paste: bool = False
    original_filename: Optional[str] = None
    creator_id: Optional[int] = None
    creator_name: Optional[str] = None


@router.post("/{org_id}/{import_id}/re-extract", response_model=ReExtractResult, summary="Re-run the unified document parser against the saved original file", description='Re-runs the unified document parser against the saved original file for an existing import — useful when the parser was upgraded after the original run.\n\n**Path parameters:** `org_id`, `import_id`.\n**Body:** `{ options?: {...} }` — optional parser overrides.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ import_id, status, parsed_rows, warnings: [...] }`.')
async def re_extract_schedule_a_import(
    org_id: int,
    import_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-run the unified document parser against the saved original file.

    Useful after model upgrades or parser fixes. Does NOT modify any songs —
    callers are expected to feed the returned rows back through the normal
    /api/csv/import flow if they want to import them.
    """
    membership = _membership_or_403(db, current_user, org_id)
    _admin_or_403(membership)

    rec = db.query(ScheduleAImport).filter(
        ScheduleAImport.id == import_id,
        ScheduleAImport.organization_id == org_id,
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Import not found")

    content = schedule_a_storage.open_bytes(rec.stored_path) if rec.stored_path else None
    if content is None:
        raise HTTPException(status_code=410, detail="Original file is no longer available")

    from ..services.document_parser import parse_document_unified

    if rec.is_text_paste:
        try:
            text = content.decode("utf-8", errors="replace")
        except Exception:
            text = ""
        result = parse_document_unified(None, rec.original_filename or "pasted.txt", pasted_text=text, org_id=org_id)
    else:
        result = parse_document_unified(content, rec.original_filename or "schedule_a", org_id=org_id)

    payload = result.to_preview_response()
    return ReExtractResult(
        success=bool(payload.get("success", True)),
        extraction_method=payload.get("extraction_method"),
        preview_rows=payload.get("preview_rows", []),
        row_count=payload.get("row_count", 0) or len(payload.get("preview_rows", [])),
        creator_info=payload.get("creator_info") or {},
        contract_terms=payload.get("contract_terms") or {},
        document_info=payload.get("document_info") or {},
        warnings=payload.get("warnings") or [],
        errors=payload.get("errors") or [],
        is_text_paste=bool(rec.is_text_paste),
        original_filename=rec.original_filename,
        creator_id=rec.creator_id,
        creator_name=rec.creator_name,
    )
