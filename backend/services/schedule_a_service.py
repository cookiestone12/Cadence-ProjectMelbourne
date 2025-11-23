from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
import csv
import io
from ..models import Creator, Song, SongCredit, SongDSPLink

def generate_schedule_a_csv(creator_id: int, db: Session) -> str:
    """Generate Schedule A CSV for a creator's catalog"""
    
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise ValueError("Creator not found")
    
    credits = db.query(SongCredit, Song).join(
        Song, SongCredit.song_id == Song.id
    ).filter(
        SongCredit.creator_id == creator_id
    ).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Song Title',
        'Role',
        'Share %',
        'ISRC',
        'ISWC',
        'Primary Artist',
        'Project',
        'Release Date',
        'Apple Music URL',
        'Spotify URL',
        'Registered with PRO',
        'Registered with DSP',
        'Contract Sent',
        'Contract Executed',
        'Invoiced',
        'Paid'
    ])
    
    for credit, song in credits:
        dsp_links = db.query(SongDSPLink).filter(SongDSPLink.song_id == song.id).all()
        
        apple_url = ""
        spotify_url = ""
        for link in dsp_links:
            if link.platform == "APPLE_MUSIC":
                apple_url = link.url
            elif link.platform == "SPOTIFY":
                spotify_url = link.url
        
        writer.writerow([
            song.title,
            credit.role,
            f"{credit.share_percentage:.2f}" if credit.share_percentage else "N/A",
            song.isrc or "",
            song.iswc or "",
            song.primary_artist,
            song.project_title or "",
            song.release_date.isoformat() if song.release_date else "",
            apple_url,
            spotify_url,
            "Yes" if song.is_registered_with_pro else "No",
            "Yes" if song.is_registered_with_dsp else "No",
            "Yes" if song.has_contract_sent else "No",
            "Yes" if song.has_contract_executed else "No",
            "Yes" if song.is_invoiced else "No",
            "Yes" if song.is_paid else "No"
        ])
    
    csv_content = output.getvalue()
    output.close()
    
    return csv_content
