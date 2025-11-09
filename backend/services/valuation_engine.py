from typing import Dict, Any

def calculate_valuation(analytics_data: Dict[str, Any]) -> float:
    """
    Calculate song valuation based on streaming data, playlist positions, and regional metrics.
    
    Valuation factors:
    - Spotify streams (weight: 0.4)
    - Playlist reach (weight: 0.3)
    - Chartmetric score (weight: 0.2)
    - Regional performance (weight: 0.1)
    """
    
    # Extract data from different sources
    spotify_streams = analytics_data.get('spotify_streams', 0)
    playlist_count = analytics_data.get('playlist_count', 0)
    chartmetric_score = analytics_data.get('chartmetric_score', 0)
    
    # Stream value: $0.003 per stream average
    stream_value = spotify_streams * 0.003
    
    # Playlist value: Higher follower count playlists increase value
    playlist_value = 0
    top_playlists = analytics_data.get('top_playlists', [])
    for playlist in top_playlists:
        followers = playlist.get('followers', 0)
        position = playlist.get('position', 100)
        # Better position (lower number) = higher value
        position_multiplier = max(0, (100 - position) / 100)
        playlist_value += (followers / 1000) * position_multiplier * 0.5
    
    # Chartmetric score value
    score_value = (chartmetric_score / 100) * 5000
    
    # Regional performance value
    regional_value = 0
    regional_data = analytics_data.get('regional_data', {})
    for region, data in regional_data.items():
        regional_streams = data.get('streams', 0)
        regional_value += regional_streams * 0.002
    
    # Calculate weighted total
    total_valuation = (
        stream_value * 0.4 +
        playlist_value * 0.3 +
        score_value * 0.2 +
        regional_value * 0.1
    )
    
    return round(total_valuation, 2)
