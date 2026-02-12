from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
import io
from ..models import (
    get_db, Contract, ContractParty, ContractAsset, ContractDocument, RightsSplit,
    Song, Work, Creator, OrganizationMember, User
)
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/rights", tags=["rights-management"])


def verify_org_access(user: User, org_id: int, db: Session):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
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
    notes: Optional[str] = None


class SplitUpdate(BaseModel):
    rights_type: Optional[str] = None
    share_percentage: Optional[float] = None
    rights_holder_name: Optional[str] = None
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
            if ca.asset_type == "SONG":
                song = db.query(Song).filter(Song.id == ca.asset_id).first()
                asset_title = song.title if song else "Unknown Song"
            elif ca.asset_type == "WORK":
                work = db.query(Work).filter(Work.id == ca.asset_id).first()
                asset_title = work.title if work else "Unknown Work"

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
                    "notes": s.notes,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                })

            assets_data.append({
                "id": ca.id,
                "asset_type": ca.asset_type,
                "asset_id": ca.asset_id,
                "asset_title": asset_title,
                "splits": splits_data,
                "created_at": ca.created_at.isoformat() if ca.created_at else None,
            })

        result["assets"] = assets_data

    return result


@router.get("/contracts/creator/{creator_id}")
def list_contracts_by_creator(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    verify_org_access(current_user, creator.organization_id, db)

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


@router.get("/contracts/song/{song_id}")
def get_contracts_for_song(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    verify_org_access(current_user, song.organization_id, db)

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


@router.get("/song-splits/{song_id}")
def get_song_splits(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    verify_org_access(current_user, song.organization_id, db)

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
                    "notes": s.notes,
                    "contract_title": standalone_contract.title,
                    "contract_id": standalone_contract.id,
                    "is_standalone": True,
                })

    return {"splits": splits}


@router.post("/song-splits/{song_id}")
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
    if data.rights_holder_id:
        holder = db.query(Creator).filter(
            Creator.id == data.rights_holder_id,
            Creator.organization_id == song.organization_id,
        ).first()
        if not holder:
            raise HTTPException(status_code=404, detail="Rights holder not found in this organization")
        holder_name = holder_name or holder.display_name

    split = RightsSplit(
        contract_asset_id=ca.id,
        rights_holder_id=data.rights_holder_id,
        rights_holder_name=holder_name,
        rights_type=data.rights_type,
        share_percentage=data.share_percentage,
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
        "message": "Split added successfully",
    }


@router.delete("/song-splits/{split_id}")
def delete_song_split(
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
    if contract:
        verify_org_access(current_user, contract.organization_id, db)

    db.delete(split)
    db.commit()
    return {"message": "Split deleted successfully"}


@router.get("/contracts/org/{org_id}")
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


@router.post("/contracts/org/{org_id}")
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


@router.get("/contracts/{contract_id}")
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


@router.put("/contracts/{contract_id}")
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


@router.delete("/contracts/{contract_id}")
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


@router.post("/contracts/{contract_id}/parties")
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


@router.delete("/contracts/{contract_id}/parties/{party_id}")
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


@router.post("/contracts/{contract_id}/assets")
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


@router.delete("/contracts/{contract_id}/assets/{asset_id}")
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


@router.post("/contracts/{contract_id}/assets/{asset_id}/splits")
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
        notes=data.notes,
    )
    db.add(split)
    db.commit()
    db.refresh(split)
    return {
        "id": split.id,
        "rights_holder_id": split.rights_holder_id,
        "rights_type": split.rights_type,
        "share_percentage": split.share_percentage,
        "message": "Split added successfully",
    }


@router.put("/splits/{split_id}")
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

    if data.rights_type is not None:
        split.rights_type = data.rights_type
    if data.share_percentage is not None:
        split.share_percentage = data.share_percentage
    if data.rights_holder_name is not None:
        split.rights_holder_name = data.rights_holder_name
    if data.notes is not None:
        split.notes = data.notes

    db.commit()
    db.refresh(split)
    return {
        "id": split.id,
        "rights_type": split.rights_type,
        "share_percentage": split.share_percentage,
        "message": "Split updated successfully",
    }


@router.delete("/splits/{split_id}")
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

    db.delete(split)
    db.commit()
    return {"message": "Split removed successfully"}


@router.get("/asset/{org_id}")
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


@router.get("/holder/{org_id}/{creator_id}")
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


@router.get("/contracts/{contract_id}/split-sheet")
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

    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'frontend', 'public', 'rythm-logo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.2*inch, height=1.2*inch)
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
        f"Generated by Rythm Catalog Intelligence · {datetime.utcnow().strftime('%B %d, %Y')}",
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
