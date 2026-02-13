from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from ..models import get_db, User, OrganizationMember, IntegrationAccount
from ..utils.auth import get_current_user
from ..services import storage_service

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class OAuthCallbackRequest(BaseModel):
    code: str
    redirect_uri: str


def _build_redirect_uri(request: Request) -> str:
    origin = request.headers.get("origin")
    if not origin:
        proto = request.headers.get("x-forwarded-proto", "https")
        host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        origin = f"{proto}://{host}"
    return f"{origin}/dropbox-callback"


class DefaultFolderRequest(BaseModel):
    path: str


def _get_org_id(current_user: User, db: Session) -> int:
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="No organization membership found")
    return membership.organization_id


@router.get("/status")
def get_integration_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    integrations = db.query(IntegrationAccount).filter(
        IntegrationAccount.org_id == org_id,
        IntegrationAccount.is_active == True,
    ).all()

    result = []
    for integration in integrations:
        result.append({
            "provider": integration.provider,
            "account_email": integration.account_email,
            "account_display_name": integration.account_display_name,
            "default_folder_path": integration.default_folder_path,
            "connected_at": integration.created_at.isoformat() if integration.created_at else None,
            "is_active": integration.is_active,
        })
    return {"integrations": result}


@router.get("/dropbox/auth-url")
def get_dropbox_auth_url(
    request: Request,
    redirect_uri: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    if not redirect_uri:
        redirect_uri = _build_redirect_uri(request)
    try:
        url = storage_service.get_dropbox_auth_url(org_id, redirect_uri)
        return {"auth_url": url, "redirect_uri": redirect_uri}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dropbox/callback")
def dropbox_oauth_callback(
    request: OAuthCallbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    try:
        integration = storage_service.complete_dropbox_oauth(
            code=request.code,
            redirect_uri=request.redirect_uri,
            org_id=org_id,
            user_id=current_user.id,
            db=db,
        )
        return {
            "success": True,
            "provider": integration.provider,
            "account_email": integration.account_email,
            "account_display_name": integration.account_display_name,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")


@router.delete("/dropbox")
def disconnect_dropbox(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    removed = storage_service.disconnect_integration(org_id, "DROPBOX", db)
    if not removed:
        raise HTTPException(status_code=404, detail="Dropbox integration not found")
    return {"success": True, "message": "Dropbox disconnected"}


@router.get("/dropbox/files")
def list_dropbox_files(
    path: str = Query("/"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    try:
        files = storage_service.list_files(org_id, path, db)
        return {"files": files, "path": path}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/dropbox/default-folder")
def set_default_folder(
    request: DefaultFolderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    integration = storage_service.get_integration(org_id, "DROPBOX", db)
    if not integration:
        raise HTTPException(status_code=404, detail="Dropbox integration not found")
    integration.default_folder_path = request.path
    db.commit()
    return {"success": True, "default_folder_path": request.path}
