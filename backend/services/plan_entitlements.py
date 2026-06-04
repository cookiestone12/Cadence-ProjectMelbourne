"""Task #213 — central plan / entitlements definition.

Single source of truth for what each subscription plan can do. The plan is
derived from ``Organization.account_type`` (the one and only plan identifier);
there is deliberately no second "plan" column that could drift from it.

Two plans exist:

* **Professional** (``account_type == "INDIVIDUAL"``) — a single client catalog,
  no roster, cannot receive shared catalogs.
* **Enterprise** (``account_type == "ENTERPRISE"``) — full roster, can both send
  and receive shares. Capacity = base 10 catalogs plus 5 per purchased add-on
  pack (``Organization.catalog_addon_packs``).

All limits and sharing-direction rules MUST be enforced on the server through the
helpers here; frontend gating is convenience only and is never the source of
truth.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException

# account_type values
PROFESSIONAL = "INDIVIDUAL"
ENTERPRISE = "ENTERPRISE"

ENTERPRISE_BASE_CATALOGS = 10
ADDON_PACK_SIZE = 5
PROFESSIONAL_CATALOG_LIMIT = 1

PLAN_LABELS = {
    ENTERPRISE: "Enterprise",
    PROFESSIONAL: "Professional",
}


def normalize_account_type(org) -> str:
    """Resolve an org's account_type to a known plan, defaulting to Enterprise.

    Existing orgs default to Enterprise (matching the column default), so any
    unknown/None value degrades gracefully to the more permissive plan rather
    than locking an existing customer out.
    """
    at = (getattr(org, "account_type", None) or ENTERPRISE).upper()
    return at if at in (ENTERPRISE, PROFESSIONAL) else ENTERPRISE


def is_enterprise(org) -> bool:
    return normalize_account_type(org) == ENTERPRISE


def is_professional(org) -> bool:
    return normalize_account_type(org) == PROFESSIONAL


def add_on_packs(org) -> int:
    return getattr(org, "catalog_addon_packs", 0) or 0


def catalog_limit(org) -> int:
    """Effective number of client catalogs (Creators) this org may manage."""
    if normalize_account_type(org) == PROFESSIONAL:
        return PROFESSIONAL_CATALOG_LIMIT
    return ENTERPRISE_BASE_CATALOGS + add_on_packs(org) * ADDON_PACK_SIZE


def roster_enabled(org) -> bool:
    return normalize_account_type(org) == ENTERPRISE


def can_receive_shares(org) -> bool:
    return normalize_account_type(org) == ENTERPRISE


def get_entitlements(org) -> dict:
    """Plan capabilities for an org, shaped for inclusion in API responses."""
    at = normalize_account_type(org)
    return {
        "plan": at,
        "plan_label": PLAN_LABELS.get(at, "Enterprise"),
        "catalog_limit": catalog_limit(org),
        "roster_enabled": roster_enabled(org),
        "can_receive_shares": can_receive_shares(org),
        "add_on_packs": add_on_packs(org),
        "add_on_pack_size": ADDON_PACK_SIZE,
    }


def count_catalogs(db: Session, org_id: int) -> int:
    """Number of catalogs the org *manages* against its plan limit.

    A managed catalog is either a Creator the org owns OR an incoming
    ClientShare it has accepted (an accepted share occupies a roster slot
    exactly like an owned catalog), so both count toward the plan limit.
    """
    from ..models import Creator, ClientShare
    owned = db.query(func.count(Creator.id)).filter(
        Creator.organization_id == org_id
    ).scalar() or 0
    accepted_shares = db.query(func.count(ClientShare.id)).filter(
        ClientShare.recipient_org_id == org_id,
        ClientShare.status == "ACCEPTED",
    ).scalar() or 0
    return owned + accepted_shares


def _load_org(db: Session, org_id: int):
    from ..models import Organization
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


def enforce_catalog_capacity(db: Session, org_id: int, adding: int = 1) -> None:
    """Raise HTTP 403 when adding ``adding`` catalogs would exceed the plan limit.

    This is the single gate every creator-creation path must call before
    persisting a new Creator so no path can bypass the plan limit.
    """
    org = _load_org(db, org_id)
    limit = catalog_limit(org)
    current = count_catalogs(db, org_id)
    if current + adding > limit:
        if is_professional(org):
            detail = (
                "Your Professional plan is limited to a single catalog. "
                "Upgrade to Enterprise to manage multiple client catalogs."
            )
        else:
            detail = (
                f"You've reached your plan's limit of {limit} client catalogs. "
                f"Add another {ADDON_PACK_SIZE}-client pack to grow your roster."
            )
        raise HTTPException(status_code=403, detail=detail)
