from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import threading
import logging
import os
import requests

from ..models import (
    get_db, User, OrganizationMember, Song, Release, ReleaseTrack,
    AudioAsset, AudioAnalysis, AudioTag, AudioAssetTag,
)
from ..models.database import SessionLocal
from ..utils.auth import get_current_user
from ..services import storage_service

router = APIRouter(prefix="/api/audio", tags=["audio"])
logger = logging.getLogger("cadence")


class LinkAudioRequest(BaseModel):
    provider_file_id: Optional[str] = None
    path_display: str
    name: str
    size_bytes: Optional[int] = None
    file_type: str = "MAIN"
    mime_type: Optional[str] = None


class BulkLinkItem(BaseModel):
    song_id: int
    provider_file_id: Optional[str] = None
    path_display: str
    name: str
    size_bytes: Optional[int] = None
    file_type: str = "MAIN"
    mime_type: Optional[str] = None


class BulkLinkRequest(BaseModel):
    links: List[BulkLinkItem]


class UpdateFileTypeRequest(BaseModel):
    file_type: str


class BulkAnalyzeRequest(BaseModel):
    asset_ids: List[int]


class AddTagRequest(BaseModel):
    name: str
    tag_type: str = "USER"


def _get_org_id(current_user: User, db: Session) -> int:
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="No organization membership found")
    return membership.organization_id


def _serialize_asset(asset: AudioAsset) -> dict:
    analysis_data = None
    if asset.analysis and asset.analysis.status == "SUCCEEDED":
        mood_tags = []
        texture_tags = []
        genre_tags = []
        sync_tags = []
        for at in (asset.tags or []):
            if at.audio_tag:
                if at.audio_tag.tag_type == "MOOD":
                    mood_tags.append(at.audio_tag.name)
                elif at.audio_tag.tag_type == "TEXTURE":
                    texture_tags.append(at.audio_tag.name)
                elif at.audio_tag.tag_type == "GENRE":
                    genre_tags.append(at.audio_tag.name)
                elif at.audio_tag.tag_type == "SYNC":
                    sync_tags.append(at.audio_tag.name)
        analysis_data = {
            "bpm": asset.analysis.bpm,
            "musical_key": asset.analysis.musical_key,
            "time_signature": asset.analysis.time_signature,
            "energy_level": asset.analysis.energy_level,
            "has_vocals": asset.analysis.vocal_present,
            "vocal_confidence": asset.analysis.vocal_confidence,
            "lufs": asset.analysis.lufs,
            "mood_tags": mood_tags,
            "texture_tags": texture_tags,
            "genre_tags": genre_tags,
            "sync_tags": sync_tags,
            "analyzed_at": asset.analysis.analyzed_at.isoformat() if asset.analysis.analyzed_at else None,
        }

    return {
        "id": asset.id,
        "song_id": asset.song_id,
        "release_id": asset.release_id,
        "provider": asset.provider,
        "provider_file_id": asset.provider_file_id,
        "path_display": asset.path_display,
        "name": asset.name,
        "size_bytes": asset.size_bytes,
        "file_type": asset.file_type,
        "mime_type": asset.mime_type,
        "duration_seconds": asset.duration_seconds,
        "is_available": asset.is_available,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "has_analysis": asset.analysis is not None,
        "analysis_status": asset.analysis.status if asset.analysis else None,
        "analysis": analysis_data,
        "tags": [
            {
                "id": at.audio_tag_id,
                "name": at.audio_tag.name,
                "tag_type": at.audio_tag.tag_type,
                "source": at.source,
                "confidence": at.confidence,
            }
            for at in (asset.tags or [])
            if at.audio_tag
        ],
    }


