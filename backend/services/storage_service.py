import os
import base64
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from urllib.parse import quote

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import dropbox
from sqlalchemy.orm import Session

from ..models import IntegrationAccount

logger = logging.getLogger("rythm")

DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY", "")
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET", "")


def get_fernet() -> Fernet:
    secret = os.environ["SESSION_SECRET"]
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"rythm-storage-salt",
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return Fernet(key)


def encrypt_token(token: str) -> str:
    f = get_fernet()
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    f = get_fernet()
    return f.decrypt(encrypted.encode()).decode()


def get_dropbox_auth_url(org_id: int, redirect_uri: str = None) -> dict:
    if not DROPBOX_APP_KEY or not DROPBOX_APP_SECRET:
        raise ValueError("DROPBOX_APP_KEY and DROPBOX_APP_SECRET must be configured")

    auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
        consumer_key=DROPBOX_APP_KEY,
        consumer_secret=DROPBOX_APP_SECRET,
        token_access_type="offline",
        use_pkce=False,
    )
    authorize_url = auth_flow.start()
    return {"url": authorize_url}


def complete_dropbox_oauth(
    code: str,
    org_id: int,
    user_id: int,
    db: Session,
    code_verifier: str = None,
    redirect_uri: str = None,
) -> IntegrationAccount:
    auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
        consumer_key=DROPBOX_APP_KEY,
        consumer_secret=DROPBOX_APP_SECRET,
        token_access_type="offline",
        use_pkce=False,
    )
    try:
        oauth_result = auth_flow.finish(code.strip())
    except Exception as e:
        logger.error(f"Dropbox OAuth finish error: {e}")
        raise ValueError(f"Invalid authorization code: {e}")

    access_token = oauth_result.access_token
    refresh_token = oauth_result.refresh_token

    dbx = dropbox.Dropbox(access_token)
    account_info = dbx.users_get_current_account()
    account_email = account_info.email
    account_name = account_info.name.display_name

    existing = db.query(IntegrationAccount).filter(
        IntegrationAccount.org_id == org_id,
        IntegrationAccount.provider == "DROPBOX",
    ).first()

    if existing:
        existing.access_token_encrypted = encrypt_token(access_token)
        existing.refresh_token_encrypted = encrypt_token(refresh_token) if refresh_token else None
        existing.connected_by_user_id = user_id
        existing.account_email = account_email
        existing.account_display_name = account_name
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    integration = IntegrationAccount(
        org_id=org_id,
        provider="DROPBOX",
        access_token_encrypted=encrypt_token(access_token),
        refresh_token_encrypted=encrypt_token(refresh_token) if refresh_token else None,
        connected_by_user_id=user_id,
        account_email=account_email,
        account_display_name=account_name,
        is_active=True,
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def disconnect_integration(org_id: int, provider: str, db: Session) -> bool:
    integration = db.query(IntegrationAccount).filter(
        IntegrationAccount.org_id == org_id,
        IntegrationAccount.provider == provider,
    ).first()
    if not integration:
        return False
    db.delete(integration)
    db.commit()
    return True


def get_integration(org_id: int, provider: str, db: Session) -> Optional[IntegrationAccount]:
    return db.query(IntegrationAccount).filter(
        IntegrationAccount.org_id == org_id,
        IntegrationAccount.provider == provider,
        IntegrationAccount.is_active == True,
    ).first()


def get_dropbox_client(org_id: int, db: Session) -> dropbox.Dropbox:
    integration = get_integration(org_id, "DROPBOX", db)
    if not integration:
        raise ValueError("Dropbox is not connected for this organization")

    access_token = decrypt_token(integration.access_token_encrypted)

    if integration.refresh_token_encrypted:
        refresh_token = decrypt_token(integration.refresh_token_encrypted)
        dbx = dropbox.Dropbox(
            oauth2_access_token=access_token,
            oauth2_refresh_token=refresh_token,
            app_key=DROPBOX_APP_KEY,
            app_secret=DROPBOX_APP_SECRET,
        )
    else:
        dbx = dropbox.Dropbox(oauth2_access_token=access_token)

    return dbx


def list_files(org_id: int, path: str, db: Session) -> List[Dict[str, Any]]:
    dbx = get_dropbox_client(org_id, db)
    if path == "/":
        path = ""

    try:
        result = dbx.files_list_folder(path)
    except dropbox.exceptions.ApiError as e:
        logger.error(f"Dropbox list_folder error: {e}")
        raise ValueError(f"Could not list files at path: {path}")

    files = []
    for entry in result.entries:
        item = {
            "name": entry.name,
            "path_display": entry.path_display,
            "path_lower": entry.path_lower,
        }
        if isinstance(entry, dropbox.files.FileMetadata):
            item["type"] = "file"
            item["is_folder"] = False
            item["size"] = entry.size
            item["id"] = entry.id
            item["client_modified"] = entry.client_modified.isoformat() if entry.client_modified else None
            item["server_modified"] = entry.server_modified.isoformat() if entry.server_modified else None
            item["content_hash"] = entry.content_hash
        elif isinstance(entry, dropbox.files.FolderMetadata):
            item["type"] = "folder"
            item["is_folder"] = True
            item["id"] = entry.id
        files.append(item)

    files.sort(key=lambda x: (0 if x.get("type") == "folder" else 1, x["name"].lower()))
    return files


def get_temp_download_link(org_id: int, path: str, db: Session) -> str:
    dbx = get_dropbox_client(org_id, db)
    try:
        link = dbx.files_get_temporary_link(path)
        return link.link
    except dropbox.exceptions.ApiError as e:
        logger.error(f"Dropbox get_temporary_link error: {e}")
        raise ValueError(f"Could not get download link for: {path}")


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")


def get_google_drive_auth_url(org_id: int, redirect_uri: str) -> dict:
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be configured")

    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
        redirect_uri=redirect_uri,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=str(org_id),
    )
    return {"url": auth_url}


