"""Dedicated BMI Statement Parser — Task #199 Phase 1.

Parses the multi-section BMI quarterly distribution statement format
described in ``attached_assets/cadence-parser-royalty-optimization_*.md``
(Diego Avendano archive, 19 statements 2021Q1–2025Q3).

The legacy ``backend.utils.pdf_statement_parser.parse_bmi_writer_statement``
handles the older single-section "Writer Distribution Statement" layout
(Marcus Jordan-style). It stays as a fallback for that simpler format.

This new parser handles the richer 9-section layout used in modern BMI
quarterly statements, with full source tracking (65+ tier names),
T-suffix detection, parens-as-negative international adjustments,
per-line period codes, the ``000000000`` aggregate-line case, and a
stated-vs-computed total reconciliation.

IMPORTANT — BMI economics
-------------------------
BMI pays *publishing-side performance* royalties only. The amounts on
each line item already reflect the writer's share. Downstream rate
intelligence must compute the **effective** per-stream rate as
``royalty / (count * writer_share_pct / 100)`` so platform comparisons
aren't skewed by per-line writer-share differences. See
``backend/services/rate_intelligence.py``.

Money math is in ``Decimal`` end-to-end. The ``to_row_dicts`` adapter
emits a row shape compatible with ``parse_uploaded_file``'s contract,
plus extra columns the dedicated ingestion path consumes to populate
the new ``royalty_statement_lines`` BMI columns.
"""
from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("cadence.bmi_parser")


# ---------------------------------------------------------------------------
# Section vocabulary
# ---------------------------------------------------------------------------

SECTION_PATTERNS: Dict[str, re.Pattern] = {
    "us_commercial_radio": re.compile(r"U\.?S\.?\s+Performances?\s*[-–]\s*Commercial Radio", re.I),
    "us_cable_tv": re.compile(r"U\.?S\.?\s+Performances?\s*[-–]\s*Cable Television", re.I),
    "us_local_tv": re.compile(r"U\.?S\.?\s+Performances?\s*[-–]\s*Local Television", re.I),
    "us_internet_audio": re.compile(r"U\.?S\.?\s+Performances?\s*[-–]\s*Internet Audio\b", re.I),
    "us_internet_av": re.compile(r"U\.?S\.?\s+Performances?\s*[-–]\s*Internet Audiovisual", re.I),
    "us_other": re.compile(r"U\.?S\.?\s+Performances?\s*[-–]\s*Other Sources", re.I),
    "admin_services": re.compile(r"Admin Services", re.I),
    "intl_audio": re.compile(r"International Performances?\s*[-–]\s*Audio\b", re.I),
    "intl_av": re.compile(r"International Performances?\s*[-–]\s*Audiovisual", re.I),
}

# Section → revenue category bucket consumed by valuation_v2.classify_bmi_source.
SECTION_TO_BUCKET: Dict[str, str] = {
    "us_commercial_radio": "performance",
    "us_cable_tv": "sync_adjacent",
    "us_local_tv": "sync_adjacent",
    "us_internet_audio": "streaming",
    "us_internet_av": "streaming",
    "us_other": "performance",
    "admin_services": "performance",
    "intl_audio": "international",
    "intl_av": "international",
}


# ---------------------------------------------------------------------------
# Source vocabulary (65+ real-world BMI source names, see spec)
# ---------------------------------------------------------------------------

