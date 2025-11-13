import json
import os
from sqlalchemy.orm import Session
from .models import Catalog, Song, Songwriter, Analytics, get_db
from .services.valuation_engine import calculate_valuation
from .services.scoring_engine import calculate_score

def load_mock_data(file_path):
    """Load JSON mock data from file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def seed_demo_catalog(db: Session):
    """
    Seed the database with demo catalog data on startup if no data exists.
    Only runs once when the database is empty.
    """
    
    existing_catalogs = db.query(Catalog).count()
    if existing_catalogs > 0:
        print("Database already seeded. Skipping seed operation.")
        return
    
    print("Seeding database with demo catalog...")
    
    demo_catalog_path = os.path.join(os.path.dirname(__file__), '..', 'mock_data', 'demo_catalog.json')
    tracks_metrics_path = os.path.join(os.path.dirname(__file__), '..', 'mock_data', 'external_metrics_tracks.json')
    
    demo_data = load_mock_data(demo_catalog_path)
    track_metrics = load_mock_data(tracks_metrics_path)
    
    songwriter_data = demo_data.get('songwriter', {})
    songwriter = Songwriter(
        name=songwriter_data.get('name', 'Demo Songwriter'),
        pro_affiliation=songwriter_data.get('pro_affiliation'),
        ipi_number=songwriter_data.get('ipi')
    )
    db.add(songwriter)
    db.commit()
    db.refresh(songwriter)
    
    catalog = Catalog(name=demo_data.get('catalog_name', 'Demo Catalog'))
    db.add(catalog)
    db.commit()
    db.refresh(catalog)
    
    for song_data in demo_data.get('songs', []):
        title = song_data['title']
        
        metrics = track_metrics.get(title, {})
        
        analytics_data = {
            'spotify_streams': metrics.get('total_streams', 0),
            'spotify_monthly_listeners': metrics.get('monthly_streams', 0),
            'chartmetric_score': metrics.get('chartmetric_score', 0),
            'playlist_count': metrics.get('playlist_count', 0),
            'top_playlists': [
                {
                    'name': metrics.get('top_playlist', 'Unknown'),
                    'followers': metrics.get('top_playlist_followers', 0),
                    'position': 10
                }
            ],
            'regional_data': {
                territory['country']: {
                    'streams': territory['streams'],
                    'percentage': territory['percentage']
                }
                for territory in metrics.get('top_territories', [])
            },
            'trend_data': {
                'momentum': 'rising' if metrics.get('growth_3_month', 0) > 20 else 'stable'
            },
            'growth_3_month': metrics.get('growth_3_month', 0),
            'growth_12_month': metrics.get('growth_12_month', 0),
            'has_isrc': bool(song_data.get('isrc')),
            'has_iswc': bool(song_data.get('iswc')),
            'has_spotify_link': bool(song_data.get('spotify_link'))
        }
        
        valuation_result = calculate_valuation(analytics_data)
        score_result = calculate_score(analytics_data)
        
        song = Song(
            title=title,
            artist_name=song_data['artist_name'],
            publishing_percentage=song_data['publishing_percentage'],
            master_percentage=song_data['master_percentage'],
            spotify_link=song_data.get('spotify_link'),
            isrc=song_data.get('isrc'),
            iswc=song_data.get('iswc'),
            writer_splits=song_data.get('writer_splits', []),
            songwriter_id=songwriter.id,
            catalog_id=catalog.id,
            valuation_low=valuation_result['valuation_low'],
            valuation_base=valuation_result['valuation_base'],
            valuation_high=valuation_result['valuation_high'],
            estimated_revenue=valuation_result['estimated_revenue'],
            score=score_result['overall_score'],
            score_breakdown={
                'catalog_value': score_result['catalog_value'],
                'growth_momentum': score_result['growth_momentum'],
                'metadata_health': score_result['metadata_health'],
                'exploitation_potential': score_result['exploitation_potential']
            }
        )
        db.add(song)
        db.commit()
        db.refresh(song)
        
        # Calculate stream type splits (70% premium, 30% ad-supported)
        total_streams = analytics_data['spotify_streams']
        premium_streams = int(total_streams * 0.7)
        ad_supported_streams = total_streams - premium_streams
        
        streams_by_type = {
            'spotify': {
                'premium': premium_streams,
                'ad_supported': ad_supported_streams
            }
        }
        
        # Calculate territory breakdown with stream types
        territory_streams = {}
        for territory, data in analytics_data['regional_data'].items():
            territory_total = data['streams']
            territory_streams[territory] = {
                'premium': int(territory_total * 0.7),
                'ad_supported': int(territory_total * 0.3)
            }
        
        analytics = Analytics(
            song_id=song.id,
            spotify_streams=analytics_data['spotify_streams'],
            spotify_monthly_listeners=analytics_data['spotify_monthly_listeners'],
            chartmetric_score=analytics_data['chartmetric_score'],
            playlist_count=analytics_data['playlist_count'],
            top_playlists=analytics_data['top_playlists'],
            regional_data=analytics_data['regional_data'],
            trend_data=analytics_data['trend_data'],
            streams_by_type=streams_by_type,
            territory_streams=territory_streams
        )
        db.add(analytics)
    
    db.commit()
    print(f"✓ Seeded catalog '{catalog.name}' with {len(demo_data.get('songs', []))} songs")

def init_seed_data():
    """Initialize seed data on application startup"""
    db = next(get_db())
    try:
        seed_demo_catalog(db)
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()
