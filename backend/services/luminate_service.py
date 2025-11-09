import json
import os
from typing import Dict, Any

LUMINATE_API_KEY = os.getenv("LUMINATE_API_KEY")

def get_track_data(track_name: str, artist_name: str) -> Dict[str, Any]:
    """
    Fetch track data from Luminate API.
    Falls back to mock data if API key is not present.
    """
    if not LUMINATE_API_KEY:
        return get_mock_data()
    
    # TODO: Implement real Luminate API call when key is available
    # For now, return mock data
    return get_mock_data()

def get_mock_data() -> Dict[str, Any]:
    """Load mock Luminate response"""
    mock_file_path = os.path.join(os.path.dirname(__file__), "../../mock_data/luminate_response.json")
    with open(mock_file_path, 'r') as f:
        return json.load(f)
