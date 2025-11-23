"""
Import Jack Lomastro's catalog from placement status sheet.
"""
import sys
import os
from datetime import datetime, date
import openpyxl

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.database import SessionLocal
from models.models import Creator, Song, Organization, SongCredit

def parse_percentage(value):
    """Parse percentage value from sheet."""
    if value == '??' or value == 'N/A' or value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def parse_amount(value):
    """Parse dollar amount from sheet."""
    if value == '??' or value == 'N/A' or value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def parse_yes_no_na(value):
    """Parse Yes/No/N/A values."""
    if value is None:
        return 'N/A'
    value_str = str(value).strip()
    if value_str.upper() in ['YES', 'Y']:
        return 'Yes'
    elif value_str.upper() in ['NO', 'N']:
        return 'No'
    else:
        return 'N/A'

def import_jack_lomastro_catalog():
    """Import all of Jack Lomastro's songs from the placement status sheet."""
    
    # Load the Excel file
    wb = openpyxl.load_workbook('../attached_assets/JACK LOMASTRO- PLACEMENT STATUS SHEET _1763865398551.xlsx')
    ws = wb.active
    
    db = SessionLocal()
    
    try:
        # Get Demo Label Co organization
        org = db.query(Organization).filter(Organization.name == "Demo Label Co.").first()
        if not org:
            print("Error: Demo Label Co. organization not found!")
            return
        
        # Create or get Jack Lomastro as a creator
        jack = db.query(Creator).filter(
            Creator.organization_id == org.id,
            Creator.display_name == "Jack Lomastro"
        ).first()
        
        if not jack:
            jack = Creator(
                organization_id=org.id,
                display_name="Jack Lomastro",
                legal_name="Jack Lomastro",
                roles=["PRODUCER", "SONGWRITER"],
                created_at=datetime.utcnow()
            )
            db.add(jack)
            db.commit()
            db.refresh(jack)
            print(f"Created creator: Jack Lomastro (ID: {jack.id})")
        else:
            print(f"Found existing creator: Jack Lomastro (ID: {jack.id})")
        
        # Read headers from row 1
        headers = [cell.value for cell in ws[1]]
        
        # Expected columns (based on the data we saw):
        # Artist, Song, Publishing %, Master %, Advance $, Label, Contract Signed, Master Paid,
        # Contract Location, PRO Registered, DSP Registered, SoundExchange Registered, Paid to DSP,
        # Release Date, Payment Status, Notes (columns 15-16+)
        
        songs_imported = 0
        songs_updated = 0
        
        # Iterate through rows starting from row 2 (skip header)
        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row[0] and not row[1]:  # Skip empty rows
                continue
            
            artist = row[0] if row[0] else "Unknown Artist"
            song_title = row[1] if row[1] else f"Untitled {row_num}"
            publishing_pct = parse_percentage(row[2])
            master_pct = parse_percentage(row[3])
            advance = parse_amount(row[4])
            label = row[5] if row[5] else None
            
            # Contract and registration status (convert to booleans for boolean fields)
            has_contract_str = parse_yes_no_na(row[6])  # Contract Signed
            has_contract = (has_contract_str == 'Yes')
            master_paid = parse_yes_no_na(row[7])  # Master Paid (keep as string)
            contract_location = str(row[8]) if row[8] else 'N/A'  # Contract Location
            is_pro_registered_str = parse_yes_no_na(row[9])  # PRO Registered
            is_pro_registered = (is_pro_registered_str == 'Yes')
            is_dsp_registered_str = parse_yes_no_na(row[10])  # DSP Registered
            is_dsp_registered = (is_dsp_registered_str == 'Yes')
            soundexchange_registered = parse_yes_no_na(row[11])  # SoundExchange Registered (keep as string)
            
            # Release date
            release_date_val = row[13] if len(row) > 13 else None
            release_date = None
            if release_date_val and isinstance(release_date_val, datetime):
                release_date = release_date_val.date()
            
            # Payment status
            payment_status = str(row[14]).strip() if len(row) > 14 and row[14] else 'N/A'
            
            # Notes (concatenate columns 15+ if they exist)
            notes_parts = []
            if len(row) > 15 and row[15]:
                notes_parts.append(str(row[15]))
            if len(row) > 16 and row[16]:
                notes_parts.append(str(row[16]))
            notes = ' | '.join(notes_parts) if notes_parts else None
            
            # Check if song already exists
            existing_song = db.query(Song).filter(
                Song.organization_id == org.id,
                Song.title == song_title,
                Song.primary_artist == artist
            ).first()
            
            if existing_song:
                # Update existing song
                existing_song.is_released = (release_date is not None)
                existing_song.label = label
                existing_song.publishing_percentage = publishing_pct
                existing_song.master_percentage = master_pct
                existing_song.advance_amount = advance
                existing_song.master_paid = master_paid
                existing_song.soundexchange_registered = soundexchange_registered
                existing_song.payment_status = payment_status
                existing_song.contract_location = contract_location
                existing_song.notes = notes
                existing_song.release_date = release_date
                existing_song.is_registered_with_pro = is_pro_registered
                existing_song.is_registered_with_dsp = is_dsp_registered
                existing_song.has_contract_executed = has_contract
                songs_updated += 1
            else:
                # Create new song
                song = Song(
                    organization_id=org.id,
                    title=song_title,
                    primary_artist=artist,
                    is_released=(release_date is not None),
                    label=label,
                    publishing_percentage=publishing_pct,
                    master_percentage=master_pct,
                    advance_amount=advance,
                    master_paid=master_paid,
                    soundexchange_registered=soundexchange_registered,
                    payment_status=payment_status,
                    contract_location=contract_location,
                    notes=notes,
                    release_date=release_date,
                    is_registered_with_pro=is_pro_registered,
                    is_registered_with_dsp=is_dsp_registered,
                    has_contract_executed=has_contract,
                    created_at=datetime.utcnow()
                )
                db.add(song)
                db.flush()
                
                # Add Jack Lomastro as producer credit
                credit = SongCredit(
                    song_id=song.id,
                    creator_id=jack.id,
                    role="PRODUCER",
                    share_percentage=publishing_pct if publishing_pct else 10.0
                )
                db.add(credit)
                songs_imported += 1
        
        db.commit()
        print(f"\n✅ Import complete!")
        print(f"  - Songs imported: {songs_imported}")
        print(f"  - Songs updated: {songs_updated}")
        print(f"  - Total songs for Jack Lomastro: {songs_imported + songs_updated}")
        
    except Exception as e:
        db.rollback()
        print(f"Error importing catalog: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import_jack_lomastro_catalog()
