from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date
import csv
import io

from ..models import get_db, Song, SongCredit, Creator, OrganizationMember, User, SongChecklistStatus, ChecklistItem
from ..utils.auth import get_current_user
from ..utils.csv_parser import parse_csv_with_ai, apply_mapping_to_rows, validate_mapped_data

router = APIRouter(prefix="/api/csv", tags=["csv"])


class ColumnMapping(BaseModel):
    original: str
    mapped_to: Optional[str]


class CSVPreviewResponse(BaseModel):
    headers: List[str]
    mapping: Dict[str, Optional[str]]
    preview_rows: List[Dict[str, str]]
    row_count: int
    success: bool
    error: Optional[str] = None


class MappedSongData(BaseModel):
    title: str
    primary_artist: Optional[str] = None
    isrc: Optional[str] = None
    iswc: Optional[str] = None
    project_title: Optional[str] = None
    release_date: Optional[str] = None
    label: Optional[str] = None
    publishing_percentage: Optional[float] = None
    master_percentage: Optional[float] = None
    advance_amount: Optional[float] = None
    recording_code: Optional[str] = None
    notes: Optional[str] = None


class CSVImportRequest(BaseModel):
    mapping: Dict[str, Optional[str]]
    rows: List[Dict[str, str]]
    creator_id: Optional[int] = None
    create_new_creator: bool = False
    new_creator_name: Optional[str] = None


class ImportResult(BaseModel):
    songs_created: int
    songs_failed: int
    creator_id: Optional[int]
    errors: List[str]


@router.post("/preview/{org_id}", response_model=CSVPreviewResponse)
async def preview_csv(
    org_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    content = await file.read()
    try:
        text_content = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text_content = content.decode('latin-1')
        except:
            raise HTTPException(status_code=400, detail="Unable to decode file. Please ensure it's a valid CSV.")
    
    reader = csv.DictReader(io.StringIO(text_content))
    headers = reader.fieldnames or []
    
    if not headers:
        raise HTTPException(status_code=400, detail="CSV file has no headers")
    
    rows = list(reader)
    
    ai_result = parse_csv_with_ai(text_content, headers)
    
    preview_rows = rows[:5]
    
    return CSVPreviewResponse(
        headers=headers,
        mapping=ai_result.get("mapping", {}),
        preview_rows=preview_rows,
        row_count=len(rows),
        success=ai_result.get("success", False),
        error=ai_result.get("error")
    )


@router.post("/import/{org_id}", response_model=ImportResult)
async def import_csv(
    org_id: int,
    request: CSVImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")
    
    creator = None
    if request.create_new_creator and request.new_creator_name:
        creator = Creator(
            organization_id=org_id,
            display_name=request.new_creator_name,
            roles=["ARTIST"]
        )
        db.add(creator)
        db.flush()
    elif request.creator_id:
        creator = db.query(Creator).filter(
            Creator.id == request.creator_id,
            Creator.organization_id == org_id
        ).first()
        if not creator:
            raise HTTPException(status_code=404, detail="Creator not found")
    
    mapped_rows = apply_mapping_to_rows(request.rows, request.mapping)
    validation = validate_mapped_data(mapped_rows)
    
    songs_created = 0
    errors = []
    
    checklist_items = db.query(ChecklistItem).all()
    
    for idx, row_data in enumerate(validation["valid_rows"]):
        try:
            release_date = None
            if row_data.get("release_date"):
                try:
                    from datetime import datetime
                    release_date = datetime.strptime(row_data["release_date"], "%Y-%m-%d").date()
                except:
                    pass
            
            song = Song(
                organization_id=org_id,
                title=row_data.get("title", "Untitled"),
                primary_artist=row_data.get("primary_artist") or (creator.display_name if creator else "Unknown"),
                isrc=row_data.get("isrc"),
                iswc=row_data.get("iswc"),
                project_title=row_data.get("project_title"),
                release_date=release_date,
                label=row_data.get("label"),
                publishing_percentage=row_data.get("publishing_percentage"),
                master_percentage=row_data.get("master_percentage"),
                advance_amount=row_data.get("advance_amount"),
                recording_code=row_data.get("recording_code"),
                notes=row_data.get("notes"),
                is_released=(release_date is not None),
                status_health_score=calculate_health_score(row_data)
            )
            db.add(song)
            db.flush()
            
            for item in checklist_items:
                status = determine_checklist_status(item.code, row_data)
                checklist_status = SongChecklistStatus(
                    song_id=song.id,
                    checklist_item_id=item.id,
                    status=status
                )
                db.add(checklist_status)
            
            if creator:
                credit = SongCredit(
                    song_id=song.id,
                    creator_id=creator.id,
                    role="ARTIST",
                    share_percentage=row_data.get("publishing_percentage", 100)
                )
                db.add(credit)
            
            songs_created += 1
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")
    
    for invalid in validation["invalid_rows"]:
        errors.append(f"Row {invalid['row_index'] + 1}: {', '.join(invalid['errors'])}")
    
    db.commit()
    
    return ImportResult(
        songs_created=songs_created,
        songs_failed=len(validation["invalid_rows"]) + (len(validation["valid_rows"]) - songs_created),
        creator_id=creator.id if creator else None,
        errors=errors[:20]
    )


def calculate_health_score(row_data: Dict[str, Any]) -> float:
    score = 0.0
    total_weight = 100
    
    if row_data.get("isrc"):
        score += 20
    if row_data.get("iswc"):
        score += 15
    if row_data.get("title"):
        score += 10
    if row_data.get("primary_artist"):
        score += 10
    if row_data.get("release_date"):
        score += 10
    if row_data.get("label"):
        score += 5
    if row_data.get("publishing_percentage"):
        score += 10
    if row_data.get("master_percentage"):
        score += 10
    if row_data.get("project_title"):
        score += 5
    if row_data.get("recording_code"):
        score += 5
    
    return min(score, 100.0)


def determine_checklist_status(code: str, row_data: Dict[str, Any]) -> str:
    if code == "ISRC" and row_data.get("isrc"):
        return "COMPLETED"
    if code == "ISWC" and row_data.get("iswc"):
        return "COMPLETED"
    if code == "METADATA" and row_data.get("title") and row_data.get("primary_artist"):
        return "COMPLETED"
    if code == "RELEASE_DATE" and row_data.get("release_date"):
        return "COMPLETED"
    return "NOT_STARTED"
