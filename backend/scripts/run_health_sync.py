#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.models import get_db
from backend.utils.health_sync import sync_all_songs

if __name__ == "__main__":
    db = next(get_db())
    synced = sync_all_songs(db)
    print(f"Synced {synced} songs")
