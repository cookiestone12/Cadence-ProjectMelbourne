from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import logging

from ..models import get_db, PushSubscription, User
from ..utils.auth import get_current_user

logger = logging.getLogger("cadence")
router = APIRouter(prefix="/api/push", tags=["Push Notifications"])


class SubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeRequest(BaseModel):
    endpoint: str
    keys: SubscriptionKeys
    userAgent: Optional[str] = None


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


class PushSendRequest(BaseModel):
    title: str
    body: str
    url: Optional[str] = "/"
    icon: Optional[str] = "/favicon-192.png"
    tag: Optional[str] = None
    user_id: Optional[int] = None


@router.get(
    "/vapid-public-key",
    summary='Get the VAPID public key for browser web-push subscription',
    description="Returns the platform's VAPID public key the browser must use when calling `pushManager.subscribe()`.\n\n**Auth:** Bearer JWT.\n**Response:** `{ public_key }`.",
)
def get_vapid_public_key():
    key = os.environ.get("VAPID_PUBLIC_KEY", "")
    if not key:
        raise HTTPException(status_code=500, detail="VAPID public key not configured")
    return {"publicKey": key}


@router.post(
    "/subscribe",
    summary='Register a browser web-push subscription',
    description='Stores a PushSubscription for the calling user keyed by endpoint. Idempotent on endpoint.\n\n**Body:** `{ endpoint, keys: {p256dh, auth}, user_agent? }`.\n**Auth:** Bearer JWT.\n**Response:** `{ subscription_id }`.',
)
def subscribe(
    request: PushSubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(PushSubscription).filter(
        PushSubscription.endpoint == request.endpoint
    ).first()

    if existing:
        existing.p256dh = request.keys.p256dh
        existing.auth = request.keys.auth
        existing.user_id = current_user.id
        existing.user_agent = request.userAgent
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
    else:
        sub = PushSubscription(
            user_id=current_user.id,
            endpoint=request.endpoint,
            p256dh=request.keys.p256dh,
            auth=request.keys.auth,
            user_agent=request.userAgent,
            is_active=True,
        )
        db.add(sub)

    db.commit()
    return {"status": "subscribed"}


@router.post(
    "/unsubscribe",
    summary='Remove a previously-registered web-push subscription',
    description='Deletes the PushSubscription matching `endpoint`.\n\n**Body:** `{ endpoint }`.\n**Auth:** Bearer JWT.\n**Response:** `{ success: true }`.',
)
def unsubscribe(
    request: PushUnsubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = db.query(PushSubscription).filter(
        PushSubscription.endpoint == request.endpoint
    ).first()

    if sub:
        sub.is_active = False
        sub.updated_at = datetime.utcnow()
        db.commit()

    return {"status": "unsubscribed"}


@router.post(
    "/send",
    summary='Send a web-push notification to a target user',
    description="Internal/admin endpoint to dispatch a push to all of a user's registered subscriptions.\n\n**Body:** `{ user_id, title, body, url?, data? }`.\n**Auth:** Bearer JWT — staff/admin.\n**Response:** `{ delivered, failed }`.",
)
def send_push(
    request: PushSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_super_admin:
        from ..models import OrganizationMember, OrganizationMemberRole
        is_admin = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_([OrganizationMemberRole.OWNER, OrganizationMemberRole.ADMIN])
        ).first()
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

    vapid_private_key = os.environ.get("VAPID_PRIVATE_KEY")
    vapid_claims = {
        "sub": os.environ.get("VAPID_SUBJECT", "mailto:support@cadence-ci.com")
    }

    if not vapid_private_key:
        raise HTTPException(status_code=500, detail="VAPID private key not configured")

    query = db.query(PushSubscription).filter(PushSubscription.is_active == True)
    if request.user_id:
        query = query.filter(PushSubscription.user_id == request.user_id)

    subscriptions = query.all()

    import json
    from pywebpush import webpush, WebPushException

    payload = json.dumps({
        "title": request.title,
        "body": request.body,
        "url": request.url,
        "icon": request.icon,
        "tag": request.tag or "cadence-notification",
    })

    sent = 0
    failed = 0
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth,
                    }
                },
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims,
            )
            sent += 1
        except WebPushException as e:
            logger.warning(f"Push failed for subscription {sub.id}: {e}")
            if "410" in str(e) or "404" in str(e):
                sub.is_active = False
            failed += 1
        except Exception as e:
            logger.error(f"Unexpected push error for subscription {sub.id}: {e}")
            failed += 1

    db.commit()
    return {"sent": sent, "failed": failed, "total": len(subscriptions)}


@router.post(
    "/test",
    summary='Send a test push to the current user',
    description="Pushes a sample notification to the calling user's subscriptions for debugging the client-side handler.\n\n**Auth:** Bearer JWT.\n**Response:** `{ delivered, failed }`.",
)
def send_test_push(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vapid_private_key = os.environ.get("VAPID_PRIVATE_KEY")
    if not vapid_private_key:
        raise HTTPException(status_code=500, detail="VAPID private key not configured")

    subs = db.query(PushSubscription).filter(
        PushSubscription.user_id == current_user.id,
        PushSubscription.is_active == True,
    ).all()

    if not subs:
        raise HTTPException(status_code=404, detail="No active push subscriptions found for your account")

    import json
    from pywebpush import webpush, WebPushException

    vapid_claims = {
        "sub": os.environ.get("VAPID_SUBJECT", "mailto:support@cadence-ci.com")
    }

    payload = json.dumps({
        "title": "Cadence Test",
        "body": "Push notifications are working!",
        "url": "/",
        "icon": "/favicon-192.png",
        "tag": "test-notification",
    })

    sent = 0
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth}
                },
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims,
            )
            sent += 1
        except WebPushException as e:
            logger.warning(f"Test push failed: {e}")
            if "410" in str(e) or "404" in str(e):
                sub.is_active = False

    db.commit()
    return {"sent": sent, "total": len(subs)}