@router.get("/song/{song_id}")
def get_song_audio(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    song = db.query(Song).filter(Song.id == song_id, Song.organization_id == org_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    assets = db.query(AudioAsset).filter(
        AudioAsset.song_id == song_id,
        AudioAsset.org_id == org_id,
    ).all()
    return {"assets": [_serialize_asset(a) for a in assets]}


@router.post("/song/{song_id}/link")
def link_audio_to_song(
    song_id: int,
    request: LinkAudioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    song = db.query(Song).filter(Song.id == song_id, Song.organization_id == org_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    asset = AudioAsset(
        org_id=org_id,
        song_id=song_id,
        provider="DROPBOX",
        provider_file_id=request.provider_file_id,
        path_display=request.path_display,
        name=request.name,
        size_bytes=request.size_bytes,
        file_type=request.file_type,
        mime_type=request.mime_type,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _serialize_asset(asset)


@router.delete("/{asset_id}")
def unlink_audio(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    asset = db.query(AudioAsset).filter(
        AudioAsset.id == asset_id,
        AudioAsset.org_id == org_id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Audio asset not found")
    db.delete(asset)
    db.commit()
    return {"success": True, "message": "Audio asset unlinked"}


@router.put("/{asset_id}/type")
def update_audio_type(
    asset_id: int,
    request: UpdateFileTypeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    asset = db.query(AudioAsset).filter(
        AudioAsset.id == asset_id,
        AudioAsset.org_id == org_id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Audio asset not found")
    asset.file_type = request.file_type
    db.commit()
    db.refresh(asset)
    return _serialize_asset(asset)


@router.get("/release/{release_id}")
def get_release_audio(
    release_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    release = db.query(Release).filter(
        Release.id == release_id,
        Release.organization_id == org_id,
    ).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")

    tracks = db.query(ReleaseTrack).filter(ReleaseTrack.release_id == release_id).all()
    song_ids = [t.song_id for t in tracks]

    assets = db.query(AudioAsset).filter(
        AudioAsset.org_id == org_id,
        AudioAsset.song_id.in_(song_ids),
    ).all() if song_ids else []

    by_song = {}
    for asset in assets:
        by_song.setdefault(asset.song_id, []).append(_serialize_asset(asset))

    return {
        "release_id": release_id,
        "tracks": [
            {
                "song_id": t.song_id,
                "track_number": t.track_number,
                "disc_number": t.disc_number,
                "assets": by_song.get(t.song_id, []),
            }
            for t in tracks
        ],
    }


@router.post("/release/{release_id}/bulk-link")
def bulk_link_audio(
    release_id: int,
    request: BulkLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    release = db.query(Release).filter(
        Release.id == release_id,
        Release.organization_id == org_id,
    ).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")

    created = []
    for link in request.links:
        song = db.query(Song).filter(
            Song.id == link.song_id,
            Song.organization_id == org_id,
        ).first()
        if not song:
            continue
        asset = AudioAsset(
            org_id=org_id,
            song_id=link.song_id,
            release_id=release_id,
            provider="DROPBOX",
            provider_file_id=link.provider_file_id,
            path_display=link.path_display,
            name=link.name,
            size_bytes=link.size_bytes,
            file_type=link.file_type,
            mime_type=link.mime_type,
        )
        db.add(asset)
        created.append(asset)

    db.commit()
    for a in created:
        db.refresh(a)
    return {"created": len(created), "assets": [_serialize_asset(a) for a in created]}


@router.post("/{asset_id}/analyze")
def trigger_analysis(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    asset = db.query(AudioAsset).filter(
        AudioAsset.id == asset_id,
        AudioAsset.org_id == org_id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Audio asset not found")

    existing = db.query(AudioAnalysis).filter(AudioAnalysis.audio_asset_id == asset_id).first()
    if existing:
        existing.status = "QUEUED"
        existing.error_message = None
        db.commit()
        analysis_id = existing.id
    else:
        analysis = AudioAnalysis(
            org_id=org_id,
            audio_asset_id=asset_id,
            status="QUEUED",
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        analysis_id = analysis.id

    thread = threading.Thread(
        target=_run_analysis_worker,
        args=(analysis_id, asset_id, org_id),
        daemon=True,
    )
    thread.start()

    return {"success": True, "analysis_id": analysis_id, "status": "QUEUED"}


@router.post("/bulk-analyze")
def bulk_analyze(
    request: BulkAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    results = []
    for asset_id in request.asset_ids:
        asset = db.query(AudioAsset).filter(
            AudioAsset.id == asset_id,
            AudioAsset.org_id == org_id,
        ).first()
        if not asset:
            continue

        existing = db.query(AudioAnalysis).filter(AudioAnalysis.audio_asset_id == asset_id).first()
        if existing:
            existing.status = "QUEUED"
            existing.error_message = None
            db.commit()
            analysis_id = existing.id
        else:
            analysis = AudioAnalysis(
                org_id=org_id,
                audio_asset_id=asset_id,
                status="QUEUED",
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
            analysis_id = analysis.id

        thread = threading.Thread(
            target=_run_analysis_worker,
            args=(analysis_id, asset_id, org_id),
            daemon=True,
        )
        thread.start()
        results.append({"asset_id": asset_id, "analysis_id": analysis_id, "status": "QUEUED"})

    return {"queued": len(results), "results": results}


@router.get("/{asset_id}/analysis")
def get_analysis(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    asset = db.query(AudioAsset).filter(
        AudioAsset.id == asset_id,
        AudioAsset.org_id == org_id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Audio asset not found")

    analysis = db.query(AudioAnalysis).filter(AudioAnalysis.audio_asset_id == asset_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this asset")

    tags = db.query(AudioAssetTag).filter(AudioAssetTag.audio_asset_id == asset_id).all()

    return {
        "id": analysis.id,
        "status": analysis.status,
        "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
        "bpm": analysis.bpm,
        "bpm_confidence": analysis.bpm_confidence,
        "musical_key": analysis.musical_key,
        "key_confidence": analysis.key_confidence,
        "time_signature": analysis.time_signature,
        "duration_seconds": analysis.duration_seconds,
        "lufs": analysis.lufs,
        "peak_db": analysis.peak_db,
        "dynamic_range": analysis.dynamic_range,
        "vocal_present": analysis.vocal_present,
        "vocal_confidence": analysis.vocal_confidence,
        "energy_level": analysis.energy_level,
        "features_json": analysis.features_json,
        "error_message": analysis.error_message,
        "tags": [
            {
                "id": at.audio_tag_id,
                "name": at.audio_tag.name if at.audio_tag else None,
                "tag_type": at.audio_tag.tag_type if at.audio_tag else None,
                "source": at.source,
                "confidence": at.confidence,
            }
            for at in tags
        ],
    }


@router.get("/tags")
def list_tags(
    tag_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    query = db.query(AudioTag).filter(AudioTag.org_id == org_id)
    if tag_type:
        query = query.filter(AudioTag.tag_type == tag_type)
    tags = query.order_by(AudioTag.name).all()
    return {
        "tags": [
            {
                "id": t.id,
                "name": t.name,
                "tag_type": t.tag_type,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tags
        ]
    }


@router.post("/{asset_id}/tags")
def add_tag(
    asset_id: int,
    request: AddTagRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    asset = db.query(AudioAsset).filter(
        AudioAsset.id == asset_id,
        AudioAsset.org_id == org_id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Audio asset not found")

    tag = db.query(AudioTag).filter(
        AudioTag.org_id == org_id,
        AudioTag.name == request.name,
        AudioTag.tag_type == request.tag_type,
    ).first()
    if not tag:
        tag = AudioTag(
            org_id=org_id,
            name=request.name,
            tag_type=request.tag_type,
            created_by_user_id=current_user.id,
        )
        db.add(tag)
        db.flush()

    existing_link = db.query(AudioAssetTag).filter(
        AudioAssetTag.audio_asset_id == asset_id,
        AudioAssetTag.audio_tag_id == tag.id,
    ).first()
    if existing_link:
        return {"id": tag.id, "name": tag.name, "tag_type": tag.tag_type, "already_exists": True}

    asset_tag = AudioAssetTag(
        audio_asset_id=asset_id,
        audio_tag_id=tag.id,
        source="USER",
    )
    db.add(asset_tag)
    db.commit()
    return {"id": tag.id, "name": tag.name, "tag_type": tag.tag_type, "source": "USER"}


@router.delete("/{asset_id}/tags/{tag_id}")
def remove_tag(
    asset_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    asset = db.query(AudioAsset).filter(
        AudioAsset.id == asset_id,
        AudioAsset.org_id == org_id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Audio asset not found")

    link = db.query(AudioAssetTag).filter(
        AudioAssetTag.audio_asset_id == asset_id,
        AudioAssetTag.audio_tag_id == tag_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Tag not linked to this asset")
    db.delete(link)
    db.commit()
    return {"success": True}


def _run_analysis_worker(analysis_id: int, asset_id: int, org_id: int):
    db = SessionLocal()
    try:
        analysis = db.query(AudioAnalysis).filter(AudioAnalysis.id == analysis_id).first()
        if not analysis:
            return
        analysis.status = "RUNNING"
        db.commit()

        asset = db.query(AudioAsset).filter(AudioAsset.id == asset_id).first()
        if not asset:
            analysis.status = "FAILED"
            analysis.error_message = "Asset not found"
            db.commit()
            return

        song = db.query(Song).filter(Song.id == asset.song_id).first() if asset.song_id else None

        song_title = song.title if song else ""
        song_artist = song.primary_artist if song else ""
        song_lyrics = (song.lyrics or "")[:500] if song else ""
        filename = asset.name or ""
        file_size = asset.size_bytes or 0

        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"))

            prompt = f"""You are a music analysis AI. Based on the following metadata, generate a realistic analysis of this audio file.

Filename: {filename}
Song Title: {song_title}
Artist: {song_artist}
File Size: {file_size} bytes
{f'Lyrics (excerpt): {song_lyrics}' if song_lyrics else ''}

Generate a JSON response with:
- bpm: estimated BPM (number between 60-200)
- bpm_confidence: confidence 0-1
- musical_key: e.g. "C Major", "A Minor", "F# Major"
- key_confidence: confidence 0-1
- time_signature: e.g. "4/4", "3/4", "6/8"
- vocal_present: boolean
- vocal_confidence: confidence 0-1
- energy_level: one of "LOW", "MEDIUM", "HIGH"
- mood_tags: list of 3-5 mood strings (e.g. "Energetic", "Melancholic", "Uplifting")
- texture_tags: list of 2-4 texture strings (e.g. "Acoustic", "Electronic", "Orchestral")
- genre_tags: list of 1-3 genre strings (e.g. "Pop", "Hip-Hop", "R&B")
- sync_tags: list of 2-4 sync usage strings (e.g. "Commercial", "Film Score", "Workout", "Romantic Scene")

Respond ONLY with valid JSON, no other text."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            import json
            result = json.loads(response.choices[0].message.content)

            analysis.bpm = result.get("bpm")
            analysis.bpm_confidence = result.get("bpm_confidence")
            analysis.musical_key = result.get("musical_key")
            analysis.key_confidence = result.get("key_confidence")
            analysis.time_signature = result.get("time_signature")
            analysis.vocal_present = result.get("vocal_present")
            analysis.vocal_confidence = result.get("vocal_confidence")
            analysis.energy_level = result.get("energy_level")
            analysis.features_json = result
            analysis.status = "SUCCEEDED"
            analysis.analyzed_at = datetime.utcnow()
            db.commit()

            tag_groups = {
                "MOOD": result.get("mood_tags", []),
                "TEXTURE": result.get("texture_tags", []),
                "GENRE": result.get("genre_tags", []),
                "SYNC": result.get("sync_tags", []),
            }

            for tag_type, tag_names in tag_groups.items():
                for tag_name in tag_names:
                    if not tag_name:
                        continue
                    tag = db.query(AudioTag).filter(
                        AudioTag.org_id == org_id,
                        AudioTag.name == tag_name,
                        AudioTag.tag_type == tag_type,
                    ).first()
                    if not tag:
                        tag = AudioTag(
                            org_id=org_id,
                            name=tag_name,
                            tag_type=tag_type,
                        )
                        db.add(tag)
                        db.flush()

                    existing = db.query(AudioAssetTag).filter(
                        AudioAssetTag.audio_asset_id == asset_id,
                        AudioAssetTag.audio_tag_id == tag.id,
                    ).first()
                    if not existing:
                        asset_tag = AudioAssetTag(
                            audio_asset_id=asset_id,
                            audio_tag_id=tag.id,
                            source="AI",
                            confidence=0.8,
                        )
                        db.add(asset_tag)

            db.commit()

        except Exception as e:
            logger.error(f"Analysis failed for asset {asset_id}: {e}")
            analysis.status = "FAILED"
            analysis.error_message = str(e)[:500]
            db.commit()

    except Exception as e:
        logger.error(f"Analysis worker error: {e}")
    finally:
        db.close()
