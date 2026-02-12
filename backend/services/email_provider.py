import os
import logging
from abc import ABC, abstractmethod
from typing import Optional

import requests
import resend

logger = logging.getLogger("rythm")


class EmailProvider(ABC):
    @abstractmethod
    def send_email(self, to: str, subject: str, html_body: str, from_email: Optional[str] = None) -> bool:
        pass


def _get_replit_connector_header() -> Optional[str]:
    repl_identity = os.getenv("REPL_IDENTITY")
    web_repl_renewal = os.getenv("WEB_REPL_RENEWAL")
    if repl_identity:
        return f"repl {repl_identity}"
    elif web_repl_renewal:
        return f"depl {web_repl_renewal}"
    return None


def _get_resend_credentials() -> dict:
    hostname = os.getenv("REPLIT_CONNECTORS_HOSTNAME")
    x_replit_token = _get_replit_connector_header()

    if not hostname or not x_replit_token:
        raise RuntimeError("Replit connector environment not configured for Resend")

    try:
        resp = requests.get(
            f"https://{hostname}/api/v2/connection?include_secrets=true&connector_names=resend",
            headers={
                "Accept": "application/json",
                "X_REPLIT_TOKEN": x_replit_token,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        item = data.get("items", [None])[0] if data.get("items") else None
        if not item:
            raise RuntimeError("Resend connector: no connection items found")

        settings = item.get("settings", {})
        api_key = settings.get("api_key")
        from_email = settings.get("from_email")

        if not api_key:
            raise RuntimeError("Resend connector: api_key not found in settings")

        return {"api_key": api_key, "from_email": from_email}
    except requests.RequestException as e:
        logger.error(f"Resend connector request error: {e}")
        raise RuntimeError(f"Failed to fetch Resend credentials: {e}")


class ResendProvider(EmailProvider):
    def send_email(self, to: str, subject: str, html_body: str, from_email: Optional[str] = None) -> bool:
        try:
            credentials = _get_resend_credentials()
            resend.api_key = credentials["api_key"]
            connector_from = credentials.get("from_email")
            sender = from_email or connector_from or "onboarding@resend.dev"

            logger.info(f"Attempting to send email to {to} from {sender}")
            result = resend.Emails.send({
                "from": sender,
                "to": [to],
                "subject": subject,
                "html": html_body,
            })
            logger.info(f"Email sent to {to}: {subject} (result: {result})")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}", exc_info=True)
            return False


def get_email_provider() -> EmailProvider:
    return ResendProvider()
