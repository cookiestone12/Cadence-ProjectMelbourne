from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from openpyxl import load_workbook
import csv
import io
from datetime import datetime
from ..models import (
    get_db, Song, Creator, SongCredit, OrganizationMember, User
)
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/schedule-a", tags=["schedule-a"])

def parse_yes_no_na(value):
    """Parse Yes/No/N/A values from Excel"""
    if value is None:
        return 'N/A'
    str_val = str(value).strip().upper()
    if str_val in ['YES', 'Y', '1', 'TRUE']:
        return 'Yes'
    elif str_val in ['NO', 'N', '0', 'FALSE']:
        return 'No'
    return 'N/A'

def parse_percentage(value):
    """Parse percentage values"""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace('%', '').strip()
        return float(value)
    except:
        return None

def parse_amount(value):
    """Parse currency amounts (stored in cents)"""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace('$', '').replace(',', '').strip()
        amount = float(value)
        return int(amount * 100)  # Convert to cents
    except:
        return None

def parse_date(value):
    """Parse date values"""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d']:
                try:
                    return datetime.strptime(value, fmt).date()
                except:
                    continue
        elif hasattr(value, 'date'):
            return value.date()
        return None
    except:
        return None

@router.post("/upload/{org_id}")
async def upload_schedule_a(
    org_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and parse a Schedule A file (CSV or Excel).
    Expected columns (in any order):
    - Song Title (required)
    - Artist (required)
    - Writer/Creator (optional - will create/link creator)
    - ISRC, ISWC, Project Title, Release Date
    - Label, Recording Code
    - Publishing %, Master %, Advance Amount
    - Contract Signed, Master Paid, Contract Location
    - PRO Registered, DSP Registered, SoundExchange Registered
    - Payment Status, Notes
    """
    # Verify membership
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")
    
    # Security: Validate file size (max 10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
    
    # Security: Validate MIME type
    allowed_types = [
        'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/csv'
    ]
    if file.content_type not in allowed_types:
        # Fallback to extension check if MIME type is generic
        if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload CSV or Excel file")
    
    try:
        
        songs_created = 0
        songs_updated = 0
        songs_skipped = 0
        errors = []
        
        # Detect file type and parse
        if file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
            # Parse Excel file with error handling
            try:
                wb = load_workbook(io.BytesIO(contents), data_only=True, read_only=True)
                ws = wb.active
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to parse Excel file: {str(e)}")
            
            # Get headers from first row
            headers = [cell.value for cell in ws[1]]
            header_map = {}
            for idx, header in enumerate(headers):
                if header:
                    header_lower = str(header).lower().strip()
                    header_map[header_lower] = idx
            
            # Process each row
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    # Extract required fields
                    song_title = row[header_map.get('song title', header_map.get('title', 0))]
                    artist = row[header_map.get('artist', header_map.get('primary artist', 1))]
                    
                    if not song_title or not artist:
                        songs_skipped += 1
                        continue
                    
                    # Parse all fields
                    data = {
                        'isrc': row[header_map.get('isrc')] if 'isrc' in header_map else None,
                        'iswc': row[header_map.get('iswc')] if 'iswc' in header_map else None,
                        'project_title': row[header_map.get('project title', header_map.get('album'))] if 'project title' in header_map or 'album' in header_map else None,
                        'release_date': parse_date(row[header_map.get('release date')]) if 'release date' in header_map else None,
                        'label': row[header_map.get('label')] if 'label' in header_map else None,
                        'recording_code': row[header_map.get('recording code')] if 'recording code' in header_map else None,
                        'publishing_percentage': parse_percentage(row[header_map.get('publishing %', header_map.get('pub %'))]) if 'publishing %' in header_map or 'pub %' in header_map else None,
                        'master_percentage': parse_percentage(row[header_map.get('master %')]) if 'master %' in header_map else None,
                        'advance_amount': parse_amount(row[header_map.get('advance', header_map.get('advance amount'))]) if 'advance' in header_map or 'advance amount' in header_map else None,
                        'contract_location': row[header_map.get('contract location')] if 'contract location' in header_map else None,
                        'payment_status': row[header_map.get('payment status')] if 'payment status' in header_map else 'PENDING',
                        'notes': row[header_map.get('notes')] if 'notes' in header_map else None,
                    }
                    
                    # Parse Yes/No fields
                    has_contract = False
                    if 'contract signed' in header_map:
                        has_contract_str = parse_yes_no_na(row[header_map['contract signed']])
                        has_contract = (has_contract_str == 'Yes')
                    
                    is_pro_registered = False
                    if 'pro registered' in header_map:
                        is_pro_str = parse_yes_no_na(row[header_map['pro registered']])
                        is_pro_registered = (is_pro_str == 'Yes')
                    
                    is_dsp_registered = False
                    if 'dsp registered' in header_map:
                        is_dsp_str = parse_yes_no_na(row[header_map['dsp registered']])
                        is_dsp_registered = (is_dsp_str == 'Yes')
                    
                    data['master_paid'] = parse_yes_no_na(row[header_map.get('master paid')]) if 'master paid' in header_map else 'N/A'
                    data['soundexchange_registered'] = parse_yes_no_na(row[header_map.get('soundexchange registered')]) if 'soundexchange registered' in header_map else 'N/A'
                    
                    # Check if song exists
                    existing_song = db.query(Song).filter(
                        Song.organization_id == org_id,
                        Song.title == song_title,
                        Song.primary_artist == artist
                    ).first()
                    
                    if existing_song:
                        # Update existing song
                        for key, value in data.items():
                            if value is not None:
                                setattr(existing_song, key, value)
                        existing_song.has_contract_executed = has_contract
                        existing_song.is_registered_with_pro = is_pro_registered
                        existing_song.is_registered_with_dsp = is_dsp_registered
                        existing_song.is_released = (data['release_date'] is not None)
                        songs_updated += 1
                    else:
                        # Create new song
                        song = Song(
                            organization_id=org_id,
                            title=song_title,
                            primary_artist=artist,
                            is_released=(data['release_date'] is not None),
                            has_contract_executed=has_contract,
                            is_registered_with_pro=is_pro_registered,
                            is_registered_with_dsp=is_dsp_registered,
                            **data
                        )
                        db.add(song)
                        songs_created += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_idx}: {str(e)}")
                    songs_skipped += 1
        
        elif file.filename.endswith('.csv'):
            # Parse CSV file with encoding detection
            try:
                content_str = contents.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content_str = contents.decode('latin-1')
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Failed to decode CSV file: {str(e)}")
            
            csv_reader = csv.DictReader(io.StringIO(content_str))
            
            for row_idx, row in enumerate(csv_reader, start=2):
                try:
                    song_title = row.get('Song Title') or row.get('Title')
                    artist = row.get('Artist') or row.get('Primary Artist')
                    
                    if not song_title or not artist:
                        songs_skipped += 1
                        continue
                    
                    # Similar parsing logic as Excel
                    data = {
                        'isrc': row.get('ISRC'),
                        'iswc': row.get('ISWC'),
                        'project_title': row.get('Project Title') or row.get('Album'),
                        'release_date': parse_date(row.get('Release Date')),
                        'label': row.get('Label'),
                        'recording_code': row.get('Recording Code'),
                        'publishing_percentage': parse_percentage(row.get('Publishing %') or row.get('Pub %')),
                        'master_percentage': parse_percentage(row.get('Master %')),
                        'advance_amount': parse_amount(row.get('Advance') or row.get('Advance Amount')),
                        'contract_location': row.get('Contract Location'),
                        'payment_status': row.get('Payment Status') or 'PENDING',
                        'notes': row.get('Notes'),
                        'master_paid': parse_yes_no_na(row.get('Master Paid')),
                        'soundexchange_registered': parse_yes_no_na(row.get('SoundExchange Registered')),
                    }
                    
                    has_contract = parse_yes_no_na(row.get('Contract Signed')) == 'Yes'
                    is_pro_registered = parse_yes_no_na(row.get('PRO Registered')) == 'Yes'
                    is_dsp_registered = parse_yes_no_na(row.get('DSP Registered')) == 'Yes'
                    
                    # Check if song exists
                    existing_song = db.query(Song).filter(
                        Song.organization_id == org_id,
                        Song.title == song_title,
                        Song.primary_artist == artist
                    ).first()
                    
                    if existing_song:
                        for key, value in data.items():
                            if value is not None:
                                setattr(existing_song, key, value)
                        existing_song.has_contract_executed = has_contract
                        existing_song.is_registered_with_pro = is_pro_registered
                        existing_song.is_registered_with_dsp = is_dsp_registered
                        existing_song.is_released = (data['release_date'] is not None)
                        songs_updated += 1
                    else:
                        song = Song(
                            organization_id=org_id,
                            title=song_title,
                            primary_artist=artist,
                            is_released=(data['release_date'] is not None),
                            has_contract_executed=has_contract,
                            is_registered_with_pro=is_pro_registered,
                            is_registered_with_dsp=is_dsp_registered,
                            **data
                        )
                        db.add(song)
                        songs_created += 1
                
                except Exception as e:
                    errors.append(f"Row {row_idx}: {str(e)}")
                    songs_skipped += 1
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV or Excel file.")
        
        db.commit()
        
        return {
            "success": True,
            "songs_created": songs_created,
            "songs_updated": songs_updated,
            "songs_skipped": songs_skipped,
            "errors": errors[:10]  # Return first 10 errors
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")