KNOWN_SOURCES: List[str] = [
    # Amazon
    "AMAZON PRIME", "AMAZON UNLTD", "AMAZON UNLIMITED", "AMAZON VOD",
    "AMAZON STUDENT", "AMAZON FAMILY",
    # Apple
    "APPLE FAMILY", "APPLE INDIV", "APPLE INDIVIDUAL", "APPLE STUDENT",
    "APPLE TRIAL", "APPLE PLUS VOD", "APPLE VER TRIAL", "APPLE VERIZ BUN",
    "APPLE VERIZON", "APPLE WINBK FAM", "APPLE WINBK IND", "APPLE FITNESS",
    # Spotify
    "SPOTIFY FREE", "SPOTIFY PREM", "SPOTIFY PREMIUM", "SPOTIFY FAMILY",
    "SPOTIFY STUDENT", "SPOTIFY DUO",
    # YouTube
    "YOUTUBE FREE", "YOUTUBE MUSIC", "YOUTUBE PREMIUM", "YOUTUBE VOD",
    "YOUTUBE", "YOUTUBE RED",
    # Pandora
    "PANDORA", "PANDORA PLUS", "PANDORA PREMIUM",
    # SoundCloud
    "SOUNDCLOUD FREE", "SOUNDCLOUD GO", "SOUNDCLOUD PLUS",
    # Other DSPs
    "DEEZER", "TIDAL", "TIDAL WAVE", "PELOTON", "FACEBOOK",
    "NAPSTER PREMIER", "NAPSTER", "AUDIOMACK", "TIKTOK", "SNAPPIN",
    "SIRIUSXMDIGITAL", "SIRIUS XM FF", "SIRIUS XM COMM FF", "SIRIUSXM",
    # TV / Cable
    "BET", "BET HER", "FX NETWORK", "FXX", "DIRECTV ENT",
    "ECHOSTAR ENT", "IN DEMAND ENT", "HBO", "SHOWTIME", "MTV",
    "VH1", "COMEDY CENTRAL", "DISCOVERY", "TBS", "TNT",
    # Radio aggregates
    "COMMERCIAL RADIO", "RADIO",
]
KNOWN_SOURCES_SET = set(KNOWN_SOURCES)

# Map a source name onto a (platform, tier) pair used by rate intelligence.
_PLATFORM_TIER_MAP: Dict[str, Tuple[str, str]] = {}
for src in KNOWN_SOURCES:
    if " " in src:
        platform, _, tier = src.partition(" ")
    else:
        platform, tier = src, ""
    # Normalize platform aliases.
    aliases = {
        "AMAZON": "AMAZON",
        "APPLE": "APPLE",
        "SPOTIFY": "SPOTIFY",
        "YOUTUBE": "YOUTUBE",
        "PANDORA": "PANDORA",
        "SOUNDCLOUD": "SOUNDCLOUD",
        "SIRIUSXMDIGITAL": "SIRIUSXM",
        "SIRIUS": "SIRIUSXM",
    }
    _PLATFORM_TIER_MAP[src] = (aliases.get(platform, platform), tier or "")


def normalize_source(raw: str) -> Tuple[str, bool]:
    """Strip a trailing " T" tier-suffix and report whether it was present.

    Returns (canonical_source, t_suffix_flag).
    """
    raw = (raw or "").strip().upper()
    if raw.endswith(" T"):
        base = raw[:-2].strip()
        if base in KNOWN_SOURCES_SET or _looks_like_source_name(base):
            return base, True
    return raw, False


def _looks_like_source_name(s: str) -> bool:
    """Heuristic for sources we don't have in the vocabulary yet."""
    if not s or len(s) < 3:
        return False
    if any(c.isdigit() for c in s):
        return False
    return s.isupper()


