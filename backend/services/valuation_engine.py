from typing import Dict, Any

def calculate_valuation(analytics_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate song valuation based on streaming data, playlist positions, and regional metrics.
    Returns a dictionary with low/base/high valuations and estimated revenue.
    
    Valuation factors:
    - Spotify streams (weight: 0.4)
    - Playlist reach (weight: 0.3)
    - Chartmetric score (weight: 0.2)
    - Regional performance (weight: 0.1)
    
    Returns:
        {
            "estimated_revenue": float,
            "valuation_low": float,
            "valuation_base": float,
            "valuation_high": float
        }
    """
    
    spotify_streams = analytics_data.get('spotify_streams', 0)
    playlist_count = analytics_data.get('playlist_count', 0)
    chartmetric_score = analytics_data.get('chartmetric_score', 0)
    
    stream_value = spotify_streams * 0.003
    
    playlist_value = 0
    top_playlists = analytics_data.get('top_playlists', [])
    for playlist in top_playlists:
        followers = playlist.get('followers', 0)
        position = playlist.get('position', 100)
        position_multiplier = max(0, (100 - position) / 100)
        playlist_value += (followers / 1000) * position_multiplier * 0.5
    
    score_value = (chartmetric_score / 100) * 5000
    
    regional_value = 0
    regional_data = analytics_data.get('regional_data', {})
    for region, data in regional_data.items():
        regional_streams = data.get('streams', 0)
        regional_value += regional_streams * 0.002
    
    base_valuation = (
        stream_value * 0.4 +
        playlist_value * 0.3 +
        score_value * 0.2 +
        regional_value * 0.1
    )
    
    estimated_annual_revenue = spotify_streams * 0.004
    
    growth_rate = analytics_data.get('growth_3_month', 0) / 100
    
    low_multiplier = 8
    base_multiplier = 12
    high_multiplier = 18 if growth_rate > 0.3 else 15
    
    return {
        "estimated_revenue": round(estimated_annual_revenue, 2),
        "valuation_low": round(base_valuation * low_multiplier, 2),
        "valuation_base": round(base_valuation * base_multiplier, 2),
        "valuation_high": round(base_valuation * high_multiplier, 2)
    }
