from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date
import csv
import io

from ..models import get_db, Song, SongCredit, Creator, OrganizationMember, User, SongChecklistStatus, ChecklistItem
from ..utils.auth import get_current_user
from ..utils.csv_parser import parse_csv_with_ai, apply_mapping_to_rows, validate_mapped_data, infer_mapping_from_data

try:
    import openpyxl
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

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


def format_excel_cell(cell_value, number_format=None) -> str:
    """Format Excel cell value to string, handling dates and percentages specially."""
    if cell_value is None:
        return ""
    
    from datetime import datetime, date as date_type
    
    if isinstance(cell_value, (datetime, date_type)):
        return cell_value.strftime("%Y-%m-%d")
    
    if isinstance(cell_value, (int, float)):
        if number_format and '%' in str(number_format):
            converted = cell_value * 100
            if converted == int(converted):
                return str(int(converted))
            return str(round(converted, 4))
        if cell_value == int(cell_value):
            return str(int(cell_value))
        return str(cell_value)
    
    return str(cell_value).strip()


def is_valid_header_row(row: tuple) -> bool:
    """Check if a row looks like a header row (has meaningful text in multiple cells)."""
    if not row:
        return False
    
    non_empty_count = 0
    text_count = 0
    
    for cell in row:
        if cell is not None and str(cell).strip():
            non_empty_count += 1
            if isinstance(cell, str) and not cell.replace('.', '').replace('-', '').isdigit():
                text_count += 1
    
    return non_empty_count >= 2 and text_count >= 1


def parse_excel_file(content: bytes) -> tuple[list, list]:
    """Parse Excel file and return headers and rows."""
    if not EXCEL_SUPPORT:
        raise HTTPException(status_code=400, detail="Excel support not available. Please upload a CSV file.")
    
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    ws = wb.active
    
    all_rows_values = list(ws.iter_rows(values_only=True))
    all_rows_cells = list(ws.iter_rows(values_only=False))
    
    if not all_rows_values:
        wb.close()
        raise HTTPException(status_code=400, detail="Excel file has no data")
    
    header_row_idx = 0
    for idx, row in enumerate(all_rows_values[:10]):
        if is_valid_header_row(row):
            header_row_idx = idx
            break
    
    header_row = all_rows_values[header_row_idx]
    data_rows_cells = all_rows_cells[header_row_idx + 1:]
    data_rows_values = all_rows_values[header_row_idx + 1:]
    
    headers = [str(h).strip() if h else f"Column_{i}" for i, h in enumerate(header_row)]
    
    generic_header_count = sum(1 for h in headers if h.startswith("Column_"))
    if generic_header_count > len(headers) // 2 and data_rows_values:
        first_data = data_rows_values[0] if data_rows_values else None
        if first_data and is_valid_header_row(first_data):
            headers = [str(h).strip() if h else f"Column_{i}" for i, h in enumerate(first_data)]
            data_rows_cells = data_rows_cells[1:]
    
    rows = []
    for row_cells in data_rows_cells:
        if any(cell.value is not None for cell in row_cells):
            row_dict = {}
            for i, cell in enumerate(row_cells):
                if i < len(headers):
                    row_dict[headers[i]] = format_excel_cell(cell.value, cell.number_format)
            rows.append(row_dict)
    
    wb.close()
    return headers, rows


def parse_csv_file(content: bytes) -> tuple[list, list]:
    """Parse CSV file and return headers and rows."""
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
    return headers, rows


@router.post("/preview/{org_id}", response_model=CSVPreviewResponse)
async def preview_csv(
    org_id: int,
    file: UploadFile = File(...),
    all_rows: bool = Query(False, description="Return all rows instead of just preview"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")
    
    filename = file.filename.lower() if file.filename else ""
    is_excel = filename.endswith('.xlsx') or filename.endswith('.xls')
    is_csv = filename.endswith('.csv')
    
    if not is_excel and not is_csv:
        raise HTTPException(status_code=400, detail="File must be a CSV or Excel file (.csv, .xlsx, .xls)")
    
    content = await file.read()
    
    if is_excel:
        headers, rows = parse_excel_file(content)
    else:
        headers, rows = parse_csv_file(content)
    
    ai_result = parse_csv_with_ai("", headers, org_id=org_id)
    initial_mapping = ai_result.get("mapping", {})
    
    generic_count = sum(1 for h in headers if h.startswith("Column_"))
    if generic_count > 0 and rows:
        initial_mapping = infer_mapping_from_data(headers, rows, initial_mapping)
    
    preview_rows = rows if all_rows else rows[:5]
    
    return CSVPreviewResponse(
        headers=headers,
        mapping=initial_mapping,
        preview_rows=preview_rows,
        row_count=len(rows),
        success=ai_result.get("success", False),
        error=ai_result.get("error")
    )


@router.post("/document-preview/{org_id}")
async def preview_document(
    org_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from backend.services.document_parser import parse_document

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()

    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")

    filename = file.filename or ""
    lower = filename.lower()
    if not (lower.endswith('.pdf') or lower.endswith('.docx') or lower.endswith('.doc')):
        raise HTTPException(status_code=400, detail="File must be a PDF or Word document (.pdf, .docx)")

    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    content = await file.read()
    result = parse_document(content, filename)

    if result.errors:
        raise HTTPException(status_code=400, detail=result.errors[0])

    return result.to_preview_response()


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
