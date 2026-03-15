import os
import re
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
from sqlalchemy.orm import Session

from ..models import (
    Song, Work, Creator, CreatorStorageLink, StorageScanResult,
    AudioAsset, AudioAnalysis, AudioTag, AudioAssetTag, SongCredit,
    IntegrationAccount,
)
from . import storage_service

logger = logging.getLogger("cadence")

AUDIO_EXTENSIONS = {
    '.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.wma',
    '.aiff', '.aif', '.alac', '.opus', '.mp4', '.webm',
}


def is_audio_file(filename: str) -> bool:
    ext = os.path.splitext(filename.lower())[1]
    return ext in AUDIO_EXTENSIONS


def clean_filename(filename: str) -> str:
    name = os.path.splitext(filename)[0]
    name = re.sub(r'[\[\(].*?[\]\)]', '', name)
    name = re.sub(r'[-_]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def extract_title_artist(filename: str) -> Tuple[str, Optional[str]]:
    cleaned = clean_filename(filename)
    separators = [' - ', ' _ ', ' by ']
    for sep in separators:
        if sep.lower() in cleaned.lower():
            idx = cleaned.lower().index(sep.lower())
            part1 = cleaned[:idx].strip()
            part2 = cleaned[idx + len(sep):].strip()
            if part1 and part2:
                return part1, part2
    return cleaned, None


def fuzzy_match_score(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    s1_lower = s1.lower().strip()
    s2_lower = s2.lower().strip()
    if s1_lower == s2_lower:
        return 1.0
    if s1_lower in s2_lower or s2_lower in s1_lower:
        return 0.85
    return SequenceMatcher(None, s1_lower, s2_lower).ratio()


def match_file_to_catalog(
    file_name: str,
    songs: List[Song],
    works: List[Work],
    creator: Optional[Creator] = None,
) -> Dict[str, Any]:
    title, artist = extract_title_artist(file_name)
    best_match = None
    best_score = 0.0
    best_type = None
    best_reason = ""

    for song in songs:
        title_score = fuzzy_match_score(title, song.title or "")
        artist_score = 0.0
        if artist and song.primary_artist:
            artist_score = fuzzy_match_score(artist, song.primary_artist)
        elif artist:
            artist_score = 0.0
        else:
            artist_score = 0.3

        combined = title_score * 0.7 + artist_score * 0.3

        if creator and song.primary_artist:
            creator_match = fuzzy_match_score(creator.display_name, song.primary_artist)
            if creator_match > 0.7:
                combined = min(1.0, combined + 0.1)

        if combined > best_score:
            best_score = combined
            best_match = song
            best_type = "song"
            reasons = []
            if title_score > 0.5:
                reasons.append(f"Title match: {title_score:.0%}")
            if artist_score > 0.5:
                reasons.append(f"Artist match: {artist_score:.0%}")
            best_reason = "; ".join(reasons) if reasons else f"Score: {combined:.0%}"

    for work in works:
        title_score = fuzzy_match_score(title, work.title or "")
        combined = title_score * 0.8

        if creator:
            combined = min(1.0, combined + 0.05)

        if combined > best_score:
            best_score = combined
            best_match = work
            best_type = "work"
            best_reason = f"Work title match: {title_score:.0%}"

    confidence = "NONE"
    if best_score >= 0.85:
        confidence = "HIGH"
    elif best_score >= 0.6:
        confidence = "MEDIUM"
    elif best_score >= 0.4:
        confidence = "LOW"

    return {
        "match": best_match,
        "match_type": best_type,
        "score": best_score,
        "confidence": confidence,
        "reason": best_reason,
        "suggested_title": title,
        "suggested_artist": artist,
    }


def list_files_recursive(
    org_id: int,
    provider: str,
    folder_path: str,
    db: Session,
    max_depth: int = 5,
) -> List[Dict[str, Any]]:
    all_files = []

    def _scan_folder(path: str, depth: int):
        if depth > max_depth:
            return
        try:
            files = storage_service.list_files_for_provider(org_id, provider, path, db)
            for f in files:
                if f.get("is_folder"):
                    next_path = f.get("id", f["path_display"]) if provider == "GOOGLE_DRIVE" else f["path_display"]
                    _scan_folder(next_path, depth + 1)
                elif is_audio_file(f.get("name", "")):
                    all_files.append(f)
        except Exception as e:
            logger.warning(f"Error scanning folder {path}: {e}")

    _scan_folder(folder_path, 0)
    return all_files


def scan_creator_storage(
    org_id: int,
    creator_storage_link_id: int,
    db: Session,
) -> Dict[str, Any]:
    link = db.query(CreatorStorageLink).filter(
        CreatorStorageLink.id == creator_storage_link_id,
        CreatorStorageLink.org_id == org_id,
    ).first()
    if not link:
        raise ValueError("Creator storage link not found")

    creator = db.query(Creator).filter(Creator.id == link.creator_id).first()

    scan_batch_id = str(uuid.uuid4())[:12]

    audio_files = list_files_recursive(
        org_id, link.provider, link.folder_path, db,
        max_depth=5 if link.scan_recursive else 0,
    )

    songs = db.query(Song).filter(Song.organization_id == org_id).all()
    works = db.query(Work).filter(Work.organization_id == org_id).all()

    existing_paths = set(
        r[0] for r in db.query(AudioAsset.path_display).filter(
            AudioAsset.org_id == org_id,
        ).all() if r[0]
    )

    results = []
    for f in audio_files:
        file_path = f.get("path_display", "")
        if file_path in existing_paths:
            continue

        match_result = match_file_to_catalog(
            f["name"], songs, works, creator
        )

        scan_result = StorageScanResult(
            org_id=org_id,
            scan_batch_id=scan_batch_id,
            creator_storage_link_id=link.id,
            creator_id=link.creator_id,
            provider=link.provider,
            file_path=file_path,
            file_name=f["name"],
            file_size=f.get("size"),
            provider_file_id=f.get("id"),
            matched_song_id=match_result["match"].id if match_result["match_type"] == "song" else None,
            matched_work_id=match_result["match"].id if match_result["match_type"] == "work" else None,
            match_confidence=match_result["confidence"],
            match_score=match_result["score"],
            match_reason=match_result["reason"],
            suggested_title=match_result["suggested_title"],
            suggested_artist=match_result["suggested_artist"],
            status="COMPLETED",
        )
        db.add(scan_result)
        results.append(scan_result)

    link.last_scanned_at = datetime.utcnow()
    link.last_scan_file_count = len(audio_files)
    db.commit()

    for r in results:
        db.refresh(r)

    return {
        "scan_batch_id": scan_batch_id,
        "total_files_found": len(audio_files),
        "new_files": len(results),
        "already_linked": len(audio_files) - len(results),
        "high_confidence": sum(1 for r in results if r.match_confidence == "HIGH"),
        "medium_confidence": sum(1 for r in results if r.match_confidence == "MEDIUM"),
        "low_confidence": sum(1 for r in results if r.match_confidence == "LOW"),
        "no_match": sum(1 for r in results if r.match_confidence == "NONE"),
    }


def scan_all_creator_links(org_id: int, db: Session) -> Dict[str, Any]:
    links = db.query(CreatorStorageLink).filter(
        CreatorStorageLink.org_id == org_id,
    ).all()

    total_results = {
        "scanned_links": 0,
        "total_files_found": 0,
        "new_files": 0,
        "already_linked": 0,
        "high_confidence": 0,
        "medium_confidence": 0,
        "low_confidence": 0,
        "no_match": 0,
        "errors": [],
    }

    for link in links:
        try:
            result = scan_creator_storage(org_id, link.id, db)
            total_results["scanned_links"] += 1
            total_results["total_files_found"] += result["total_files_found"]
            total_results["new_files"] += result["new_files"]
            total_results["already_linked"] += result["already_linked"]
            total_results["high_confidence"] += result["high_confidence"]
            total_results["medium_confidence"] += result["medium_confidence"]
            total_results["low_confidence"] += result["low_confidence"]
            total_results["no_match"] += result["no_match"]
        except Exception as e:
            total_results["errors"].append(f"Link {link.id}: {str(e)}")
            logger.error(f"Error scanning link {link.id}: {e}")

    return total_results


def approve_scan_result(
    org_id: int,
    scan_result_id: int,
    song_id: Optional[int],
    work_id: Optional[int],
    create_new: bool,
    new_title: Optional[str],
    new_artist: Optional[str],
    db: Session,
) -> Dict[str, Any]:
    result = db.query(StorageScanResult).filter(
        StorageScanResult.id == scan_result_id,
        StorageScanResult.org_id == org_id,
    ).first()
    if not result:
        raise ValueError("Scan result not found")

    target_song_id = song_id or result.matched_song_id
    target_work_id = work_id or result.matched_work_id

    if create_new and not target_song_id:
        new_song = Song(
            organization_id=org_id,
            title=new_title or result.suggested_title or result.file_name,
            primary_artist=new_artist or result.suggested_artist or "",
        )
        db.add(new_song)
        db.flush()
        target_song_id = new_song.id

    audio_asset = AudioAsset(
        org_id=org_id,
        song_id=target_song_id,
        release_id=None,
        creator_id=result.creator_id,
        provider=result.provider,
        provider_file_id=result.provider_file_id,
        path_display=result.file_path,
        name=result.file_name,
        size_bytes=result.file_size,
        file_type="MAIN",
        is_available=True,
    )
    db.add(audio_asset)
    db.flush()

    result.reviewed = True
    result.approved = True
    result.linked_audio_asset_id = audio_asset.id
    result.matched_song_id = target_song_id
    result.matched_work_id = target_work_id
    db.commit()

    return {
        "scan_result_id": result.id,
        "audio_asset_id": audio_asset.id,
        "song_id": target_song_id,
        "work_id": target_work_id,
        "created_new_song": create_new,
    }


def reject_scan_result(org_id: int, scan_result_id: int, db: Session):
    result = db.query(StorageScanResult).filter(
        StorageScanResult.id == scan_result_id,
        StorageScanResult.org_id == org_id,
    ).first()
    if not result:
        raise ValueError("Scan result not found")
    result.reviewed = True
    result.approved = False
    db.commit()


def scan_org_wide(
    org_id: int,
    folder_path: str,
    db: Session,
    auto_link_threshold: float = 0.85,
) -> Dict[str, Any]:
    scan_batch_id = str(uuid.uuid4())[:12]

    audio_files = list_files_recursive(org_id, "DROPBOX", folder_path or "/", db, max_depth=20)

    songs = db.query(Song).filter(Song.organization_id == org_id).all()
    works = db.query(Work).filter(Work.organization_id == org_id).all()

    existing_paths = set(
        r[0] for r in db.query(AudioAsset.path_display).filter(
            AudioAsset.org_id == org_id,
        ).all() if r[0]
    )

    stats = {
        "scan_batch_id": scan_batch_id,
        "total_files_found": len(audio_files),
        "new_files": 0,
        "already_linked": 0,
        "auto_linked": 0,
        "needs_review": 0,
        "no_match": 0,
        "analysis_queued": 0,
    }

    auto_linked_asset_ids = []

    for f in audio_files:
        file_path = f.get("path_display", "")
        if file_path in existing_paths:
            stats["already_linked"] += 1
            continue

        match_result = match_file_to_catalog(f["name"], songs, works, creator=None)

        scan_result = StorageScanResult(
            org_id=org_id,
            scan_batch_id=scan_batch_id,
            creator_storage_link_id=None,
            creator_id=None,
            provider="DROPBOX",
            file_path=file_path,
            file_name=f["name"],
            file_size=f.get("size"),
            provider_file_id=f.get("id"),
            matched_song_id=match_result["match"].id if match_result["match_type"] == "song" else None,
            matched_work_id=match_result["match"].id if match_result["match_type"] == "work" else None,
            match_confidence=match_result["confidence"],
            match_score=match_result["score"],
            match_reason=match_result["reason"],
            suggested_title=match_result["suggested_title"],
            suggested_artist=match_result["suggested_artist"],
            status="COMPLETED",
        )
        db.add(scan_result)
        db.flush()
        stats["new_files"] += 1

        if match_result["score"] >= auto_link_threshold and match_result["match_type"] == "song":
            audio_asset = AudioAsset(
                org_id=org_id,
                song_id=match_result["match"].id,
                provider="DROPBOX",
                provider_file_id=f.get("id"),
                path_display=file_path,
                name=f["name"],
                size_bytes=f.get("size"),
                file_type="MAIN",
                is_available=True,
            )
            db.add(audio_asset)
            db.flush()

            scan_result.reviewed = True
            scan_result.approved = True
            scan_result.linked_audio_asset_id = audio_asset.id
            stats["auto_linked"] += 1
            auto_linked_asset_ids.append((audio_asset.id, match_result["match"].id))
        elif match_result["confidence"] == "NONE":
            stats["no_match"] += 1
        else:
            stats["needs_review"] += 1

    db.commit()

    queued_analysis_ids = []
    for asset_id, song_id in auto_linked_asset_ids:
        existing = db.query(AudioAnalysis).filter(
            AudioAnalysis.audio_asset_id == asset_id,
        ).first()
        if existing and existing.status in ("SUCCEEDED", "RUNNING", "QUEUED"):
            continue
        if not existing:
            analysis = AudioAnalysis(
                org_id=org_id,
                audio_asset_id=asset_id,
                status="QUEUED",
            )
            db.add(analysis)
            db.flush()
            queued_analysis_ids.append((analysis.id, asset_id))
            stats["analysis_queued"] += 1

    db.commit()

    stats["queued_analysis_ids"] = queued_analysis_ids
    return stats


def bulk_approve_high_confidence(
    org_id: int,
    scan_batch_id: str,
    min_confidence: str,
    db: Session,
) -> Dict[str, Any]:
    confidence_levels = {"HIGH": 0.85, "MEDIUM": 0.6, "LOW": 0.4}
    min_score = confidence_levels.get(min_confidence, 0.85)

    results = db.query(StorageScanResult).filter(
        StorageScanResult.org_id == org_id,
        StorageScanResult.scan_batch_id == scan_batch_id,
        StorageScanResult.reviewed == False,
        StorageScanResult.match_score >= min_score,
        StorageScanResult.matched_song_id.isnot(None),
    ).all()

    approved = 0
    created_asset_ids = []
    for result in results:
        try:
            approve_result = approve_scan_result(
                org_id, result.id, result.matched_song_id, result.matched_work_id,
                False, None, None, db,
            )
            approved += 1
            if approve_result.get("audio_asset_id"):
                created_asset_ids.append(approve_result["audio_asset_id"])
        except Exception as e:
            logger.warning(f"Failed to approve scan result {result.id}: {e}")

    return {"approved": approved, "total_eligible": len(results), "created_asset_ids": created_asset_ids}
