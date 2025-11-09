import json
import os
from typing import Dict, Any

CHARTMETRIC_API_KEY = os.getenv("CHARTMETRIC_API_KEY")

def get_track_data(track_name: str, artist_name: str) -> Dict[str, Any]:
    """
    Fetch track data from Chartmetric API.
    Falls back to mock data if API key is not present.
    """
    if not CHARTMETRIC_API_KEY:
        return get_mock_data()
    
    # TODO: Implement real Chartmetric API call when key is available
    # For now, return mock data
    return get_mock_data()

def get_mock_data() -> Dict[str, Any]:
    """Load mock Chartmetric response"""
    mock_file_path = os.path.join(os.path.dirname(__file__), "../../mock_data/chartmetric_response.json")
    with open(mock_file_path, 'r') as f:
        return json.load(f)
