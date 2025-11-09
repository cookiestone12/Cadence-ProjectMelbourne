from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from ..models import get_db, Song, Songwriter, Analytics, User
from ..utils.auth import get_current_user
from ..services import chartmetric_service, spotify_service, luminate_service
from ..services import valuation_engine, scoring_engine
import openpyxl
import PyPDF2
import io

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

class SongResponse(BaseModel):
    id: int
    title: str
    artist_name: str
    publishing_percentage: float
    master_percentage: float
    spotify_link: str | None
    valuation: float
    score: float
    
    class Config:
        from_attributes = True

class SongDetailResponse(BaseModel):
    id: int
    title: str
    artist_name: str
    publishing_percentage: float
    master_percentage: float
    spotify_link: str | None
    valuation: float
    score: float
    analytics: dict | None
    
    class Config:
        from_attributes = True

@router.get("/songs", response_model=List[SongResponse])
def get_songs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    songs = db.query(Song).all()
    return songs

@router.get("/songs/{song_id}", response_model=SongDetailResponse)
def get_song(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    analytics_data = None
    if song.analytics:
        analytics_data = {
            "spotify_streams": song.analytics.spotify_streams,
            "spotify_monthly_listeners": song.analytics.spotify_monthly_listeners,
            "chartmetric_score": song.analytics.chartmetric_score,
            "playlist_count": song.analytics.playlist_count,
            "top_playlists": song.analytics.top_playlists,
            "regional_data": song.analytics.regional_data,
            "trend_data": song.analytics.trend_data
        }
    
    return {
        "id": song.id,
        "title": song.title,
        "artist_name": song.artist_name,
        "publishing_percentage": song.publishing_percentage,
        "master_percentage": song.master_percentage,
        "spotify_link": song.spotify_link,
        "valuation": song.valuation,
        "score": song.score,
        "analytics": analytics_data
    }

@router.post("/upload")
async def upload_schedule_a(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and parse Schedule A template.
    Supports PDF and Excel formats.
    """
    
    content = await file.read()
    filename = (file.filename or "").lower()
    
    songs_data = []
    songwriter_data = {}
    
    try:
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            # Parse Excel file
            wb = openpyxl.load_workbook(io.BytesIO(content))
            ws = wb.active
            
            # Extract songwriter info (assuming first few rows)
            songwriter_data = {
                "name": ws['B1'].value if ws['B1'].value else "Unknown",
                "pro_affiliation": ws['B2'].value,
                "ipi_number": ws['B3'].value
            }
            
            # Extract song data (assuming table starts at row 5+)
            for row in ws.iter_rows(min_row=6, values_only=True):
                if row[0]:  # If title exists
                    songs_data.append({
                        "title": row[0],
                        "artist_name": row[1] if row[1] else "Unknown",
                        "publishing_percentage": float(row[2]) if row[2] else 0.0,
                        "master_percentage": float(row[3]) if row[3] else 0.0,
                        "spotify_link": row[4] if row[4] else None
                    })
        
        elif filename.endswith('.pdf'):
            # Basic PDF parsing (simple text extraction)
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            
            # Simple parsing logic (this would need to be more sophisticated)
            lines = text.split('\n')
            songwriter_data = {
                "name": "Extracted from PDF",
                "pro_affiliation": None,
                "ipi_number": None
            }
            
            # For now, create a placeholder song
            songs_data.append({
                "title": "Song from PDF",
                "artist_name": "Artist from PDF",
                "publishing_percentage": 0.0,
                "master_percentage": 0.0,
                "spotify_link": None
            })
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing file: {str(e)}")
    
    # Create songwriter
    songwriter = Songwriter(**songwriter_data)
    db.add(songwriter)
    db.commit()
    db.refresh(songwriter)
    
    # Create songs and fetch analytics
    created_songs = []
    for song_data in songs_data:
        # Fetch analytics from mock/real APIs
        chartmetric_data = chartmetric_service.get_track_data(
            song_data['title'], 
            song_data['artist_name']
        )
        spotify_data = spotify_service.get_track_data(song_data.get('spotify_link'))
        luminate_data = luminate_service.get_track_data(
            song_data['title'],
            song_data['artist_name']
        )
        
        # Combine analytics
        analytics_combined = {
            "spotify_streams": spotify_data.get('streams_data', {}).get('total_streams', 0),
            "spotify_monthly_listeners": spotify_data.get('streams_data', {}).get('monthly_streams', 0),
            "chartmetric_score": chartmetric_data.get('chartmetric_score', 0),
            "playlist_count": chartmetric_data.get('playlist_count', 0),
            "top_playlists": chartmetric_data.get('top_playlists', []),
            "regional_data": luminate_data.get('regional_performance', {}),
            "trend_data": {"momentum": chartmetric_data.get('trend_momentum', 'stable')}
        }
        
        # Calculate valuation and score
        valuation = valuation_engine.calculate_valuation(analytics_combined)
        score = scoring_engine.calculate_score(analytics_combined)
        
        # Create song
        song = Song(
            title=song_data['title'],
            artist_name=song_data['artist_name'],
            publishing_percentage=song_data['publishing_percentage'],
            master_percentage=song_data['master_percentage'],
            spotify_link=song_data.get('spotify_link'),
            songwriter_id=songwriter.id,
            valuation=valuation,
            score=score
        )
        db.add(song)
        db.commit()
        db.refresh(song)
        
        # Create analytics
        analytics = Analytics(
            song_id=song.id,
            spotify_streams=analytics_combined['spotify_streams'],
            spotify_monthly_listeners=analytics_combined['spotify_monthly_listeners'],
            chartmetric_score=analytics_combined['chartmetric_score'],
            playlist_count=analytics_combined['playlist_count'],
            top_playlists=analytics_combined['top_playlists'],
            regional_data=analytics_combined['regional_data'],
            trend_data=analytics_combined['trend_data']
        )
        db.add(analytics)
        db.commit()
        
        created_songs.append(song)
    
    return {
        "message": f"Successfully uploaded {len(created_songs)} songs",
        "songs": [{"id": s.id, "title": s.title} for s in created_songs]
    }
