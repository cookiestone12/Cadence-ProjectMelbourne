from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import os
import uuid
from pathlib import Path

from ..models import get_db, Contract, ContractDocument, OrganizationMember, User, Song, Work, Release
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/rights", tags=["Contracts"])

UPLOAD_DIR = Path("uploads/contract_docs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".xls", ".xlsx"}


def verify_org_access(user: User, org_id: int, db: Session):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


def _document_to_dict(doc: ContractDocument, db: Session = None):
    linked_asset_type = None
    linked_asset_name = None
    if db:
        if doc.song_id:
            song = db.query(Song).filter(Song.id == doc.song_id).first()
            linked_asset_type = "Song"
            linked_asset_name = song.title if song else "Unknown"
        elif doc.work_id:
            work = db.query(Work).filter(Work.id == doc.work_id).first()
            linked_asset_type = "Work"
            linked_asset_name = work.title if work else "Unknown"
        elif doc.release_id:
            release = db.query(Release).filter(Release.id == doc.release_id).first()
            linked_asset_type = "Release"
            linked_asset_name = release.title if release else "Unknown"
    return {
        "id": doc.id,
        "contract_id": doc.contract_id,
        "organization_id": doc.organization_id,
        "file_name": doc.file_name,
        "file_size_bytes": doc.file_size_bytes,
        "mime_type": doc.mime_type,
        "description": doc.description,
        "song_id": doc.song_id,
        "work_id": doc.work_id,
        "release_id": doc.release_id,
        "linked_asset_type": linked_asset_type,
        "linked_asset_name": linked_asset_name,
        "uploaded_by_user_id": doc.uploaded_by_user_id,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.post(
    "/contracts/{contract_id}/documents",
    summary='Attach a document file to a contract',
    description="Multipart upload of a contract document (PDF, Word, scanned image). Stored in object storage and recorded as a ContractDocument.\n\n**Path parameter:** `contract_id`.\n**Body (multipart/form-data):** `file` (the document); `category?` (`signed`, `draft`, `redline`, `attachment`); `notes?`.\n**Auth:** Bearer JWT — caller must be a member of the contract's org.\n**Response:** `{ id, filename, size, content_type, category, uploaded_at }`.",
)
async def upload_document(
    contract_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    song_id: Optional[int] = Form(None),
    work_id: Optional[int] = Form(None),
    release_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    verify_org_access(current_user, contract.organization_id, db)

    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")

    if song_id:
        song = db.query(Song).filter(Song.id == song_id, Song.organization_id == contract.organization_id).first()
        if not song:
            raise HTTPException(status_code=404, detail="Song not found in this organization")

    if work_id:
        work = db.query(Work).filter(Work.id == work_id, Work.organization_id == contract.organization_id).first()
        if not work:
            raise HTTPException(status_code=404, detail="Work not found in this organization")

    if release_id:
        release = db.query(Release).filter(Release.id == release_id, Release.organization_id == contract.organization_id).first()
        if not release:
            raise HTTPException(status_code=404, detail="Release not found in this organization")

    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    doc = ContractDocument(
        contract_id=contract_id,
        organization_id=contract.organization_id,
        file_name=file.filename,
        file_path=str(file_path),
        file_size_bytes=file_size,
        mime_type=file.content_type,
        description=description,
        song_id=song_id,
        work_id=work_id,
        release_id=release_id,
        uploaded_by_user_id=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return _document_to_dict(doc, db)


@router.get(
    "/contracts/{contract_id}/documents",
    summary='List documents attached to a contract',
    description="Returns every ContractDocument for the contract.\n\n**Path parameter:** `contract_id`.\n**Auth:** Bearer JWT — caller must be a member of the contract's org.\n**Response:** `{ documents: [{id, filename, size, content_type, category, uploaded_at, uploaded_by}] }`.",
)
def list_documents(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    verify_org_access(current_user, contract.organization_id, db)

    docs = db.query(ContractDocument).filter(
        ContractDocument.contract_id == contract_id
    ).order_by(ContractDocument.created_at.desc()).all()

    return [_document_to_dict(d, db) for d in docs]


@router.get(
    "/contracts/documents/{document_id}/download",
    summary='Download a contract document',
    description="Streams the binary file as an attachment download.\n\n**Path parameter:** `document_id`.\n**Auth:** Bearer JWT — caller must be a member of the document's contract org.\n**Response:** the file with the appropriate `Content-Type`.",
)
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(ContractDocument).filter(ContractDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    verify_org_access(current_user, doc.organization_id, db)

    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    return FileResponse(
        path=str(file_path),
        filename=doc.file_name,
        media_type=doc.mime_type or "application/octet-stream",
    )


@router.delete(
    "/contracts/documents/{document_id}",
    summary='Delete a contract document',
    description="Removes the file from storage and deletes the ContractDocument row.\n\n**Path parameter:** `document_id`.\n**Auth:** Bearer JWT — caller must be a member of the document's contract org.\n**Response:** `{ success: true }`.",
)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(ContractDocument).filter(ContractDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    verify_org_access(current_user, doc.organization_id, db)

    file_path = Path(doc.file_path)
    if file_path.exists():
        os.remove(file_path)

    db.delete(doc)
    db.commit()

    return {"message": "Document deleted successfully"}
