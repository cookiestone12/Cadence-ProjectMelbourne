from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
import io
from ..models import (
    get_db, Contract, ContractParty, ContractAsset, ContractDocument, RightsSplit,
    Song, Work, Release, Creator, OrganizationMember, User, AudioAsset, CreativeContact,
    SongCredit
)
from ..utils.auth import get_current_user
from ..services.contract_parser import parse_contract_document
import logging

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/rights", tags=["Rights Management"])


def _sync_song_pub_percentage(db: Session, song_id: int):
    total_pub = db.query(func.sum(RightsSplit.share_percentage)).join(
        ContractAsset, ContractAsset.id == RightsSplit.contract_asset_id
    ).filter(
        ContractAsset.asset_type == "SONG",
        ContractAsset.asset_id == song_id,
        RightsSplit.rights_type == "PUBLISHING",
    ).scalar()
    total_master = db.query(func.sum(RightsSplit.share_percentage)).join(
        ContractAsset, ContractAsset.id == RightsSplit.contract_asset_id
    ).filter(
        ContractAsset.asset_type == "SONG",
        ContractAsset.asset_id == song_id,
        RightsSplit.rights_type == "MASTER",
    ).scalar()
    song = db.query(Song).filter(Song.id == song_id).first()
    if song:
        song.publishing_percentage = float(total_pub) if total_pub else None
        song.master_percentage = float(total_master) if total_master else None


def _sync_splits_to_credits(db: Session, song_id: int, creator_id: int):
    cas = db.query(ContractAsset).join(
        Contract, Contract.id == ContractAsset.contract_id
    ).filter(
        ContractAsset.asset_type == "SONG",
        ContractAsset.asset_id == song_id,
    ).all()
    ca_ids = [ca.id for ca in cas]
    if not ca_ids:
        return

    pub_total = db.query(func.sum(RightsSplit.share_percentage)).filter(
        RightsSplit.contract_asset_id.in_(ca_ids),
        RightsSplit.rights_holder_id == creator_id,
        RightsSplit.rights_type == "PUBLISHING",
    ).scalar()

    master_total = db.query(func.sum(RightsSplit.share_percentage)).filter(
        RightsSplit.contract_asset_id.in_(ca_ids),
        RightsSplit.rights_holder_id == creator_id,
        RightsSplit.rights_type == "MASTER",
    ).scalar()

    credit = db.query(SongCredit).filter(
        SongCredit.song_id == song_id,
        SongCredit.creator_id == creator_id,
    ).first()
    if credit:
        credit.pub_share = float(pub_total) if pub_total else None
        credit.master_share = float(master_total) if master_total else None


def _get_or_create_split_sheet(db: Session, song: Song, user_id: int):
    contract = db.query(Contract).filter(
        Contract.organization_id == song.organization_id,
        Contract.title == f"Song Splits: {song.title}",
        Contract.contract_type == "SPLIT_SHEET",
    ).first()
    if not contract:
        contract = Contract(
            organization_id=song.organization_id,
            title=f"Song Splits: {song.title}",
            contract_type="SPLIT_SHEET",
            status="ACTIVE",
            created_by_user_id=user_id,
        )
        db.add(contract)
        db.flush()

    ca = db.query(ContractAsset).filter(
        ContractAsset.contract_id == contract.id,
        ContractAsset.asset_type == "SONG",
        ContractAsset.asset_id == song.id,
    ).first()
    if not ca:
        ca = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=song.id,
        )
        db.add(ca)
        db.flush()
    return ca


def sync_credit_to_splits(db: Session, song: Song, creator_id: int, pub_share, master_share, role: str, user_id: int):
    ca = _get_or_create_split_sheet(db, song, user_id)
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    holder_name = creator.display_name if creator else "Unknown"

    for rights_type, share_val in [("PUBLISHING", pub_share), ("MASTER", master_share)]:
        existing = db.query(RightsSplit).filter(
            RightsSplit.contract_asset_id == ca.id,
            RightsSplit.rights_holder_id == creator_id,
            RightsSplit.rights_type == rights_type,
        ).first()

        if share_val is not None and share_val > 0:
            if existing:
                existing.share_percentage = float(share_val)
                existing.role = role or existing.role
            else:
                new_split = RightsSplit(
                    contract_asset_id=ca.id,
                    rights_holder_id=creator_id,
                    rights_holder_name=holder_name,
                    rights_type=rights_type,
                    share_percentage=float(share_val),
                    role=role or "",
                )
                db.add(new_split)
        elif existing:
            db.delete(existing)

    db.flush()
    _sync_song_pub_percentage(db, song.id)
    # Task #140 — credit/split mutations now drive the LG-02 / MD-03
    # checklist items, so we must recompute health here too. Without this,
    # adding splits via the Rights & Splits tab leaves the score stale until
    # the next song-field edit.
    from ..utils.health_sync import sync_song_to_checklist
    sync_song_to_checklist(db, song)


def verify_org_access(user: User, org_id: int, db: Session, creator_id: int = None):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
        if creator_id:
            from .client_sharing import has_shared_access
            if has_shared_access(db, user.id, creator_id, required_module="contracts"):
                return None
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


class PartyCreate(BaseModel):
    party_name: str
    party_role: str = "OTHER"
    creator_id: Optional[int] = None
    contact_email: Optional[str] = None
    contact_info: Optional[str] = None


class ContractCreate(BaseModel):
    title: str
    contract_type: str = "OTHER"
    payment_direction: str = "INCOMING"
    status: str = "DRAFT"
    reference_number: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    territory: Optional[List[str]] = []
    advance_amount: Optional[float] = 0.0
    advance_currency: str = "USD"
    notes: Optional[str] = None
    terms_summary: Optional[str] = None
    creator_id: Optional[int] = None
    parties: Optional[List[PartyCreate]] = []


class ContractUpdate(BaseModel):
    title: Optional[str] = None
    contract_type: Optional[str] = None
    payment_direction: Optional[str] = None
    status: Optional[str] = None
    reference_number: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    territory: Optional[List[str]] = None
    advance_amount: Optional[float] = None
    advance_currency: Optional[str] = None
    advance_recouped: Optional[float] = None
    notes: Optional[str] = None
    terms_summary: Optional[str] = None
    creator_id: Optional[int] = None


class AssetLink(BaseModel):
    asset_type: str
    asset_id: int


class SplitCreate(BaseModel):
    rights_holder_id: Optional[int] = None
    rights_holder_name: Optional[str] = None
    rights_type: str = "MASTER"
    share_percentage: float
    role: Optional[str] = None
    notes: Optional[str] = None
    ipi: Optional[str] = None
    pro: Optional[str] = None
    contact_id: Optional[int] = None


class SplitUpdate(BaseModel):
    rights_type: Optional[str] = None
    share_percentage: Optional[float] = None
    rights_holder_name: Optional[str] = None
    role: Optional[str] = None
    notes: Optional[str] = None


