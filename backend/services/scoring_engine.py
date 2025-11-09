from typing import Dict, Any

def calculate_score(analytics_data: Dict[str, Any]) -> float:
    """
    Calculate song score based on commercial potential, trend analysis, and catalog health.
    Returns a score from 0-100.
    
    Scoring factors:
    - Commercial potential (0-40 points): Based on streams and playlist positions
    - Trend momentum (0-30 points): Rising, stable, or declining
    - Catalog health (0-30 points): Quality metrics and engagement
    """
    
    score = 0.0
    
    # Commercial Potential (0-40 points)
    spotify_streams = analytics_data.get('spotify_streams', 0)
    monthly_listeners = analytics_data.get('spotify_monthly_listeners', 0)
    
    # Stream score (0-20)
    if spotify_streams > 10000000:
        stream_score = 20
    elif spotify_streams > 5000000:
        stream_score = 18
    elif spotify_streams > 1000000:
        stream_score = 15
    elif spotify_streams > 500000:
        stream_score = 12
    elif spotify_streams > 100000:
        stream_score = 8
    else:
        stream_score = min(20, spotify_streams / 5000)
    
    # Playlist score (0-20)
    playlist_count = analytics_data.get('playlist_count', 0)
    top_playlists = analytics_data.get('top_playlists', [])
    
    playlist_score = min(10, playlist_count / 2)  # Up to 10 points for count
    
    # Bonus for high-follower playlists
    for playlist in top_playlists[:3]:  # Top 3 playlists
        followers = playlist.get('followers', 0)
        if followers > 20000000:
            playlist_score += 3.33
        elif followers > 10000000:
            playlist_score += 2
        elif followers > 1000000:
            playlist_score += 1
    
    playlist_score = min(20, playlist_score)
    
    score += stream_score + playlist_score
    
    # Trend Momentum (0-30 points)
    trend_data = analytics_data.get('trend_data', {})
    trend_momentum = trend_data.get('momentum', 'stable')
    
    if trend_momentum == 'rising':
        trend_score = 30
    elif trend_momentum == 'stable':
        trend_score = 20
    elif trend_momentum == 'declining':
        trend_score = 10
    else:
        trend_score = 15
    
    score += trend_score
    
    # Catalog Health (0-30 points)
    chartmetric_score = analytics_data.get('chartmetric_score', 0)
    
    # Chartmetric score translates to health (0-20)
    health_score = (chartmetric_score / 100) * 20
    
    # Engagement score based on listener ratio (0-10)
    if monthly_listeners > 0 and spotify_streams > 0:
        # Good engagement if avg streams per listener is high
        avg_per_listener = spotify_streams / monthly_listeners
        if avg_per_listener > 50:
            engagement_score = 10
        elif avg_per_listener > 30:
            engagement_score = 8
        elif avg_per_listener > 15:
            engagement_score = 6
        else:
            engagement_score = 4
    else:
        engagement_score = 5
    
    score += health_score + engagement_score
    
    return round(min(100, score), 2)
