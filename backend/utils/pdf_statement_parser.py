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
#   "Period Ending: 12/31/2023"
_PERIOD_HEADER_RE = re.compile(
    r"(?i)(?:performance\s+period|statement\s+period|for\s+the\s+period|reporting\s+period|royalty\s+period|period)\s*[:\-]?\s*(.+?)$",
    re.MULTILINE,
)
_MONTH_RANGE_RE = re.compile(
    r"(?i)\b([a-z]{3,9})\.?\s*(\d{0,2})\s*[,\-/]?\s*(\d{4})?\s*[\-\u2013to]+\s*([a-z]{3,9})\.?\s*(\d{0,2})\s*[,\-/]?\s*(\d{4})"
)


def _last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    from calendar import monthrange
    return monthrange(year, month)[1]


def parse_period_from_text(text: str) -> Tuple[Optional[date], Optional[date]]:
    """Best-effort period extraction from the first page or two of a statement.

    Returns (period_start, period_end) — either may be None if not parseable.
    Recognizes patterns like "Performance Period: Jul - Dec 2023",
    "Statement Period: July 1, 2023 - December 31, 2023".
    """
    if not text:
        return None, None
    for m in _PERIOD_HEADER_RE.finditer(text[:4000]):
        candidate = m.group(1).strip()
        rng = _MONTH_RANGE_RE.search(candidate)
        if not rng:
            continue
        start_mon = _MONTH_TO_NUM.get(rng.group(1).lower().rstrip("."))
        end_mon = _MONTH_TO_NUM.get(rng.group(4).lower().rstrip("."))
        if not start_mon or not end_mon:
            continue
        end_year_str = rng.group(6)
        start_year_str = rng.group(3) or end_year_str
        try:
            start_year = int(start_year_str)
            end_year = int(end_year_str)
        except (TypeError, ValueError):
            continue
        start_day = int(rng.group(2)) if rng.group(2) else 1
        end_day = int(rng.group(5)) if rng.group(5) else _last_day_of_month(end_year, end_mon)
        try:
            return date(start_year, start_mon, start_day), date(end_year, end_mon, end_day)
        except ValueError:
            continue
    return None, None


def parse_period_from_pdf(content: bytes) -> Tuple[Optional[date], Optional[date]]:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            text = ""
            for page in pdf.pages[:2]:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return parse_period_from_text(text)
    except Exception as e:
        logger.warning(f"parse_period_from_pdf failed: {e}")
        return None, None


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
