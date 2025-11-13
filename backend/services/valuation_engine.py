from typing import Dict, Any

def calculate_valuation(analytics_data: Dict[str, Any], publishing_revenue: float = 0.0, master_revenue: float = 0.0) -> Dict[str, float]:
    """
    Calculate song valuation based on streaming data, playlist positions, and regional metrics.
    Returns a dictionary with low/base/high valuations for both publishing and master, plus estimated revenue.
    
    Valuation factors:
    - Spotify streams (weight: 0.4)
    - Playlist reach (weight: 0.3)
    - Chartmetric score (weight: 0.2)
    - Regional performance (weight: 0.1)
    
    Returns:
        {
            "estimated_revenue": float,
            "valuation_low": float (legacy - sum of pub + master),
            "valuation_base": float (legacy - sum of pub + master),
            "valuation_high": float (legacy - sum of pub + master),
            "valuation_low_pub": float,
            "valuation_base_pub": float,
            "valuation_high_pub": float,
            "valuation_low_master": float,
            "valuation_base_master": float,
            "valuation_high_master": float
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
    
    # Fixed multipliers for all valuations (publishing and master)
    low_multiplier = 8
    base_multiplier = 12
    high_multiplier = 18
    
    # Calculate publishing valuations based on publishing revenue
    valuation_low_pub = publishing_revenue * low_multiplier
    valuation_base_pub = publishing_revenue * base_multiplier
    valuation_high_pub = publishing_revenue * high_multiplier
    
    # Calculate master valuations based on master revenue
    valuation_low_master = master_revenue * low_multiplier
    valuation_base_master = master_revenue * base_multiplier
    valuation_high_master = master_revenue * high_multiplier
    
    # Legacy combined valuations (sum of publishing + master)
    legacy_low = valuation_low_pub + valuation_low_master
    legacy_base = valuation_base_pub + valuation_base_master
    legacy_high = valuation_high_pub + valuation_high_master
    
    return {
        "estimated_revenue": round(estimated_annual_revenue, 2),
        "valuation_low": round(legacy_low, 2),
        "valuation_base": round(legacy_base, 2),
        "valuation_high": round(legacy_high, 2),
        "valuation_low_pub": round(valuation_low_pub, 2),
        "valuation_base_pub": round(valuation_base_pub, 2),
        "valuation_high_pub": round(valuation_high_pub, 2),
        "valuation_low_master": round(valuation_low_master, 2),
        "valuation_base_master": round(valuation_base_master, 2),
        "valuation_high_master": round(valuation_high_master, 2)
    }
