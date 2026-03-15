import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging

from ..models import (
    get_db, User, OrganizationMember, Creator,
    CreatorStorageLink, StorageScanResult, IntegrationAccount,
    AudioAsset, AudioAnalysis, Song,
)
from ..utils.auth import get_current_user
from ..services import scan_service, storage_service

router = APIRouter(prefix="/api/storage-scan", tags=["storage-scan"])
logger = logging.getLogger("cadence")


def verify_org_access(user: User, org_id: int, db: Session):
    if user.is_super_admin:
        return
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")


def verify_org_admin(user: User, org_id: int, db: Session):
    if user.is_super_admin:
        return
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    if membership.role not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="Admin access required for this action")


class CreatorStorageLinkCreate(BaseModel):
    creator_id: int
    provider: str = "DROPBOX"
    folder_path: str
    container_name: Optional[str] = None
    scan_recursive: bool = True
    auto_scan_enabled: bool = False
    auto_scan_frequency: Optional[str] = None


class CreatorStorageLinkUpdate(BaseModel):
    folder_path: Optional[str] = None
    container_name: Optional[str] = None
    scan_recursive: Optional[bool] = None
    auto_scan_enabled: Optional[bool] = None
    auto_scan_frequency: Optional[str] = None


class ApproveRequest(BaseModel):
    song_id: Optional[int] = None
    work_id: Optional[int] = None
    create_new: bool = False
    new_title: Optional[str] = None
    new_artist: Optional[str] = None


class BulkApproveRequest(BaseModel):
    scan_batch_id: str
    min_confidence: str = "HIGH"


class ReassignMatchRequest(BaseModel):
    song_id: Optional[int] = None
    work_id: Optional[int] = None


