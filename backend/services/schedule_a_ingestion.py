"""
Schedule A Ingestion Service - Parses Excel/CSV placement sheets and creates creators/songs.
"""
import os
import re
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Tuple
from io import BytesIO

import openpyxl
import csv

from sqlalchemy.orm import Session
from backend.models.models import Creator, Song, Organization, SongCredit, ChecklistItem, SongChecklistStatus


class ScheduleAIngestionResult:
    """Result of a Schedule A ingestion operation."""
    def __init__(self):
        self.songs_created = 0
        self.songs_updated = 0
        self.songs_skipped = 0
        self.credits_created = 0
        self.creator_name = None
        self.creator_id = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "songs_created": self.songs_created,
            "songs_updated": self.songs_updated,
            "songs_skipped": self.songs_skipped,
            "credits_created": self.credits_created,
            "creator_name": self.creator_name,
            "creator_id": self.creator_id,
            "errors": self.errors,
            "warnings": self.warnings
        }


def parse_percentage(value) -> Optional[float]:
    """Parse percentage value from sheet (handles decimals like 0.24 = 24%).
    Always caps at 100% and rounds to 2 decimal places."""
    if value == '??' or value == 'N/A' or value is None:
        return None
    try:
        pct = float(value)
        if pct < 1:
            pct = pct * 100
        pct = min(pct, 100.0)
        return round(pct, 2)
    except (ValueError, TypeError):
        return None


def parse_amount(value) -> Optional[int]:
    """Parse dollar amount from sheet and convert to cents."""
    if value == '??' or value == 'N/A' or value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace('$', '').replace(',', '').strip()
        dollars = float(value)
        return int(dollars * 100)
    except (ValueError, TypeError):
        return None


def parse_yes_no(value) -> bool:
    """Parse Yes/No values to boolean."""
    if value is None:
        return False
    value_str = str(value).strip().upper()
    return value_str in ['YES', 'Y', 'TRUE', '1', 'X', 'DONE', 'COMPLETED']


def parse_yes_no_na(value):
    """Parse Yes/No/N/A values as string. Returns None for missing values."""
    if value is None:
        return None
    value_str = str(value).strip().upper()
    if not value_str:
        return None
    if value_str in ['YES', 'Y', 'TRUE', '1', 'X', 'DONE', 'COMPLETED']:
        return 'Yes'
    elif value_str in ['NO', 'N', 'FALSE', '0']:
        return 'No'
    elif value_str in ['N/A', 'NA', 'NOT APPLICABLE']:
        return 'N/A'
    else:
        return None


def parse_date(value) -> Optional[date]:
    """Parse date from various formats."""
    if value is None:
        return None
    try:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%d/%m/%Y']:
                try:
                    return datetime.strptime(value.strip(), fmt).date()
                except:
                    continue
        return None
    except:
        return None


def extract_creator_name_from_filename(filename: str) -> Optional[str]:
    """
    Extract creator name from filename.
    Expects format like: "JACK LOMASTRO- PLACEMENT STATUS SHEET.xlsx"
    or "Creator Name - Placement Sheet.xlsx"
    """
    if not filename:
        return None
    
    base = os.path.splitext(filename)[0]
    
    patterns = [
        r'^([A-Z][A-Z\s]+?)[\s]*[-–—][\s]*PLACEMENT',
        r'^([A-Za-z][A-Za-z\s]+?)[\s]*[-–—][\s]*[Pp]lacement',
        r'^([A-Za-z][A-Za-z\s]+?)[\s]*[-–—][\s]*[Ss]chedule',
        r'^([A-Za-z][A-Za-z\s]+?)[\s]*[-–—]',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, base)
        if match:
            name = match.group(1).strip()
            name = ' '.join(word.capitalize() for word in name.lower().split())
            return name
    
    return None


def find_column_index(headers: List[str], possible_names: List[str]) -> Optional[int]:
    """Find the column index that matches any of the possible names."""
    for i, header in enumerate(headers):
        if header:
            header_lower = str(header).lower().strip()
            for name in possible_names:
                if name.lower() in header_lower:
                    return i
    return None