def complete_google_drive_oauth(
    code: str,
    org_id: int,
    user_id: int,
    redirect_uri: str,
    db: Session,
) -> IntegrationAccount:
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
        redirect_uri=redirect_uri,
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials

    service = build("drive", "v3", credentials=credentials)
    about = service.about().get(fields="user").execute()
    account_email = about["user"].get("emailAddress", "")
    account_name = about["user"].get("displayName", "")

    access_token = credentials.token
    refresh_token = credentials.refresh_token

    existing = db.query(IntegrationAccount).filter(
        IntegrationAccount.org_id == org_id,
        IntegrationAccount.provider == "GOOGLE_DRIVE",
    ).first()

    if existing:
        existing.access_token_encrypted = encrypt_token(access_token)
        existing.refresh_token_encrypted = encrypt_token(refresh_token) if refresh_token else None
        existing.connected_by_user_id = user_id
        existing.account_email = account_email
        existing.account_display_name = account_name
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    integration = IntegrationAccount(
        org_id=org_id,
        provider="GOOGLE_DRIVE",
        access_token_encrypted=encrypt_token(access_token),
        refresh_token_encrypted=encrypt_token(refresh_token) if refresh_token else None,
        connected_by_user_id=user_id,
        account_email=account_email,
        account_display_name=account_name,
        is_active=True,
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def get_google_drive_credentials(org_id: int, db: Session):
    from google.oauth2.credentials import Credentials

    integration = get_integration(org_id, "GOOGLE_DRIVE", db)
    if not integration:
        raise ValueError("Google Drive is not connected for this organization")

    access_token = decrypt_token(integration.access_token_encrypted)
    refresh_token = None
    if integration.refresh_token_encrypted:
        refresh_token = decrypt_token(integration.refresh_token_encrypted)

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return creds


def list_google_drive_files(org_id: int, folder_id: str, db: Session) -> List[Dict[str, Any]]:
    from googleapiclient.discovery import build

    creds = get_google_drive_credentials(org_id, db)
    service = build("drive", "v3", credentials=creds)

    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        pageSize=100,
        fields="files(id, name, mimeType, size, modifiedTime, parents)",
        orderBy="folder,name",
    ).execute()

    files = []
    for item in results.get("files", []):
        is_folder = item["mimeType"] == "application/vnd.google-apps.folder"
        files.append({
            "name": item["name"],
            "path_display": item["name"],
            "path_lower": item["name"].lower(),
            "type": "folder" if is_folder else "file",
            "is_folder": is_folder,
            "id": item["id"],
            "size": int(item.get("size", 0)) if not is_folder else None,
            "client_modified": item.get("modifiedTime"),
            "provider": "GOOGLE_DRIVE",
        })

    files.sort(key=lambda x: (0 if x.get("type") == "folder" else 1, x["name"].lower()))
    return files


def get_google_drive_download_link(org_id: int, file_id: str, db: Session) -> str:
    from googleapiclient.discovery import build

    creds = get_google_drive_credentials(org_id, db)
    service = build("drive", "v3", credentials=creds)

    file_meta = service.files().get(fileId=file_id, fields="webContentLink").execute()
    link = file_meta.get("webContentLink")
    if not link:
        link = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    return link


def list_files_for_provider(org_id: int, provider: str, path: str, db: Session) -> List[Dict[str, Any]]:
    if provider == "DROPBOX":
        return list_files(org_id, path, db)
    elif provider == "GOOGLE_DRIVE":
        folder_id = path if path and path != "/" else "root"
        return list_google_drive_files(org_id, folder_id, db)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