def _contract_to_dict(contract: Contract, db: Session, include_details: bool = False):
    asset_count = db.query(ContractAsset).filter(ContractAsset.contract_id == contract.id).count()
    document_count = db.query(ContractDocument).filter(ContractDocument.contract_id == contract.id).count()
    parties = []
    for p in contract.parties:
        parties.append({
            "id": p.id,
            "party_name": p.party_name,
            "party_role": p.party_role,
            "creator_id": p.creator_id,
            "contact_email": p.contact_email,
            "contact_info": p.contact_info,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    creator_name = None
    if contract.creator_id:
        creator = db.query(Creator).filter(Creator.id == contract.creator_id).first()
        if creator:
            creator_name = creator.display_name or creator.legal_name

    result = {
        "id": contract.id,
        "organization_id": contract.organization_id,
        "title": contract.title,
        "contract_type": contract.contract_type,
        "payment_direction": contract.payment_direction,
        "status": contract.status,
        "reference_number": contract.reference_number,
        "start_date": contract.start_date.isoformat() if contract.start_date else None,
        "end_date": contract.end_date.isoformat() if contract.end_date else None,
        "territory": contract.territory or [],
        "advance_amount": contract.advance_amount,
        "advance_currency": contract.advance_currency,
        "advance_recouped": contract.advance_recouped,
        "notes": contract.notes,
        "terms_summary": contract.terms_summary,
        "creator_id": contract.creator_id,
        "creator_name": creator_name,
        "created_at": contract.created_at.isoformat() if contract.created_at else None,
        "updated_at": contract.updated_at.isoformat() if contract.updated_at else None,
        "created_by_user_id": contract.created_by_user_id,
        "parties": parties,
        "asset_count": asset_count,
        "document_count": document_count,
    }

    if include_details:
        assets_data = []
        for ca in contract.assets:
            asset_title = None
            asset_artist = None
            audio_info = None
            if ca.asset_type == "SONG":
                song = db.query(Song).filter(Song.id == ca.asset_id).first()
                asset_title = song.title if song else "Unknown Song"
                asset_artist = song.primary_artist if song else None
                if song:
                    audio = db.query(AudioAsset).filter(
                        AudioAsset.song_id == song.id,
                        AudioAsset.org_id == contract.organization_id,
                    ).first()
                    if audio:
                        audio_info = {
                            "id": audio.id,
                            "name": audio.name,
                            "provider": audio.provider,
                            "path_display": audio.path_display,
                            "file_type": audio.file_type,
                        }
            elif ca.asset_type == "WORK":
                work = db.query(Work).filter(Work.id == ca.asset_id).first()
                asset_title = work.title if work else "Unknown Work"
            elif ca.asset_type == "RELEASE":
                release = db.query(Release).filter(Release.id == ca.asset_id).first()
                asset_title = release.title if release else "Unknown Release"
                asset_artist = release.primary_artist if release else None
                if release:
                    audio = db.query(AudioAsset).filter(
                        AudioAsset.release_id == release.id,
                        AudioAsset.org_id == contract.organization_id,
                    ).first()
                    if audio:
                        audio_info = {
                            "id": audio.id,
                            "name": audio.name,
                            "provider": audio.provider,
                            "path_display": audio.path_display,
                            "file_type": audio.file_type,
                        }

            splits = db.query(RightsSplit).filter(RightsSplit.contract_asset_id == ca.id).all()
            splits_data = []
            for s in splits:
                if s.rights_holder_id:
                    holder = db.query(Creator).filter(Creator.id == s.rights_holder_id).first()
                    holder_name = holder.display_name if holder else (s.rights_holder_name or "Unknown")
                else:
                    holder_name = s.rights_holder_name or "Unknown"
                splits_data.append({
                    "id": s.id,
                    "rights_holder_id": s.rights_holder_id,
                    "rights_holder_name": holder_name,
                    "rights_type": s.rights_type,
                    "share_percentage": s.share_percentage,
                    "role": s.role,
                    "notes": s.notes,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                })

            assets_data.append({
                "id": ca.id,
                "asset_type": ca.asset_type,
                "asset_id": ca.asset_id,
                "asset_title": asset_title,
                "asset_artist": asset_artist,
                "audio_linked": audio_info,
                "splits": splits_data,
                "created_at": ca.created_at.isoformat() if ca.created_at else None,
            })

        result["assets"] = assets_data

    return result


@router.get(
    "/contracts/creator/{creator_id}",
    summary="List a creator's contracts",
    description=(
        "Returns every contract in the creator's organization where the creator "
        "is either the primary `creator_id` on the Contract row or named as a "
        "ContractParty. Useful for the creator profile page's Contracts tab.\n\n"
        "**Path parameter:** `creator_id` — Cadence Creator ID.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the creator's "
        "organization (admins of the org or super-admins always pass).\n\n"
        "**Response:** `{ contracts: [...], total: int }`. Each contract entry "
        "carries `id`, `title`, `contract_type`, `status`, `reference_number`, "
        "`start_date` and `end_date`. Returns `{ contracts: [], total: 0 }` if "
        "there are no matches."
    ),
)
def list_contracts_by_creator(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    verify_org_access(current_user, creator.organization_id, db, creator_id=creator_id)

    direct_ids = db.query(Contract.id).filter(
        Contract.organization_id == creator.organization_id,
        Contract.creator_id == creator_id
    ).all()
    party_ids = db.query(ContractParty.contract_id).join(
        Contract, Contract.id == ContractParty.contract_id
    ).filter(
        ContractParty.creator_id == creator_id,
        Contract.organization_id == creator.organization_id
    ).all()

    all_ids = list(set([r[0] for r in direct_ids] + [r[0] for r in party_ids]))
    if not all_ids:
        return {"contracts": [], "total": 0}

    contracts = db.query(Contract).filter(
        Contract.id.in_(all_ids),
        Contract.organization_id == creator.organization_id
    ).order_by(Contract.created_at.desc()).all()
    return {"contracts": [_contract_to_dict(c, db) for c in contracts], "total": len(contracts)}


@router.get(
    "/contracts/song/{song_id}",
    summary="List contracts attached to a song",
    description=(
        "Returns every Contract that has the song linked as a ContractAsset "
        "(`asset_type=SONG, asset_id={song_id}`). The result is the same shape "
        "the song detail page uses to render the Rights / Splits sidebar.\n\n"
        "**Path parameter:** `song_id` — Cadence Song ID.\n\n"
        "**Auth:** Bearer JWT. The caller must be a member of the song's "
        "organization (or, if the song has a primary credit, of that creator's "
        "shared scope).\n\n"
        "**Response:** `{ contracts: [...] }` with a slim record per contract: "
        "`id`, `title`, `contract_type`, `status`, `reference_number`, "
        "`start_date`, `end_date`. Returns `{ contracts: [] }` when nothing is "
        "linked. 404 if the song doesn't exist."
    ),
)
def get_contracts_for_song(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    from ..models import SongCredit
    song_credit = db.query(SongCredit).filter(SongCredit.song_id == song_id).first()
    verify_org_access(current_user, song.organization_id, db, creator_id=song_credit.creator_id if song_credit else None)

    asset_links = db.query(ContractAsset).filter(
        ContractAsset.asset_type == "SONG",
        ContractAsset.asset_id == song_id,
    ).all()

    if not asset_links:
        return {"contracts": []}

    contract_ids = list(set(ca.contract_id for ca in asset_links))
    contracts = db.query(Contract).filter(
        Contract.id.in_(contract_ids),
        Contract.organization_id == song.organization_id,
    ).order_by(Contract.created_at.desc()).all()

    return {"contracts": [{
        "id": c.id,
        "title": c.title,
        "contract_type": c.contract_type,
        "status": c.status,
        "reference_number": c.reference_number,
        "start_date": c.start_date.isoformat() if c.start_date else None,
        "end_date": c.end_date.isoformat() if c.end_date else None,
    } for c in contracts]}


@router.get(
    "/song-splits/{song_id}",
    summary="List rights splits for a song",
    description=(
        "Returns the merged set of RightsSplit rows attached to the song "
        "across every linked Contract plus the song's standalone "
        "`Song Splits: <title>` SPLIT_SHEET (the implicit container Cadence "
        "creates when a user adds a split with no source contract).\n\n"
        "**Path parameter:** `song_id` — Cadence Song ID.\n\n"
        "**Auth:** Bearer JWT. Caller must belong to the song's org or share "
        "the primary creator's scope.\n\n"
        "**Response:** `{ splits: [...] }`. Each split exposes `id`, "
        "`contract_asset_id`, `rights_holder_id`, `rights_holder_name` "
        "(de-referenced through the Creator table when possible), "
        "`rights_type` (MASTER / PUBLISHING / PERFORMANCE / MECHANICAL / "
        "DISTRIBUTION / SYNC / OTHER), `share_percentage` (0–100), `role`, "
        "`notes`, `contract_title`, `contract_id`, and `is_standalone=true` "
        "for splits that live in the auto-created split sheet."
    ),
)
def get_song_splits(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    from ..models import SongCredit
    song_credit = db.query(SongCredit).filter(SongCredit.song_id == song_id).first()
    verify_org_access(current_user, song.organization_id, db, creator_id=song_credit.creator_id if song_credit else None)

    asset_links = db.query(ContractAsset).filter(
        ContractAsset.asset_type == "SONG",
        ContractAsset.asset_id == song_id,
    ).all()

    splits = []
    for ca in asset_links:
        ca_splits = db.query(RightsSplit).filter(RightsSplit.contract_asset_id == ca.id).all()
        contract = db.query(Contract).filter(Contract.id == ca.contract_id).first()
        for s in ca_splits:
            if s.rights_holder_id:
                holder = db.query(Creator).filter(Creator.id == s.rights_holder_id).first()
                h_name = holder.display_name if holder else (s.rights_holder_name or "Unknown")
            else:
                h_name = s.rights_holder_name or "Unknown"
            splits.append({
                "id": s.id,
                "contract_asset_id": s.contract_asset_id,
                "rights_holder_id": s.rights_holder_id,
                "rights_holder_name": h_name,
                "rights_type": s.rights_type,
                "share_percentage": s.share_percentage,
                "role": s.role,
                "notes": s.notes,
                "contract_title": contract.title if contract else None,
                "contract_id": contract.id if contract else None,
            })

    standalone_contract = db.query(Contract).filter(
        Contract.organization_id == song.organization_id,
        Contract.title == f"Song Splits: {song.title}",
        Contract.contract_type == "SPLIT_SHEET",
    ).first()

    if standalone_contract:
        standalone_ca = db.query(ContractAsset).filter(
            ContractAsset.contract_id == standalone_contract.id,
            ContractAsset.asset_type == "SONG",
            ContractAsset.asset_id == song_id,
        ).first()
        if standalone_ca:
            standalone_splits = db.query(RightsSplit).filter(
                RightsSplit.contract_asset_id == standalone_ca.id
            ).all()
            for s in standalone_splits:
                if any(existing["id"] == s.id for existing in splits):
                    continue
                if s.rights_holder_id:
                    holder = db.query(Creator).filter(Creator.id == s.rights_holder_id).first()
                    h_name = holder.display_name if holder else (s.rights_holder_name or "Unknown")
                else:
                    h_name = s.rights_holder_name or "Unknown"
                splits.append({
                    "id": s.id,
                    "contract_asset_id": s.contract_asset_id,
                    "rights_holder_id": s.rights_holder_id,
                    "rights_holder_name": h_name,
                    "rights_type": s.rights_type,
                    "share_percentage": s.share_percentage,
                    "role": s.role,
                    "notes": s.notes,
                    "contract_title": standalone_contract.title,
                    "contract_id": standalone_contract.id,
                    "is_standalone": True,
                })

    return {"splits": splits}


@router.post(
    "/song-splits/{song_id}",
    summary="Add a rights split to a song",
    description=(
        "Adds a single RightsSplit row to the song's standalone split sheet, "
        "creating the SPLIT_SHEET Contract and ContractAsset on first use. "
        "Side effects: refreshes the song's cached `publishing_percentage` / "
        "`master_percentage`, syncs the matching SongCredit when the split "
        "type is PUBLISHING or MASTER, ensures a CreativeContact exists for "
        "the holder, and writes a `record_split_change` audit row.\n\n"
        "**Path parameter:** `song_id` — Cadence Song ID.\n\n"
        "**Body (`SplitCreate`):** one of `rights_holder_id` (Creator FK) or "
        "`rights_holder_name` is required; `rights_type` must be one of "
        "MASTER / PUBLISHING / PERFORMANCE / MECHANICAL / DISTRIBUTION / "
        "SYNC / OTHER; `share_percentage` is 0.01–100; optional `role`, "
        "`notes`, `ipi`, `pro`, `contact_id`. The endpoint rejects with 400 "
        "if the new total per `rights_type` would exceed 100%.\n\n"
        "**Auth:** Bearer JWT, caller must belong to the song's organization.\n\n"
        "**Response:** `{ id, rights_holder_name, rights_type, "
        "share_percentage, role, ipi, message }`. 404 if song or named "
        "rights holder isn't in the org."
    ),
)
def add_song_split(
    song_id: int,
    data: SplitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    verify_org_access(current_user, song.organization_id, db)

    if not data.rights_holder_id and not data.rights_holder_name:
        raise HTTPException(status_code=400, detail="Either rights_holder_id or rights_holder_name is required")

    allowed_rights_types = {"MASTER", "PUBLISHING", "PERFORMANCE", "MECHANICAL", "DISTRIBUTION", "SYNC", "OTHER"}
    if data.rights_type not in allowed_rights_types:
        raise HTTPException(status_code=400, detail=f"Invalid rights type. Must be one of: {', '.join(sorted(allowed_rights_types))}")

    if data.share_percentage <= 0 or data.share_percentage > 100:
        raise HTTPException(status_code=400, detail="Share percentage must be between 0.01 and 100")

    contract = db.query(Contract).filter(
        Contract.organization_id == song.organization_id,
        Contract.title == f"Song Splits: {song.title}",
        Contract.contract_type == "SPLIT_SHEET",
    ).first()

    if not contract:
        contract = Contract(
            organization_id=song.organization_id,
            title=f"Song Splits: {song.title}",
            contract_type="SPLIT_SHEET",
            status="ACTIVE",
            created_by_user_id=current_user.id,
        )
        db.add(contract)
        db.flush()

    ca = db.query(ContractAsset).filter(
        ContractAsset.contract_id == contract.id,
        ContractAsset.asset_type == "SONG",
        ContractAsset.asset_id == song_id,
    ).first()

    if not ca:
        ca = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=song_id,
        )
        db.add(ca)
        db.flush()

    existing_total = db.query(func.coalesce(func.sum(RightsSplit.share_percentage), 0)).filter(
        RightsSplit.contract_asset_id == ca.id,
        RightsSplit.rights_type == data.rights_type,
    ).scalar()

    if existing_total + data.share_percentage > 100:
        raise HTTPException(
            status_code=400,
            detail=f"Total {data.rights_type} splits would exceed 100% (existing: {existing_total}%, new: {data.share_percentage}%)"
        )

    holder_name = data.rights_holder_name
    holder_ipi = data.ipi
    holder_pro = data.pro
    if data.rights_holder_id:
        holder = db.query(Creator).filter(
            Creator.id == data.rights_holder_id,
            Creator.organization_id == song.organization_id,
        ).first()
        if not holder:
            raise HTTPException(status_code=404, detail="Rights holder not found in this organization")
        holder_name = holder_name or holder.display_name
        if not holder_ipi:
            holder_ipi = holder.primary_ipi
        if not holder_pro:
            holder_pro = holder.primary_pro
        existing_contact = db.query(CreativeContact).filter(
            CreativeContact.organization_id == song.organization_id,
            CreativeContact.creator_id == holder.id,
        ).first()
        if not existing_contact:
            new_contact = CreativeContact(
                organization_id=song.organization_id,
                creator_id=holder.id,
                display_name=holder.display_name,
                legal_name=holder.legal_name,
                email=holder.email,
                phone=holder.phone,
                pro=holder_pro or holder.primary_pro,
                ipi=holder_ipi or holder.primary_ipi,
                publisher_name=holder.publisher_name,
                roles=holder.roles or [],
                territory=holder.primary_territory,
            )
            db.add(new_contact)
            db.flush()
        elif existing_contact:
            if holder_ipi and not existing_contact.ipi:
                existing_contact.ipi = holder_ipi
            if holder_pro and not existing_contact.pro:
                existing_contact.pro = holder_pro
            db.flush()
    elif data.contact_id:
        contact = db.query(CreativeContact).filter(
            CreativeContact.id == data.contact_id,
            CreativeContact.organization_id == song.organization_id,
        ).first()
        if contact:
            holder_name = holder_name or contact.display_name
            if not holder_ipi:
                holder_ipi = contact.ipi
            if not holder_pro:
                holder_pro = contact.pro
            if holder_ipi and not contact.ipi:
                contact.ipi = holder_ipi
            if holder_pro and not contact.pro:
                contact.pro = holder_pro
            db.flush()

    if not data.rights_holder_id and not data.contact_id and holder_name:
        existing_contact = db.query(CreativeContact).filter(
            CreativeContact.organization_id == song.organization_id,
            func.lower(CreativeContact.display_name) == holder_name.lower(),
        ).first()
        if not existing_contact:
            new_contact = CreativeContact(
                organization_id=song.organization_id,
                display_name=holder_name,
                ipi=holder_ipi,
                pro=holder_pro,
                roles=["Collaborator"],
            )
            db.add(new_contact)
            db.flush()

    split = RightsSplit(
        contract_asset_id=ca.id,
        rights_holder_id=data.rights_holder_id,
        rights_holder_name=holder_name,
        rights_type=data.rights_type,
        share_percentage=data.share_percentage,
        role=data.role,
        notes=data.notes,
    )
    db.add(split)
    db.flush()

    from ..utils.edit_history import record_split_change
    record_split_change(db, song_id, song.organization_id, current_user.id, holder_name, data.rights_type, None, data.share_percentage, notes=data.notes)

    _sync_song_pub_percentage(db, song_id)
    if data.rights_holder_id and data.rights_type in ("PUBLISHING", "MASTER"):
        _sync_splits_to_credits(db, song_id, data.rights_holder_id)

    # Task #140 — adding a split through the standalone Rights & Splits tab
    # can flip LG-02 to COMPLETED once pub shares total 100%.
    from ..utils.health_sync import sync_song_to_checklist
    sync_song_to_checklist(db, song)

    db.commit()
    db.refresh(split)

    return {
        "id": split.id,
        "rights_holder_name": holder_name,
        "rights_type": split.rights_type,
        "share_percentage": split.share_percentage,
        "role": split.role,
        "ipi": holder_ipi,
        "message": "Split added successfully",
    }


@router.delete(
    "/song-splits/{split_id}",
    summary="Delete a song rights split",
    description=(
        "Deletes the RightsSplit row, recomputes the song's cached "
        "publishing/master percentages, re-syncs the matching SongCredit, "
        "and writes a `record_split_change` audit entry capturing the prior "
        "share value.\n\n"
        "**Path parameter:** `split_id` — RightsSplit row id.\n"
        "**Optional query:** `notes` — free-text reason captured in the "
        "edit-history record.\n\n"
        "**Auth:** Bearer JWT. Caller must belong to the parent contract's "
        "organization.\n\n"
        "**Response:** `{ message: \"Split deleted successfully\" }`. "
        "404 if the split or its asset row is missing."
    ),
)
def delete_song_split(
    split_id: int,
    notes: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    split = db.query(RightsSplit).filter(RightsSplit.id == split_id).first()
    if not split:
        raise HTTPException(status_code=404, detail="Split not found")

    ca = db.query(ContractAsset).filter(ContractAsset.id == split.contract_asset_id).first()
    if not ca:
        raise HTTPException(status_code=404, detail="Contract asset not found")

    contract = db.query(Contract).filter(Contract.id == ca.contract_id).first()
    if contract:
        verify_org_access(current_user, contract.organization_id, db)

    song_id = ca.asset_id if ca.asset_type == "SONG" else None
    creator_id = split.rights_holder_id
    rights_type = split.rights_type
    old_pct = split.share_percentage
    holder_name = split.rights_holder_name or str(creator_id)

    if song_id:
        song_for_hist = db.query(Song).filter(Song.id == song_id).first()
        if song_for_hist:
            from ..utils.edit_history import record_split_change
            record_split_change(db, song_id, song_for_hist.organization_id, current_user.id, holder_name, rights_type, old_pct, None, notes=notes)

    db.delete(split)
    db.flush()

    if song_id:
        _sync_song_pub_percentage(db, song_id)
        if creator_id and rights_type in ("PUBLISHING", "MASTER"):
            _sync_splits_to_credits(db, song_id, creator_id)
        # Task #140 — deleting a split can drop pub totals back below
        # 100%, which must flip LG-02 back to NOT_STARTED.
        song_for_health = db.query(Song).filter(Song.id == song_id).first()
        if song_for_health:
            from ..utils.health_sync import sync_song_to_checklist
            sync_song_to_checklist(db, song_for_health)

    db.commit()
    return {"message": "Split deleted successfully"}


@router.get(
    "/release-splits/{release_id}",
    summary="List rights splits for a release",
    description=(
        "Mirrors `GET /song-splits/{song_id}` but for Release-level (master) "
        "splits. Returns the merged split list across linked contracts plus "
        "the release's standalone `Release Splits: <title>` SPLIT_SHEET.\n\n"
        "**Path parameter:** `release_id` — Cadence Release ID.\n\n"
        "**Auth:** Bearer JWT. Caller must belong to the release's "
        "organization.\n\n"
        "**Response:** `{ splits: [...] }` with the same per-split fields as "
        "the song endpoint."
    ),
)
def get_release_splits(
    release_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    asset_links = db.query(ContractAsset).join(
        Contract, Contract.id == ContractAsset.contract_id
    ).filter(
        ContractAsset.asset_type == "RELEASE",
        ContractAsset.asset_id == release_id,
        Contract.organization_id == release.organization_id,
    ).all()

    splits = []
    seen_ids = set()
    for ca in asset_links:
        ca_splits = db.query(RightsSplit).filter(RightsSplit.contract_asset_id == ca.id).all()
        contract = db.query(Contract).filter(Contract.id == ca.contract_id).first()
        for s in ca_splits:
            if s.id in seen_ids:
                continue
            seen_ids.add(s.id)
            if s.rights_holder_id:
                holder = db.query(Creator).filter(Creator.id == s.rights_holder_id).first()
                h_name = holder.display_name if holder else (s.rights_holder_name or "Unknown")
            else:
                h_name = s.rights_holder_name or "Unknown"
            splits.append({
                "id": s.id,
                "contract_asset_id": s.contract_asset_id,
                "rights_holder_id": s.rights_holder_id,
                "rights_holder_name": h_name,
                "rights_type": s.rights_type,
                "share_percentage": s.share_percentage,
                "role": s.role,
                "notes": s.notes,
                "contract_title": contract.title if contract else None,
                "contract_id": contract.id if contract else None,
            })

    standalone_contract = db.query(Contract).filter(
        Contract.organization_id == release.organization_id,
        Contract.title == f"Release Splits: {release.title}",
        Contract.contract_type == "SPLIT_SHEET",
    ).first()

    if standalone_contract:
        standalone_ca = db.query(ContractAsset).filter(
            ContractAsset.contract_id == standalone_contract.id,
            ContractAsset.asset_type == "RELEASE",
            ContractAsset.asset_id == release_id,
        ).first()
        if standalone_ca:
            standalone_splits = db.query(RightsSplit).filter(
                RightsSplit.contract_asset_id == standalone_ca.id
            ).all()
            for s in standalone_splits:
                if s.id in seen_ids:
                    continue
                seen_ids.add(s.id)
                if s.rights_holder_id:
                    holder = db.query(Creator).filter(Creator.id == s.rights_holder_id).first()
                    h_name = holder.display_name if holder else (s.rights_holder_name or "Unknown")
                else:
                    h_name = s.rights_holder_name or "Unknown"
                splits.append({
                    "id": s.id,
                    "contract_asset_id": s.contract_asset_id,
                    "rights_holder_id": s.rights_holder_id,
                    "rights_holder_name": h_name,
                    "rights_type": s.rights_type,
                    "share_percentage": s.share_percentage,
                    "role": s.role,
                    "notes": s.notes,
                    "contract_title": standalone_contract.title,
                    "contract_id": standalone_contract.id,
                    "is_standalone": True,
                })

    return {"splits": splits}


@router.post(
    "/release-splits/{release_id}",
    summary="Add a rights split to a release",
    description=(
        "Release counterpart of `POST /song-splits/{song_id}`. Adds a single "
        "RightsSplit row to the release's standalone SPLIT_SHEET, creating "
        "the contract container on first call. Enforces the per-rights-type "
        "100% cap and ensures a CreativeContact exists for the holder.\n\n"
        "**Path parameter:** `release_id` — Cadence Release ID.\n"
        "**Body (`SplitCreate`):** identical to the song endpoint.\n\n"
        "**Auth:** Bearer JWT. Caller must belong to the release's organization.\n\n"
        "**Response:** `{ id, rights_holder_name, rights_type, "
        "share_percentage, role, ipi, message }`."
    ),
)
def add_release_split(
    release_id: int,
    data: SplitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    if not data.rights_holder_id and not data.rights_holder_name:
        raise HTTPException(status_code=400, detail="Either rights_holder_id or rights_holder_name is required")

    allowed_rights_types = {"MASTER", "PUBLISHING", "PERFORMANCE", "MECHANICAL", "DISTRIBUTION", "SYNC", "OTHER"}
    if data.rights_type not in allowed_rights_types:
        raise HTTPException(status_code=400, detail=f"Invalid rights type. Must be one of: {', '.join(sorted(allowed_rights_types))}")

    if data.share_percentage <= 0 or data.share_percentage > 100:
        raise HTTPException(status_code=400, detail="Share percentage must be between 0.01 and 100")

    contract = db.query(Contract).filter(
        Contract.organization_id == release.organization_id,
        Contract.title == f"Release Splits: {release.title}",
        Contract.contract_type == "SPLIT_SHEET",
    ).first()

    if not contract:
        contract = Contract(
            organization_id=release.organization_id,
            title=f"Release Splits: {release.title}",
            contract_type="SPLIT_SHEET",
            status="ACTIVE",
            created_by_user_id=current_user.id,
        )
        db.add(contract)
        db.flush()

    ca = db.query(ContractAsset).filter(
        ContractAsset.contract_id == contract.id,
        ContractAsset.asset_type == "RELEASE",
        ContractAsset.asset_id == release_id,
    ).first()

    if not ca:
        ca = ContractAsset(
            contract_id=contract.id,
            asset_type="RELEASE",
            asset_id=release_id,
        )
        db.add(ca)
        db.flush()

    existing_total = db.query(func.coalesce(func.sum(RightsSplit.share_percentage), 0)).filter(
        RightsSplit.contract_asset_id == ca.id,
        RightsSplit.rights_type == data.rights_type,
    ).scalar()

    if existing_total + data.share_percentage > 100:
        raise HTTPException(
            status_code=400,
            detail=f"Total {data.rights_type} splits would exceed 100% (existing: {existing_total}%, new: {data.share_percentage}%)"
        )

    holder_name = data.rights_holder_name
    holder_ipi = data.ipi
    if data.rights_holder_id:
        holder = db.query(Creator).filter(
            Creator.id == data.rights_holder_id,
            Creator.organization_id == release.organization_id,
        ).first()
        if not holder:
            raise HTTPException(status_code=404, detail="Rights holder not found in this organization")
        holder_name = holder_name or holder.display_name
        if not holder_ipi:
            holder_ipi = holder.primary_ipi
    elif data.contact_id:
        contact = db.query(CreativeContact).filter(
            CreativeContact.id == data.contact_id,
            CreativeContact.organization_id == release.organization_id,
        ).first()
        if contact:
            holder_name = holder_name or contact.display_name
            if not holder_ipi:
                holder_ipi = contact.ipi

    if not data.rights_holder_id and not data.contact_id and holder_name:
        existing_contact = db.query(CreativeContact).filter(
            CreativeContact.organization_id == release.organization_id,
            func.lower(CreativeContact.display_name) == holder_name.lower(),
        ).first()
        if not existing_contact:
            new_contact = CreativeContact(
                organization_id=release.organization_id,
                display_name=holder_name,
                ipi=holder_ipi,
                pro=data.pro,
                roles=["Collaborator"],
            )
            db.add(new_contact)
            db.flush()

    split = RightsSplit(
        contract_asset_id=ca.id,
        rights_holder_id=data.rights_holder_id,
        rights_holder_name=holder_name,
        rights_type=data.rights_type,
        share_percentage=data.share_percentage,
        role=data.role,
        notes=data.notes,
    )
    db.add(split)
    db.commit()
    db.refresh(split)

    return {
        "id": split.id,
        "rights_holder_name": holder_name,
        "rights_type": split.rights_type,
        "share_percentage": split.share_percentage,
        "role": split.role,
        "ipi": holder_ipi,
        "message": "Split added successfully",
    }


@router.get(
    "/contracts/org/{org_id}",
    summary="List an organization's contracts",
    description=(
        "Returns the contract registry for the given organization, ordered by "
        "most recently created. Backs the org-level Contracts list view.\n\n"
        "**Path parameter:** `org_id` — Cadence Organization ID.\n"
        "**Optional query:** `status` — when provided, narrows the result to "
        "contracts whose `status` matches exactly (e.g. `ACTIVE`, `DRAFT`, "
        "`EXPIRED`).\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ contracts: [...], total: int }`. Each contract uses "
        "the same slim shape as `GET /contracts/song/{song_id}`."
    ),
)
def list_contracts(
    org_id: int,
    status: Optional[str] = None,
    contract_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(Contract).filter(Contract.organization_id == org_id)

    if status:
        query = query.filter(Contract.status == status)
    if contract_type:
        query = query.filter(Contract.contract_type == contract_type)

    contracts = query.order_by(Contract.created_at.desc()).all()
    return {"contracts": [_contract_to_dict(c, db) for c in contracts], "total": len(contracts)}


@router.post(
    "/contracts/parse-document",
    summary="Parse a contract upload into structured fields",
    description=(
        "Accepts a contract document (PDF / DOCX / TXT) as multipart upload "
        "and runs Cadence's contract parser to extract suggested fields the "
        "Create-Contract form can pre-fill (title, type, parties, dates, "
        "reference number, asset list).\n\n"
        "**Body (multipart):** `file` — the document, ≤ 10 MB.\n\n"
        "**Auth:** Bearer JWT. Read-only with respect to the database — "
        "nothing is persisted; the parsed payload is returned for the "
        "caller to inspect and POST back to `/contracts/org/{org_id}`.\n\n"
        "**Response:** the raw parser dict — typically "
        "`{ title, contract_type, reference_number, start_date, end_date, "
        "parties: [...], assets: [...], confidence: { ... } }`. 400 on "
        "unparsable input."
    ),
)
async def parse_contract_doc(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("pdf", "docx"):
        raise HTTPException(status_code=400, detail="Please upload a PDF or Word document (.pdf, .docx)")

    file_bytes = await file.read()
    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 20MB.")

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    caller_org_id = membership.organization_id if membership else None

    result = parse_contract_document(file_bytes, file.filename, org_id=caller_org_id)

    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Failed to parse document"))

    return result


@router.post(
    "/contracts/org/{org_id}",
    summary="Create a contract in an organization",
    description=(
        "Creates a Contract row, optionally seeded with parties and asset "
        "links in the same call. Use the parser endpoint first to draft the "
        "payload from an uploaded document.\n\n"
        "**Path parameter:** `org_id` — Cadence Organization ID.\n"
        "**Body (`ContractCreate`):** `title` (required), `contract_type`, "
        "`status`, `reference_number`, `start_date`, `end_date`, `notes`, "
        "`creator_id` (primary creator), `parties: [{party_role, party_name, "
        "creator_id?, contact_email?}]`, `assets: [{asset_type, asset_id}]`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** the full contract record (same shape as "
        "`GET /contracts/{contract_id}` with `include_details=true`)."
    ),
)
def create_contract(
    org_id: int,
    data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    contract = Contract(
        organization_id=org_id,
        title=data.title,
        contract_type=data.contract_type,
        payment_direction=data.payment_direction,
        status=data.status,
        reference_number=data.reference_number,
        start_date=data.start_date,
        end_date=data.end_date,
        territory=data.territory or [],
        advance_amount=data.advance_amount,
        advance_currency=data.advance_currency,
        notes=data.notes,
        terms_summary=data.terms_summary,
        creator_id=data.creator_id,
        created_by_user_id=current_user.id,
    )
    db.add(contract)
    db.flush()

    if data.parties:
        for p in data.parties:
            party = ContractParty(
                contract_id=contract.id,
                party_name=p.party_name,
                party_role=p.party_role,
                creator_id=p.creator_id,
                contact_email=p.contact_email,
                contact_info=p.contact_info,
            )
            db.add(party)

    db.commit()
    db.refresh(contract)
    return _contract_to_dict(contract, db)


@router.get(
    "/contracts/{contract_id}",
    summary="Get a contract with full details",
    description=(
        "Returns the full Contract record with parties, linked assets, "
        "rights splits, and document attachments. This is the source-of-"
        "truth fetch the Contract Detail page uses.\n\n"
        "**Path parameter:** `contract_id` — Contract row id.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contract's "
        "organization.\n\n"
        "**Response:** `{ id, title, contract_type, status, reference_number, "
        "start_date, end_date, notes, organization_id, creator_id, "
        "parties: [...], assets: [{id, asset_type, asset_id, asset_label, "
        "splits: [...]}], documents: [...], created_at, updated_at }`. "
        "404 if not found."
    ),
)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    verify_org_access(current_user, contract.organization_id, db)
    return _contract_to_dict(contract, db, include_details=True)


@router.put(
    "/contracts/{contract_id}",
    summary="Update a contract",
    description=(
        "Patches the top-level Contract fields. Parties, assets and splits "
        "have their own dedicated endpoints; this call does not touch them.\n\n"
        "**Path parameter:** `contract_id` — Contract row id.\n"
        "**Body (`ContractUpdate`):** any subset of `title`, `contract_type`, "
        "`status`, `reference_number`, `start_date`, `end_date`, `notes`, "
        "`creator_id`. Unspecified fields are left untouched.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contract's "
        "organization.\n\n"
        "**Response:** the updated contract record (same shape as "
        "`GET /contracts/{contract_id}`)."
    ),
)
def update_contract(
    contract_id: int,
    data: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    verify_org_access(current_user, contract.organization_id, db)

    for field, value in data.dict(exclude_unset=True).items():
        setattr(contract, field, value)

    db.commit()
    db.refresh(contract)
    return _contract_to_dict(contract, db)


@router.delete(
    "/contracts/{contract_id}",
    summary="Delete a contract",
    description=(
        "Hard-deletes the Contract along with its parties, asset links and "
        "RightsSplit rows (cascade). Cached publishing/master percentages on "
        "linked songs are not recomputed automatically — re-fetch them via "
        "the song split endpoint if needed.\n\n"
        "**Path parameter:** `contract_id` — Contract row id.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contract's "
        "organization.\n\n"
        "**Response:** `{ message: \"Contract deleted successfully\" }`. "
        "404 if the contract is missing."
    ),
)
def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    verify_org_access(current_user, contract.organization_id, db)

    for ca in contract.assets:
        db.query(RightsSplit).filter(RightsSplit.contract_asset_id == ca.id).delete()

    db.delete(contract)
    db.commit()
    return {"message": "Contract deleted successfully"}


@router.post(
    "/contracts/{contract_id}/parties",
    summary="Attach a party to a contract",
    description=(
        "Adds a ContractParty row to an existing contract.\n\n"
        "**Path parameter:** `contract_id` — Contract row id.\n"
        "**Body (`PartyCreate`):** `party_role` (e.g. `WRITER`, `PUBLISHER`, "
        "`LICENSOR`, `LICENSEE`), `party_name` (required when no `creator_id`), "
        "`creator_id` (optional Creator FK), `contact_email` (optional).\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contract's "
        "organization.\n\n"
        "**Response:** `{ id, party_role, party_name, creator_id, "
        "contact_email, message }`."
    ),
)
def add_party(
    contract_id: int,
    data: PartyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    verify_org_access(current_user, contract.organization_id, db)

    party = ContractParty(
        contract_id=contract_id,
        party_name=data.party_name,
        party_role=data.party_role,
        creator_id=data.creator_id,
        contact_email=data.contact_email,
        contact_info=data.contact_info,
    )
    db.add(party)
    db.commit()
    db.refresh(party)
    return {
        "id": party.id,
        "party_name": party.party_name,
        "party_role": party.party_role,
        "creator_id": party.creator_id,
        "contact_email": party.contact_email,
        "message": "Party added successfully",
    }


@router.delete(
    "/contracts/{contract_id}/parties/{party_id}",
    summary="Remove a party from a contract",
    description=(
        "Detaches and deletes a single ContractParty row from the contract. "
        "Does not affect the underlying Creator or CreativeContact record.\n\n"
        "**Path parameters:** `contract_id`, `party_id`.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contract's "
        "organization.\n\n"
        "**Response:** `{ message: \"Party removed successfully\" }`. "
        "404 if the party doesn't belong to the contract."
    ),
)
def remove_party(
    contract_id: int,
    party_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    verify_org_access(current_user, contract.organization_id, db)

    party = db.query(ContractParty).filter(
        ContractParty.id == party_id,
        ContractParty.contract_id == contract_id,
    ).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    db.delete(party)
    db.commit()
    return {"message": "Party removed successfully"}


@router.post(
    "/contracts/{contract_id}/assets",
    summary="Link an asset (song / release / work) to a contract",
    description=(
        "Creates a ContractAsset row that pins a Song, Release or Work to "
        "the contract. Idempotent: a duplicate (`asset_type, asset_id`) pair "
        "returns the existing row instead of erroring.\n\n"
        "**Path parameter:** `contract_id` — Contract row id.\n"
        "**Body (`AssetLink`):** `asset_type` (one of `SONG`, `RELEASE`, "
        "`WORK`), `asset_id` (target row id in the matching table).\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contract's "
        "organization.\n\n"
        "**Response:** `{ id, asset_type, asset_id, message }`."
    ),
)
def link_asset(
    contract_id: int,
    data: AssetLink,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    verify_org_access(current_user, contract.organization_id, db)

    if data.asset_type not in ("SONG", "WORK"):
        raise HTTPException(status_code=400, detail="asset_type must be SONG or WORK")

    if data.asset_type == "SONG":
        asset = db.query(Song).filter(Song.id == data.asset_id, Song.organization_id == contract.organization_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Song not found in this organization")
    else:
        asset = db.query(Work).filter(Work.id == data.asset_id, Work.organization_id == contract.organization_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Work not found in this organization")

    existing = db.query(ContractAsset).filter(
        ContractAsset.contract_id == contract_id,
        ContractAsset.asset_type == data.asset_type,
        ContractAsset.asset_id == data.asset_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Asset already linked to this contract")

    ca = ContractAsset(
        contract_id=contract_id,
        asset_type=data.asset_type,
        asset_id=data.asset_id,
    )
    db.add(ca)
    db.commit()
    db.refresh(ca)
    return {"id": ca.id, "asset_type": ca.asset_type, "asset_id": ca.asset_id, "message": "Asset linked successfully"}


@router.delete(
    "/contracts/{contract_id}/assets/{asset_id}",
    summary="Unlink an asset from a contract",
    description=(
        "Deletes a ContractAsset row by its own primary key (the `asset_id` "
        "in the path is the ContractAsset.id, **not** the Song / Release / "
        "Work id). Cascades to the RightsSplit rows underneath it.\n\n"
        "**Path parameters:** `contract_id`, `asset_id` (ContractAsset id).\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contract's "
        "organization.\n\n"
        "**Response:** `{ message: \"Asset unlinked successfully\" }`."
    ),
)
def unlink_asset(
    contract_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    verify_org_access(current_user, contract.organization_id, db)

    ca = db.query(ContractAsset).filter(
        ContractAsset.id == asset_id,
        ContractAsset.contract_id == contract_id,
    ).first()
    if not ca:
        raise HTTPException(status_code=404, detail="Contract asset not found")

    db.query(RightsSplit).filter(RightsSplit.contract_asset_id == ca.id).delete()
    db.delete(ca)
    db.commit()
    return {"message": "Asset unlinked successfully"}


@router.post(
    "/contracts/{contract_id}/assets/{asset_id}/splits",
    summary="Add a rights split under a specific contract asset",
    description=(
        "Lower-level than the song/release split endpoints: writes a "
        "RightsSplit directly against an existing ContractAsset, bypassing "
        "the auto-created split-sheet logic. Use this when entering splits "
        "from a real source contract (publishing deal, recording agreement).\n\n"
        "**Path parameters:** `contract_id`, `asset_id` (ContractAsset id).\n"
        "**Body (`SplitCreate`):** same shape as the song-split endpoint. "
        "The 100% per-rights-type cap is still enforced.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contract's "
        "organization.\n\n"
        "**Response:** `{ id, rights_holder_id, rights_type, "
        "share_percentage, message }`."
    ),
)
def add_split(
    contract_id: int,
    asset_id: int,
    data: SplitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    verify_org_access(current_user, contract.organization_id, db)

    ca = db.query(ContractAsset).filter(
        ContractAsset.id == asset_id,
        ContractAsset.contract_id == contract_id,
    ).first()
    if not ca:
        raise HTTPException(status_code=404, detail="Contract asset not found")

    holder_name = data.rights_holder_name
    if data.rights_holder_id:
        holder = db.query(Creator).filter(
            Creator.id == data.rights_holder_id,
            Creator.organization_id == contract.organization_id,
        ).first()
        if not holder:
            raise HTTPException(status_code=404, detail="Rights holder not found in this organization")
        holder_name = holder_name or holder.display_name
    elif not data.rights_holder_name:
        raise HTTPException(status_code=400, detail="Either rights_holder_id or rights_holder_name is required")

    if data.share_percentage < 0 or data.share_percentage > 100:
        raise HTTPException(status_code=400, detail="share_percentage must be between 0 and 100")

    existing_total = db.query(func.coalesce(func.sum(RightsSplit.share_percentage), 0.0)).filter(
        RightsSplit.contract_asset_id == ca.id,
        RightsSplit.rights_type == data.rights_type,
    ).scalar()

    if existing_total + data.share_percentage > 100.0:
        raise HTTPException(
            status_code=400,
            detail=f"Total splits for {data.rights_type} would exceed 100% (current: {existing_total}%, adding: {data.share_percentage}%)"
        )

    split = RightsSplit(
        contract_asset_id=ca.id,
        rights_holder_id=data.rights_holder_id,
        rights_holder_name=holder_name,
        rights_type=data.rights_type,
        share_percentage=data.share_percentage,
        role=data.role,
        notes=data.notes,
    )
    db.add(split)
    db.flush()

    if ca.asset_type == "SONG":
        from ..utils.edit_history import record_split_change
        record_split_change(db, ca.asset_id, contract.organization_id, current_user.id, holder_name, data.rights_type, None, data.share_percentage, notes=data.notes)
        _sync_song_pub_percentage(db, ca.asset_id)
        if data.rights_holder_id and data.rights_type in ("PUBLISHING", "MASTER"):
            _sync_splits_to_credits(db, ca.asset_id, data.rights_holder_id)

    db.commit()
    db.refresh(split)
    return {
        "id": split.id,
        "rights_holder_id": split.rights_holder_id,
        "rights_type": split.rights_type,
        "share_percentage": split.share_percentage,
        "message": "Split added successfully",
    }


@router.put(
    "/splits/{split_id}",
    summary="Update a rights split",
    description=(
        "Patches share/role/notes/holder on a RightsSplit row. If the split "
        "belongs to a song's contract asset, the song's cached "
        "publishing/master percentages and the matching SongCredit are "
        "re-synced. Edit history is recorded.\n\n"
        "**Path parameter:** `split_id` — RightsSplit row id.\n"
        "**Body (`SplitUpdate`):** any subset of `share_percentage`, `role`, "
        "`notes`, `rights_holder_id`, `rights_holder_name`, `rights_type`. "
        "The 100% per-rights-type cap is rechecked.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contract's "
        "organization.\n\n"
        "**Response:** `{ id, rights_type, share_percentage, message }`."
    ),
)
def update_split(
    split_id: int,
    data: SplitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    split = db.query(RightsSplit).filter(RightsSplit.id == split_id).first()
    if not split:
        raise HTTPException(status_code=404, detail="Split not found")

    ca = db.query(ContractAsset).filter(ContractAsset.id == split.contract_asset_id).first()
    if not ca:
        raise HTTPException(status_code=404, detail="Contract asset not found")

    contract = db.query(Contract).filter(Contract.id == ca.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    verify_org_access(current_user, contract.organization_id, db)

    new_rights_type = data.rights_type if data.rights_type is not None else split.rights_type
    new_percentage = data.share_percentage if data.share_percentage is not None else split.share_percentage

    if new_percentage < 0 or new_percentage > 100:
        raise HTTPException(status_code=400, detail="share_percentage must be between 0 and 100")

    existing_total = db.query(func.coalesce(func.sum(RightsSplit.share_percentage), 0.0)).filter(
        RightsSplit.contract_asset_id == ca.id,
        RightsSplit.rights_type == new_rights_type,
        RightsSplit.id != split_id,
    ).scalar()

    if existing_total + new_percentage > 100.0:
        raise HTTPException(
            status_code=400,
            detail=f"Total splits for {new_rights_type} would exceed 100% (others: {existing_total}%, new: {new_percentage}%)"
        )

    old_pct = split.share_percentage
    old_rights_type = split.rights_type
    holder_name = split.rights_holder_name or str(split.rights_holder_id or "unknown")

    if data.rights_type is not None:
        split.rights_type = data.rights_type
    if data.share_percentage is not None:
        split.share_percentage = data.share_percentage
    if data.rights_holder_name is not None:
        split.rights_holder_name = data.rights_holder_name
    if data.role is not None:
        split.role = data.role
    if data.notes is not None:
        split.notes = data.notes

    db.flush()
    if ca.asset_type == "SONG":
        if old_pct != split.share_percentage or old_rights_type != split.rights_type:
            from ..utils.edit_history import record_split_change
            record_split_change(db, ca.asset_id, contract.organization_id, current_user.id, holder_name, split.rights_type, old_pct, split.share_percentage, notes=data.notes)
        _sync_song_pub_percentage(db, ca.asset_id)
        if split.rights_holder_id:
            _sync_splits_to_credits(db, ca.asset_id, split.rights_holder_id)

    db.commit()
    db.refresh(split)
    return {
        "id": split.id,
        "rights_type": split.rights_type,
        "share_percentage": split.share_percentage,
        "message": "Split updated successfully",
    }


@router.delete(
    "/splits/{split_id}",
    summary="Delete a contract-asset rights split",
    description=(
        "Generic counterpart to `DELETE /song-splits/{split_id}` for splits "
        "that don't live in the auto-created song split sheet. Cascade-safe "
        "and re-syncs cached song percentages / SongCredits when applicable.\n\n"
        "**Path parameter:** `split_id` — RightsSplit row id.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contract's "
        "organization.\n\n"
        "**Response:** `{ message: \"Split deleted successfully\" }`."
    ),
)
def delete_split(
    split_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    split = db.query(RightsSplit).filter(RightsSplit.id == split_id).first()
    if not split:
        raise HTTPException(status_code=404, detail="Split not found")

    ca = db.query(ContractAsset).filter(ContractAsset.id == split.contract_asset_id).first()
    if not ca:
        raise HTTPException(status_code=404, detail="Contract asset not found")

    contract = db.query(Contract).filter(Contract.id == ca.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    verify_org_access(current_user, contract.organization_id, db)

    asset_type = ca.asset_type
    asset_id = ca.asset_id
    holder_id = split.rights_holder_id
    old_pct = split.share_percentage
    holder_name = split.rights_holder_name or str(holder_id or "unknown")
    rights_type = split.rights_type

    if asset_type == "SONG":
        from ..utils.edit_history import record_split_change
        record_split_change(db, asset_id, contract.organization_id, current_user.id, holder_name, rights_type, old_pct, None)

    db.delete(split)
    db.flush()
    if asset_type == "SONG":
        _sync_song_pub_percentage(db, asset_id)
        if holder_id:
            _sync_splits_to_credits(db, asset_id, holder_id)
    db.commit()
    return {"message": "Split removed successfully"}


@router.get(
    "/asset/{org_id}",
    summary="Look up the rights stack for any asset",
    description=(
        "Generic asset-keyed view: given an organization plus an "
        "(`asset_type`, `asset_id`) pair, returns every contract that "
        "touches the asset together with the rights splits attached to it. "
        "Used by song / release / work detail pages to render a unified "
        "Rights tab.\n\n"
        "**Path parameter:** `org_id` — Cadence Organization ID.\n"
        "**Required query:** `asset_type` (`SONG` / `RELEASE` / `WORK`), "
        "`asset_id` (target row id).\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ asset_type, asset_id, contracts: [{contract_id, "
        "title, contract_type, status, splits: [...]}] }`."
    ),
)
def get_asset_rights(
    org_id: int,
    asset_type: str = Query(...),
    asset_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    if asset_type not in ("SONG", "WORK"):
        raise HTTPException(status_code=400, detail="asset_type must be SONG or WORK")

    contract_assets = db.query(ContractAsset).filter(
        ContractAsset.asset_type == asset_type,
        ContractAsset.asset_id == asset_id,
    ).all()

    results = []
    for ca in contract_assets:
        contract = db.query(Contract).filter(
            Contract.id == ca.contract_id,
            Contract.organization_id == org_id,
        ).first()
        if not contract:
            continue

        splits = db.query(RightsSplit).filter(RightsSplit.contract_asset_id == ca.id).all()
        splits_data = []
        for s in splits:
            if s.rights_holder_id:
                holder = db.query(Creator).filter(Creator.id == s.rights_holder_id).first()
                h_name = holder.display_name if holder else (s.rights_holder_name or "Unknown")
            else:
                h_name = s.rights_holder_name or "Unknown"
            splits_data.append({
                "id": s.id,
                "rights_holder_id": s.rights_holder_id,
                "rights_holder_name": h_name,
                "rights_type": s.rights_type,
                "share_percentage": s.share_percentage,
                "role": s.role,
                "notes": s.notes,
            })

        parties = []
        for p in contract.parties:
            parties.append({
                "id": p.id,
                "party_name": p.party_name,
                "party_role": p.party_role,
                "creator_id": p.creator_id,
            })

        results.append({
            "contract_id": contract.id,
            "contract_title": contract.title,
            "contract_type": contract.contract_type,
            "contract_status": contract.status,
            "contract_asset_id": ca.id,
            "parties": parties,
            "splits": splits_data,
        })

    return {"asset_type": asset_type, "asset_id": asset_id, "contracts": results}


@router.get(
    "/holder/{org_id}/{creator_id}",
    summary="List a rights holder's contracts and shares",
    description=(
        "Holder-keyed inverse of `GET /asset/{org_id}`. Returns every "
        "contract in the org where the creator appears as a `rights_holder_id` "
        "on a RightsSplit row, grouped under their parent contracts.\n\n"
        "**Path parameters:** `org_id` — Organization ID; `creator_id` — "
        "Creator ID acting as rights holder.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the organization.\n\n"
        "**Response:** `{ creator_id, creator_name, contracts: [{contract_id, "
        "title, contract_type, status, splits: [...]}] }`."
    ),
)
def get_holder_rights(
    org_id: int,
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    creator = db.query(Creator).filter(
        Creator.id == creator_id,
        Creator.organization_id == org_id,
    ).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found in this organization")

    splits = db.query(RightsSplit).filter(RightsSplit.rights_holder_id == creator_id).all()

    contracts_map = {}
    for s in splits:
        ca = db.query(ContractAsset).filter(ContractAsset.id == s.contract_asset_id).first()
        if not ca:
            continue
        contract = db.query(Contract).filter(
            Contract.id == ca.contract_id,
            Contract.organization_id == org_id,
        ).first()
        if not contract:
            continue

        if contract.id not in contracts_map:
            contracts_map[contract.id] = {
                "contract_id": contract.id,
                "contract_title": contract.title,
                "contract_type": contract.contract_type,
                "contract_status": contract.status,
                "assets": [],
            }

        asset_title = None
        if ca.asset_type == "SONG":
            song = db.query(Song).filter(Song.id == ca.asset_id).first()
            asset_title = song.title if song else "Unknown Song"
        elif ca.asset_type == "WORK":
            work = db.query(Work).filter(Work.id == ca.asset_id).first()
            asset_title = work.title if work else "Unknown Work"

        contracts_map[contract.id]["assets"].append({
            "contract_asset_id": ca.id,
            "asset_type": ca.asset_type,
            "asset_id": ca.asset_id,
            "asset_title": asset_title,
            "rights_type": s.rights_type,
            "share_percentage": s.share_percentage,
            "split_id": s.id,
        })

    return {
        "creator_id": creator_id,
        "creator_name": creator.display_name,
        "contracts": list(contracts_map.values()),
    }


@router.get(
    "/contracts/{contract_id}/split-sheet",
    summary="Export a contract's split sheet as CSV",
    description=(
        "Streams a CSV split sheet for the contract: one row per "
        "(asset, rights_holder, rights_type) tuple with `share_percentage`, "
        "`role`, IPI/PRO if known, and totals per rights type at the bottom. "
        "Filename is `<contract-title>-split-sheet.csv`.\n\n"
        "**Path parameter:** `contract_id` — Contract row id.\n"
        "**Optional query:** `split_type` — `publishing`, `master`, or "
        "`both` (default). Filters which rights types are included.\n\n"
        "**Auth:** Bearer JWT. Caller must be a member of the contract's "
        "organization.\n\n"
        "**Response:** `text/csv` streaming download."
    ),
)
def export_split_sheet(
    contract_id: int,
    split_type: str = Query(default="both"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import os

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    verify_org_access(current_user, contract.organization_id, db)

    contract_assets = db.query(ContractAsset).filter(ContractAsset.contract_id == contract.id).all()

    publishing_types = ("PUBLISHING", "PERFORMANCE", "MECHANICAL")
    master_types = ("MASTER", "DISTRIBUTION")

    assets_data = []
    all_holders = {}
    for ca in contract_assets:
        asset_title = None
        asset_isrc = None
        asset_artist = None
        if ca.asset_type == "SONG":
            song = db.query(Song).filter(Song.id == ca.asset_id).first()
            if song:
                asset_title = song.title
                asset_isrc = song.isrc
                asset_artist = song.primary_artist
        elif ca.asset_type == "WORK":
            work = db.query(Work).filter(Work.id == ca.asset_id).first()
            if work:
                asset_title = work.title

        splits = db.query(RightsSplit).filter(RightsSplit.contract_asset_id == ca.id).all()
        filtered_splits = []
        for s in splits:
            if split_type == "publishing" and s.rights_type not in publishing_types:
                continue
            if split_type == "master" and s.rights_type not in master_types:
                continue
            holder = None
            party = None
            if s.rights_holder_id:
                holder = db.query(Creator).filter(Creator.id == s.rights_holder_id).first()
                party = db.query(ContractParty).filter(
                    ContractParty.contract_id == contract.id,
                    ContractParty.creator_id == s.rights_holder_id,
                ).first()
            filtered_splits.append({
                "holder": holder,
                "party": party,
                "split": s,
            })
            if holder and holder.id not in all_holders:
                all_holders[holder.id] = holder

        assets_data.append({
            "asset_type": ca.asset_type,
            "asset_title": asset_title or "Untitled",
            "asset_isrc": asset_isrc,
            "asset_artist": asset_artist,
            "splits": filtered_splits,
        })

    sage = colors.HexColor("#5B8A72")
    sage_light = colors.HexColor("#E8F0EB")
    dark_text = colors.HexColor("#3D4A44")
    muted = colors.HexColor("#7A8580")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            topMargin=0.5*inch, bottomMargin=0.5*inch,
                            leftMargin=0.6*inch, rightMargin=0.6*inch)

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('SSTitle', parent=styles['Title'], fontSize=22, textColor=dark_text, spaceAfter=4)
    style_subtitle = ParagraphStyle('SSSub', parent=styles['Normal'], fontSize=11, textColor=muted, spaceAfter=12)
    style_heading = ParagraphStyle('SSHead', parent=styles['Heading2'], fontSize=14, textColor=sage, spaceBefore=16, spaceAfter=8)
    style_normal = ParagraphStyle('SSNorm', parent=styles['Normal'], fontSize=10, textColor=dark_text, leading=14)
    style_small = ParagraphStyle('SSSmall', parent=styles['Normal'], fontSize=8, textColor=muted, leading=11)
    style_center = ParagraphStyle('SSCenter', parent=styles['Normal'], fontSize=8, textColor=muted, alignment=TA_CENTER)
    style_agreement = ParagraphStyle('SSAgree', parent=styles['Normal'], fontSize=10, textColor=dark_text, leading=14, spaceBefore=16, spaceAfter=12)

    elements = []

    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'cadence-logo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=2.0*inch, height=1.125*inch)
        logo.hAlign = 'LEFT'
        elements.append(logo)
        elements.append(Spacer(1, 6))

    elements.append(Paragraph("SPLIT SHEET", style_title))
    if split_type == "publishing":
        subtitle_text = "Publishing Rights Only"
    elif split_type == "master":
        subtitle_text = "Master Rights Only"
    else:
        subtitle_text = "Publishing & Master Rights"
    elements.append(Paragraph(subtitle_text, style_subtitle))

    elements.append(HRFlowable(width="100%", thickness=1, color=sage_light, spaceAfter=12))

    elements.append(Paragraph("Contract Information", style_heading))
    territory_str = ", ".join(contract.territory) if contract.territory else "—"
    meta_data = [
        ["Title", contract.title or "—", "Reference #", contract.reference_number or "—"],
        ["Type", contract.contract_type or "—", "Status", contract.status or "—"],
        ["Territory", territory_str, "Start Date", contract.start_date.strftime("%B %d, %Y") if contract.start_date else "—"],
        ["", "", "End Date", contract.end_date.strftime("%B %d, %Y") if contract.end_date else "—"],
    ]
    meta_table = Table(meta_data, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
    meta_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), muted),
        ('TEXTCOLOR', (2, 0), (2, -1), muted),
        ('TEXTCOLOR', (1, 0), (1, -1), dark_text),
        ('TEXTCOLOR', (3, 0), (3, -1), dark_text),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 8))

    for asset in assets_data:
        elements.append(Paragraph(asset["asset_title"], style_heading))
        detail_parts = []
        if asset["asset_isrc"]:
            detail_parts.append(f"ISRC: {asset['asset_isrc']}")
        if asset["asset_artist"]:
            detail_parts.append(f"Artist: {asset['asset_artist']}")
        if detail_parts:
            elements.append(Paragraph(" · ".join(detail_parts), style_small))
            elements.append(Spacer(1, 6))

        header_row = ["Rights Holder", "Role", "PRO", "IPI #", "Publisher", "Rights Type", "Share %"]
        table_data = [header_row]
        totals_by_type = {}
        for entry in asset["splits"]:
            holder = entry["holder"]
            party = entry["party"]
            s = entry["split"]
            holder_name = holder.display_name if holder else (s.rights_holder_name or "Unknown")
            party_role = party.party_role if party else "—"
            pro = (holder.primary_pro if holder and holder.primary_pro else "—")
            ipi = (holder.primary_ipi if holder and holder.primary_ipi else "—")
            publisher = (holder.publisher_name if holder and holder.publisher_name else "—")
            rights_type = s.rights_type
            share = f"{s.share_percentage}%"
            table_data.append([holder_name, party_role, pro, ipi, publisher, rights_type, share])
            if rights_type not in totals_by_type:
                totals_by_type[rights_type] = 0.0
            totals_by_type[rights_type] += s.share_percentage

        for rt_name, rt_total in totals_by_type.items():
            table_data.append(["", "", "", "", "Total", rt_name, f"{rt_total}%"])

        col_widths = [1.3*inch, 0.8*inch, 0.7*inch, 0.7*inch, 1.0*inch, 1.0*inch, 0.7*inch]
        split_table = Table(table_data, colWidths=col_widths)
        split_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), sage),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, sage_light),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, sage_light]),
            ('FONTNAME', (0, -len(totals_by_type)), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -len(totals_by_type)), (-1, -1), sage_light),
            ('TEXTCOLOR', (0, 1), (-1, -1), dark_text),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ]))
        elements.append(split_table)
        elements.append(Spacer(1, 12))

    elements.append(HRFlowable(width="100%", thickness=1, color=sage_light, spaceAfter=12))
    elements.append(Paragraph("Agreement", style_heading))
    elements.append(Paragraph(
        "By signing below, all parties acknowledge and agree to the ownership splits documented above.",
        style_agreement,
    ))
    elements.append(Spacer(1, 12))

    all_external_names = set()
    for asset in assets_data:
        for entry in asset["splits"]:
            if not entry["holder"] and entry["split"].rights_holder_name:
                all_external_names.add(entry["split"].rights_holder_name)

    signer_names = [h.display_name for h in all_holders.values()] + list(all_external_names)
    sig_rows = []
    for i in range(0, len(signer_names), 2):
        row = []
        for j in range(2):
            if i + j < len(signer_names):
                name = signer_names[i + j]
                sig_block = (
                    f"<b>{name}</b><br/><br/>"
                    f"Name: ______________________________<br/><br/>"
                    f"Signature: __________________________<br/><br/>"
                    f"Date: ______________________________"
                )
                row.append(Paragraph(sig_block, style_normal))
            else:
                row.append("")
        sig_rows.append(row)

    if sig_rows:
        sig_table = Table(sig_rows, colWidths=[3.3*inch, 3.3*inch])
        sig_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(sig_table)

    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=sage_light, spaceAfter=8))
    elements.append(Paragraph(
        f"Generated by Cadence Catalog Intelligence · {datetime.utcnow().strftime('%B %d, %Y')}",
        style_center,
    ))

    doc.build(elements)
    buffer.seek(0)

    safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in (contract.title or "Untitled")).strip().replace(" ", "_")
    filename = f"Split_Sheet_{safe_title}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
