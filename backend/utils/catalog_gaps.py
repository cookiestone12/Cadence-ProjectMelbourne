from sqlalchemy.orm import Session
from typing import List, Dict
from ..models import Song, SongCredit, SongDSPLink, ActionItem, Creator, SongContract


def analyze_creator_catalog_gaps(db: Session, creator_id: int) -> List[Dict]:
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        return []
    
    credits = db.query(SongCredit).filter(SongCredit.creator_id == creator_id).all()
    song_ids = [c.song_id for c in credits]
    
    if not song_ids:
        return []
    
    songs = db.query(Song).filter(Song.id.in_(song_ids)).all()
    
    existing_actions = db.query(ActionItem).filter(
        ActionItem.creator_id == creator_id,
        ActionItem.status != "COMPLETED"
    ).all()
    
    existing_action_keys = set()
    for action in existing_actions:
        key = (action.action_type, action.song_id)
        existing_action_keys.add(key)
    
    gaps = []
    
    for song in songs:
        if not song.isrc:
            key = ("MISSING_ISRC", song.id)
            if key not in existing_action_keys:
                gaps.append({
                    "action_type": "MISSING_ISRC",
                    "title": f"Register ISRC for \"{song.title}\"",
                    "description": f"Song is missing an ISRC code which is required for streaming royalties.",
                    "song_id": song.id,
                    "priority": 1
                })
        
        if not song.iswc:
            key = ("MISSING_ISWC", song.id)
            if key not in existing_action_keys:
                gaps.append({
                    "action_type": "MISSING_ISWC",
                    "title": f"Register ISWC for \"{song.title}\"",
                    "description": f"Song is missing an ISWC code which is required for publishing royalties.",
                    "song_id": song.id,
                    "priority": 2
                })
        
        if not song.has_contract_executed:
            key = ("CONTRACT_PENDING", song.id)
            if key not in existing_action_keys:
                has_contract = db.query(SongContract).filter(
                    SongContract.song_id == song.id
                ).first()
                if not has_contract:
                    gaps.append({
                        "action_type": "CONTRACT_PENDING",
                        "title": f"Upload contract for \"{song.title}\"",
                        "description": f"No executed contract on file for this song.",
                        "song_id": song.id,
                        "priority": 2
                    })
        
        if not song.is_registered_with_pro:
            key = ("PRO_INCOMPLETE", song.id)
            if key not in existing_action_keys:
                gaps.append({
                    "action_type": "PRO_INCOMPLETE",
                    "title": f"Complete PRO registration for \"{song.title}\"",
                    "description": f"Song is not registered with a Performing Rights Organization.",
                    "song_id": song.id,
                    "priority": 2
                })
        
        if song.is_registered_with_dsp not in ("Yes", "N/A"):
            dsp_links = db.query(SongDSPLink).filter(SongDSPLink.song_id == song.id).count()
            if dsp_links == 0:
                key = ("DSP_REGISTRATION", song.id)
                if key not in existing_action_keys:
                    gaps.append({
                        "action_type": "DSP_REGISTRATION",
                        "title": f"Register \"{song.title}\" with DSPs",
                        "description": f"Song has no DSP links (Spotify, Apple Music, etc.).",
                        "song_id": song.id,
                        "priority": 3
                    })
    
    return gaps


def generate_actions_from_gaps(
    db: Session, 
    creator_id: int, 
    organization_id: int,
    created_by_user_id: int
) -> int:
    gaps = analyze_creator_catalog_gaps(db, creator_id)
    
    created_count = 0
    for gap in gaps:
        new_action = ActionItem(
            organization_id=organization_id,
            creator_id=creator_id,
            song_id=gap.get("song_id"),
            action_type=gap["action_type"],
            title=gap["title"],
            description=gap.get("description"),
            priority=gap.get("priority", 2),
            created_by_user_id=created_by_user_id,
            is_auto_generated=True
        )
        db.add(new_action)
        created_count += 1
    
    if created_count > 0:
        db.commit()
    
    return created_count
