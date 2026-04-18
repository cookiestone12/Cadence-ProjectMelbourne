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

router = APIRouter(prefix="/api/storage-scan", tags=["Storage Scan"])
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


@router.get(
    "/org/{org_id}/links",
    summary="List a creator's connected cloud-storage folders",
    description=(
        "Returns every CreatorStorageLink in the org — a link is a "
        "(creator, provider, folder_path) tuple that storage scans crawl "
        "for new audio. Optionally filter to a single creator.\n\n"
        "**Path parameter:** `org_id` — Cadence Organization ID.\n"
        "**Optional query:** `creator_id` — restrict to a single Creator.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `List[{ id, creator_id, provider, folder_path, "
        "container_name, scan_recursive, auto_scan_enabled, "
        "auto_scan_frequency, last_scanned_at }]`."
    ),
)
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


@router.post(
    "/org/{org_id}/links",
    summary="Connect a cloud-storage folder to a creator",
    description=(
        "Pins a folder in the org's connected provider (Dropbox / Google "
        "Drive / OneDrive / S3) to a Creator. Future scans will index audio "
        "files under that path and propose Song matches. The folder must be "
        "reachable by the org's IntegrationAccount for `provider`.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Body (`CreatorStorageLinkCreate`):** `creator_id`, `provider` "
        "(default `DROPBOX`), `folder_path`, optional `container_name` "
        "(bucket / drive id), `scan_recursive` (default true), "
        "`auto_scan_enabled` (default false), `auto_scan_frequency` "
        "(`DAILY` / `WEEKLY` / `MONTHLY`).\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ id, creator_id, provider, folder_path }`."
    ),
)
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


@router.put(
    "/org/{org_id}/links/{link_id}",
    summary="Update a creator storage link",
    description=(
        "Patches an existing CreatorStorageLink. Use the dedicated "
        "`/schedule` endpoint to change auto-scan timing without touching "
        "the path.\n\n"
        "**Path parameters:** `org_id`, `link_id`.\n"
        "**Body (`CreatorStorageLinkUpdate`):** any subset of `folder_path`, "
        "`container_name`, `scan_recursive`, `auto_scan_enabled`, "
        "`auto_scan_frequency`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ message: \"Storage link updated\" }`."
    ),
)
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


@router.delete(
    "/org/{org_id}/links/{link_id}",
    summary="Disconnect a creator storage link",
    description=(
        "Removes the CreatorStorageLink. Already-imported AudioAssets and "
        "match results are preserved; only the future-scan binding is "
        "broken.\n\n"
        "**Path parameters:** `org_id`, `link_id`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ message: \"Storage link deleted\" }`."
    ),
)
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


@router.post(
    "/org/{org_id}/scan/{link_id}",
    summary="Run a one-off scan against a single storage link",
    description=(
        "Kicks off a synchronous crawl of the linked folder. New audio "
        "files are imported into AudioAsset and run through the matcher to "
        "produce StorageScanResult rows the user can later approve or "
        "reject. Existing files are skipped via content hash.\n\n"
        "**Path parameters:** `org_id`, `link_id`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ scan_batch_id, scanned, imported, matched, "
        "skipped, errors }`."
    ),
)
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


@router.post(
    "/org/{org_id}/scan-all",
    summary="Run a fresh scan of every storage link in the org",
    description=(
        "Iterates every CreatorStorageLink in the org and runs the same "
        "import-and-match flow as the per-link scan endpoint. Long-running; "
        "consider using `/org-scan` (batched/async) for very large orgs.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ scan_batch_id, links_scanned, totals: { scanned, "
        "imported, matched, skipped, errors } }`."
    ),
)
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


@router.get(
    "/org/{org_id}/results",
    summary="List storage-scan match results",
    description=(
        "Returns the queue of StorageScanResult rows produced by recent "
        "scans — each row is a candidate Song/Work match for an imported "
        "AudioAsset that needs human review.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Optional query:** `creator_id`, `status` (`PENDING` / `APPROVED` "
        "/ `REJECTED`), `confidence` (`HIGH` / `MEDIUM` / `LOW`), "
        "`scan_batch_id`, `limit`, `offset`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ items: [...], total }` ordered by newest first."
    ),
)
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


@router.get(
    "/org/{org_id}/batches",
    summary="List recent scan batches with summary counts",
    description=(
        "Groups StorageScanResult rows by `scan_batch_id` and returns one "
        "row per batch with totals. Used to power the Scan History view.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Optional query:** `limit` (default 20).\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `List[{ scan_batch_id, started_at, link_id, "
        "creator_id, total, pending, approved, rejected }]`."
    ),
)
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


@router.post(
    "/org/{org_id}/results/{result_id}/approve",
    summary="Approve a scan result and link the audio to a song / work",
    description=(
        "Accepts the proposed match (or a manual override) and binds the "
        "imported AudioAsset to the chosen Song/Work. Three modes:\n"
        "1. Accept the proposed match — body `{}`.\n"
        "2. Override with an existing record — body `{ song_id }` or "
        "`{ work_id }`.\n"
        "3. Create a new Song on the fly — body `{ create_new: true, "
        "new_title, new_artist }`.\n\n"
        "**Path parameters:** `org_id`, `result_id`.\n"
        "**Body:** `ApproveRequest` (see modes above).\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ message, song_id?, work_id?, asset_id }`."
    ),
)
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


