"""Statement source-type registry.

Single source of truth for:
- the canonical enum of royalty-statement source types Cadence accepts,
- per-source-type column-name aliases used by the parser to suggest a
  mapping from a raw uploaded file's headers onto our internal field
  names (track_title, isrc, revenue, etc.),
- per-source-type metadata (period cadence, default currency, detection
  keywords) used by the parser orchestrator.

Operators add a new statement format by appending one entry to
``SOURCE_FORMAT_REGISTRY`` (and one value to ``StatementSourceType``).
No engine code edits required.

Backwards-compat:
- ``BASE_COLUMN_HINTS`` is the same dict that used to live in
  ``backend/routes/royalties.py`` as ``COLUMN_HINTS``.
- ``SOURCE_FORMAT_REGISTRY`` extends what used to be
  ``PRO_SOURCE_TYPES`` with the formats Tim Burnett's spec adds
  (MLC, HARRY_FOX, LABEL, DSP) on top of the existing PROs.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional


class StatementSourceType(str, Enum):
    """Canonical enum of royalty-statement source types.

    String-valued so it serializes naturally in JSON / FastAPI Forms
    and round-trips into ``RoyaltyStatement.source_type`` (which stays
    a nullable String column for forward compat with formats we
    haven't classified yet).

    **Canonical token policy (locked-in contract for downstream
    valuation / reconciliation work)**

    * Tokens are screaming-snake-case ASCII (``BMI``, ``ASCAP``,
      ``MLC``, ``HARRY_FOX``, ``LABEL``, ``DSP``, ``SOCAN``, ``PRS``,
      ``OTHER_PRO``, ``OTHER``) **with one deliberate exception**:
      ``SOUNDEXCHANGE`` stores its enum *value* as ``"SoundExchange"``
      (mixed case). This preserves backward compatibility with rows
      already persisted under the legacy mixed-case form across
      ``royalty_statements.source_type``, ``royalty_statement_lines``
      provenance, and analytics rollups. Migrating that token to
      ``"SOUNDEXCHANGE"`` would require a coordinated data backfill
      (see DEPLOYMENT.md §Future Work) and is intentionally deferred.
      Downstream code MUST compare against ``StatementSourceType``
      members rather than string literals when ambiguity matters.

    * The strict task spec named only BMI / ASCAP / SESAC / MLC /
      HARRY_FOX / LABEL / SOUNDEXCHANGE / DSP / OTHER. The enum
      additionally exposes ``SOCAN``, ``PRS``, and ``OTHER_PRO`` as a
      forward-compatibility extension — international PROs and
      generic-PRO buckets surface frequently in real statements
      (UK / Canadian publishers, smaller societies licensing through
      pass-throughs) and rejecting them at the API boundary would
      force operators to lie about the source. Treat these as
      **registry extensions**, not contract changes — they are safe
      for consumers that switch on ``StatementSourceType`` (default
      branch handles them) and ignored by source-specific format
      hints in ``SOURCE_FORMAT_REGISTRY`` if a format isn't defined.
    """

    BMI = "BMI"
    ASCAP = "ASCAP"
    SESAC = "SESAC"
    MLC = "MLC"
    HARRY_FOX = "HARRY_FOX"
    LABEL = "LABEL"
    SOUNDEXCHANGE = "SoundExchange"  # see canonical token policy above
    SOCAN = "SOCAN"  # registry extension (international PRO)
    PRS = "PRS"  # registry extension (international PRO)
    DSP = "DSP"
    OTHER_PRO = "OTHER_PRO"  # registry extension (generic PRO bucket)
    OTHER = "OTHER"


# Friendly display labels for the frontend dropdown. Keep keys aligned
# to ``StatementSourceType`` values.
SOURCE_TYPE_LABELS: Dict[str, str] = {
    StatementSourceType.DSP.value: "DSP / Distributor (Spotify, Apple Music, DistroKid, etc.)",
    StatementSourceType.BMI.value: "BMI",
    StatementSourceType.ASCAP.value: "ASCAP",
    StatementSourceType.SESAC.value: "SESAC",
    StatementSourceType.MLC.value: "MLC (Mechanical Licensing Collective)",
    StatementSourceType.HARRY_FOX.value: "Harry Fox Agency",
    StatementSourceType.LABEL.value: "Label / Publisher Statement",
    StatementSourceType.SOUNDEXCHANGE.value: "SoundExchange",
    StatementSourceType.SOCAN.value: "SOCAN",
    StatementSourceType.PRS.value: "PRS for Music",
    StatementSourceType.OTHER_PRO.value: "Other PRO",
    StatementSourceType.OTHER.value: "Other",
}


# Generic header aliases. The parser starts from these and overlays
# the per-source ``extra_hints`` from ``SOURCE_FORMAT_REGISTRY`` when
# a source type is detected.
BASE_COLUMN_HINTS: Dict[str, List[str]] = {
    "isrc": ["isrc"],
    "upc": ["upc", "barcode"],
    "track_title": [
        "title", "track", "song", "track_title", "song_title", "track name", "song name",
        "work title", "composition", "composition title", "work", "musical work",
    ],
    "artist": [
        "artist", "performer", "band", "artist name", "primary artist",
        "writer", "writer name", "composer", "author", "songwriter",
        "interested party", "ip name", "affiliate name", "member name",
    ],
    "revenue": [
        "revenue", "amount", "earnings", "net", "royalty", "payment", "gross", "total", "payout",
        "royalty amount", "net amount", "gross amount", "total earned", "net royalty",
        "domestic amount", "foreign amount", "total amount", "license fee",
        "accrued amount", "accrual amount",
    ],
    "quantity": [
        "quantity", "streams", "plays", "downloads", "units", "count",
        "performances", "performance count", "feature performances", "total performances",
        "credits", "detections", "spins",
    ],
    "territory": ["territory", "country", "region", "market"],
    "platform": [
        "platform", "store", "service", "dsp", "source",
        "licensee", "music user", "station", "network", "broadcaster",
        "survey type", "medium", "use type",
    ],
    "revenue_type": [
        "type", "revenue_type", "sale type", "transaction type", "usage type",
        "right type", "rights type", "royalty type", "income type", "license type",
        "performance type", "category",
    ],
    "publisher": [
        "publisher", "publisher name", "original publisher", "sub-publisher",
        "admin publisher", "pub name",
    ],
    "iswc": ["iswc", "work code", "work id"],
    "work_id": [
        "work id", "work #", "work number", "song code", "song number", "internal id",
        "bmi work#", "ascap work id", "sesac work id", "bmi work id",
    ],
    "share_percentage": [
        "share", "share %", "ownership", "ownership %", "percentage",
        "writer share", "publisher share", "split", "pro rata",
    ],
}


# Per-source format spec. Each entry declares:
#   - keywords: substrings the auto-detector looks for in headers /
#     filename / source_name to identify this source type.
#   - period_cadence: typical reporting cadence ("monthly",
#     "quarterly", "semi-annual", "varies"). Used by the valuation
#     engine and for sanity-checking reported periods.
#   - default_currency: the currency these statements are usually
#     denominated in if the upload form omits one.
#   - extra_hints: per-field header aliases that take precedence over
#     ``BASE_COLUMN_HINTS`` when this source is detected.
SOURCE_FORMAT_REGISTRY: Dict[str, Dict] = {
    StatementSourceType.BMI.value: {
        "keywords": ["bmi", "broadcast music"],
        "period_cadence": "quarterly",
        "default_currency": "USD",
        "extra_hints": {
            "track_title": ["work title", "song title"],
            "artist": ["writer", "writer name", "affiliated writer"],
            "revenue": ["current activity royalty", "royalty amount", "total earned", "accrued amount"],
            "quantity": ["performances", "performance count", "credits", "total performances"],
            "work_id": ["bmi work#", "work #", "bmi work id", "song number"],
            "platform": ["source", "survey type", "medium"],
        },
    },
    StatementSourceType.ASCAP.value: {
        "keywords": ["ascap", "american society"],
        "period_cadence": "quarterly",
        "default_currency": "USD",
        "extra_hints": {
            "track_title": ["title", "work title"],
            "artist": ["writer/publisher", "interested party", "writer name"],
            "revenue": ["dollars", "amount", "domestic amount", "foreign amount", "total earned"],
            "quantity": ["credits", "performances"],
            "work_id": ["ascap work id", "work id"],
        },
    },
    StatementSourceType.SESAC.value: {
        "keywords": ["sesac"],
        "period_cadence": "quarterly",
        "default_currency": "USD",
        "extra_hints": {
            "track_title": ["composition", "title"],
            "artist": ["affiliate", "writer"],
            "revenue": ["royalty", "amount", "net amount"],
            "quantity": ["performances", "detections"],
            "work_id": ["sesac work id", "song code"],
        },
    },
    StatementSourceType.MLC.value: {
        "keywords": ["mlc", "mechanical licensing collective", "the mlc", "the_mlc"],
        "period_cadence": "monthly",
        "default_currency": "USD",
        "extra_hints": {
            "track_title": ["song title", "track title", "title", "work title"],
            "artist": ["performer", "artist", "writer"],
            "revenue": ["royalty", "amount", "net amount", "total earned", "payment amount"],
            "isrc": ["isrc"],
            "iswc": ["iswc", "hfa song code"],
            "quantity": ["streams", "plays", "uses"],
            "platform": ["service", "dsp", "licensee"],
        },
    },
    StatementSourceType.HARRY_FOX.value: {
        "keywords": ["harry fox", "harry_fox", "harry-fox", "hfa", "rumblefish"],
        "period_cadence": "quarterly",
        "default_currency": "USD",
        "extra_hints": {
            "track_title": ["song title", "track title", "title"],
            "artist": ["recording artist", "performer", "artist"],
            "revenue": ["royalty", "net amount", "amount due", "payment amount"],
            "isrc": ["isrc"],
            "iswc": ["iswc", "hfa song code", "hfa code"],
            "quantity": ["units", "downloads", "streams"],
            "platform": ["licensee", "service"],
        },
    },
    StatementSourceType.LABEL.value: {
        "keywords": ["label statement", "record label", "master royalty"],
        "period_cadence": "semi-annual",
        "default_currency": "USD",
        "extra_hints": {
            "track_title": ["track", "track title", "title", "release title"],
            "artist": ["artist", "primary artist"],
            "revenue": ["net royalty", "royalty earned", "artist royalty", "amount payable"],
            "isrc": ["isrc"],
            "upc": ["upc", "barcode"],
            "quantity": ["units sold", "units", "streams", "downloads"],
            "platform": ["channel", "configuration", "format"],
            "territory": ["territory", "country"],
        },
    },
    StatementSourceType.SOUNDEXCHANGE.value: {
        "keywords": ["soundexchange", "sound exchange"],
        "period_cadence": "quarterly",
        "default_currency": "USD",
        "extra_hints": {
            "track_title": ["featured title", "track title", "sound recording"],
            "artist": ["featured artist", "artist"],
            "revenue": ["royalty", "amount"],
            "quantity": ["performances", "plays"],
        },
    },
    StatementSourceType.SOCAN.value: {
        "keywords": ["socan"],
        "period_cadence": "quarterly",
        "default_currency": "CAD",
        "extra_hints": {
            "track_title": ["work title", "title"],
            "artist": ["member", "writer"],
            "revenue": ["distribution amount", "amount"],
        },
    },
    StatementSourceType.PRS.value: {
        "keywords": ["prs", "prs for music"],
        "period_cadence": "quarterly",
        "default_currency": "GBP",
        "extra_hints": {
            "track_title": ["work title", "title"],
            "artist": ["writer", "member"],
            "revenue": ["royalty", "amount", "net"],
        },
    },
    StatementSourceType.DSP.value: {
        "keywords": ["spotify", "apple music", "amazon music", "youtube music", "tidal", "deezer", "distrokid", "tunecore", "cd baby", "stem"],
        "period_cadence": "monthly",
        "default_currency": "USD",
        "extra_hints": {
            "track_title": ["track title", "track name", "title"],
            "artist": ["artist name", "artist", "primary artist"],
            "revenue": ["earnings (usd)", "earnings", "royalty", "net amount", "amount", "net revenue"],
            "isrc": ["isrc"],
            "upc": ["upc", "barcode"],
            "quantity": ["streams", "quantity", "downloads", "units"],
            "platform": ["store", "service", "dsp"],
            "territory": ["country", "country of sale", "territory"],
        },
    },
}


# Lower-cased lookup: arbitrary user-supplied string → canonical enum
# value. Used by ``canonical_source_type``. Keys here are tolerated
# spellings; values must be a member of ``StatementSourceType``.
_SOURCE_TYPE_ALIASES: Dict[str, str] = {
    # Canonical values themselves (case-insensitive match)
    **{v.lower(): v for v in SOURCE_FORMAT_REGISTRY.keys()},
    StatementSourceType.OTHER.value.lower(): StatementSourceType.OTHER.value,
    StatementSourceType.OTHER_PRO.value.lower(): StatementSourceType.OTHER_PRO.value,
    # Common spellings
    "sound exchange": StatementSourceType.SOUNDEXCHANGE.value,
    "harry fox": StatementSourceType.HARRY_FOX.value,
    "harry fox agency": StatementSourceType.HARRY_FOX.value,
    "hfa": StatementSourceType.HARRY_FOX.value,
    "the mlc": StatementSourceType.MLC.value,
    "mechanical licensing collective": StatementSourceType.MLC.value,
    "label": StatementSourceType.LABEL.value,
    "publisher": StatementSourceType.LABEL.value,
    "publisher statement": StatementSourceType.LABEL.value,
    "prs for music": StatementSourceType.PRS.value,
    "other pro": StatementSourceType.OTHER_PRO.value,
}


def canonical_source_type(value: Optional[str]) -> Optional[str]:
    """Resolve an arbitrary case-insensitive source-type string to a
    canonical ``StatementSourceType`` value.

    Returns ``None`` for an empty / missing input.
    Returns ``None`` for an unrecognized non-empty input — callers
    that need strict validation should compare against ``None`` and
    raise an HTTP 400.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return _SOURCE_TYPE_ALIASES.get(s.lower())


def get_format_spec(source_type: Optional[str]) -> Optional[Dict]:
    """Return the registry entry for a (possibly non-canonical) source
    type, or ``None`` if no format spec is registered.
    """
    canonical = canonical_source_type(source_type)
    if not canonical:
        return None
    return SOURCE_FORMAT_REGISTRY.get(canonical)


# Display-ordered list of (value, label) tuples for the frontend
# dropdown. Order: DSP first (most common upload), then PROs in usage
# order, then mechanical / label sources, then catch-alls.
DROPDOWN_ORDER: List[str] = [
    StatementSourceType.DSP.value,
    StatementSourceType.BMI.value,
    StatementSourceType.ASCAP.value,
    StatementSourceType.SESAC.value,
    StatementSourceType.MLC.value,
    StatementSourceType.HARRY_FOX.value,
    StatementSourceType.LABEL.value,
    StatementSourceType.SOUNDEXCHANGE.value,
    StatementSourceType.SOCAN.value,
    StatementSourceType.PRS.value,
    StatementSourceType.OTHER_PRO.value,
    StatementSourceType.OTHER.value,
]