def platform_tier_for(source: str) -> Tuple[str, str]:
    """Return (platform, tier) for a normalized source name.

    Falls back to splitting on whitespace if the source isn't in the
    known map — keeps new BMI source names usable without a code edit.
    """
    if source in _PLATFORM_TIER_MAP:
        return _PLATFORM_TIER_MAP[source]
    parts = source.split(" ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return source, ""


# ---------------------------------------------------------------------------
# Country / society dictionary (international section)
# ---------------------------------------------------------------------------

# Society codes seen on real BMI international sections.
KNOWN_SOCIETIES = {
    "APRA", "PRS", "SOCAN", "SADAIC", "UBC", "SABAM", "GEMA", "SACEM",
    "JASRAC", "STIM", "TONO", "SUISA", "AKM", "ZAIKS", "SACM", "ABRAMUS",
    "ACUM", "CASH", "COMPASS", "MACP", "MCSC", "MUST", "WAMI",
}

COUNTRY_SOCIETY_RE = re.compile(
    r"^(?P<country>[A-Z][A-Z .\-/]+?)\s*[-–]\s*(?P<society>[A-Z]{3,8})\s*$"
)


# ---------------------------------------------------------------------------
# Header / boilerplate strippers
# ---------------------------------------------------------------------------

PAGE_HEADER_PATTERNS: List[re.Pattern] = [
    re.compile(r"^Page\s+\d+\s+of\s+\d+\s*$", re.I),
    re.compile(r"^BROADCAST MUSIC,?\s*INC\.?\b", re.I),
    re.compile(r"^Royalty\s+BMI\s*®", re.I),
    re.compile(r"\d+ Music Square East", re.I),
    re.compile(r"7 World Trade Center", re.I),
    re.compile(r"8730 Sunset Blvd", re.I),
    re.compile(r"84 Harley House", re.I),
    re.compile(r"3340 Peachtree", re.I),
    re.compile(r"1400 S Congress", re.I),
    re.compile(r"WRITER DISTRIBUTION STATEMENT", re.I),
    re.compile(r"BMI\s*\(R\)", re.I),
    re.compile(r"^CONFIDENTIAL\b", re.I),
]


def _is_page_header(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    for p in PAGE_HEADER_PATTERNS:
        if p.search(s):
            return True
    return False


# ---------------------------------------------------------------------------
# Amount / count helpers
# ---------------------------------------------------------------------------

def parse_amount(s: str) -> Decimal:
    """Parse a dollar amount; (xx.xx) → -xx.xx; commas + $ stripped.

    Raises InvalidOperation only if the string is not amount-like; callers
    should catch and skip the line.
    """
    s = (s or "").strip().replace(",", "").replace("$", "")
    if not s or s == "-":
        return Decimal("0")
    if s.startswith("(") and s.endswith(")"):
        return -Decimal(s[1:-1])
    return Decimal(s)


def parse_count(s: str) -> Optional[int]:
    s = (s or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Line patterns
# ---------------------------------------------------------------------------

# Internet Audio / Commercial Radio / Internet AV row:
# TITLE WORK_NUM USE COUNT PERIOD SHARE% [WH] [BONUS] ROYALTY
_AUDIO_ROW_RE = re.compile(
    r"^(?P<title>[A-Z0-9][A-Z0-9 \-'\.&,/!?]*?)\s+"
    r"(?P<work>\d{9})\s+"
    r"(?P<use>[A-Z]{1,3})\s+"
    r"(?P<count>[\d,]+)\s+"
    r"(?P<period>\d{4,5})\s+"
    r"(?P<share>\d+\.\d+)%\s*"
    r"(?:\$(?P<wh>-?[\d,]+\.\d{2})\s+)?"
    r"(?:\$(?P<bonus>-?[\d,]+\.\d{2})\s+)?"
    r"\$(?P<royalty>-?[\d,]+\.\d{2})\s*$"
)

# Cable / Local TV row:
# COUNT TITLE WORK USE TIMING PERIOD SHARE% SUPER ROYALTY
_TV_ROW_RE = re.compile(
    r"^(?P<count>\d+)\s+"
    r"(?P<title>[A-Z0-9][A-Z0-9 \-'\.&,/!?]*?)\s+"
    r"(?P<work>\d{9})\s+"
    r"(?P<use>[A-Z]{1,3})\s+"
    r"(?P<timing>\d{2}:\d{2})\s+"
    r"(?P<period>\d{4,5})\s+"
    r"(?P<share>\d+\.\d+)%\s+"
    r"\$(?P<super>-?[\d,]+\.\d{2})\s+"
    r"\$(?P<royalty>-?[\d,]+\.\d{2})\s*$"
)

# International row (no count, no period code):
# TITLE WORK SOURCE [PERIOD] [Y] [WH] ROYALTY     (royalty may be in parens)
_INTL_ROW_RE = re.compile(
    r"^(?P<title>[A-Z0-9][A-Z0-9 \-'\.&,/!?]*?)\s+"
    r"(?P<work>\d{9})\s+"
    r"(?P<source>[A-Z][A-Z ]{2,30}?)\s*"
    r"(?:(?P<period>\d{4,5})\s+)?"
    r"(?P<adj>Y\s+)?"
    r"(?:\$(?P<wh>-?[\d,]+\.\d{2})\s+)?"
    r"(?P<royalty>\(?\$?-?[\d,]+\.\d{2}\)?)\s*$"
)

# Source line on its own (e.g. "SPOTIFY PREM" or "SPOTIFY PREM T").
_SOURCE_LINE_RE = re.compile(r"^([A-Z][A-Z0-9 ]{2,30}?)(?:\s+T)?\s*$")

# Total / subtotal lines we capture for validation.
_TOTAL_RE = re.compile(
    r"(?i)(Source Total|Current Activity Royalty Total|Super Usage Total|"
    r"Section Total|Grand Total)\s*\$?(-?[\d,]+\.\d{2})"
)


# ---------------------------------------------------------------------------
# Datamodel
# ---------------------------------------------------------------------------

@dataclass
class BMILineItem:
    title: str
    work_number: str
    use_code: str = ""
    count: Optional[int] = None
    period_code: str = ""
    writer_share_pct: Decimal = Decimal("0")
    withholding: Decimal = Decimal("0")
    royalty_amount: Decimal = Decimal("0")
    bonus_amount: Decimal = Decimal("0")
    super_usage: Decimal = Decimal("0")
    timing: str = ""
    series_film: str = ""
    section: str = ""
    source: str = ""
    source_t_suffix: bool = False
    country: str = ""
    society: str = ""
    is_adjustment: bool = False

    @property
    def is_aggregate(self) -> bool:
        return self.work_number == "000000000"

    @property
    def period_year(self) -> Optional[int]:
        if len(self.period_code) >= 4 and self.period_code[:4].isdigit():
            return int(self.period_code[:4])
        return None

    @property
    def period_quarter(self) -> Optional[int]:
        if len(self.period_code) == 5 and self.period_code[4].isdigit():
            q = int(self.period_code[4])
            return q if 1 <= q <= 4 else None
        return None


@dataclass
class BMIParsedStatement:
    affiliate_name: str = ""
    account_number: str = ""
    ip_number: str = ""
    distribution_date: str = ""
    performance_period: str = ""
    intl_accounting: str = ""
    total_pages: int = 0
    us_total: Decimal = Decimal("0")
    admin_total: Decimal = Decimal("0")
    intl_total: Decimal = Decimal("0")
    grand_total: Decimal = Decimal("0")
    line_items: List[BMILineItem] = field(default_factory=list)
    section_totals: Dict[str, Decimal] = field(default_factory=dict)
    parse_warnings: List[str] = field(default_factory=list)
    unparsed_lines: List[str] = field(default_factory=list)

    @property
    def computed_total(self) -> Decimal:
        return sum((li.royalty_amount for li in self.line_items), Decimal("0"))

    @property
    def validation_delta(self) -> Decimal:
        if self.grand_total == 0:
            return Decimal("0")
        return self.computed_total - self.grand_total

    @property
    def parse_quality(self) -> float:
        """0–1 score: 1.0 - share of unparsed lines, capped at delta tolerance.

        Parse quality combines two signals so a single bad signal can't
        artificially inflate it:
        - Line-level: 1.0 when no lines were skipped, scaling down with
          the share of unparsed lines vs. parsed lines.
        - Total-level: 1.0 when computed matches stated within $1, scaling
          down to 0 at >5% delta.
        """
        line_score = 1.0
        denom = len(self.line_items) + len(self.unparsed_lines)
        if denom > 0:
            line_score = max(0.0, 1.0 - (len(self.unparsed_lines) / denom))
        total_score = 1.0
        if self.grand_total and self.grand_total != 0:
            pct = abs(float(self.validation_delta) / float(self.grand_total))
            if pct >= 0.05:
                total_score = 0.0
            elif pct >= 0.001:
                total_score = max(0.0, 1.0 - (pct / 0.05))
        return round((line_score + total_score) / 2.0, 4)

    @property
    def unique_songs(self) -> int:
        return len({(li.title, li.work_number) for li in self.line_items})

    @property
    def unique_sources(self) -> int:
        return len({li.source for li in self.line_items if li.source})


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def is_bmi_quarterly_statement(content: bytes) -> bool:
    """True iff the bytes look like a multi-section BMI quarterly statement.

    We look for combination signals that the Diego-style format uses but
    that the older single-section "Writer Distribution Statement" parser
    in ``pdf_statement_parser`` does not: section headers like
    ``U.S. Performances - Internet Audio`` plus a 9-digit account number
    plus a "Distribution Date" line.
    """
    try:
        import pdfplumber  # noqa: WPS433
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            head = ""
            for page in pdf.pages[:3]:
                t = page.extract_text() or ""
                head += t + "\n"
    except Exception:
        return False
    head_u = head.upper()
    has_section = any(p.search(head) for p in SECTION_PATTERNS.values())
    has_account = bool(re.search(r"ACCOUNT\s*N[O0]\.?[:\s]+\d{9}", head_u))
    has_dist = "DISTRIBUTION DATE" in head_u
    has_bmi = "BROADCAST MUSIC" in head_u or "BMI" in head_u
    return has_bmi and has_section and (has_account or has_dist)


# ---------------------------------------------------------------------------
# Parser entry point
# ---------------------------------------------------------------------------

def parse_bmi_quarterly_pdf(content: bytes) -> Optional[BMIParsedStatement]:
    """Open a PDF, extract text per page, and parse into BMIParsedStatement."""
    try:
        import pdfplumber  # noqa: WPS433
        text_parts: List[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                text_parts.append(t)
        full_text = "\n".join(text_parts)
    except Exception as e:
        logger.error("BMI quarterly parser failed to open PDF: %s", e)
        return None
    return parse_bmi_quarterly_text(full_text)


def parse_bmi_quarterly_text(text: str) -> Optional[BMIParsedStatement]:
    """Pure-text parser, isolated from PDF I/O for testability."""
    if not text:
        return None
    result = BMIParsedStatement()
    lines = text.split("\n")

    _parse_header_block(lines, result)
    _walk_lines_with_state(lines, result)
    _validate(result)

    if not result.line_items:
        logger.warning("BMI quarterly parser produced 0 rows")
        return None

    logger.info(
        "BMI quarterly parse: %d items, %d songs, %d sources, "
        "stated=$%s computed=$%s delta=$%s quality=%.2f",
        len(result.line_items), result.unique_songs, result.unique_sources,
        result.grand_total, result.computed_total,
        result.validation_delta, result.parse_quality,
    )
    return result


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _parse_header_block(lines: List[str], result: BMIParsedStatement) -> None:
    """Pull account / period / summary fields out of the first ~120 lines."""
    head_text = "\n".join(lines[:120])

    m = re.search(r"Account\s*N[o0]\.?[:\s]+(\d{9})", head_text, re.I)
    if m:
        result.account_number = m.group(1)
    m = re.search(r"IP\s*N[o0]\.?[:\s]+([\d.]+)", head_text, re.I)
    if m:
        result.ip_number = m.group(1)
    m = re.search(r"Affiliate:\s*([A-Z][A-Z ()'\.\-]+)", head_text)
    if m:
        result.affiliate_name = m.group(1).strip()
    m = re.search(r"Distribution\s+Date:\s*([A-Za-z]+\s+\d+,?\s+\d{4})", head_text, re.I)
    if m:
        result.distribution_date = m.group(1)
    m = re.search(
        r"(?:U\.?S\.?\s+)?Performance\s+Period:\s*(\w+\s+QUARTER\s+\d{4})",
        head_text,
        re.I,
    )
    if m:
        result.performance_period = m.group(1)
    m = re.search(r"International:\s*(\d+\w+\s+ACCOUNTING)", head_text, re.I)
    if m:
        result.intl_accounting = m.group(1)
    m = re.search(r"Page\s+\d+\s+of\s+(\d+)", head_text, re.I)
    if m:
        result.total_pages = int(m.group(1))

    # Summary table — try a flexible pattern that catches "Total Earnings"
    # with 4 dollar amounts in U.S. / Admin / Intl / Total order.
    m = re.search(
        r"(?:Total\s+(?:Current\s+)?Earnings|Amount\s+Paid)\s*"
        r"\$?([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})",
        head_text,
        re.I,
    )
    if m:
        try:
            result.us_total = parse_amount(m.group(1))
            result.admin_total = parse_amount(m.group(2))
            result.intl_total = parse_amount(m.group(3))
            result.grand_total = parse_amount(m.group(4))
        except (InvalidOperation, ValueError):
            pass


def _detect_section(line: str) -> Optional[str]:
    """Return a section key if the line is a section header, else None."""
    for name, pat in SECTION_PATTERNS.items():
        if pat.search(line):
            return name
    return None


def _walk_lines_with_state(lines: List[str], result: BMIParsedStatement) -> None:
    """Single pass over the body, tracking section + source + country state."""
    current_section = ""
    current_source = ""
    current_t_suffix = False
    current_country = ""
    current_society = ""
    current_series_film = ""

    in_body = False  # don't try to parse rows until we see the first section

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if _is_page_header(line):
            continue

        # Section change?
        section = _detect_section(line)
        if section:
            current_section = section
            in_body = True
            current_source = ""
            current_t_suffix = False
            current_country = ""
            current_society = ""
            current_series_film = ""
            continue

        if not in_body:
            continue

        # Total / subtotal lines — record but don't emit as a line item.
        m_total = _TOTAL_RE.search(line)
        if m_total:
            try:
                result.section_totals[
                    f"{current_section}:{m_total.group(1).strip()}"
                ] = parse_amount(m_total.group(2))
            except (InvalidOperation, ValueError):
                pass
            continue

        # International country/society line.
        if current_section.startswith("intl"):
            m_cs = COUNTRY_SOCIETY_RE.match(line)
            if m_cs:
                current_country = m_cs.group("country").strip()
                current_society = m_cs.group("society").strip()
                continue

        # Source/Series header line (own line, no $ amounts on it).
        if "$" not in line and not any(c.isdigit() for c in line):
            m_src = _SOURCE_LINE_RE.match(line)
            if m_src:
                candidate = m_src.group(1).strip()
                if candidate in KNOWN_SOURCES_SET or _looks_like_source_name(candidate):
                    current_source, current_t_suffix = normalize_source(line)
                    current_series_film = ""
                    continue

        # Series/Film banner for TV sections (e.g. "Series/Film: ...").
        if current_section in ("us_cable_tv", "us_local_tv"):
            m_series = re.match(r"(?i)Series/?Film:\s*(.+)$", line)
            if m_series:
                current_series_film = m_series.group(1).strip()
                continue

        # Try the appropriate row parser.
        item: Optional[BMILineItem] = None
        if current_section in ("us_cable_tv", "us_local_tv"):
            item = _try_tv_row(line)
        elif current_section.startswith("intl"):
            item = _try_intl_row(line)
        else:
            # us_internet_audio / us_internet_av / us_commercial_radio /
            # us_other / admin_services all share the audio shape.
            item = _try_audio_row(line)

        if item is None:
            # Skip pure noise (headers we didn't catch); record numeric-looking
            # leftovers as unparsed for visibility.
            if any(c.isdigit() for c in line) and "$" in line:
                result.unparsed_lines.append(line)
            continue

        item.section = current_section
        # For intl rows the row regex captured the source per-line; only
        # overwrite if we have an explicit standalone source header.
        if current_source or not item.source:
            item.source = current_source or item.source
        item.source_t_suffix = current_t_suffix
        if current_section.startswith("intl"):
            item.country = current_country
            item.society = current_society
        if current_section in ("us_cable_tv", "us_local_tv"):
            item.series_film = current_series_film

        result.line_items.append(item)


def _try_audio_row(line: str) -> Optional[BMILineItem]:
    m = _AUDIO_ROW_RE.match(line)
    if not m:
        return None
    try:
        return BMILineItem(
            title=m.group("title").strip(),
            work_number=m.group("work"),
            use_code=m.group("use"),
            count=parse_count(m.group("count")),
            period_code=m.group("period"),
            writer_share_pct=Decimal(m.group("share")),
            withholding=parse_amount(m.group("wh") or "0"),
            bonus_amount=parse_amount(m.group("bonus") or "0"),
            royalty_amount=parse_amount(m.group("royalty")),
        )
    except (InvalidOperation, ValueError):
        return None


def _try_tv_row(line: str) -> Optional[BMILineItem]:
    m = _TV_ROW_RE.match(line)
    if not m:
        # TV rows can also fall through to the audio shape (some sources
        # don't report timing). Try that as a fallback.
        return _try_audio_row(line)
    try:
        return BMILineItem(
            title=m.group("title").strip(),
            work_number=m.group("work"),
            use_code=m.group("use"),
            count=parse_count(m.group("count")),
            period_code=m.group("period"),
            timing=m.group("timing"),
            writer_share_pct=Decimal(m.group("share")),
            super_usage=parse_amount(m.group("super")),
            royalty_amount=parse_amount(m.group("royalty")),
        )
    except (InvalidOperation, ValueError):
        return None


def _try_intl_row(line: str) -> Optional[BMILineItem]:
    m = _INTL_ROW_RE.match(line)
    if not m:
        return None
    try:
        # Carry the row-level source token (e.g. "PRS", "GEMA") onto
        # the line item so international source fidelity is preserved
        # through ingestion. The state-machine in ``_walk_lines_with_state``
        # leaves intl ``item.source`` alone unless ``current_source`` is
        # populated from a standalone source-header line.
        return BMILineItem(
            title=m.group("title").strip(),
            work_number=m.group("work"),
            source=(m.group("source") or "").strip(),
            period_code=(m.group("period") or ""),
            writer_share_pct=Decimal("0"),
            withholding=parse_amount(m.group("wh") or "0"),
            royalty_amount=parse_amount(m.group("royalty")),
            is_adjustment=bool(m.group("adj")),
        )
    except (InvalidOperation, ValueError):
        return None


def _validate(result: BMIParsedStatement) -> None:
    """Cross-check the computed total against the stated grand total."""
    if result.grand_total and result.grand_total != 0:
        delta = result.validation_delta
        if abs(delta) > Decimal("1.00"):
            result.parse_warnings.append(
                f"Stated grand total ${result.grand_total} vs computed "
                f"${result.computed_total} (delta=${delta})"
            )


# ---------------------------------------------------------------------------
# Adapter — produce the row dict shape `parse_uploaded_file` returns
# ---------------------------------------------------------------------------

# Header order kept in lockstep with the dict keys below. Downstream
# `parse_statement_to_lines` accepts any header set so the BMI extras are
# stored on the new RoyaltyStatementLine columns via the metadata path.
BMI_V2_HEADERS = [
    "Track Title", "Writer/Artist", "Work Number", "Source/Collector",
    "Source Detail", "Income Type", "Territory", "Units",
    "Writer Share", "Rate", "Gross Amount", "Net Amount",
    # Extras consumed by the dedicated ingestion path (not surfaced in
    # the generic mapping UI).
    "Platform Source", "Platform Tier", "T Suffix",
    "Period Code", "Section Code", "Country", "Society",
    "Is Adjustment", "Is Aggregate", "Super Usage",
]


def to_row_dicts(result: BMIParsedStatement) -> List[Dict[str, str]]:
    """Convert parsed line items to the dict-of-strings row shape the
    upload ingestion pipeline expects.
    """
    rows: List[Dict[str, str]] = []
    for li in result.line_items:
        platform, tier = platform_tier_for(li.source) if li.source else ("", "")
        territory = "International" if li.section.startswith("intl") else "US"
        rows.append({
            "Track Title": li.title,
            "Writer/Artist": "",  # BMI is per-affiliate; populated at statement level
            "Work Number": li.work_number,
            "Source/Collector": li.source or "BMI",
            "Source Detail": li.source or li.section,
            "Income Type": SECTION_TO_BUCKET.get(li.section, "performance"),
            "Territory": li.country or territory,
            "Units": str(li.count) if li.count is not None else "",
            "Writer Share": f"{li.writer_share_pct}%" if li.writer_share_pct else "",
            "Rate": "",
            "Gross Amount": str(li.royalty_amount),
            "Net Amount": str(li.royalty_amount),
            "Platform Source": li.source,
            "Platform Tier": tier,
            "T Suffix": "1" if li.source_t_suffix else "",
            "Period Code": li.period_code,
            "Section Code": li.section,
            "Country": li.country,
            "Society": li.society,
            "Is Adjustment": "1" if li.is_adjustment else "",
            "Is Aggregate": "1" if li.is_aggregate else "",
            "Super Usage": str(li.super_usage) if li.super_usage else "",
        })
    return rows


def to_metadata(result: BMIParsedStatement) -> Dict:
    """Top-level metadata dict that downstream ingestion uses for the
    statement-level reconciliation card and the parse-quality score."""
    return {
        "client_name": result.affiliate_name,
        "account_number": result.account_number,
        "ip_number": result.ip_number,
        "period": result.performance_period,
        "intl_accounting": result.intl_accounting,
        "distribution_date": result.distribution_date,
        "grand_total_net": float(result.grand_total) if result.grand_total else None,
        "computed_total_net": float(result.computed_total),
        "validation_delta": float(result.validation_delta),
        "parse_quality": result.parse_quality,
        "section_totals": {k: float(v) for k, v in result.section_totals.items()},
        "parse_warnings": list(result.parse_warnings),
        "unparsed_lines_count": len(result.unparsed_lines),
        "us_total": float(result.us_total) if result.us_total else None,
        "admin_total": float(result.admin_total) if result.admin_total else None,
        "intl_total": float(result.intl_total) if result.intl_total else None,
        "parser": "bmi_quarterly_v2",
        "suggested_mapping": {
            "track_title": "Track Title",
            "artist": "Writer/Artist",
            "revenue": "Net Amount",
            "quantity": "Units",
            "territory": "Territory",
            "platform": "Platform Source",
            "revenue_type": "Income Type",
            "gross_amount": "Gross Amount",
            "release_title": "Source Detail",
        },
    }
