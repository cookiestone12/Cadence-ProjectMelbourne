"""Shared branding/theme resolver for the unified export engines.

PDF (`pdf_engine`) and Excel (`excel_engine`) both consume :class:`OrgTheme`
so a single org's logo + primary color produce visually consistent downloads
across formats. Logo bytes are fetched once per theme instance (data URLs and
HTTP URLs both supported) with a network-safe fallback that degrades to text.

The "Powered by Cadence" footer/caption is non-negotiable per Task #189 — it
is enforced inside the engines, not here.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional, Tuple

logger = logging.getLogger("cadence")

CADENCE_SAGE = "#5B8A72"
CADENCE_SAGE_DARK = "#4A7A62"
CADENCE_INK = "#3D4A44"
CADENCE_GRAY = "#7A8580"
CADENCE_LIGHT_BG = "#F5F7F4"
CADENCE_DIVIDER = "#D0D5D1"

POWERED_BY = "Powered by Cadence"

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")
_HEX_SHORT_RE = re.compile(r"^#?([0-9a-fA-F]{3})$")


def parse_hex_color(value: Optional[str], default: str = CADENCE_SAGE) -> str:
    """Normalize a hex color string to the canonical ``#RRGGBB`` form.

    Accepts ``#RRGGBB``, ``RRGGBB``, ``#RGB`` and ``RGB``. Returns ``default``
    when ``value`` is ``None``, blank, or unparseable. Never raises so a
    bad org-level color cannot crash a report.
    """
    if not value:
        return default
    s = str(value).strip()
    m = _HEX_RE.match(s)
    if m:
        return "#" + m.group(1).upper()
    m = _HEX_SHORT_RE.match(s)
    if m:
        rgb = m.group(1)
        return "#" + (rgb[0]*2 + rgb[1]*2 + rgb[2]*2).upper()
    return default


def lighten_hex(hex_color: str, amount: float = 0.85) -> str:
    """Blend a hex color toward white. Used for branded zebra striping/light bg."""
    h = parse_hex_color(hex_color)
    r = int(h[1:3], 16)
    g = int(h[3:5], 16)
    b = int(h[5:7], 16)
    r = int(r + (255 - r) * amount)
    g = int(g + (255 - g) * amount)
    b = int(b + (255 - b) * amount)
    return f"#{r:02X}{g:02X}{b:02X}"


def darken_hex(hex_color: str, amount: float = 0.18) -> str:
    """Slightly darken a hex color (used for header text contrast guard)."""
    h = parse_hex_color(hex_color)
    r = int(int(h[1:3], 16) * (1 - amount))
    g = int(int(h[3:5], 16) * (1 - amount))
    b = int(int(h[5:7], 16) * (1 - amount))
    return f"#{r:02X}{g:02X}{b:02X}"


def _decode_data_url(data_url: str) -> Optional[bytes]:
    """Decode a ``data:image/...;base64,...`` URL into raw bytes."""
    try:
        header, payload = data_url.split(",", 1)
        if ";base64" in header:
            return base64.b64decode(payload)
        # Plain (non-base64) data URLs are rare for images — treat as utf-8 bytes.
        return payload.encode("utf-8")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to decode data URL logo: %s", exc)
        return None


def _fetch_http_logo(url: str, timeout_seconds: float = 10.0) -> Optional[bytes]:
    """Fetch a remote logo with a tight timeout. Returns ``None`` on any failure."""
    try:
        import httpx  # local import — only the engines need this dependency
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning("Logo fetch %s returned %s", url, resp.status_code)
                return None
            return resp.content
    except Exception as exc:
        logger.warning("Logo fetch %s failed: %s", url, exc)
        return None


def _resolve_local_logo() -> Optional[bytes]:
    """Fall back to the bundled Cadence logo when an org has no logo configured."""
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "cadence-logo.png"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "public", "cadence-logo.png"),
    ]
    for path in candidates:
        try:
            if os.path.exists(path):
                with open(path, "rb") as fh:
                    return fh.read()
        except Exception:  # pragma: no cover
            continue
    return None


@dataclass
class OrgTheme:
    """Per-org branding values consumed by the export engines.

    ``logo_url`` may be a remote URL, a ``data:image/...;base64,...`` URL,
    or ``None``. ``primary_color`` may be ``None``; the engines fall back
    to Cadence sage. ``logo_bytes`` is fetched lazily and cached on the
    instance — engines build a new theme per request, so caching is
    request-scoped, not process-global.
    """

    org_id: Optional[int] = None
    name: str = "Cadence"
    display_name: str = "Cadence"
    primary_color: str = CADENCE_SAGE
    primary_color_dark: str = CADENCE_SAGE_DARK
    accent_color: str = CADENCE_INK
    text_color: str = CADENCE_INK
    muted_color: str = CADENCE_GRAY
    light_bg: str = CADENCE_LIGHT_BG
    divider: str = CADENCE_DIVIDER
    zebra_color: str = field(default_factory=lambda: lighten_hex(CADENCE_SAGE, 0.92))
    logo_url: Optional[str] = None
    logo_orientation: str = "square"
    powered_by_text: str = POWERED_BY
    is_cadence_default: bool = True

    _logo_bytes_cache: Optional[bytes] = field(default=None, repr=False)
    _logo_fetched: bool = field(default=False, repr=False)

    def fetch_logo_bytes(self) -> Optional[bytes]:
        """Fetch (and cache) raw logo bytes. Network-safe: never raises."""
        if self._logo_fetched:
            return self._logo_bytes_cache
        self._logo_fetched = True

        if self.logo_url:
            url = self.logo_url.strip()
            if url.startswith("data:"):
                self._logo_bytes_cache = _decode_data_url(url)
            elif url.startswith("http://") or url.startswith("https://"):
                self._logo_bytes_cache = _fetch_http_logo(url)
            elif url.startswith("/"):
                # Relative path within the project (uploads/, public/, etc.)
                rel = url.lstrip("/")
                roots = [
                    os.path.dirname(os.path.dirname(__file__)),  # backend/
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # repo root
                ]
                for root in roots:
                    candidate = os.path.join(root, rel)
                    if os.path.exists(candidate):
                        try:
                            with open(candidate, "rb") as fh:
                                self._logo_bytes_cache = fh.read()
                                break
                        except Exception:  # pragma: no cover
                            pass
            else:
                logger.warning("Unknown logo_url scheme: %s", url[:30])

        if self._logo_bytes_cache is None and self.is_cadence_default:
            self._logo_bytes_cache = _resolve_local_logo()

        return self._logo_bytes_cache

    def logo_dimensions(self, max_width_px: float, max_height_px: float) -> Tuple[float, float]:
        """Return (width, height) honoring ``logo_orientation`` while fitting the box."""
        orient = (self.logo_orientation or "square").lower()
        if orient == "horizontal":
            # 3:1 aspect, prefer wide
            ratio = 1.0 / 3.0
            w = max_width_px
            h = w * ratio
            if h > max_height_px:
                h = max_height_px
                w = h / ratio
        elif orient == "vertical":
            ratio = 3.0
            h = max_height_px
            w = h / ratio
            if w > max_width_px:
                w = max_width_px
                h = w * ratio
        else:
            side = min(max_width_px, max_height_px)
            w = h = side
        return w, h


def theme_from_org(org) -> OrgTheme:
    """Build an :class:`OrgTheme` from an ``Organization`` row.

    ``org`` may be ``None``; the result then matches the Cadence default
    theme. Only attributes accessed below are required, so this works
    against both ORM models and dict-like rows from raw queries.
    """
    if org is None:
        return OrgTheme()

    name = getattr(org, "name", None) or "Organization"
    display = getattr(org, "display_name", None) or name
    raw_color = getattr(org, "primary_color", None)
    color = parse_hex_color(raw_color, default=CADENCE_SAGE)
    logo_url = getattr(org, "logo_url", None)
    orientation = getattr(org, "logo_orientation", None) or "square"

    is_default = (
        not raw_color
        and not logo_url
    )

    return OrgTheme(
        org_id=getattr(org, "id", None),
        name=name,
        display_name=display,
        primary_color=color,
        primary_color_dark=darken_hex(color, 0.15),
        accent_color=CADENCE_INK,
        text_color=CADENCE_INK,
        muted_color=CADENCE_GRAY,
        light_bg=CADENCE_LIGHT_BG,
        divider=CADENCE_DIVIDER,
        zebra_color=lighten_hex(color, 0.92),
        logo_url=logo_url,
        logo_orientation=orientation,
        is_cadence_default=is_default,
    )


def get_org_theme(db, organization_id: Optional[int]) -> OrgTheme:
    """Convenience: load an org by id and return its theme."""
    if organization_id is None:
        return OrgTheme()
    try:
        from ..models import Organization  # local import to avoid cycles
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        return theme_from_org(org)
    except Exception as exc:  # pragma: no cover
        logger.warning("get_org_theme(%s) failed: %s", organization_id, exc)
        return OrgTheme()


def safe_filename_segment(value: Optional[str], fallback: str = "report") -> str:
    """Sanitize a string for use inside a Content-Disposition filename."""
    if not value:
        return fallback
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip())
    s = s.strip("_")
    return s or fallback
