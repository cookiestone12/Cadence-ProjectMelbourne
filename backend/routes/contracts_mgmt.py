from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
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
    status: str = "DRAFT"
    reference_number: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    territory: Optional[List[str]] = []
    advance_amount: Optional[float] = 0.0
    advance_currency: str = "USD"
    notes: Optional[str] = None
    terms_summary: Optional[str] = None
    parties: Optional[List[PartyCreate]] = []


class ContractUpdate(BaseModel):
    title: Optional[str] = None
    contract_type: Optional[str] = None
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


class AssetLink(BaseModel):
    asset_type: str
    asset_id: int


class SplitCreate(BaseModel):
    rights_holder_id: int
    rights_type: str = "MASTER"
    share_percentage: float
    notes: Optional[str] = None


class SplitUpdate(BaseModel):
    rights_type: Optional[str] = None
    share_percentage: Optional[float] = None
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

    result = {
        "id": contract.id,
        "organization_id": contract.organization_id,
        "title": contract.title,
        "contract_type": contract.contract_type,
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
                holder = db.query(Creator).filter(Creator.id == s.rights_holder_id).first()
                splits_data.append({
                    "id": s.id,
                    "rights_holder_id": s.rights_holder_id,
                    "rights_holder_name": holder.display_name if holder else "Unknown",
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
        status=data.status,
        reference_number=data.reference_number,
        start_date=data.start_date,
        end_date=data.end_date,
        territory=data.territory or [],
        advance_amount=data.advance_amount,
        advance_currency=data.advance_currency,
        notes=data.notes,
        terms_summary=data.terms_summary,
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

    holder = db.query(Creator).filter(
        Creator.id == data.rights_holder_id,
        Creator.organization_id == contract.organization_id,
    ).first()
    if not holder:
        raise HTTPException(status_code=404, detail="Rights holder not found in this organization")

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
            holder = db.query(Creator).filter(Creator.id == s.rights_holder_id).first()
            splits_data.append({
                "id": s.id,
                "rights_holder_id": s.rights_holder_id,
                "rights_holder_name": holder.display_name if holder else "Unknown",
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
