import json
import os
import re
import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

KB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kb", "royalty_knowledge_base.json")

_kb_cache = None

def _load_kb():
    global _kb_cache
    if _kb_cache is not None:
        return _kb_cache
    try:
        with open(KB_PATH, "r") as f:
            _kb_cache = json.load(f)
        return _kb_cache
    except Exception as e:
        logger.error(f"Failed to load KB: {e}")
        return None


TERRITORY_MAP = None

def _get_territory_map() -> dict:
    global TERRITORY_MAP
    if TERRITORY_MAP is not None:
        return TERRITORY_MAP
    kb = _load_kb()
    if kb:
        TERRITORY_MAP = kb.get("rules", {}).get("territory_normalization", {}).get("dictionary", {})
    if not TERRITORY_MAP:
        TERRITORY_MAP = {
            "US": "US", "United States": "US", "UNITED STATES": "US", "USA": "US",
            "GB": "GB", "United Kingdom": "GB", "UK": "GB",
            "CA": "CA", "Canada": "CA",
            "DE": "DE", "Germany": "DE",
            "FR": "FR", "France": "FR",
            "JP": "JP", "Japan": "JP",
            "AU": "AU", "Australia": "AU",
            "WORLD": "WW", "Worldwide": "WW", "WW": "WW",
        }
    return TERRITORY_MAP


RIGHT_CATEGORY_RULES = [
    (["Mechanical"], "mechanical"),
    (["Synch", "Synchronisation", "Synchronization", "Sync License"], "sync"),
    (["Performance"], "performance"),
    (["Print", "Lyrics", "Lyric"], "print_lyrics"),
    (["Neighboring", "Neighbouring", "Master Use", "Sound Recording"], "neighboring_rights"),
]

CHANNEL_RULES = [
    (["Streaming", "Stream", "On Demand"], "streaming"),
    (["Download", "DPD", "Permanent Digital"], "download"),
    (["Radio", "TV", "Film", "Broadcast", "Television"], "broadcast"),
    (["Live", "Concert"], "live"),
    (["UGC", "User Generated"], "ugc"),
    (["Social", "Short-Form", "Short Form", "TikTok", "Reels"], "social"),
    (["Physical", "CD", "Vinyl"], "physical"),
]


def classify_right_category(raw_income_type: Optional[str], raw_revenue_type: Optional[str] = None) -> str:
    if not raw_income_type and not raw_revenue_type:
        return "other"
    combined = f"{raw_income_type or ''} {raw_revenue_type or ''}".strip()
    for keywords, category in RIGHT_CATEGORY_RULES:
        for kw in keywords:
            if kw.lower() in combined.lower():
                return category
    return "other"


def classify_channel(raw_income_type: Optional[str], raw_revenue_type: Optional[str] = None, store: Optional[str] = None) -> str:
    if not raw_income_type and not raw_revenue_type and not store:
        return "other"
    combined = f"{raw_income_type or ''} {raw_revenue_type or ''} {store or ''}".strip()
    for keywords, channel in CHANNEL_RULES:
        for kw in keywords:
            if kw.lower() in combined.lower():
                return channel
    streaming_stores = ["spotify", "apple music", "amazon music", "youtube music", "tidal", "deezer", "pandora", "soundcloud"]
    if store and any(s in store.lower() for s in streaming_stores):
        return "streaming"
    download_stores = ["itunes", "bandcamp"]
    if store and any(s in store.lower() for s in download_stores):
        return "download"
    if store and any(s in (store or "").lower() for s in ["youtube", "facebook", "instagram"]):
        return "ugc"
    return "other"


def classify_accounting_flags(
    raw_income_type: Optional[str] = None,
    raw_revenue_type: Optional[str] = None,
    net_amount: Optional[float] = None,
    gross_amount: Optional[float] = None,
    deductions: Optional[float] = None,
) -> Dict[str, bool]:
    flags = {
        "is_retro_adjustment": False,
        "is_withholding": False,
        "is_reserve_movement": False,
        "is_recoupment": False,
        "is_nonroyalty_charge": False,
    }
    combined = f"{raw_income_type or ''} {raw_revenue_type or ''}".lower()

    if any(kw in combined for kw in ["adjustment", "retro", "true-up", "trueup", "correction"]):
        flags["is_retro_adjustment"] = True
    if any(kw in combined for kw in ["withholding", "tax", "w/h"]):
        flags["is_withholding"] = True
    if any(kw in combined for kw in ["reserve", "holdback"]):
        flags["is_reserve_movement"] = True
    if any(kw in combined for kw in ["recoup", "advance recovery"]):
        flags["is_recoupment"] = True
    if any(kw in combined for kw in ["charge", "fee", "cost", "deduction", "commission"]):
        flags["is_nonroyalty_charge"] = True
    if deductions and deductions < 0:
        flags["is_withholding"] = True

    return flags


def normalize_territory(raw_territory: Optional[str]) -> Tuple[Optional[str], str]:
    if not raw_territory:
        return None, "none"
    raw = raw_territory.strip()
    territory_map = _get_territory_map()
    if raw in territory_map:
        return territory_map[raw], "exact"
    raw_upper = raw.upper()
    for key, val in territory_map.items():
        if key.upper() == raw_upper:
            return val, "exact"
    if len(raw) == 2 and raw.upper().isalpha():
        return raw.upper(), "assumed_iso2"
    for key, val in territory_map.items():
        if len(key) > 3 and key.lower() in raw.lower():
            return val, "fuzzy"
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
