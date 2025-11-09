from typing import Dict, Any

def calculate_score(analytics_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate song score based on catalog value, growth, metadata, and exploitation potential.
    Returns a dictionary with overall score and breakdown.
    
    Scoring factors (each 0-25 points):
    - Catalog Value: Based on streams and commercial performance
    - Growth Momentum: Trend analysis and growth indicators
    - Metadata Health: Data completeness and quality
    - Exploitation Potential: Playlist positions and market reach
    
    Returns:
        {
            "overall_score": float (0-100),
            "catalog_value": float (0-25),
            "growth_momentum": float (0-25),
            "metadata_health": float (0-25),
            "exploitation_potential": float (0-25)
        }
    """
    
    spotify_streams = analytics_data.get('spotify_streams', 0)
    monthly_listeners = analytics_data.get('spotify_monthly_listeners', 0)
    playlist_count = analytics_data.get('playlist_count', 0)
    top_playlists = analytics_data.get('top_playlists', [])
    chartmetric_score = analytics_data.get('chartmetric_score', 0)
    
    catalog_value_score = 0.0
    if spotify_streams > 10000000:
        catalog_value_score = 25
    elif spotify_streams > 5000000:
        catalog_value_score = 22
    elif spotify_streams > 1000000:
        catalog_value_score = 18
    elif spotify_streams > 500000:
        catalog_value_score = 15
    elif spotify_streams > 100000:
        catalog_value_score = 10
    else:
        catalog_value_score = min(25, spotify_streams / 4000)
    
    growth_3_month = analytics_data.get('growth_3_month', 0)
    growth_12_month = analytics_data.get('growth_12_month', 0)
    
    growth_momentum_score = 0.0
    if growth_3_month > 50:
        growth_momentum_score = 25
    elif growth_3_month > 30:
        growth_momentum_score = 20
    elif growth_3_month > 15:
        growth_momentum_score = 15
    elif growth_3_month > 5:
        growth_momentum_score = 10
    elif growth_3_month > 0:
        growth_momentum_score = 5
    else:
        growth_momentum_score = 2
    
    if growth_12_month > 200:
        growth_momentum_score = min(25, growth_momentum_score + 5)
    
    has_isrc = analytics_data.get('has_isrc', True)
    has_iswc = analytics_data.get('has_iswc', True)
    has_spotify_link = analytics_data.get('has_spotify_link', True)
    
    metadata_health_score = 0.0
    metadata_health_score += 8 if has_isrc else 0
    metadata_health_score += 8 if has_iswc else 0
    metadata_health_score += 9 if has_spotify_link else 0
    
    if chartmetric_score > 80:
        metadata_health_score = 25
    elif chartmetric_score > 60:
        metadata_health_score = max(metadata_health_score, 20)
    
    exploitation_potential_score = 0.0
    
    playlist_score = min(15, playlist_count / 10)
    exploitation_potential_score += playlist_score
    
    for playlist in top_playlists[:3]:
        followers = playlist.get('followers', 0)
        if followers > 10000000:
            exploitation_potential_score += 3.33
        elif followers > 5000000:
            exploitation_potential_score += 2
        elif followers > 1000000:
            exploitation_potential_score += 1
    
    exploitation_potential_score = min(25, exploitation_potential_score)
    
    overall_score = (
        catalog_value_score +
        growth_momentum_score +
        metadata_health_score +
        exploitation_potential_score
    )
    
    return {
        "overall_score": round(min(100, overall_score), 2),
        "catalog_value": round(catalog_value_score, 2),
        "growth_momentum": round(growth_momentum_score, 2),
        "metadata_health": round(metadata_health_score, 2),
        "exploitation_potential": round(exploitation_potential_score, 2)
    }