@router.get("/org/{org_id}/links")
def list_creator_storage_links(
    org_id: int,
    creator_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(CreatorStorageLink).filter(CreatorStorageLink.org_id == org_id)
    if creator_id:
        query = query.filter(CreatorStorageLink.creator_id == creator_id)
    links = query.all()

    return [{
        "id": l.id,
        "creator_id": l.creator_id,
        "creator_name": l.creator.display_name if l.creator else None,
        "provider": l.provider,
        "folder_path": l.folder_path,
        "container_name": l.container_name,
        "scan_recursive": l.scan_recursive,
        "auto_scan_enabled": l.auto_scan_enabled,
        "auto_scan_frequency": l.auto_scan_frequency,
        "last_scanned_at": l.last_scanned_at.isoformat() if l.last_scanned_at else None,
        "last_scan_file_count": l.last_scan_file_count,
    } for l in links]


@router.post("/org/{org_id}/links")
def create_creator_storage_link(
    org_id: int,
    request: CreatorStorageLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    creator = db.query(Creator).filter(
        Creator.id == request.creator_id,
        Creator.organization_id == org_id,
    ).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    integration = db.query(IntegrationAccount).filter(
        IntegrationAccount.org_id == org_id,
        IntegrationAccount.provider == request.provider,
        IntegrationAccount.is_active == True,
    ).first()
    if not integration:
        raise HTTPException(
            status_code=400,
            detail=f"{request.provider} is not connected. Please connect it first in Settings."
        )

    link = CreatorStorageLink(
        org_id=org_id,
        creator_id=request.creator_id,
        provider=request.provider,
        folder_path=request.folder_path,
        container_name=request.container_name,
        scan_recursive=request.scan_recursive,
        auto_scan_enabled=request.auto_scan_enabled,
        auto_scan_frequency=request.auto_scan_frequency,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return {
        "id": link.id,
        "creator_id": link.creator_id,
        "provider": link.provider,
        "folder_path": link.folder_path,
    }


@router.put("/org/{org_id}/links/{link_id}")
def update_creator_storage_link(
    org_id: int,
    link_id: int,
    request: CreatorStorageLinkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    link = db.query(CreatorStorageLink).filter(
        CreatorStorageLink.id == link_id,
        CreatorStorageLink.org_id == org_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Storage link not found")

    if request.folder_path is not None:
        link.folder_path = request.folder_path
    if request.container_name is not None:
        link.container_name = request.container_name
    if request.scan_recursive is not None:
        link.scan_recursive = request.scan_recursive
    if request.auto_scan_enabled is not None:
        link.auto_scan_enabled = request.auto_scan_enabled
    if request.auto_scan_frequency is not None:
        link.auto_scan_frequency = request.auto_scan_frequency

    db.commit()
    return {"message": "Updated"}


@router.delete("/org/{org_id}/links/{link_id}")
def delete_creator_storage_link(
    org_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    link = db.query(CreatorStorageLink).filter(
        CreatorStorageLink.id == link_id,
        CreatorStorageLink.org_id == org_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Storage link not found")
    db.delete(link)
    db.commit()
    return {"message": "Deleted"}


@router.post("/org/{org_id}/scan/{link_id}")
def scan_creator_folder(
    org_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    try:
        result = scan_service.scan_creator_storage(org_id, link_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Scan error: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.post("/org/{org_id}/scan-all")
def scan_all_folders(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    try:
        result = scan_service.scan_all_creator_links(org_id, db)
        return result
    except Exception as e:
        logger.error(f"Scan all error: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.get("/org/{org_id}/results")
def get_scan_results(
    org_id: int,
    scan_batch_id: Optional[str] = None,
    creator_id: Optional[int] = None,
    confidence: Optional[str] = None,
    reviewed: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(StorageScanResult).filter(StorageScanResult.org_id == org_id)

    if scan_batch_id:
        query = query.filter(StorageScanResult.scan_batch_id == scan_batch_id)
    if creator_id:
        query = query.filter(StorageScanResult.creator_id == creator_id)
    if confidence:
        query = query.filter(StorageScanResult.match_confidence == confidence)
    if reviewed is not None:
        query = query.filter(StorageScanResult.reviewed == reviewed)

    results = query.order_by(StorageScanResult.match_score.desc()).all()

    return [{
        "id": r.id,
        "scan_batch_id": r.scan_batch_id,
        "creator_id": r.creator_id,
        "creator_name": r.creator.display_name if r.creator else None,
        "provider": r.provider,
        "file_path": r.file_path,
        "file_name": r.file_name,
        "file_size": r.file_size,
        "matched_song_id": r.matched_song_id,
        "matched_song_title": r.matched_song.title if r.matched_song else None,
        "matched_song_artist": r.matched_song.primary_artist if r.matched_song else None,
        "matched_work_id": r.matched_work_id,
        "matched_work_title": r.matched_work.title if r.matched_work else None,
        "match_confidence": r.match_confidence,
        "match_score": r.match_score,
        "match_reason": r.match_reason,
        "suggested_title": r.suggested_title,
        "suggested_artist": r.suggested_artist,
        "reviewed": r.reviewed,
        "approved": r.approved,
        "linked_audio_asset_id": r.linked_audio_asset_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in results]


@router.get("/org/{org_id}/batches")
def get_scan_batches(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    from sqlalchemy import func, distinct

    batches = db.query(
        StorageScanResult.scan_batch_id,
        func.count(StorageScanResult.id).label("total"),
        func.min(StorageScanResult.created_at).label("created_at"),
        func.count(distinct(StorageScanResult.creator_id)).label("creator_count"),
    ).filter(
        StorageScanResult.org_id == org_id,
    ).group_by(StorageScanResult.scan_batch_id).order_by(
        func.min(StorageScanResult.created_at).desc()
    ).all()

    result = []
    for b in batches:
        reviewed_count = db.query(StorageScanResult).filter(
            StorageScanResult.scan_batch_id == b.scan_batch_id,
            StorageScanResult.reviewed == True,
        ).count()
        approved_count = db.query(StorageScanResult).filter(
            StorageScanResult.scan_batch_id == b.scan_batch_id,
            StorageScanResult.approved == True,
        ).count()
        result.append({
            "scan_batch_id": b.scan_batch_id,
            "total": b.total,
            "reviewed": reviewed_count,
            "approved": approved_count,
            "pending": b.total - reviewed_count,
            "creator_count": b.creator_count,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        })
    return result


@router.post("/org/{org_id}/results/{result_id}/approve")
def approve_result(
    org_id: int,
    result_id: int,
    request: ApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    try:
        result = scan_service.approve_scan_result(
            org_id, result_id, request.song_id, request.work_id,
            request.create_new, request.new_title, request.new_artist, db,
        )

        asset_id = result.get("audio_asset_id")
        if asset_id:
            existing_analysis = db.query(AudioAnalysis).filter(
                AudioAnalysis.audio_asset_id == asset_id,
            ).first()
            if not existing_analysis:
                analysis = AudioAnalysis(
                    org_id=org_id,
                    audio_asset_id=asset_id,
                    status="QUEUED",
                )
                db.add(analysis)
                db.commit()

                import threading
                from ..routes.audio import _run_analysis_worker
                thread = threading.Thread(
                    target=_run_analysis_worker,
                    args=(analysis.id, asset_id, org_id),
                    daemon=True,
                )
                thread.start()
                result["analysis_queued"] = True

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/org/{org_id}/results/{result_id}/reject")
def reject_result(
    org_id: int,
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    try:
        scan_service.reject_scan_result(org_id, result_id, db)
        return {"message": "Rejected"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/org/{org_id}/results/{result_id}/reassign")
def reassign_match(
    org_id: int,
    result_id: int,
    request: ReassignMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    result = db.query(StorageScanResult).filter(
        StorageScanResult.id == result_id,
        StorageScanResult.org_id == org_id,
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Scan result not found")

    if request.song_id:
        song = db.query(Song).filter(Song.id == request.song_id, Song.organization_id == org_id).first()
        if not song:
            raise HTTPException(status_code=404, detail="Song not found")
        result.matched_song_id = request.song_id
        result.match_confidence = "HIGH"
        result.match_reason = "Manually assigned"
    if request.work_id:
        result.matched_work_id = request.work_id
    db.commit()
    return {"message": "Reassigned"}


@router.post("/org/{org_id}/bulk-approve")
def bulk_approve(
    org_id: int,
    request: BulkApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_admin(current_user, org_id, db)
    try:
        result = scan_service.bulk_approve_high_confidence(
            org_id, request.scan_batch_id, request.min_confidence, db,
        )

        new_asset_ids = result.get("created_asset_ids", [])
        if new_asset_ids:
            import threading
            from ..routes.audio import _run_analysis_worker

            for asset_id in new_asset_ids:
                existing_analysis = db.query(AudioAnalysis).filter(
                    AudioAnalysis.audio_asset_id == asset_id,
                ).first()
                if not existing_analysis:
                    analysis = AudioAnalysis(
                        org_id=org_id,
                        audio_asset_id=asset_id,
                        status="QUEUED",
                    )
                    db.add(analysis)
                    db.flush()
                    db.commit()
                    thread = threading.Thread(
                        target=_run_analysis_worker,
                        args=(analysis.id, asset_id, org_id),
                        daemon=True,
                    )
                    thread.start()
            result["analysis_queued"] = len(new_asset_ids)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AnalyzeLinkedRequest(BaseModel):
    song_ids: Optional[List[int]] = None
    scan_batch_id: Optional[str] = None


@router.post("/org/{org_id}/analyze-linked")
def analyze_linked_songs(
    org_id: int,
    request: AnalyzeLinkedRequest = AnalyzeLinkedRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    import threading
    from ..routes.audio import _run_analysis_worker

    query = db.query(AudioAsset).filter(
        AudioAsset.org_id == org_id,
        AudioAsset.song_id.isnot(None),
    )

    if request.song_ids:
        query = query.filter(AudioAsset.song_id.in_(request.song_ids))

    if request.scan_batch_id:
        approved_asset_ids = [
            r[0] for r in db.query(StorageScanResult.linked_audio_asset_id).filter(
                StorageScanResult.scan_batch_id == request.scan_batch_id,
                StorageScanResult.approved == True,
                StorageScanResult.linked_audio_asset_id.isnot(None),
            ).all()
        ]
        if approved_asset_ids:
            query = query.filter(AudioAsset.id.in_(approved_asset_ids))

    assets = query.all()

    queued = 0
    for asset in assets:
        existing = db.query(AudioAnalysis).filter(
            AudioAnalysis.audio_asset_id == asset.id,
        ).first()
        if existing and existing.status in ("SUCCEEDED", "RUNNING", "QUEUED"):
            continue

        if existing:
            existing.status = "QUEUED"
            existing.error_message = None
            db.commit()
            analysis_id = existing.id
        else:
            analysis = AudioAnalysis(
                org_id=org_id,
                audio_asset_id=asset.id,
                status="QUEUED",
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
            analysis_id = analysis.id

        thread = threading.Thread(
            target=_run_analysis_worker,
            args=(analysis_id, asset.id, org_id),
            daemon=True,
        )
        thread.start()
        queued += 1

    return {"queued": queued, "total_assets": len(assets)}


class OrgWideScanRequest(BaseModel):
    folder_path: str = "/"
    auto_link_threshold: float = 0.85


@router.post("/org/{org_id}/org-scan")
def org_wide_scan(
    org_id: int,
    request: OrgWideScanRequest = OrgWideScanRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_admin(current_user, org_id, db)

    threshold = max(0.5, min(1.0, request.auto_link_threshold))

    integration = db.query(IntegrationAccount).filter(
        IntegrationAccount.org_id == org_id,
        IntegrationAccount.provider == "DROPBOX",
        IntegrationAccount.is_active == True,
    ).first()
    if not integration:
        raise HTTPException(status_code=400, detail="Dropbox is not connected. Please connect it first in Settings.")

    try:
        result = scan_service.scan_org_wide(org_id, request.folder_path, db, auto_link_threshold=threshold)

        queued_pairs = result.pop("queued_analysis_ids", [])
        if queued_pairs:
            import threading
            from ..routes.audio import _run_analysis_worker

            for analysis_id, asset_id in queued_pairs:
                thread = threading.Thread(
                    target=_run_analysis_worker,
                    args=(analysis_id, asset_id, org_id),
                    daemon=True,
                )
                thread.start()

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Org-wide scan error: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.get("/org/{org_id}/coverage")
def get_audio_coverage(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    from sqlalchemy import func

    total_songs = db.query(func.count(Song.id)).filter(
        Song.organization_id == org_id
    ).scalar() or 0

    songs_with_audio = db.query(func.count(func.distinct(AudioAsset.song_id))).filter(
        AudioAsset.org_id == org_id,
        AudioAsset.song_id.isnot(None),
    ).scalar() or 0

    songs_analyzed = db.query(func.count(func.distinct(AudioAsset.song_id))).filter(
        AudioAsset.org_id == org_id,
        AudioAsset.song_id.isnot(None),
    ).join(AudioAnalysis, AudioAnalysis.audio_asset_id == AudioAsset.id).filter(
        AudioAnalysis.status == "SUCCEEDED",
    ).scalar() or 0

    songs_queued = db.query(func.count(func.distinct(AudioAsset.song_id))).filter(
        AudioAsset.org_id == org_id,
        AudioAsset.song_id.isnot(None),
    ).join(AudioAnalysis, AudioAnalysis.audio_asset_id == AudioAsset.id).filter(
        AudioAnalysis.status.in_(["QUEUED", "RUNNING"]),
    ).scalar() or 0

    songs_failed = db.query(func.count(func.distinct(AudioAsset.song_id))).filter(
        AudioAsset.org_id == org_id,
        AudioAsset.song_id.isnot(None),
    ).join(AudioAnalysis, AudioAnalysis.audio_asset_id == AudioAsset.id).filter(
        AudioAnalysis.status == "FAILED",
    ).scalar() or 0

    total_assets = db.query(func.count(AudioAsset.id)).filter(
        AudioAsset.org_id == org_id,
    ).scalar() or 0

    return {
        "total_songs": total_songs,
        "songs_with_audio": songs_with_audio,
        "songs_analyzed": songs_analyzed,
        "songs_queued": songs_queued,
        "songs_failed": songs_failed,
        "songs_unlinked": total_songs - songs_with_audio,
        "total_assets": total_assets,
        "audio_coverage_pct": round((songs_with_audio / total_songs * 100), 1) if total_songs > 0 else 0,
        "analysis_coverage_pct": round((songs_analyzed / total_songs * 100), 1) if total_songs > 0 else 0,
    }


@router.post("/org/{org_id}/analyze-all-unanalyzed")
def analyze_all_unanalyzed(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_admin(current_user, org_id, db)
    import threading
    from ..routes.audio import _run_analysis_worker

    assets = db.query(AudioAsset).filter(
        AudioAsset.org_id == org_id,
        AudioAsset.song_id.isnot(None),
    ).all()

    queued = 0
    for asset in assets:
        existing = db.query(AudioAnalysis).filter(
            AudioAnalysis.audio_asset_id == asset.id,
        ).first()
        if existing and existing.status in ("SUCCEEDED", "RUNNING", "QUEUED"):
            continue

        if existing:
            existing.status = "QUEUED"
            existing.error_message = None
            db.commit()
            analysis_id = existing.id
        else:
            analysis = AudioAnalysis(
                org_id=org_id,
                audio_asset_id=asset.id,
                status="QUEUED",
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
            analysis_id = analysis.id

        thread = threading.Thread(
            target=_run_analysis_worker,
            args=(analysis_id, asset.id, org_id),
            daemon=True,
        )
        thread.start()
        queued += 1

    return {"queued": queued, "message": f"Queued {queued} assets for analysis"}


class ScheduleScanRequest(BaseModel):
    auto_scan_enabled: bool
    auto_scan_frequency: Optional[str] = "daily"


@router.put("/org/{org_id}/links/{link_id}/schedule")
def update_scan_schedule(
    org_id: int,
    link_id: int,
    request: ScheduleScanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    link = db.query(CreatorStorageLink).filter(
        CreatorStorageLink.id == link_id,
        CreatorStorageLink.org_id == org_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Storage link not found")

    link.auto_scan_enabled = request.auto_scan_enabled
    link.auto_scan_frequency = request.auto_scan_frequency if request.auto_scan_enabled else None
    db.commit()
    return {
        "message": "Schedule updated",
        "auto_scan_enabled": link.auto_scan_enabled,
        "auto_scan_frequency": link.auto_scan_frequency,
    }


@router.get("/org/{org_id}/providers")
def get_connected_providers(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    integrations = db.query(IntegrationAccount).filter(
        IntegrationAccount.org_id == org_id,
        IntegrationAccount.is_active == True,
    ).all()

    return [{
        "provider": i.provider,
        "account_email": i.account_email,
        "account_display_name": i.account_display_name,
        "connected_at": i.created_at.isoformat() if i.created_at else None,
    } for i in integrations]


@router.get("/org/{org_id}/browse")
async def browse_provider_folders(
    org_id: int,
    provider: str = Query("DROPBOX"),
    path: str = Query(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    normalized_path = path if path else "/"
    try:
        files = await asyncio.to_thread(storage_service.list_files_for_provider, org_id, provider, normalized_path, db)
        return {"files": files, "path": normalized_path, "provider": provider}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
