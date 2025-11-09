import json
import os
from typing import Dict, Any

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

def get_track_data(spotify_link: str = None) -> Dict[str, Any]:
    """
    Fetch track data from Spotify API.
    Falls back to mock data if API keys are not present.
    """
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return get_mock_data()
    
    # TODO: Implement real Spotify API call when keys are available
    # For now, return mock data
    return get_mock_data()

def get_mock_data() -> Dict[str, Any]:
    """Load mock Spotify response"""
    mock_file_path = os.path.join(os.path.dirname(__file__), "../../mock_data/spotify_response.json")
    with open(mock_file_path, 'r') as f:
        return json.load(f)
