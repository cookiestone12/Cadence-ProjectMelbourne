from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from pydantic import BaseModel
from ..models import get_db, Song, Songwriter, Analytics, User, Catalog
from ..utils.auth import get_current_user
from ..services import chartmetric_service, spotify_service, luminate_service
from ..services import valuation_engine, scoring_engine
import openpyxl
import PyPDF2
import io
import json
import os

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

class ValuationResponse(BaseModel):
    estimated_revenue: float
    low: float
    base: float
    high: float

class ScoreBreakdownResponse(BaseModel):
    catalog_value: float
    growth_momentum: float
    metadata_health: float
    exploitation_potential: float

class SongResponse(BaseModel):
    id: int
    title: str
    artist_name: str
    publishing_percentage: float
    master_percentage: float
    spotify_link: str | None
    estimated_revenue: float
    valuation_low: float
    valuation_base: float
    valuation_high: float
    score: float
    score_breakdown: dict | None
    
    class Config:
        from_attributes = True

class SongDetailResponse(BaseModel):
    id: int
    title: str
    artist_name: str
    publishing_percentage: float
    master_percentage: float
    spotify_link: str | None
    isrc: str | None
    iswc: str | None
    writer_splits: list | None
    estimated_revenue: float
    valuation_low: float
    valuation_base: float
    valuation_high: float
    score: float
    score_breakdown: dict | None
    analytics: dict | None
    
    class Config:
        from_attributes = True

class CatalogSummaryResponse(BaseModel):
    id: int
    name: str
    total_songs: int
    total_publishing_percentage: float
    total_valuation_low: float
    total_valuation_base: float
    total_valuation_high: float
    avg_score: float
    avg_score_breakdown: dict

@router.get("/summary", response_model=List[CatalogSummaryResponse])
def get_catalog_summary(
    db: Session = Depends(get_db)
):
    """Get summary for all catalogs"""
    catalogs = db.query(Catalog).all()
    result = []
    
    for catalog in catalogs:
        songs = catalog.songs
        if not songs:
            continue
            
        total_publishing = sum(s.publishing_percentage for s in songs)
        total_val_low = sum(s.valuation_low for s in songs)
        total_val_base = sum(s.valuation_base for s in songs)
        total_val_high = sum(s.valuation_high for s in songs)
        avg_score = sum(s.score for s in songs) / len(songs) if songs else 0
        
        avg_breakdown = {
            "catalog_value": 0,
            "growth_momentum": 0,
            "metadata_health": 0,
            "exploitation_potential": 0
        }
        
        for song in songs:
            if song.score_breakdown:
                for key in avg_breakdown.keys():
                    avg_breakdown[key] += song.score_breakdown.get(key, 0)
        
        for key in avg_breakdown.keys():
            avg_breakdown[key] = round(avg_breakdown[key] / len(songs), 2) if songs else 0
        
        result.append({
            "id": catalog.id,
            "name": catalog.name,
            "total_songs": len(songs),
            "total_publishing_percentage": round(total_publishing, 2),
            "total_valuation_low": round(total_val_low, 2),
            "total_valuation_base": round(total_val_base, 2),
            "total_valuation_high": round(total_val_high, 2),
            "avg_score": round(avg_score, 2),
            "avg_score_breakdown": avg_breakdown
        })
    
    return result

@router.get("/songs", response_model=List[SongResponse])
def get_songs(
    db: Session = Depends(get_db)
):
    songs = db.query(Song).all()
    return songs

