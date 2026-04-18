import re
import io
import logging
from datetime import date
from typing import Optional, Tuple

logger = logging.getLogger("cadence")

INCOME_TYPES = [
    "MECHANICAL - BROADCAST",
    "MECHANICAL - DIGITAL",
    "MECHANICAL - DOWNLOAD",
    "MECHANICAL - STREAMING",
    "MECHANICAL - VIDEO",
    "MECHANICAL",
    "OTHER - LYRICS",
    "OTHER - YOUTUBE",
    "PERF - DOMESTIC",
    "PERF - FOREIGN DOWNLOAD",
    "PERF - FOREIGN RADIO",
    "PERF - FOREIGN STREAMING",
    "PERF - FOREIGN TELEVISION",
    "PERF - FOREIGN",
    "SYNCHRONIZATION",
]

HEADER_LINE_PATTERNS = [
    re.compile(r"^Title\s+\(Writer/Artist\)", re.IGNORECASE),
    re.compile(r"^Source\s+Production\s+Income\s+Type", re.IGNORECASE),
]

CLIENT_PATTERN = re.compile(r"^Client:\s*\((\d+)\)\s*(.+?)(?:\s+Page\s+\d+)?$", re.IGNORECASE)
PERIOD_PATTERN = re.compile(r"^For the Period:\s*(.+)$", re.IGNORECASE)
TOTAL_PATTERN = re.compile(r"^Total:\s*([\d,]+\.\d+)\s+([\d,]+\.\d+)$")
GRAND_TOTAL_PATTERN = re.compile(r"^Grand\s+Total:?\s*([\d,]+\.\d+)\s+([\d,]+\.\d+)$", re.IGNORECASE)

DATA_LINE_RE = re.compile(
    r"^(.+?)\s+"
    r"(\d[\d,]*)\s+"
    r"(\(?-?[\d,]*\.?\d+\)?)\s+"
    r"(\d+\.\d+%)\s+"
    r"(\(?-?[\d,]*\.?\d+\)?)$"
)

DATA_LINE_NO_UNITS_RE = re.compile(
    r"^(.+?)\s+"
    r"(\(?-?[\d,]*\.?\d+\)?)\s+"
    r"(\d+\.\d+%)\s+"
    r"(\(?-?[\d,]*\.?\d+\)?)$"
)

DATA_LINE_MINIMAL_RE = re.compile(
    r"^(.+?)\s+"
    r"(-?[\d,]+\.\d{2})\s+"
    r"(-?[\d,]+\.\d{2})$"
)

SUBTOTAL_RE = re.compile(
    r"^([\d,]*\.?\d+)\s+([\d,]*\.?\d+)$"
)

WRITER_LINE_RE = re.compile(r"^\(([A-Za-z][A-Za-z\s,/.'&\-]+)\)$")
WRITER_CONT_RE = re.compile(r"^[A-Za-z][A-Za-z\s,/.'&\-]*\)$")
WRITER_START_RE = re.compile(r"^\([A-Za-z][A-Za-z\s,/.'&\-]*$")

KNOWN_SOURCES = {
    "BMI", "ASCAP", "SESAC", "SOCAN", "PRS", "APRA", "GEMA", "SACEM",
    "CMRRA", "KOBALT", "THE MLC", "MCPS", "HARRY FOX", "HFA",
    "MUSIC REPORTS - AMAZON MUSIC U", "MUSIC REPORTS - TWITCH",
    "YOUTUBE RESIDUAL LIQUIDATION", "KOBALT (DIGITAL)", "KOBALT BLACK BOX",
}


def _is_header_line(line: str) -> bool:
    return any(p.match(line) for p in HEADER_LINE_PATTERNS)


def _is_source_line(line: str) -> bool:
    stripped = line.strip()
    if stripped in KNOWN_SOURCES:
        return True
    if "(" in stripped or ")" in stripped:
        return False
    if len(stripped) < 40 and stripped.isupper() and not any(c.isdigit() for c in stripped):
        words = stripped.split()
        if 1 <= len(words) <= 6:
            if not any(it in stripped for it in INCOME_TYPES):
                return True
    return False


def _split_income_type(text: str) -> tuple:
    for it in INCOME_TYPES:
        idx = text.find(it)
        if idx >= 0:
            before = text[:idx].strip()
            after = text[idx + len(it):].strip()
            return before, it, after
    return text, "", ""