def map_columns(headers: List[str]) -> Dict[str, Optional[int]]:
    """Map expected fields to column indices based on headers."""
    return {
        'artist': find_column_index(headers, ['artist', 'artist name', 'primary artist']),
        'title': find_column_index(headers, ['song title', 'title', 'song', 'track title', 'track']),
        'publishing_pct': find_column_index(headers, ['publishing %', 'publishing', 'pub %', 'pub']),
        'master_pct': find_column_index(headers, ['royalty', 'master %', 'master', 'roy %']),
        'advance': find_column_index(headers, ['advance', 'advance ($)', 'advance amount', 'advance $$']),
        'label': find_column_index(headers, ['label', 'record label']),
        'credited': find_column_index(headers, ['credited', 'credit']),
        'paperwork': find_column_index(headers, ['received paperwork', 'paperwork', 'received']),
        'agreement': find_column_index(headers, ['agreement', 'contract', 'contract location']),
        'bmi_registration': find_column_index(headers, ['bmi', 'bmi registration', 'pro registration', 'pro reg']),
        'kobalt_registration': find_column_index(headers, ['kobalt', 'kobalt reg', 'dsp registration', 'dsp reg']),
        'soundexchange': find_column_index(headers, ['soundexchange', 'sound exchange', 'sx']),
        'payment_received': find_column_index(headers, ['payment received', 'payment', 'paid']),
        'release_date': find_column_index(headers, ['date released', 'release date', 'released']),
        'invoice_sent': find_column_index(headers, ['invoice sent', 'invoice', 'invoiced']),
        'notes': find_column_index(headers, ['notes', 'note']),
        'notes_2': find_column_index(headers, ['notes 2', 'notes: 2', 'additional notes']),
        'isrc': find_column_index(headers, ['isrc', 'isrc code']),
        'iswc': find_column_index(headers, ['iswc', 'iswc code']),
    }


def get_cell_value(row: tuple, index: Optional[int]) -> Any:
    """Safely get a cell value from a row by index."""
    if index is None or index >= len(row):
        return None
    return row[index]


