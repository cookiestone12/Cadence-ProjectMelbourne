import logging
from typing import Optional, Dict, Tuple

from ..kb import (
    get_kb,
    normalize_territory as kb_normalize_territory,
    classify_right_type as kb_classify_right_type,
    classify_channel as kb_classify_channel,
    classify_accounting_flags as kb_classify_accounting_flags,
)

logger = logging.getLogger(__name__)


def classify_right_category(raw_income_type: Optional[str], raw_revenue_type: Optional[str] = None) -> str:
    if not raw_income_type and not raw_revenue_type:
        return "other"
    return kb_classify_right_type(raw_income_type or "", raw_revenue_type or "")


def classify_channel(raw_income_type: Optional[str], raw_revenue_type: Optional[str] = None, store: Optional[str] = None) -> str:
    if not raw_income_type and not raw_revenue_type and not store:
        return "other"
    source_text = f"{store or ''} {raw_income_type or ''}"
    income_text = f"{raw_income_type or ''} {raw_revenue_type or ''}"
    result = kb_classify_channel(source_text, income_text)
    if result == "other" and store:
        streaming_stores = ["spotify", "apple music", "amazon music", "youtube music", "tidal", "deezer", "pandora", "soundcloud"]
        if any(s in store.lower() for s in streaming_stores):
            return "streaming"
        download_stores = ["itunes", "bandcamp"]
        if any(s in store.lower() for s in download_stores):
            return "download"
        if any(s in store.lower() for s in ["youtube", "facebook", "instagram"]):
            return "ugc"
    return result


def classify_accounting_flags(
    raw_income_type: Optional[str] = None,
    raw_revenue_type: Optional[str] = None,
    net_amount: Optional[float] = None,
    gross_amount: Optional[float] = None,
    deductions: Optional[float] = None,
) -> Dict[str, bool]:
    text_fields = [raw_income_type or "", raw_revenue_type or ""]
    kb_flags = kb_classify_accounting_flags(text_fields)

    flags = {
        "is_retro_adjustment": "retro_adjustment" in kb_flags,
        "is_withholding": "withholding" in kb_flags,
        "is_reserve_movement": "reserve_movement" in kb_flags,
        "is_recoupment": "recoupment" in kb_flags,
        "is_nonroyalty_charge": "chargeback" in kb_flags,
    }

    if deductions and deductions < 0:
        flags["is_withholding"] = True

    return flags


def normalize_territory(raw_territory: Optional[str]) -> Tuple[Optional[str], str]:
    if not raw_territory:
        return None, "none"
    result = kb_normalize_territory(raw_territory)
    if result:
        raw_upper = raw_territory.strip().upper()
        if len(raw_upper) == 2 and raw_upper == result:
            return result, "assumed_iso2"
        return result, "exact"
    if len(raw_territory.strip()) == 2 and raw_territory.strip().upper().isalpha():
        return raw_territory.strip().upper(), "assumed_iso2"
    return None, "unresolved"


def classify_line(
    revenue_type: Optional[str] = None,
    usage_type: Optional[str] = None,
    store: Optional[str] = None,
    territory_raw: Optional[str] = None,
    net_amount: Optional[float] = None,
    gross_amount: Optional[float] = None,
    deductions: Optional[float] = None,
) -> dict:
    right_category = classify_right_category(revenue_type, usage_type)
    channel = classify_channel(revenue_type, usage_type, store)
    accounting_flags = classify_accounting_flags(revenue_type, usage_type, net_amount, gross_amount, deductions)
    territory_iso2, territory_confidence = normalize_territory(territory_raw)

    return {
        "canonical_right_category": right_category,
        "canonical_channel": channel,
        "accounting_flags": accounting_flags,
        "territory_iso2": territory_iso2,
        "territory_confidence": territory_confidence,
    }