def _parse_amount(s: str) -> float:
    return float(s.replace(",", ""))


_MONTH_TO_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

# Patterns we recognize at the top of PRO/publisher statements:
#   "Performance Period: Jul - Dec 2023"
#   "Statement Period: July 1, 2023 - December 31, 2023"
#   "For the Period: Jul - Dec 2023"
#   "Royalty Distribution Period: Jan - Jun 2024"
#   "Distribution Period: Q1 2024"
#   "Period Ending: 12/31/2023"
_PERIOD_HEADER_RE = re.compile(
    r"(?i)(?:performance\s+period|statement\s+period|royalty\s+distribution\s+period|"
    r"distribution\s+period|for\s+the\s+period|reporting\s+period|royalty\s+period|"
    r"earnings\s+period|accounting\s+period|period\s+covered|period)\s*[:\-]?\s*(.+?)$",
    re.MULTILINE,
)
_MONTH_RANGE_RE = re.compile(
    r"(?i)\b([a-z]{3,9})\.?\s*(\d{0,2})\s*[,\-/]?\s*(\d{4})?\s*[\-\u2013to]+\s*([a-z]{3,9})\.?\s*(\d{0,2})\s*[,\-/]?\s*(\d{4})"
)
# "1Q 2024", "Q1 2024", "1st Quarter 2024", "First Quarter 2024"
_QUARTER_RE = re.compile(
    r"(?i)\b(?:(?P<n1>[1-4])(?:st|nd|rd|th)?\s*(?:q|quarter)|q\s*(?P<n2>[1-4])|"
    r"(?P<word>first|second|third|fourth)\s+quarter)\b[\s,]*(?P<year>\d{4})"
)
_QUARTER_WORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}
# "1H 2024", "H1 2024", "First Half 2024", "Second Half 2024"
_HALF_RE = re.compile(
    r"(?i)\b(?:(?P<n1>[12])\s*h|h\s*(?P<n2>[12])|"
    r"(?P<word>first|second)\s+half)\b[\s,]*(?P<year>\d{4})"
)
_HALF_WORD = {"first": 1, "second": 2}
# "From 1/1/2024 to 6/30/2024", "01/01/2024 - 06/30/2024"
_DATE_PAIR_RE = re.compile(
    r"(?:from\s+)?(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})\s*(?:to|through|-|\u2013)\s*"
    r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})",
    re.IGNORECASE,
)
# "Period Ending: 12/31/2023"
_PERIOD_ENDING_RE = re.compile(
    r"(?i)period\s+ending\s*[:\-]?\s*(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})"
)


def _last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    from calendar import monthrange
    return monthrange(year, month)[1]


def _norm_year(y: int) -> int:
    if y < 100:
        return 2000 + y if y < 70 else 1900 + y
    return y