def ingest_schedule_a(
    db: Session,
    organization: Organization,
    file_content: bytes,
    filename: str,
    creator_name_override: Optional[str] = None
) -> ScheduleAIngestionResult:
    """
    Ingest a Schedule A / Placement Status Sheet file.
    
    Args:
        db: Database session
        organization: The organization to import songs into
        file_content: Raw file bytes
        filename: Original filename (used to extract creator name)
        creator_name_override: Optional explicit creator name (takes precedence)
    
    Returns:
        ScheduleAIngestionResult with import statistics
    """
    result = ScheduleAIngestionResult()
    
    creator_name = creator_name_override or extract_creator_name_from_filename(filename)
    if not creator_name:
        result.errors.append(f"Could not determine creator name from filename: {filename}. Please rename the file to 'CREATOR NAME - Placement Sheet.xlsx'")
        return result
    
    result.creator_name = creator_name
    
    try:
        if filename.lower().endswith('.csv'):
            rows = parse_csv(file_content)
        else:
            rows = parse_excel(file_content)
        
        if not rows or len(rows) < 2:
            result.errors.append("File is empty or has no data rows")
            return result
        
        headers = [str(h).strip() if h else '' for h in rows[0]]
        column_map = map_columns(headers)
        
        if column_map['title'] is None:
            result.errors.append("Could not find 'Song Title' or 'Title' column in the file")
            return result
        
        creator = db.query(Creator).filter(
            Creator.organization_id == organization.id,
            Creator.display_name.ilike(creator_name)
        ).first()
        
        if not creator:
            creator = Creator(
                organization_id=organization.id,
                display_name=creator_name,
                legal_name=creator_name,
                roles=["PRODUCER", "SONGWRITER"],
                created_at=datetime.utcnow()
            )
            db.add(creator)
            db.flush()
            result.warnings.append(f"Created new creator: {creator_name}")
        
        result.creator_id = creator.id
        
        for row_num, row in enumerate(rows[1:], start=2):
            try:
                song_title = get_cell_value(row, column_map['title'])
                if not song_title or str(song_title).strip() == '' or str(song_title).strip() == 'None':
                    result.songs_skipped += 1
                    continue
                
                song_title = str(song_title).strip()
                artist = str(get_cell_value(row, column_map['artist']) or 'Unknown Artist').strip()
                
                publishing_pct = parse_percentage(get_cell_value(row, column_map['publishing_pct']))
                master_pct = parse_percentage(get_cell_value(row, column_map['master_pct']))
                advance = parse_amount(get_cell_value(row, column_map['advance']))
                label = get_cell_value(row, column_map['label'])
                label = str(label).strip() if label else None
                
                has_contract_sent = parse_yes_no(get_cell_value(row, column_map['credited']))
                has_contract_executed = parse_yes_no(get_cell_value(row, column_map['paperwork']))
                contract_location = get_cell_value(row, column_map['agreement'])
                contract_location = str(contract_location).strip() if contract_location else None
                
                is_registered_with_pro = parse_yes_no(get_cell_value(row, column_map['bmi_registration']))
                is_registered_with_dsp = parse_yes_no_na(get_cell_value(row, column_map['kobalt_registration']))
                soundexchange_registered = parse_yes_no_na(get_cell_value(row, column_map['soundexchange']))
                
                is_paid = parse_yes_no_na(get_cell_value(row, column_map['payment_received']))
                release_date = parse_date(get_cell_value(row, column_map['release_date']))
                is_invoiced = parse_yes_no_na(get_cell_value(row, column_map['invoice_sent']))
                
                notes_1 = get_cell_value(row, column_map['notes'])
                notes_2 = get_cell_value(row, column_map['notes_2'])
                notes_1 = str(notes_1).strip() if notes_1 else ''
                notes_2 = str(notes_2).strip() if notes_2 else ''
                notes = f"{notes_1}\n{notes_2}".strip() if notes_1 or notes_2 else None
                
                isrc = get_cell_value(row, column_map['isrc'])
                isrc = str(isrc).strip() if isrc else None
                iswc = get_cell_value(row, column_map['iswc'])
                iswc = str(iswc).strip() if iswc else None
                
                if is_paid == 'Yes':
                    payment_status = 'PAID'
                elif is_invoiced == 'Yes':
                    payment_status = 'INVOICED'
                else:
                    payment_status = 'PENDING'
                
                master_paid = 'Yes' if is_paid == 'Yes' else None
                
                existing_song = db.query(Song).filter(
                    Song.organization_id == organization.id,
                    Song.title == song_title,
                    Song.primary_artist == artist
                ).first()
                
                if existing_song:
                    existing_song.publishing_percentage = publishing_pct
                    existing_song.master_percentage = master_pct
                    existing_song.advance_amount = advance
                    existing_song.label = label
                    existing_song.has_contract_sent = has_contract_sent
                    existing_song.has_contract_executed = has_contract_executed
                    existing_song.contract_location = contract_location
                    existing_song.is_registered_with_pro = is_registered_with_pro
                    existing_song.is_registered_with_dsp = is_registered_with_dsp
                    existing_song.soundexchange_registered = soundexchange_registered
                    existing_song.is_paid = is_paid
                    existing_song.is_invoiced = is_invoiced
                    existing_song.release_date = release_date
                    existing_song.is_released = (release_date is not None)
                    existing_song.payment_status = payment_status
                    existing_song.master_paid = master_paid
                    existing_song.notes = notes
                    if isrc:
                        existing_song.isrc = isrc
                    if iswc:
                        existing_song.iswc = iswc
                    
                    from backend.utils.health_sync import sync_song_to_checklist
                    sync_song_to_checklist(db, existing_song)
                    
                    song = existing_song
                    result.songs_updated += 1
                else:
                    song = Song(
                        organization_id=organization.id,
                        title=song_title,
                        primary_artist=artist,
                        publishing_percentage=publishing_pct,
                        master_percentage=master_pct,
                        advance_amount=advance,
                        label=label,
                        has_contract_sent=has_contract_sent,
                        has_contract_executed=has_contract_executed,
                        contract_location=contract_location,
                        is_registered_with_pro=is_registered_with_pro,
                        is_registered_with_dsp=is_registered_with_dsp,
                        soundexchange_registered=soundexchange_registered,
                        is_paid=is_paid,
                        is_invoiced=is_invoiced,
                        release_date=release_date,
                        is_released=(release_date is not None),
                        payment_status=payment_status,
                        master_paid=master_paid,
                        notes=notes,
                        isrc=isrc,
                        iswc=iswc,
                        created_at=datetime.utcnow()
                    )
                    db.add(song)
                    db.flush()
                    
                    from backend.utils.health_sync import sync_song_to_checklist
                    sync_song_to_checklist(db, song)
                    
                    result.songs_created += 1
                
                existing_credit = db.query(SongCredit).filter(
                    SongCredit.song_id == song.id,
                    SongCredit.creator_id == creator.id
                ).first()
                
                if not existing_credit:
                    credit = SongCredit(
                        song_id=song.id,
                        creator_id=creator.id,
                        role="Producer",
                        share_percentage=publishing_pct or 100.0
                    )
                    db.add(credit)
                    result.credits_created += 1
                    
            except Exception as e:
                result.warnings.append(f"Row {row_num}: {str(e)}")
                continue
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        result.errors.append(f"Failed to process file: {str(e)}")
    
    return result


def parse_excel(file_content: bytes) -> List[tuple]:
    """Parse Excel file and return rows as list of tuples."""
    wb = openpyxl.load_workbook(BytesIO(file_content), data_only=True)
    ws = wb.active
    
    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append(row)
    
    return rows


def parse_csv(file_content: bytes) -> List[tuple]:
    """Parse CSV file and return rows as list of tuples."""
    content = file_content.decode('utf-8-sig')
    reader = csv.reader(content.splitlines())
    return [tuple(row) for row in reader]
