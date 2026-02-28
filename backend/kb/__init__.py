import json
import os
from functools import lru_cache
from typing import Any, Dict

_KB_PATH = os.path.join(os.path.dirname(__file__), "underwriting_kb.json")


@lru_cache(maxsize=1)
def get_kb() -> Dict[str, Any]:
    with open(_KB_PATH, "r") as f:
        return json.load(f)


def get_kb_version() -> str:
    return get_kb()["kb_version"]


def get_territory_lookup() -> Dict[str, str]:
    kb = get_kb()
    lookup = {}
    for iso_code, aliases in kb["normalization"]["territory_dictionary"].items():
        for alias in aliases:
            lookup[alias.upper().strip()] = iso_code
    return lookup


def normalize_territory(raw: str) -> str | None:
    if not raw:
        return None
    lookup = get_territory_lookup()
    cleaned = raw.upper().strip()
    if cleaned in lookup:
        return lookup[cleaned]
    if len(cleaned) == 2 and cleaned.isalpha():
        return cleaned
    return None


def classify_right_type(income_type_text: str, revenue_type_text: str = "") -> str:
    kb = get_kb()
    combined = f"{income_type_text} {revenue_type_text}".upper()
    for rule in kb["classification"]["right_type_rules"]:
        for keyword in rule["if_income_type_contains"]:
            if keyword.upper() in combined:
                return rule["right_type"]
    return "other"


def classify_channel(source_text: str, income_type_text: str = "") -> str:
    kb = get_kb()
    source_upper = source_text.upper() if source_text else ""
    income_upper = income_type_text.upper() if income_type_text else ""
    for rule in kb["classification"]["channel_rules"]:
        if "if_source_contains" in rule:
            for keyword in rule["if_source_contains"]:
                if keyword.upper() in source_upper:
                    return rule["channel"]
        if "if_income_type_contains" in rule:
            for keyword in rule["if_income_type_contains"]:
                if keyword.upper() in income_upper or keyword.upper() in source_upper:
                    return rule["channel"]
    return "other"


def classify_accounting_flags(text_fields: list[str]) -> list[str]:
    kb = get_kb()
    combined = " ".join(t.upper() for t in text_fields if t)
    flags = []
    for rule in kb["classification"]["flag_rules"]:
        for keyword in rule["if_text_contains"]:
            if keyword.upper() in combined:
                flags.append(rule["flag"])
                break
    if not flags:
        flags.append("current")
    return flags
