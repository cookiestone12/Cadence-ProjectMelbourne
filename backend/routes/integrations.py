import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from ..models import get_db, User, OrganizationMember, IntegrationAccount
from ..utils.auth import get_current_user, get_active_membership
from ..services import storage_service

router = APIRouter(prefix="/api/integrations", tags=["Integrations"])


class OAuthCallbackRequest(BaseModel):
    code: str
    code_verifier: Optional[str] = None
    redirect_uri: Optional[str] = None


class DefaultFolderRequest(BaseModel):
    path: str


def _get_org_id(current_user: User, db: Session) -> int:
    membership = get_active_membership(db, current_user)
    if not membership:
        raise HTTPException(status_code=403, detail="No organization membership found")
    return membership.organization_id


@router.get(
    "/status",
    summary='Get the integration connection status for the current user',
    description='Returns whether the calling user has connected each supported third-party storage integration (Dropbox, Google Drive) plus the configured default folder for each.\n\n**Auth:** Bearer JWT.\n**Response:** `{ dropbox: {connected, account_email, default_folder}, google_drive: {connected, account_email, default_folder} }`.',
)
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


@router.get(
    "/dropbox/auth-url",
    summary='Get the OAuth URL to start a Dropbox connection',
    description='Returns the URL the browser should redirect to so the user can grant Dropbox access. The state parameter is signed and round-trips through `/dropbox/callback`.\n\n**Query:** `redirect_uri` (where Dropbox should send the user back to after consent).\n**Auth:** Bearer JWT.\n**Response:** `{ auth_url }`.',
)
def get_dropbox_auth_url(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    try:
        result = storage_service.get_dropbox_auth_url(org_id)
        return {"auth_url": result["url"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/dropbox/callback",
    summary='Complete the Dropbox OAuth flow',
    description="Exchanges the OAuth `code` returned by Dropbox for an access token, stores it on the user's IntegrationConnection row, and returns the connected account's email.\n\n**Body:** `{ code: string, state: string, redirect_uri: string }`.\n**Auth:** Bearer JWT.\n**Response:** `{ connected: true, account_email }`.",
)
def dropbox_oauth_callback(
    request: OAuthCallbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    try:
        integration = storage_service.complete_dropbox_oauth(
            code=request.code,
            org_id=org_id,
            user_id=current_user.id,
            db=db,
            code_verifier=request.code_verifier,
            redirect_uri=request.redirect_uri,
        )
        return {
            "success": True,
            "provider": integration.provider,
            "account_email": integration.account_email,
            "account_display_name": integration.account_display_name,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")


@router.delete(
    "/dropbox",
    summary='Disconnect Dropbox for the current user',
    description='Revokes the stored access token and deletes the IntegrationConnection.\n\n**Auth:** Bearer JWT.\n**Response:** `{ success: true }`.',
)
def disconnect_dropbox(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    removed = storage_service.disconnect_integration(org_id, "DROPBOX", db)
    if not removed:
        raise HTTPException(status_code=404, detail="Dropbox integration not found")
    return {"success": True, "message": "Dropbox disconnected"}


@router.get(
    "/dropbox/files",
    summary="Browse the user's Dropbox folder tree",
    description='Lists files and folders at a given Dropbox path so the UI can render a picker. Pagination via `cursor`.\n\n**Query:** `path` (default `""` for root), `cursor`, `limit`.\n**Auth:** Bearer JWT — must have a connected Dropbox.\n**Response:** `{ entries: [{id, name, path, kind: "file"|"folder", size, modified}], cursor }`.',
)
async def list_dropbox_files(
    path: str = Query("/"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    normalized_path = path if path else "/"
    last_error = None
    for attempt in range(2):
        try:
            files = await asyncio.to_thread(storage_service.list_files, org_id, normalized_path, db)
            return {"files": files, "path": normalized_path}
        except ValueError as e:
            last_error = e
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            raise HTTPException(status_code=400, detail=str(e))
    raise HTTPException(status_code=400, detail=str(last_error))


@router.put(
    "/dropbox/default-folder",
    summary='Set the default Dropbox upload folder',
    description='Stores a default folder path that uploads/imports will land in by default.\n\n**Body:** `{ path: string }`.\n**Auth:** Bearer JWT.\n**Response:** `{ default_folder }`.',
)
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


@router.get(
    "/google-drive/auth-url",
    summary='Get the OAuth URL to start a Google Drive connection',
    description='Returns the Google OAuth consent URL. State round-trips through `/google-drive/callback`.\n\n**Query:** `redirect_uri`.\n**Auth:** Bearer JWT.\n**Response:** `{ auth_url }`.',
)
def get_google_drive_auth_url(
    redirect_uri: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    try:
        result = storage_service.get_google_drive_auth_url(org_id, redirect_uri)
        return {"auth_url": result["url"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/google-drive/callback",
    summary='Complete the Google Drive OAuth flow',
    description="Exchanges the OAuth `code` for an access + refresh token and stores it on the user's IntegrationConnection.\n\n**Body:** `{ code, state, redirect_uri }`.\n**Auth:** Bearer JWT.\n**Response:** `{ connected: true, account_email }`.",
)
def google_drive_oauth_callback(
    request: OAuthCallbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    try:
        integration = storage_service.complete_google_drive_oauth(
            code=request.code,
            org_id=org_id,
            user_id=current_user.id,
            redirect_uri=request.redirect_uri or "",
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


@router.delete(
    "/google-drive",
    summary='Disconnect Google Drive for the current user',
    description='Revokes the stored token and deletes the IntegrationConnection.\n\n**Auth:** Bearer JWT.\n**Response:** `{ success: true }`.',
)
def disconnect_google_drive(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    removed = storage_service.disconnect_integration(org_id, "GOOGLE_DRIVE", db)
    if not removed:
        raise HTTPException(status_code=404, detail="Google Drive integration not found")
    return {"success": True, "message": "Google Drive disconnected"}


@router.get(
    "/google-drive/files",
    summary="Browse the user's Google Drive",
    description='Lists files and folders. Pagination via `page_token`.\n\n**Query:** `parent_id` (default `"root"`), `page_token`, `limit`, `q` (Drive search expression).\n**Auth:** Bearer JWT — must have a connected Google Drive.\n**Response:** `{ entries: [{id, name, mime_type, size, modified}], page_token }`.',
)
def list_google_drive_files(
    folder_id: str = Query("root"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    try:
        files = storage_service.list_google_drive_files(org_id, folder_id, db)
        return {"files": files, "folder_id": folder_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/files",
    summary='Unified browse across all connected providers',
    description='Single endpoint that proxies to the right provider browser based on `provider` — used by the file picker that supports both Dropbox and Drive.\n\n**Query:** `provider` (`dropbox|google_drive`), `path`/`parent_id`, `cursor`/`page_token`, `limit`.\n**Auth:** Bearer JWT — must have the requested provider connected.\n**Response:** `{ provider, entries: [...], next }`.',
)
def list_provider_files(
    provider: str = Query(...),
    path: str = Query("/"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)
    try:
        files = storage_service.list_files_for_provider(org_id, provider, path, db)
        return {"files": files, "path": path, "provider": provider}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