@router.get("/songs/{song_id}", response_model=SongDetailResponse)
def get_song(
    song_id: int,
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
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
        
        # Add growth metrics to analytics for valuation/scoring
        analytics_combined['growth_3_month'] = chartmetric_data.get('growth_3_month', 0)
        analytics_combined['growth_12_month'] = chartmetric_data.get('growth_12_month', 0)
        analytics_combined['has_isrc'] = False
        analytics_combined['has_iswc'] = False
        analytics_combined['has_spotify_link'] = bool(song_data.get('spotify_link'))
        
        # Calculate valuation and score
        valuation = valuation_engine.calculate_valuation(analytics_combined)
        score = scoring_engine.calculate_score(analytics_combined)
        
        # Create or get first catalog
        catalog = db.query(Catalog).first()
        if not catalog:
            catalog = Catalog(name="Uploaded Catalog")
            db.add(catalog)
            db.commit()
            db.refresh(catalog)
        
        # Create song
        song = Song(
            title=song_data['title'],
            artist_name=song_data['artist_name'],
            publishing_percentage=song_data['publishing_percentage'],
            master_percentage=song_data['master_percentage'],
            spotify_link=song_data.get('spotify_link'),
            songwriter_id=songwriter.id,
            catalog_id=catalog.id,
            valuation_low=valuation['valuation_low'],
            valuation_base=valuation['valuation_base'],
            valuation_high=valuation['valuation_high'],
            estimated_revenue=valuation['estimated_revenue'],
            score=score['overall_score'],
            score_breakdown={
                'catalog_value': score['catalog_value'],
                'growth_momentum': score['growth_momentum'],
                'metadata_health': score['metadata_health'],
                'exploitation_potential': score['exploitation_potential']
            }
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

@router.get("/search")
def search_songs(
    q: str,
    db: Session = Depends(get_db)
):
    """
    Search for songs by title or artist name.
    Returns local catalog matches or mock external data if no match found.
    """
    
    search_term = q.lower().strip()
    
    local_songs = db.query(Song).filter(
        or_(
            Song.title.ilike(f"%{search_term}%"),
            Song.artist_name.ilike(f"%{search_term}%")
        )
    ).all()
    
    results = []
    
    for song in local_songs:
        analytics_data = {}
        if song.analytics:
            analytics_data = {
                "total_streams": song.analytics.spotify_streams,
                "monthly_streams": song.analytics.spotify_monthly_listeners,
                "playlist_count": song.analytics.playlist_count,
                "top_playlist": song.analytics.top_playlists[0]['name'] if song.analytics.top_playlists else None,
                "top_playlist_followers": song.analytics.top_playlists[0]['followers'] if song.analytics.top_playlists else 0,
                "growth_3_month": song.analytics.trend_data.get('growth_3_month', 0),
                "chartmetric_score": song.analytics.chartmetric_score,
                "top_territories": [
                    {"country": country, "streams": data.get('streams', 0)}
                    for country, data in (song.analytics.regional_data or {}).items()
                ][:3]
            }
        
        results.append({
            "title": song.title,
            "artist_name": song.artist_name,
            "in_catalog": True,
            "catalog_name": song.catalog.name if song.catalog else None,
            "publishing_percentage": song.publishing_percentage,
            "master_percentage": song.master_percentage,
            "spotify_link": song.spotify_link,
            "valuation": {
                "estimated_revenue": song.estimated_revenue,
                "low": song.valuation_low,
                "base": song.valuation_base,
                "high": song.valuation_high
            },
            "score": song.score,
            "score_breakdown": song.score_breakdown,
            "metrics": analytics_data
        })
    
    if not results:
        tracks_path = os.path.join(os.path.dirname(__file__), '..', '..', 'mock_data', 'external_metrics_tracks.json')
        artists_path = os.path.join(os.path.dirname(__file__), '..', '..', 'mock_data', 'external_metrics_artists.json')
        
        try:
            with open(tracks_path, 'r') as f:
                track_metrics = json.load(f)
            with open(artists_path, 'r') as f:
                artist_metrics = json.load(f)
            
            for title, metrics in track_metrics.items():
                if search_term in title.lower():
                    artist_name = "Unknown Artist"
                    for artist, artist_data in artist_metrics.items():
                        if search_term in artist.lower():
                            artist_name = artist
                            break
                    
                    analytics_data = {
                        'spotify_streams': metrics.get('total_streams', 0),
                        'spotify_monthly_listeners': metrics.get('monthly_streams', 0),
                        'chartmetric_score': metrics.get('chartmetric_score', 0),
                        'playlist_count': metrics.get('playlist_count', 0),
                        'top_playlists': [{
                            'name': metrics.get('top_playlist', ''),
                            'followers': metrics.get('top_playlist_followers', 0),
                            'position': 10
                        }],
                        'growth_3_month': metrics.get('growth_3_month', 0),
                        'growth_12_month': metrics.get('growth_12_month', 0),
                        'has_isrc': True,
                        'has_iswc': True,
                        'has_spotify_link': True
                    }
                    
                    valuation = valuation_engine.calculate_valuation(analytics_data)
                    score = scoring_engine.calculate_score(analytics_data)
                    
                    artist_data = artist_metrics.get(artist_name, {})
                    
                    results.append({
                        "title": title,
                        "artist_name": artist_name,
                        "in_catalog": False,
                        "catalog_name": None,
                        "publishing_percentage": 0,
                        "master_percentage": 0,
                        "spotify_link": None,
                        "valuation": valuation,
                        "score": score['overall_score'],
                        "score_breakdown": {
                            "catalog_value": score['catalog_value'],
                            "growth_momentum": score['growth_momentum'],
                            "metadata_health": score['metadata_health'],
                            "exploitation_potential": score['exploitation_potential']
                        },
                        "metrics": {
                            "total_streams": metrics.get('total_streams', 0),
                            "monthly_streams": metrics.get('monthly_streams', 0),
                            "playlist_count": metrics.get('playlist_count', 0),
                            "top_playlist": metrics.get('top_playlist'),
                            "top_playlist_followers": metrics.get('top_playlist_followers', 0),
                            "growth_3_month": metrics.get('growth_3_month', 0),
                            "chartmetric_score": metrics.get('chartmetric_score', 0),
                            "top_territories": metrics.get('top_territories', [])
                        },
                        "artist_metrics": {
                            "monthly_listeners": artist_data.get('monthly_listeners', 0),
                            "followers": artist_data.get('followers', 0),
                            "follower_growth_3_month": artist_data.get('follower_growth_3_month', 0),
                            "genre_tags": artist_data.get('genre_tags', [])
                        }
                    })
                    break
        except Exception as e:
            print(f"Error loading mock data: {e}")
    
    return {"results": results, "count": len(results)}