def parse_period_from_text(text: str) -> Tuple[Optional[date], Optional[date]]:
    """Best-effort period extraction from the first page or two of a statement.

    Returns (period_start, period_end) — either may be None if not parseable.
    Recognizes:
      * "Performance Period: Jul - Dec 2023"
      * "Statement Period: July 1, 2023 - December 31, 2023"
      * "Royalty Distribution Period: 1H 2024" / "Q1 2024" / "First Half 2024"
      * "From 01/01/2024 to 06/30/2024"
      * "Period Ending: 12/31/2023"  (infers half-year ending on that date)
    """
    if not text:
        return None, None
    window = text[:8000]

    # 1) Try header line + month-range (most explicit).
    for m in _PERIOD_HEADER_RE.finditer(window):
        candidate = m.group(1).strip()

        rng = _MONTH_RANGE_RE.search(candidate)
        if rng:
            start_mon = _MONTH_TO_NUM.get(rng.group(1).lower().rstrip("."))
            end_mon = _MONTH_TO_NUM.get(rng.group(4).lower().rstrip("."))
            if start_mon and end_mon:
                end_year_str = rng.group(6)
                start_year_str = rng.group(3) or end_year_str
                try:
                    start_year = int(start_year_str)
                    end_year = int(end_year_str)
                    start_day = int(rng.group(2)) if rng.group(2) else 1
                    end_day = int(rng.group(5)) if rng.group(5) else _last_day_of_month(end_year, end_mon)
                    return date(start_year, start_mon, start_day), date(end_year, end_mon, end_day)
                except (TypeError, ValueError):
                    pass

        # Quarter notation under a period header.
        q = _QUARTER_RE.search(candidate)
        if q:
            try:
                year = int(q.group("year"))
                qnum = int(q.group("n1") or q.group("n2") or 0) or _QUARTER_WORD.get(
                    (q.group("word") or "").lower(), 0
                )
                if qnum:
                    s_mon = (qnum - 1) * 3 + 1
                    e_mon = s_mon + 2
                    return date(year, s_mon, 1), date(year, e_mon, _last_day_of_month(year, e_mon))
            except (TypeError, ValueError):
                pass

        # Half-year notation under a period header.
        h = _HALF_RE.search(candidate)
        if h:
            try:
                year = int(h.group("year"))
                hnum = int(h.group("n1") or h.group("n2") or 0) or _HALF_WORD.get(
                    (h.group("word") or "").lower(), 0
                )
                if hnum == 1:
                    return date(year, 1, 1), date(year, 6, 30)
                if hnum == 2:
                    return date(year, 7, 1), date(year, 12, 31)
            except (TypeError, ValueError):
                pass

        # Numeric date pair under a period header.
        dp = _DATE_PAIR_RE.search(candidate)
        if dp:
            try:
                s_m, s_d, s_y = int(dp.group(1)), int(dp.group(2)), _norm_year(int(dp.group(3)))
                e_m, e_d, e_y = int(dp.group(4)), int(dp.group(5)), _norm_year(int(dp.group(6)))
                return date(s_y, s_m, s_d), date(e_y, e_m, e_d)
            except (TypeError, ValueError):
                pass

    # 2) Free-floating "Period Ending: 12/31/2023" — infer the half/quarter
    #    that ends on that date so we don't make up a 3-year window.
    pe = _PERIOD_ENDING_RE.search(window)
    if pe:
        try:
            m_, d_, y_ = int(pe.group(1)), int(pe.group(2)), _norm_year(int(pe.group(3)))
            end_d = date(y_, m_, d_)
            # If end_d looks like end-of-quarter, infer that quarter; otherwise
            # infer the half-year ending on that date.
            if (m_, d_) in {(3, 31), (6, 30), (9, 30), (12, 31)}:
                # half-year preference: Jun 30 → H1, Dec 31 → H2
                if (m_, d_) == (6, 30):
                    return date(y_, 1, 1), end_d
                if (m_, d_) == (12, 31):
                    return date(y_, 7, 1), end_d
                # quarter
                qstart_mon = ((m_ - 1) // 3) * 3 + 1
                return date(y_, qstart_mon, 1), end_d
            # Generic fallback: 6 months ending on end_d.
            from dateutil.relativedelta import relativedelta  # type: ignore
            return end_d - relativedelta(months=5, day=1), end_d
        except Exception:
            pass

    # NOTE: We deliberately do NOT scan for free-floating quarter/half
    # tokens (e.g. a stray "Q1 2024" in a table cell). Without an
    # accompanying period header, those tokens produce false positives
    # from narrative text or summary tables. Quarter/half phrasing is
    # only honoured when it appears under a period header — handled in
    # step 1 above.

    return None, None


def parse_period_from_pdf(content: bytes) -> Tuple[Optional[date], Optional[date]]:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            text = ""
            # Scan first 3 pages — some PRO statements bury the period below
            # a long client-info block on page 1.
            for page in pdf.pages[:3]:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return parse_period_from_text(text)
    except Exception as e:
        logger.warning(f"parse_period_from_pdf failed: {e}")
        return None, None


VANGUARD_REV_TYPE_PREFIXES = [
    ("Performance Royalties (Domestic)", "Performance Royalties (Do"),
    ("Performance Royalties (International)", "Performance Royalties (In"),
    ("Mechanical Royalties - Streaming", "Mechanical Royalties - St"),
    ("Mechanical Royalties - Physical", "Mechanical Royalties - Ph"),
    ("Mechanical Royalties - Downloads", "Mechanical Royalties - Do"),
    ("Synchronization Fees", "Synchronization Fees"),
    ("Print Royalties", "Print Royalties"),
    ("Micro-Sync / User Generated Content", "Micro-Sync / User Generat"),
]

VANGUARD_ISRC_RE = re.compile(r"\b([A-Z]{2}[A-Z0-9]{3}\d{7})\b")
VANGUARD_DETAIL_RE = re.compile(
    r"^(?P<prefix>.+?)\s+(?P<units>[\d,]+|--|-)\s+(?P<rate>\$[\d,]+\.\d+|--|-)\s+\$(?P<amount>[\d,]+\.\d{2})$"
)
VANGUARD_WORK_TOTAL_RE = re.compile(r"^Work Total:\s*\$([\d,]+\.\d{2})$", re.IGNORECASE)
VANGUARD_GRAND_TOTAL_RE = re.compile(
    r"(?i)Gross\s+Royalties\s+Earned:\s*\$([\d,]+\.\d{2})"
)
VANGUARD_TABLE_HEADER_RE = re.compile(
    r"^WORK\s+TITLE\s+ISRC\s+REVENUE\s+TYPE", re.IGNORECASE
)


def is_vanguard_statement(content: bytes) -> bool:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages[:3]:
                text = page.extract_text() or ""
                if "VANGUARD" in text.upper() and (
                    "VANGUARD MUSIC PUBLISHING" in text.upper()
                    or "VANGUARD ROYALTY STATEMENT" in text.upper()
                ):
                    return True
    except Exception:
        pass
    return False


def _split_vanguard_prefix(prefix: str, current_rev_type: str) -> tuple:
    """Strip a known revenue-type prefix from `prefix` and return
    (revenue_type_full, source). If no prefix matches, source = full prefix and
    revenue_type stays at current_rev_type."""
    for full_name, marker in VANGUARD_REV_TYPE_PREFIXES:
        if prefix.startswith(marker + " "):
            return full_name, prefix[len(marker):].strip()
        if prefix == marker:
            return full_name, ""
    return current_rev_type, prefix


def parse_vanguard_statement(content: bytes) -> Optional[dict]:
    """Parser for the Vanguard Music Publishing statement format.

    The Vanguard PDF text layout (no detectable tables) looks like:
        WORK TITLE ISRC REVENUE TYPE SOURCE UNITS/PLAYS RATE AMOUNT
        Break My Soul USSM12202365 Performance Royalties (Do Pandora 9,766 $6.1253 $59.82
            TikTok 7,167 $3.4087 $24.43
            Performance Royalties (In Facebook/Meta 3,540 $2.0282 $7.18
            ...
            Work Total: $2,032.61
        Deja Vu USUG12100660 Performance Royalties (Do Deezer ...

    Revenue-type names are truncated by the column width ("Performance
    Royalties (Do" = Domestic, "Mechanical Royalties - Do" = Downloads).
    The first row of each work carries the work title + ISRC; subsequent
    rows for the same work omit them. Subsequent rows for the same revenue
    type omit the type. Rate/units may be "--".
    """
    import pdfplumber

    metadata = {
        "client_name": None,
        "period": None,
        "grand_total_net": None,
    }
    rows = []

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            full_text = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"
    except Exception as e:
        logger.error(f"Vanguard parser: failed to open PDF: {e}")
        return None

    return _parse_vanguard_text(full_text)


def _parse_vanguard_text(full_text: str) -> Optional[dict]:
    """Pure-text Vanguard parser. Split out from parse_vanguard_statement so
    it can be unit-tested without a real PDF on disk."""
    metadata = {
        "client_name": None,
        "period": None,
        "grand_total_net": None,
    }
    rows = []

    if not full_text:
        return None

    grand_match = VANGUARD_GRAND_TOTAL_RE.search(full_text)
    if grand_match:
        try:
            metadata["grand_total_net"] = float(grand_match.group(1).replace(",", ""))
        except ValueError:
            pass

    writer_match = re.search(r"(?im)^Writer:\s*(.+?)(?:\s+Publisher:|$)", full_text)
    if writer_match:
        metadata["client_name"] = writer_match.group(1).strip()

    period_match = re.search(r"(?i)Statement\s+Period:\s*(.+?)(?:\n|$)", full_text)
    if period_match:
        metadata["period"] = period_match.group(1).strip()

    current_work_title = ""
    current_isrc = ""
    current_rev_type = ""

    for raw_line in full_text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        if VANGUARD_TABLE_HEADER_RE.match(line):
            continue
        upper_line = line.upper()
        if "VANGUARD MUSIC PUBLISHING" in upper_line and "ROYALTY STATEMENT" in upper_line:
            continue
        if "CONFIDENTIAL" in upper_line and "PAGE" in upper_line:
            continue
        if upper_line.startswith("PAYMENT SUMMARY") or upper_line.startswith("TERMS"):
            break

        wt = VANGUARD_WORK_TOTAL_RE.match(line)
        if wt:
            continue

        isrc_m = VANGUARD_ISRC_RE.search(line)
        m = VANGUARD_DETAIL_RE.match(line)
        if not m:
            continue

        prefix = m.group("prefix").strip()
        units_raw = m.group("units")
        rate_raw = m.group("rate")
        amount_raw = m.group("amount")

        if isrc_m and isrc_m.group(1) in prefix:
            isrc = isrc_m.group(1)
            before, after = prefix.split(isrc, 1)
            new_title = before.strip()
            if new_title:
                current_work_title = new_title
            current_isrc = isrc
            remainder = after.strip()
            current_rev_type, source = _split_vanguard_prefix(remainder, current_rev_type)
        else:
            current_rev_type, source = _split_vanguard_prefix(prefix, current_rev_type)

        units_val = "" if units_raw in ("--", "-") else units_raw.replace(",", "")
        amount_val = amount_raw.replace(",", "")

        rows.append({
            "Track Title": current_work_title,
            "Writer/Artist": metadata.get("client_name") or "",
            "ISRC": current_isrc,
            "Source/Collector": "Vanguard Music Publishing",
            "Source Detail": source,
            "Income Type": current_rev_type,
            "Territory": "",
            "Units": units_val,
            "Rate": "" if rate_raw in ("--", "-") else rate_raw,
            "Gross Amount": amount_val,
            "Net Amount": amount_val,
        })

    if not rows:
        logger.warning("Vanguard parser produced 0 rows")
        return None

    headers = [
        "Track Title", "Writer/Artist", "ISRC", "Source/Collector", "Source Detail",
        "Income Type", "Territory", "Units", "Rate", "Gross Amount", "Net Amount",
    ]

    parsed_sum = sum(float(r["Net Amount"]) for r in rows if r["Net Amount"])
    logger.info(
        f"Vanguard parser extracted {len(rows)} rows, parsed_sum=${parsed_sum:.2f}, "
        f"grand_total=${metadata.get('grand_total_net') or 0:.2f}"
    )

    return {
        "headers": headers,
        "rows": rows,
        "metadata": metadata,
    }


BMI_FIRST_ROW_RE = re.compile(
    r"^(?P<title>.+?)\s+(?P<work_no>W-\d+)\s+(?P<category>.+?)\s+"
    r"(?P<performances>[\d,]+)\s+(?P<writer_pct>\d+\.\d+%)\s+"
    r"\$(?P<amount>-?[\d,]+\.\d{2})$"
)
BMI_CONT_ROW_RE = re.compile(
    r"^(?P<category>.+?)\s+(?P<performances>[\d,]+)\s+"
    r"(?P<writer_pct>\d+\.\d+%)\s+\$(?P<amount>-?[\d,]+\.\d{2})$"
)
BMI_SUBTOTAL_RE = re.compile(r"^Subtotal:\s*\$([\d,]+\.\d{2})$", re.IGNORECASE)
BMI_GRAND_TOTAL_RE = re.compile(
    r"(?i)TOTAL\s+CURRENT\s+PERIOD.*?\$([\d,]+\.\d{2})"
)
BMI_WRITER_NAME_RE = re.compile(
    r"(?im)^Writer\s*Name:\s*(.+?)(?:\s+Address:|\s{2,}|$)"
)
BMI_PERIOD_RE = re.compile(r"(?im)Performance\s+Period:\s*(.+?)$")

# Truncated category names → full names (the BMI PDF column width truncates
# anything beyond ~25 characters in the per-work detail tables, e.g.
# "Digital - Audio Visual St" is the truncated form of
# "Digital - Audio Visual Streaming").
BMI_CATEGORY_FULL_NAMES = {
    "Radio": "Radio",
    "Television - Network": "Television - Network",
    "Television - Cable": "Television - Cable",
    "Television - Local": "Television - Local",
    "Digital - Audio Streaming": "Digital - Audio Streaming",
    "Digital - Audio Visual St": "Digital - Audio Visual Streaming",
    "Digital - Audio Visual Streaming": "Digital - Audio Visual Streaming",
    "Digital - Download": "Digital - Download",
    "Live Performance": "Live Performance",
    "General Licensing": "General Licensing",
    "International": "International",
}


def is_bmi_writer_statement(content: bytes) -> bool:
    """Detect the BMI Writer Distribution Statement PDF format.

    These statements have a unique header ("WRITER DISTRIBUTION STATEMENT" +
    "BROADCAST MUSIC, INC.") and a per-work detail layout that the generic
    publishing parser cannot read because the text has no detectable table
    grid lines.
    """
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages[:2]:
                text = (page.extract_text() or "").upper()
                if (
                    "WRITER DISTRIBUTION STATEMENT" in text
                    and "BROADCAST MUSIC" in text
                ):
                    return True
    except Exception:
        pass
    return False


def parse_bmi_writer_statement(content: bytes) -> Optional[dict]:
    """Parse a BMI Writer Distribution Statement PDF.

    The detail section repeats per work::

        WORK TITLE WORK # PERF. CATEGORY PERFORMANCES WRITER % ROYALTY AMT
        Deja Vu W-10806201 Digital - Audio Streaming 155,437 50.0% $517.77
            Radio 36,795 50.0% $158.25
            Digital - Audio Visual St 50,943 50.0% $211.61
            ...
            Subtotal: $1,495.89
        Montero W-10513037 Digital - Audio Streaming 59,595 33.3% $659.87
            ...

    The first row of each work carries the title + work number; subsequent
    rows omit them. Categories may be truncated by the PDF column width
    (e.g. "Digital - Audio Visual St" → "Digital - Audio Visual Streaming").
    """
    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            full_text = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"
    except Exception as e:
        logger.error(f"BMI parser: failed to open PDF: {e}")
        return None

    return _parse_bmi_writer_text(full_text)


def _parse_bmi_writer_text(full_text: str) -> Optional[dict]:
    """Pure-text BMI parser. Split out from parse_bmi_writer_statement so
    it can be unit-tested without a real PDF on disk."""
    metadata = {
        "client_name": None,
        "period": None,
        "grand_total_net": None,
    }
    rows = []

    if not full_text:
        return None

    gt = BMI_GRAND_TOTAL_RE.search(full_text)
    if gt:
        try:
            metadata["grand_total_net"] = float(gt.group(1).replace(",", ""))
        except ValueError:
            pass

    wn = BMI_WRITER_NAME_RE.search(full_text)
    if wn:
        metadata["client_name"] = wn.group(1).strip()

    pm = BMI_PERIOD_RE.search(full_text)
    if pm:
        metadata["period"] = pm.group(1).strip()

    current_title = ""
    current_work_no = ""

    for raw_line in full_text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        # Skip headers, page banners, summary rows and subtotals.
        upper = line.upper()
        if upper.startswith("WORK TITLE") and "WORK #" in upper:
            continue
        if "WRITER DISTRIBUTION STATEMENT" in upper:
            continue
        if "BROADCAST MUSIC, INC. - CONFIDENTIAL" in upper:
            continue
        if BMI_SUBTOTAL_RE.match(line):
            continue

        m_first = BMI_FIRST_ROW_RE.match(line)
        if m_first:
            current_title = m_first.group("title").strip()
            current_work_no = m_first.group("work_no").strip()
            category = m_first.group("category").strip()
            performances = m_first.group("performances").replace(",", "")
            writer_pct = m_first.group("writer_pct")
            amount = m_first.group("amount").replace(",", "")
        else:
            m_cont = BMI_CONT_ROW_RE.match(line)
            if not m_cont:
                continue
            # Continuation rows only valid once we've seen a work header.
            if not current_title:
                continue
            category_raw = m_cont.group("category").strip()
            # Reject lines that look like category-row but are actually
            # the STATEMENT SUMMARY rows (which have an extra adjustments
            # column producing a different shape — those rarely match
            # the strict end-with-$amount pattern, but guard anyway by
            # requiring the category text to be a recognized BMI bucket).
            if category_raw not in BMI_CATEGORY_FULL_NAMES:
                # Surface unknown categories rather than dropping them silently —
                # if BMI ever introduces or renames a category, the warning will
                # show up in logs before the total quietly drifts again.
                logger.warning(
                    "BMI parser: skipped continuation row with unknown "
                    f"category {category_raw!r} (line: {line!r})"
                )
                continue
            category = category_raw
            performances = m_cont.group("performances").replace(",", "")
            writer_pct = m_cont.group("writer_pct")
            amount = m_cont.group("amount").replace(",", "")

        full_category = BMI_CATEGORY_FULL_NAMES.get(category, category)

        rows.append({
            "Track Title": current_title,
            "Writer/Artist": metadata.get("client_name") or "",
            "Work Number": current_work_no,
            "Source/Collector": "BMI",
            "Source Detail": full_category,
            "Income Type": full_category,
            "Territory": "International" if full_category == "International" else "US",
            "Units": performances,
            "Writer Share": writer_pct,
            "Rate": "",
            "Gross Amount": amount,
            "Net Amount": amount,
        })

    if not rows:
        logger.warning("BMI parser produced 0 rows")
        return None

    headers = [
        "Track Title", "Writer/Artist", "Work Number", "Source/Collector",
        "Source Detail", "Income Type", "Territory", "Units",
        "Writer Share", "Rate", "Gross Amount", "Net Amount",
    ]

    parsed_sum = sum(float(r["Net Amount"]) for r in rows if r["Net Amount"])
    logger.info(
        f"BMI parser extracted {len(rows)} rows, parsed_sum=${parsed_sum:.2f}, "
        f"grand_total=${metadata.get('grand_total_net') or 0:.2f}"
    )

    return {
        "headers": headers,
        "rows": rows,
        "metadata": metadata,
    }


def is_publishing_statement(content: bytes) -> bool:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages[:5]:
                text = page.extract_text()
                if text:
                    if "Title (Writer/Artist)" in text and "Income Type" in text:
                        return True
                    if "SUMMARY STATEMENT" in text and "Opening Balance" in text:
                        return True
    except Exception:
        pass
    return False


def parse_publishing_statement(content: bytes) -> Optional[dict]:
    import pdfplumber

    all_lines = []
    metadata = {
        "client_id": None,
        "client_name": None,
        "period": None,
        "total_gross": None,
        "total_net": None,
        "opening_balance": None,
    }

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            summary_text = ""
            for page in pdf.pages[:2]:
                text = page.extract_text()
                if text:
                    summary_text += text + "\n"

            for line in summary_text.split("\n"):
                line = line.strip()
                m = CLIENT_PATTERN.match(line)
                if m:
                    metadata["client_id"] = m.group(1)
                    metadata["client_name"] = m.group(2).strip()
                m = PERIOD_PATTERN.match(line)
                if m:
                    metadata["period"] = m.group(1).strip()
                if "Opening Balance:" in line:
                    parts = line.split("Opening Balance:")
                    if len(parts) > 1:
                        bal = parts[1].strip().replace(",", "")
                        try:
                            metadata["opening_balance"] = float(bal)
                        except ValueError:
                            pass

            for page_idx, page in enumerate(pdf.pages[2:], start=3):
                try:
                    text = page.extract_text()
                    if text:
                        for line in text.split("\n"):
                            all_lines.append(line.strip())
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_idx}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Failed to open PDF for publishing statement parsing: {e}")
        return None

    if not all_lines:
        return None

    headers = [
        "Track Title", "Writer/Artist", "Source/Collector", "Source Detail",
        "Income Type", "Territory", "Units", "Net Amount",
        "Rate", "Gross Amount"
    ]
    rows = []
    skipped_data_lines = []
    current_song_title = ""
    current_writers = ""
    current_source = ""
    building_title = False
    title_parts = []

    i = 0
    while i < len(all_lines):
        line = all_lines[i]

        if not line:
            i += 1
            continue

        if _is_header_line(line):
            building_title = False
            title_parts = []
            i += 1
            continue

        m = CLIENT_PATTERN.match(line)
        if m:
            if not metadata["client_name"]:
                metadata["client_id"] = m.group(1)
                metadata["client_name"] = m.group(2).strip()
            i += 1
            continue

        m = PERIOD_PATTERN.match(line)
        if m:
            if not metadata["period"]:
                metadata["period"] = m.group(1).strip()
            i += 1
            continue

        m = GRAND_TOTAL_PATTERN.match(line)
        if m:
            metadata["grand_total_gross"] = _parse_amount(m.group(1))
            metadata["grand_total_net"] = _parse_amount(m.group(2))
            logger.info(f"Found Grand Total: gross={m.group(1)}, net={m.group(2)}")
            i += 1
            continue

        m = TOTAL_PATTERN.match(line)
        if m:
            metadata["total_gross"] = _parse_amount(m.group(1))
            metadata["total_net"] = _parse_amount(m.group(2))
            i += 1
            continue

        m = DATA_LINE_RE.match(line)
        if m:
            building_title = False
            prefix = m.group(1)
            units = m.group(2).replace(",", "")
            gross = m.group(3)
            rate = m.group(4)
            net = m.group(5)

            source_detail, income_type, territory = _split_income_type(prefix)
            if not income_type:
                source_detail = prefix
                territory = ""

            rows.append({
                "Track Title": current_song_title,
                "Writer/Artist": current_writers,
                "Source/Collector": current_source,
                "Source Detail": source_detail,
                "Income Type": income_type,
                "Territory": territory,
                "Units": units,
                "Gross Amount": gross,
                "Rate": rate,
                "Net Amount": net,
            })
            i += 1
            continue

        m = DATA_LINE_NO_UNITS_RE.match(line)
        if m:
            building_title = False
            prefix = m.group(1)
            gross = m.group(2)
            rate = m.group(3)
            net = m.group(4)

            source_detail, income_type, territory = _split_income_type(prefix)
            if not income_type:
                source_detail = prefix
                territory = ""

            rows.append({
                "Track Title": current_song_title,
                "Writer/Artist": current_writers,
                "Source/Collector": current_source,
                "Source Detail": source_detail,
                "Income Type": income_type,
                "Territory": territory,
                "Units": "",
                "Gross Amount": gross,
                "Rate": rate,
                "Net Amount": net,
            })
            i += 1
            continue

        m = DATA_LINE_MINIMAL_RE.match(line)
        if m and current_song_title:
            building_title = False
            prefix = m.group(1)
            gross = m.group(2)
            net = m.group(3)

            source_detail, income_type, territory = _split_income_type(prefix)
            if not income_type:
                source_detail = prefix
                territory = ""

            rows.append({
                "Track Title": current_song_title,
                "Writer/Artist": current_writers,
                "Source/Collector": current_source,
                "Source Detail": source_detail,
                "Income Type": income_type,
                "Territory": territory,
                "Units": "",
                "Gross Amount": gross,
                "Rate": "",
                "Net Amount": net,
            })
            i += 1
            continue

        if building_title:
            title_parts.append(line)
            if ")" in line:
                combined = " ".join(title_parts)
                paren_start = combined.find("(")
                if paren_start >= 0:
                    current_song_title = combined[:paren_start].strip()
                    paren_end = combined.rfind(")")
                    if paren_end > paren_start:
                        current_writers = combined[paren_start + 1:paren_end].strip()
                else:
                    current_song_title = combined.strip()
                building_title = False
            i += 1
            continue

        if SUBTOTAL_RE.match(line):
            i += 1
            continue

        if WRITER_LINE_RE.match(line):
            current_writers = line.strip("()")
            i += 1
            continue

        if WRITER_START_RE.match(line):
            title_parts = [line]
            building_title = True
            i += 1
            continue

        if _is_source_line(line):
            current_source = line
            i += 1
            continue

        is_likely_title = True
        if any(c.isdigit() for c in line) and ("%" in line or "." in line):
            is_likely_title = False

        if is_likely_title:
            if "(" in line and ")" in line:
                paren_start = line.find("(")
                paren_end = line.rfind(")")
                current_song_title = line[:paren_start].strip()
                current_writers = line[paren_start + 1:paren_end].strip()
                building_title = False
            elif "(" in line:
                title_parts = [line]
                building_title = True
            else:
                current_song_title = line.strip()
                building_title = False
            current_source = ""
            i += 1
            continue

        if any(c.isdigit() for c in line) and "." in line:
            skipped_data_lines.append(line)

        i += 1

    if not rows:
        return None

    if skipped_data_lines:
        logger.warning(f"Publishing parser skipped {len(skipped_data_lines)} potential data lines")
        for sl in skipped_data_lines[:20]:
            logger.warning(f"  SKIPPED: {sl!r}")

    logger.info(f"Publishing statement parser extracted {len(rows)} line items")

    return {
        "headers": headers,
        "rows": [{h: row.get(h, "") for h in headers} for row in rows],
        "metadata": metadata,
    }
