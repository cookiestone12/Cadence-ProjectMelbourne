from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from ..models import (
    ActionItem, Contract, Release, RoyaltyStatement, RoyaltyTransaction,
    Placement, Song, Work
)


def generate_cross_module_tasks(db: Session, org_id: int, user_id: int) -> int:
    created_count = 0
    now = datetime.utcnow()

    existing_actions = db.query(ActionItem).filter(
        ActionItem.organization_id == org_id,
        ActionItem.status != "COMPLETED",
        ActionItem.is_auto_generated == True
    ).all()
    existing_keys = set()
    for a in existing_actions:
        key = (a.action_type, a.contract_id, a.release_id, a.placement_id, a.song_id, a.work_id)
        existing_keys.add(key)

    contracts = db.query(Contract).filter(
        Contract.organization_id == org_id,
        Contract.status == "ACTIVE",
        Contract.end_date.isnot(None),
        Contract.end_date <= (now + timedelta(days=30)).date()
    ).all()

    for contract in contracts:
        key = ("CONTRACT_EXPIRING", contract.id, None, None, None, None)
        if key not in existing_keys:
            days_left = (contract.end_date - now.date()).days
            action = ActionItem(
                organization_id=org_id,
                contract_id=contract.id,
                entity_type="contract",
                entity_label=contract.title,
                action_type="CONTRACT_EXPIRING",
                title=f"Contract \"{contract.title}\" expires in {days_left} days",
                description=f"Review and decide on renewal for contract ending {contract.end_date}.",
                priority=1 if days_left <= 7 else 2,
                deadline=datetime.combine(contract.end_date, datetime.min.time()),
                is_auto_generated=True,
                created_by_user_id=user_id,
            )
            db.add(action)
            created_count += 1

    releases = db.query(Release).filter(
        Release.organization_id == org_id,
        Release.status.in_(["DRAFT", "READY"])
    ).all()

    for release in releases:
        missing = []
        if not release.upc:
            missing.append("UPC")
        if not release.primary_artist:
            missing.append("Primary Artist")
        if not release.release_date:
            missing.append("Release Date")
        if not release.label:
            missing.append("Label")
        if not release.genre:
            missing.append("Genre")
        if not release.copyright_line:
            missing.append("Copyright Line")

        if missing:
            key = ("RELEASE_INCOMPLETE", None, release.id, None, None, None)
            if key not in existing_keys:
                action = ActionItem(
                    organization_id=org_id,
                    release_id=release.id,
                    entity_type="release",
                    entity_label=release.title,
                    action_type="RELEASE_INCOMPLETE",
                    title=f"Release \"{release.title}\" missing: {', '.join(missing[:3])}",
                    description=f"Complete missing metadata before submission: {', '.join(missing)}",
                    priority=2,
                    is_auto_generated=True,
                    created_by_user_id=user_id,
                )
                db.add(action)
                created_count += 1

    try:
        unmatched_count = db.query(func.count(RoyaltyTransaction.id)).filter(
            RoyaltyTransaction.organization_id == org_id,
            RoyaltyTransaction.match_status == "UNMATCHED"
        ).scalar() or 0

        if unmatched_count > 0:
            key = ("UNMATCHED_ROYALTIES", None, None, None, None, None)
            if key not in existing_keys:
                action = ActionItem(
                    organization_id=org_id,
                    entity_type="royalty",
                    entity_label="Royalty Transactions",
                    action_type="UNMATCHED_ROYALTIES",
                    title=f"{unmatched_count} unmatched royalty transactions need review",
                    description="Review and match unmatched royalty transactions to catalog assets.",
                    priority=2,
                    is_auto_generated=True,
                    created_by_user_id=user_id,
                )
                db.add(action)
                created_count += 1
    except Exception:
        pass

    placements = db.query(Placement).filter(
        Placement.organization_id == org_id,
        Placement.status.in_(["PITCHED", "IN_REVIEW", "IN_NEGOTIATION"])
    ).all()

    for placement in placements:
        if placement.pitched_date:
            days_since = (now.date() - placement.pitched_date).days
            if days_since > 14 and placement.status == "PITCHED":
                key = ("PLACEMENT_FOLLOWUP", None, None, placement.id, None, None)
                if key not in existing_keys:
                    action = ActionItem(
                        organization_id=org_id,
                        placement_id=placement.id,
                        entity_type="placement",
                        entity_label=placement.title,
                        action_type="PLACEMENT_FOLLOWUP",
                        title=f"Follow up on placement \"{placement.title}\" ({days_since} days since pitch)",
                        description=f"Pitched {days_since} days ago to {placement.client_name or 'client'}. Consider following up.",
                        priority=2,
                        is_auto_generated=True,
                        created_by_user_id=user_id,
                    )
                    db.add(action)
                    created_count += 1

        if placement.status == "SECURED" and not placement.contract_id:
            key = ("PLACEMENT_NEEDS_CONTRACT", None, None, placement.id, None, None)
            if key not in existing_keys:
                action = ActionItem(
                    organization_id=org_id,
                    placement_id=placement.id,
                    entity_type="placement",
                    entity_label=placement.title,
                    action_type="PLACEMENT_NEEDS_CONTRACT",
                    title=f"Create contract for secured placement \"{placement.title}\"",
                    description="Placement is secured but has no linked contract. Create and attach a sync license contract.",
                    priority=1,
                    is_auto_generated=True,
                    created_by_user_id=user_id,
                )
                db.add(action)
                created_count += 1

    pending_works = db.query(Work).filter(
        Work.organization_id == org_id,
        Work.status == "PENDING"
    ).all()

    for work in pending_works:
        key = ("WORK_PENDING_APPROVAL", None, None, None, None, work.id)
        if key not in existing_keys:
            action = ActionItem(
                organization_id=org_id,
                work_id=work.id,
                entity_type="work",
                entity_label=work.title,
                action_type="WORK_PENDING_APPROVAL",
                title=f"Review & approve work: {work.title}",
                description=f"Composition '{work.title}' requires admin approval before it becomes active in the catalog.",
                priority=2,
                is_auto_generated=True,
                created_by_user_id=user_id,
            )
            db.add(action)
            created_count += 1

    if created_count > 0:
        db.commit()

    return created_count
