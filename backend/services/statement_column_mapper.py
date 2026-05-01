"""Confidence-scored column auto-mapper for royalty statements.

Given a list of raw header strings from an uploaded statement and an
optional source type (BMI / ASCAP / MLC / etc), produce a mapping
from canonical Cadence fields (track_title, isrc, revenue, ...) to
the actual header in the file, plus an aggregate confidence score.

The mapper is the source-of-truth used by the upload preview path
to decide whether the file can be processed silently or whether the
operator must confirm a column mapping.

Scoring:
- 1.00  exact (case- and whitespace-insensitive) match against any
        alias for that field, after overlaying source-type extra
        hints onto the base hints.
- 0.80-0.99  fuzzy match via ``difflib.SequenceMatcher`` above the
        ``FUZZY_THRESHOLD``. Score reflects the closest alias
        ratio. (We use SequenceMatcher rather than raw Levenshtein
        distance because it is in the stdlib — no extra dependency
        — and produces a normalized 0..1 ratio that is directly
        comparable to the threshold; the empirical ranking on
        royalty-statement headers is equivalent to Levenshtein for
        the short header strings we operate on.)
- 0.0   no match — field stays unmapped.

Aggregate ``_confidence`` averages the per-field scores for the
fields that actually got mapped. ``_confident`` is True only when
both the *required* fields are mapped at >= ``REQUIRED_THRESHOLD``:
- (title OR isrc) AND amount.

Returned shape::

    {
        "isrc": "ISRC",
        "track_title": "Work Title",
        "revenue": "Royalty Amount",
        ...
        "_confidence": 0.94,
        "_confident": True,
        "_unmapped": ["Some Other Column"],
        "_field_scores": {"isrc": 1.0, "track_title": 1.0, ...},
    }
"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List, Optional

from ..config.statement_formats import (
    BASE_COLUMN_HINTS,
    canonical_source_type,
    get_format_spec,
)


FUZZY_THRESHOLD = 0.80
REQUIRED_THRESHOLD = 0.80


CANONICAL_FIELDS: List[str] = [
    "isrc",
    "upc",
    "iswc",
    "work_id",
    "track_title",
    "artist",
    "revenue",
    "quantity",
    "territory",
    "platform",
    "revenue_type",
    "publisher",
    "share_percentage",
]


def _normalize(s: Optional[str]) -> str:
    """Lower-case and collapse non-alphanumerics so ``Track Title`` and
    ``track_title`` and ``track-title`` all compare equal."""
    if not s:
        return ""
    out = []
    for ch in str(s).lower():
        if ch.isalnum():
            out.append(ch)
        else:
            # collapse runs of non-alnum into single spaces; we strip
            # later, so consecutive non-alnums fold together cleanly.
            out.append(" ")
    return " ".join("".join(out).split())


def _aliases_for(field: str, source_type: Optional[str]) -> List[str]:
    """Aliases for a field = base hints + per-source extra hints,
    de-duplicated, in order of preference (per-source first so a
    BMI file's ``Current Activity Royalty`` beats the generic
    ``revenue``)."""
    base = list(BASE_COLUMN_HINTS.get(field, []))
    spec = get_format_spec(source_type) if source_type else None
    extra = []
    if spec:
        extra = list((spec.get("extra_hints") or {}).get(field, []))
    # Per-source first, then base, dedupe preserving order.
    seen = set()
    out: List[str] = []
    for alias in extra + base:
        key = _normalize(alias)
        if key and key not in seen:
            seen.add(key)
            out.append(alias)
    return out


_IDENTIFIER_TOKENS = {"isrc", "upc", "iswc", "ean", "barcode"}


def _score_header(header: str, aliases: List[str]) -> tuple:
    """Return ``(score, specificity)`` for ``header``'s best alias
    match.

    ``score`` is in [0.0, 1.0]. ``specificity`` is the token count of
    the winning alias and is used purely as a tie-breaker — longer
    aliases (e.g. ``"ascap work id"``) outrank generic ones (``"work
    id"``) when both score 1.0 against the same header.

    Scoring rules (first match wins):
      1. Exact normalized match → 1.0.
      2. Multi-word alias appears as a contiguous word substring of
         the header → 1.0 (so ``"Work Title"`` matches the alias
         ``"work title"`` even when prefixed with ``"BMI"``).
      3. Single-word *identifier* alias (isrc / upc / iswc / etc) is
         a token of the header → 1.0 (catches ``"ISRC Code"``,
         ``"UPC #"``).
      4. Otherwise SequenceMatcher ratio; values below
         ``FUZZY_THRESHOLD`` collapse to 0.

    Generic single-word aliases like ``"work"``, ``"track"``,
    ``"amount"`` deliberately do NOT promote to 1.0 via token
    membership — they would otherwise grab columns like
    ``"BMI Work#"`` or ``"Work ID"``, poisoning the mapping.
    """
    h_norm = _normalize(header)
    if not h_norm:
        return (0.0, 0)
    h_tokens = h_norm.split()
    best_score = 0.0
    best_specificity = 0
    for alias in aliases:
        a_norm = _normalize(alias)
        if not a_norm:
            continue
        a_tokens = a_norm.split()
        a_specificity = len(a_tokens)
        score = 0.0
        if h_norm == a_norm:
            score = 1.0
        elif len(a_tokens) >= 2:
            # Rule 2: multi-word alias appears as contiguous word run.
            joined = " " + h_norm + " "
            if " " + a_norm + " " in joined:
                score = 1.0
        elif a_norm in _IDENTIFIER_TOKENS and a_norm in h_tokens:
            # Rule 3: short identifier code as a header token.
            score = 1.0
        if score < 1.0:
            ratio = SequenceMatcher(None, h_norm, a_norm).ratio()
            if ratio >= FUZZY_THRESHOLD and ratio > score:
                score = ratio
        if score > best_score or (
            score == best_score and a_specificity > best_specificity
        ):
            best_score = score
            best_specificity = a_specificity
    if best_score < FUZZY_THRESHOLD:
        return (0.0, 0)
    return (best_score, best_specificity)


def auto_map_columns(
    headers: List[str],
    source_type: Optional[str] = None,
) -> Dict[str, object]:
    """Auto-map a file's headers onto Cadence's canonical fields.

    Args:
        headers: raw header strings as they appear in the upload.
        source_type: optional canonical source type (will be
            normalized via ``canonical_source_type``). Drives which
            per-source aliases are overlaid onto the base hints.

    Returns:
        ``{<canonical_field>: <header_or_None>, "_confidence": float,
        "_confident": bool, "_unmapped": [headers],
        "_field_scores": {field: score}}``.
    """
    canonical_source = canonical_source_type(source_type)
    headers = [h for h in (headers or []) if h is not None and str(h).strip()]

    # Score every (field, header) pair so we can do a greedy global
    # assignment that prevents one header from being claimed twice.
    # Each candidate carries (score, specificity, field, header) so a
    # tie at score=1.0 falls to whichever field had the more specific
    # alias (e.g. "ascap work id" beats the generic "work id").
    candidates: List[tuple] = []
    for field in CANONICAL_FIELDS:
        aliases = _aliases_for(field, canonical_source)
        if not aliases:
            continue
        for header in headers:
            score, specificity = _score_header(header, aliases)
            if score > 0.0:
                candidates.append((score, specificity, field, header))

    # Greedy: highest score wins, ties broken by more specific alias,
    # then by field/header name for deterministic ordering.
    candidates.sort(key=lambda t: (-t[0], -t[1], t[2], t[3]))

    mapping: Dict[str, Optional[str]] = {f: None for f in CANONICAL_FIELDS}
    field_scores: Dict[str, float] = {}
    used_headers: set = set()
    used_fields: set = set()

    for score, _specificity, field, header in candidates:
        if field in used_fields or header in used_headers:
            continue
        mapping[field] = header
        field_scores[field] = score
        used_fields.add(field)
        used_headers.add(header)

    # Aggregate confidence over fields that were mapped.
    if field_scores:
        avg_confidence = sum(field_scores.values()) / len(field_scores)
    else:
        avg_confidence = 0.0

    title_score = field_scores.get("track_title", 0.0)
    isrc_score = field_scores.get("isrc", 0.0)
    amount_score = field_scores.get("revenue", 0.0)
    has_title_or_isrc = max(title_score, isrc_score) >= REQUIRED_THRESHOLD
    has_amount = amount_score >= REQUIRED_THRESHOLD

    # Anti-poison guard: a 2-column file like ``["work","amount"]``
    # technically satisfies (title|isrc) AND amount — but every real
    # royalty statement carries at least one structured signal beyond
    # those two: an actual identifier (ISRC/UPC/ISWC/work_id), an
    # artist column, a quantity, a territory, or a platform. Require
    # one of those before declaring the mapping confident so that
    # mis-uploaded ad-hoc CSVs don't silently sail through.
    has_identifier = any(
        field_scores.get(f, 0.0) >= REQUIRED_THRESHOLD
        for f in ("isrc", "upc", "iswc", "work_id")
    )
    has_supporting_signal = has_identifier or any(
        field_scores.get(f, 0.0) >= REQUIRED_THRESHOLD
        for f in ("artist", "quantity", "territory", "platform")
    )
    confident = has_title_or_isrc and has_amount and has_supporting_signal

    unmapped = [h for h in headers if h not in used_headers]

    result: Dict[str, object] = dict(mapping)
    result["_confidence"] = round(avg_confidence, 3)
    result["_confident"] = confident
    result["_unmapped"] = unmapped
    result["_field_scores"] = {k: round(v, 3) for k, v in field_scores.items()}
    return result


__all__ = ["auto_map_columns", "CANONICAL_FIELDS", "FUZZY_THRESHOLD"]