@router.post(
    "/org/{org_id}/results/{result_id}/reject",
    summary="Reject a scan result",
    description=(
        "Marks a StorageScanResult as `REJECTED`. The underlying AudioAsset "
        "stays in the system but is excluded from the review queue. "
        "Re-scanning the folder will not re-propose this asset.\n\n"
        "**Path parameters:** `org_id`, `result_id`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ message: \"Result rejected\" }`."
    ),
)
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


@router.post(
    "/org/{org_id}/results/{result_id}/reassign",
    summary="Reassign an already-approved scan result to a different song",
    description=(
        "Used to fix mistakes: moves the linked AudioAsset off its current "
        "Song/Work and onto a different one without going back through the "
        "approval queue.\n\n"
        "**Path parameters:** `org_id`, `result_id`.\n"
        "**Body (`ReassignMatchRequest`):** exactly one of `song_id` or "
        "`work_id`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ message: \"Match reassigned\" }`."
    ),
)
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


@router.post(
    "/org/{org_id}/bulk-approve",
    summary="Bulk-approve a scan batch's high-confidence matches",
    description=(
        "Auto-approves every PENDING StorageScanResult in `scan_batch_id` "
        "whose match confidence meets `min_confidence`. Equivalent to "
        "calling the per-result approve endpoint with the proposed match "
        "for each row, but in a single transaction.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Body (`BulkApproveRequest`):** `scan_batch_id` (from the batches "
        "endpoint), `min_confidence` (`HIGH` / `MEDIUM` / `LOW`, default "
        "`HIGH`).\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ approved, skipped, errors }`."
    ),
)
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


@router.post(
    "/org/{org_id}/analyze-linked",
    summary="Queue audio analysis for every linked AudioAsset that lacks it",
    description=(
        "Walks the org's AudioAssets that are already linked to a Song/Work "
        "but have no AudioAnalysis row yet, and enqueues them for "
        "fingerprinting/key/BPM analysis.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Optional query:** `creator_id` (limit to one creator's catalog).\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ total_assets, queued }`."
    ),
)
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


@router.post(
    "/org/{org_id}/org-scan",
    summary="Trigger an asynchronous org-wide deep scan",
    description=(
        "Enqueues a background job that fans out scans across every "
        "CreatorStorageLink in the org and follows up with audio analysis "
        "for any new imports. Returns immediately with a `scan_batch_id` "
        "the UI can poll via `/batches`.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ scan_batch_id, queued: true }`."
    ),
)
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


@router.get(
    "/org/{org_id}/coverage",
    summary="Audio + analysis coverage stats for the org",
    description=(
        "Reports how much of the catalog has audio attached and how much "
        "of that audio has been analyzed. Powers the Coverage widget on "
        "the storage dashboard.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Optional query:** `creator_id` to scope to a single roster.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ total_songs, songs_with_audio, songs_unlinked, "
        "songs_analyzed, songs_queued, songs_failed, total_assets, "
        "audio_coverage_pct, analysis_coverage_pct }`."
    ),
)
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


@router.post(
    "/org/{org_id}/analyze-all-unanalyzed",
    summary="Queue audio analysis for every AudioAsset without one",
    description=(
        "Broader counterpart of `/analyze-linked`: ignores Song/Work linkage "
        "and just queues an AudioAnalysis job for any AudioAsset in the org "
        "that doesn't have one yet (or whose previous analysis failed).\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ message, queued }`."
    ),
)
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


@router.put(
    "/org/{org_id}/links/{link_id}/schedule",
    summary="Configure a link's automatic scan schedule",
    description=(
        "Toggles whether the storage link is included in scheduled scans "
        "and at what cadence. The platform scheduler runs daily and picks "
        "up enabled links whose `auto_scan_frequency` window has elapsed.\n\n"
        "**Path parameters:** `org_id`, `link_id`.\n"
        "**Body:** `{ auto_scan_enabled: bool, auto_scan_frequency?: "
        "\"DAILY\" | \"WEEKLY\" | \"MONTHLY\" }`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ message, auto_scan_enabled, auto_scan_frequency }`."
    ),
)
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


@router.get(
    "/org/{org_id}/providers",
    summary="List the org's connected cloud-storage providers",
    description=(
        "Returns one row per IntegrationAccount of provider type "
        "(`DROPBOX`, `GOOGLE_DRIVE`, `ONEDRIVE`, `S3`) — these are the "
        "providers the link/browse endpoints can target.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `List[{ provider, account_email, connected_at, "
        "status }]`."
    ),
)
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


@router.get(
    "/org/{org_id}/browse",
    summary="Browse a folder in a connected provider",
    description=(
        "Lists immediate folder/file children at `path` in the org's "
        "connected `provider` so the New Link wizard can render a folder "
        "picker. Read-only; no scanning is triggered.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Required query:** `provider` (e.g. `DROPBOX`).\n"
        "**Optional query:** `path` (default root, provider-specific "
        "format), `container_name` (bucket / drive id when applicable).\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ provider, path, files: [{name, path, is_folder, "
        "size, modified}] }`."
    ),
)
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
