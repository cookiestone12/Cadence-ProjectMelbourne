"""
Document Parser Service - Parses PDF and DOCX Schedule A documents.
Extracts creator info, song entries with artist/title/percentage from
text-based documents like Schedule A / Schedule B sheets.

Supports two formats:
  1. Legacy dash format:  "Song Title - Artist 50%"
  2. Tabular columnar format with explicit headers like
     "# | COMPOSITION TITLE | ISRC | ISWC | WRITER % | YEAR | ERA | STATUS"
"""
import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from io import BytesIO

logger = logging.getLogger("cadence")


ISRC_RE = re.compile(r'\b([A-Z]{2}[A-Z0-9]{3}\d{7})\b')
ISWC_RE = re.compile(r'\b(T[-\s]?\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[-\s]?\d)\b')
PCT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*%')
YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')


class DocumentParseResult:
    def __init__(self):
        self.creator_name: Optional[str] = None
        self.bmi_ipi: Optional[str] = None
        self.bmi_id: Optional[str] = None
        self.pro_name: Optional[str] = None
        self.publisher: Optional[str] = None
        self.agreement_type: Optional[str] = None
        self.effective_date: Optional[str] = None
        self.territory: Optional[str] = None
        self.term: Optional[str] = None
        self.schedule_a_songs: List[Dict[str, str]] = []
        self.schedule_b_songs: List[Dict[str, str]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.extraction_method: str = "tabular_pdf"

    def to_preview_response(self) -> Dict[str, Any]:
        headers = ["title", "primary_artist", "publishing_percentage", "isrc", "iswc", "section", "notes"]
        all_songs = []
        for s in self.schedule_a_songs:
            row = {
                "title": s.get("title", ""),
                "primary_artist": s.get("primary_artist", ""),
                "publishing_percentage": s.get("publishing_percentage", ""),
                "isrc": s.get("isrc", ""),
                "iswc": s.get("iswc", ""),
                "section": "Schedule A",
                "notes": s.get("notes", ""),
                "_confidence": s.get("_confidence", 1.0),
                "_source": s.get("_source", ""),
            }
            all_songs.append(row)
        for s in self.schedule_b_songs:
            row = {
                "title": s.get("title", ""),
                "primary_artist": s.get("primary_artist", ""),
                "publishing_percentage": s.get("publishing_percentage", ""),
                "isrc": s.get("isrc", ""),
                "iswc": s.get("iswc", ""),
                "section": "Schedule B (Pipeline)",
                "notes": s.get("notes", ""),
                "_confidence": s.get("_confidence", 1.0),
                "_source": s.get("_source", ""),
            }
            all_songs.append(row)

        mapping = {
            "title": "title",
            "primary_artist": "primary_artist",
            "publishing_percentage": "publishing_percentage",
            "isrc": "isrc",
            "iswc": "iswc",
            "section": None,
            "notes": "notes",
        }

        return {
            "headers": headers,
            "mapping": mapping,
            "preview_rows": all_songs,
            "row_count": len(all_songs),
            "success": True,
            "error": None,
            "document_info": {
                "creator_name": self.creator_name,
                "bmi_ipi": self.bmi_ipi,
                "bmi_id": self.bmi_id,
                "pro_name": self.pro_name,
            },
            "contract_terms": {
                "publisher": self.publisher,
                "agreement_type": self.agreement_type,
                "effective_date": self.effective_date,
                "territory": self.territory,
                "term": self.term,
            },
            "is_document_import": True,
            "warnings": self.warnings,
            "extraction_method": self.extraction_method,
        }


def extract_text_from_pdf(content: bytes) -> str:
    import pdfplumber
    text_parts = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


COLUMN_ALIASES = {
    "title": ["title", "composition", "song", "track", "work"],
    "isrc": ["isrc"],
    "iswc": ["iswc"],
    "publishing_percentage": ["%", "writer", "pub", "publishing", "share", "split"],
    "year": ["year"],
    "era": ["era"],
    "status": ["status"],
    "primary_artist": ["artist"],
    "row_num": ["#", "no", "no.", "num"],
    "notes": ["notes", "note"],
}


def _classify_header_token(token: str) -> Optional[str]:
    t = token.lower().strip().rstrip(":").strip()
    if not t:
        return None
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if t == alias or alias in t:
                return field
    return None


def _group_words_into_lines(words: List[Dict[str, Any]], y_tol: float = 3.0) -> List[List[Dict[str, Any]]]:
    """Group pdfplumber words into visual lines based on y-coordinate."""
    if not words:
        return []
    sorted_words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    lines: List[List[Dict[str, Any]]] = []
    for w in sorted_words:
        placed = False
        for line in lines:
            if abs(line[0]["top"] - w["top"]) <= y_tol:
                line.append(w)
                placed = True
                break
        if not placed:
            lines.append([w])
    for line in lines:
        line.sort(key=lambda w: w["x0"])
    return lines


def _detect_columns_from_header(line_words: List[Dict[str, Any]]) -> Optional[List[Tuple[str, float, float]]]:
    """Return list of (field_name, x_start, x_end) describing each column.

    Adjacent header tokens that map to the same field are merged. Column
    x-ranges extend to halfway between adjacent column centers, with the
    first and last extending to the page edges (None x_end means open end).
    """
    classified: List[Tuple[str, float, float]] = []
    for w in line_words:
        field = _classify_header_token(w["text"])
        if field:
            classified.append((field, w["x0"], w["x1"]))

    if not classified:
        return None

    has_title = any(c[0] in ("title",) for c in classified)
    has_anchor = any(c[0] in ("isrc", "iswc", "publishing_percentage") for c in classified)
    if not (has_title and has_anchor):
        return None

    merged: List[List[Any]] = []
    for field, x0, x1 in classified:
        if merged and merged[-1][0] == field and (x0 - merged[-1][2]) < 30:
            merged[-1][2] = x1
        else:
            merged.append([field, x0, x1])

    merged.sort(key=lambda c: c[1])

    columns: List[Tuple[str, float, float]] = []
    for i, (field, x0, x1) in enumerate(merged):
        if i == 0:
            left_bound = 0.0
        else:
            prev_x1 = merged[i - 1][2]
            left_bound = (prev_x1 + x0) / 2.0
        if i == len(merged) - 1:
            right_bound = float("inf")
        else:
            next_x0 = merged[i + 1][1]
            right_bound = (x1 + next_x0) / 2.0
        columns.append((field, left_bound, right_bound))

    return columns


def _row_words_to_record(
    row_words: List[Dict[str, Any]],
    columns: List[Tuple[str, float, float]],
) -> Optional[Dict[str, str]]:
    """Bucket each word into a column by x-coordinate center."""
    buckets: Dict[str, List[str]] = {col[0]: [] for col in columns}
    for w in row_words:
        cx = (w["x0"] + w["x1"]) / 2.0
        for field, lo, hi in columns:
            if lo <= cx < hi:
                buckets[field].append(w["text"])
                break

    title = " ".join(buckets.get("title", [])).strip()
    if not title:
        return None
    if re.fullmatch(r'\d+', title):
        return None

    pct_raw = " ".join(buckets.get("publishing_percentage", [])).strip()
    pct_match = PCT_RE.search(pct_raw) if pct_raw else None
    pct_value: str = ""
    if pct_match:
        pct_value = pct_match.group(1)
    elif pct_raw:
        bare = re.match(r'^(\d+(?:\.\d+)?)\s*$', pct_raw)
        if bare:
            try:
                if 0.0 <= float(bare.group(1)) <= 100.0:
                    pct_value = bare.group(1)
            except ValueError:
                pass

    isrc_raw = " ".join(buckets.get("isrc", [])).strip()
    isrc_match = ISRC_RE.search(isrc_raw) if isrc_raw else None

    iswc_raw = " ".join(buckets.get("iswc", [])).strip()
    iswc_match = ISWC_RE.search(iswc_raw) if iswc_raw else None

    notes_parts: List[str] = []
    status_text = " ".join(buckets.get("status", [])).strip()
    if status_text:
        notes_parts.append(status_text)
    era_text = " ".join(buckets.get("era", [])).strip()
    if era_text and era_text.lower() not in ("active", ""):
        notes_parts.append(era_text)
    extra_notes = " ".join(buckets.get("notes", [])).strip()
    if extra_notes:
        notes_parts.append(extra_notes)

    artist = " ".join(buckets.get("primary_artist", [])).strip()

    return {
        "primary_artist": artist,
        "title": title,
        "publishing_percentage": pct_value,
        "isrc": isrc_match.group(1) if isrc_match else "",
        "iswc": iswc_match.group(1) if iswc_match else "",
        "notes": " | ".join([n for n in notes_parts if n]),
    }


def extract_tabular_rows_from_pdf(content: bytes) -> Optional[Dict[str, Any]]:
    """Column-aware tabular extraction using pdfplumber word x-coordinates.

    Returns a dict with keys 'rows' (list[dict]), 'header_text' (str of all
    pre-table lines so creator/PRO info can still be parsed) on success,
    or None if no tabular header is detected on any page.
    """
    import pdfplumber
    all_rows: List[Dict[str, str]] = []
    header_text_lines: List[str] = []
    found_header = False
    page_columns: Optional[List[Tuple[str, float, float]]] = None

    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            try:
                words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            except Exception:
                words = []
            if not words:
                continue
            lines = _group_words_into_lines(words)

            for line_words in lines:
                line_text = " ".join(w["text"] for w in line_words)

                if page_columns is None:
                    columns = _detect_columns_from_header(line_words)
                    if columns:
                        page_columns = columns
                        found_header = True
                        continue
                    header_text_lines.append(line_text)
                else:
                    if any(re.search(p, line_text, re.IGNORECASE) for p in [
                        r'^\s*total\s+(controlled|compositions|songs)',
                        r'^\s*effective\s+date',
                        r'\bpage\s+\d+\s*\|',
                    ]):
                        continue
                    record = _row_words_to_record(line_words, page_columns)
                    if record:
                        all_rows.append(record)

    if not found_header:
        return None

    return {
        "rows": all_rows,
        "header_text": "\n".join(header_text_lines),
    }


def extract_text_from_docx(content: bytes) -> str:
    from docx import Document
    doc = Document(BytesIO(content))
    text_parts = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            text_parts.append(text)
    return "\n".join(text_parts)


def parse_creator_info(text: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    creator_name = None
    bmi_ipi = None
    bmi_id = None
    pro_name = None

    writer_match = re.search(
        r'Writer\s*:?\s*([^|\n]+?)(?:\s*p/k/a\s*([^|\n]+?))?\s*(?:\||$|\n)',
        text,
        re.IGNORECASE,
    )
    if writer_match:
        pka = (writer_match.group(2) or '').strip()
        legal = (writer_match.group(1) or '').strip()
        creator_name = pka if pka else legal

    cae_match = re.search(r'(?:CAE\s*/\s*IPI|CAE/IPI|IPI)\s*#?\s*:?\s*(\d{6,})', text, re.IGNORECASE)
    if cae_match:
        bmi_ipi = cae_match.group(1)

    pro_match = re.search(r'\bPRO\s*:?\s*(BMI|ASCAP|SESAC|GMR|SOCAN|PRS|GEMA|SACEM)\b', text, re.IGNORECASE)
    if pro_match:
        pro_name = pro_match.group(1).upper()

    if not bmi_ipi:
        ipi_match = re.search(r'(?:BMI|ASCAP|SESAC|GMR)\s+IPI\s*#?\s*:?\s*(\d+)', text, re.IGNORECASE)
        if ipi_match:
            bmi_ipi = ipi_match.group(1)
            if not pro_name:
                pro_match2 = re.search(r'(BMI|ASCAP|SESAC|GMR)\s+IPI', text, re.IGNORECASE)
                if pro_match2:
                    pro_name = pro_match2.group(1).upper()

    id_match = re.search(r'(?:BMI|ASCAP|SESAC|GMR)[-\s]+(?:ID\s*#?\s*:?\s*)?(\d{6,})', text, re.IGNORECASE)
    if id_match:
        bmi_id = id_match.group(1)

    if not creator_name:
        lines = text.split('\n')
        for line in lines[:10]:
            line = line.strip()
            if not line:
                continue
            if re.search(r'(IPI|ID)\s*#', line, re.IGNORECASE):
                continue
            if re.search(r'schedule\s+[ab]', line, re.IGNORECASE):
                continue
            if re.match(r'^\d+%?$', line):
                continue
            if len(line) > 3 and not re.search(r'\d{5,}', line):
                name_candidate = re.sub(r'\(.*?\)', '', line).strip()
                if name_candidate and len(name_candidate) > 2:
                    creator_name = name_candidate
                    break

    return creator_name, bmi_ipi, bmi_id, pro_name


def parse_contract_terms(text: str) -> Dict[str, Optional[str]]:
    """Extract deal-level contract terms from a Schedule A header block.

    Looks for Publisher, Agreement (type), Effective Date, Territory, and Term
    fields written as 'Label: value' on their own lines (case-insensitive).
    Values stop at the first line break or pipe separator so multi-field
    header rows like 'Territory: World | Term: 5 years' parse correctly.
    """
    terms: Dict[str, Optional[str]] = {
        "publisher": None,
        "agreement_type": None,
        "effective_date": None,
        "territory": None,
        "term": None,
    }
    if not text:
        return terms

    def _find(label_pattern: str) -> Optional[str]:
        m = re.search(
            rf'(?im)(?:^|\|)\s*(?:{label_pattern})\s*:\s*([^\n|]+?)\s*(?:\||$)',
            text,
        )
        if not m:
            return None
        val = m.group(1).strip().rstrip(',;.').strip()
        return val or None

    terms["publisher"] = _find(r'publisher')
    terms["agreement_type"] = _find(r'agreement(?:\s+type)?')
    terms["effective_date"] = _find(r'effective\s+date')
    terms["territory"] = _find(r'territory')
    terms["term"] = _find(r'term')

    return terms


def is_tabular_header(line: str) -> bool:
    """Detect a columnar Schedule A header row.

    Looks for a line containing TITLE/COMPOSITION plus at least two of
    ISRC, ISWC, WRITER %, PUB %, YEAR, STATUS markers.
    """
    upper = line.upper()
    has_title = ('TITLE' in upper) or ('COMPOSITION' in upper)
    if not has_title:
        return False
    indicators = 0
    if 'ISRC' in upper:
        indicators += 1
    if 'ISWC' in upper:
        indicators += 1
    if '%' in upper or 'WRITER' in upper or 'PUB' in upper or 'SHARE' in upper:
        indicators += 1
    if 'STATUS' in upper or 'YEAR' in upper or 'ERA' in upper:
        indicators += 1
    return indicators >= 2


def parse_tabular_row(line: str) -> Optional[Dict[str, str]]:
    """Parse a single tabular Schedule A row.

    Expected token layout (whitespace-separated, columns may vary):
        <row#> <Title ...> <ISRC?> <ISWC?> <Writer %?> <Year?> <Era?> <Status?>

    Identifiers are detected by regex (ISRC, ISWC, %), and the title is
    everything between the row number and the first identifier.
    """
    line = line.strip()
    if not line:
        return None

    row_match = re.match(r'^(\d+)\s+(.+)$', line)
    if not row_match:
        return None
    rest = row_match.group(2)

    isrc_match = ISRC_RE.search(rest)
    iswc_match = ISWC_RE.search(rest)
    pct_match = PCT_RE.search(rest)

    if not (isrc_match or iswc_match or pct_match):
        return None

    cut_positions = []
    if isrc_match:
        cut_positions.append(isrc_match.start())
    if iswc_match:
        cut_positions.append(iswc_match.start())
    if pct_match:
        cut_positions.append(pct_match.start())
    cut = min(cut_positions) if cut_positions else len(rest)

    title = rest[:cut].strip()
    title = re.sub(r'\s*\([^)]*\)\s*$', '', title).strip()
    if not title:
        return None

    notes_parts: List[str] = []
    after_pct_start = pct_match.end() if pct_match else cut
    trailing = rest[after_pct_start:].strip()
    paren_notes = re.findall(r'\(([^)]+)\)', trailing)
    for pn in paren_notes:
        notes_parts.append(pn.strip())

    trailing_no_parens = re.sub(r'\s*\([^)]*\)\s*', ' ', trailing).strip()
    trailing_tokens = trailing_no_parens.split()
    status_tokens = []
    for tok in trailing_tokens:
        if YEAR_RE.fullmatch(tok):
            continue
        status_tokens.append(tok)
    if status_tokens:
        status_text = ' '.join(status_tokens).strip()
        if status_text and status_text.lower() not in ('active',):
            notes_parts.insert(0, status_text)

    notes = ' | '.join([n for n in notes_parts if n])

    return {
        "primary_artist": "",
        "title": title,
        "publishing_percentage": pct_match.group(1) if pct_match else "",
        "isrc": isrc_match.group(1) if isrc_match else "",
        "iswc": iswc_match.group(1) if iswc_match else "",
        "notes": notes,
    }


def parse_song_line(line: str, creator_name: Optional[str] = None) -> Optional[Dict[str, str]]:
    line = line.strip()
    if not line or len(line) < 3:
        return None

    skip_patterns = [
        r'^schedule\s+[ab]',
        r'^pipeline',
        r'^\(holds?\)',
        r'^BMI\s',
        r'^ASCAP\s',
        r'^SESAC\s',
        r'^IPI',
        r'^ID\s*#',
        r'^\d+$',
    ]
    for pattern in skip_patterns:
        if re.match(pattern, line, re.IGNORECASE):
            return None

    if creator_name:
        clean_line = re.sub(r'\(.*?\)', '', line).strip()
        if clean_line.lower() == creator_name.lower():
            return None
        name_parts = creator_name.lower().split()
        if len(name_parts) >= 2 and all(p in clean_line.lower() for p in name_parts):
            if '-' not in line and '–' not in line and '—' not in line:
                return None

    notes = ""
    paren_notes = re.findall(r'\(([^)]+)\)', line)
    line_no_parens = re.sub(r'\s*\([^)]*\)\s*', ' ', line).strip()

    for pn in paren_notes:
        if not re.match(r'^(remix|feat|ft|featuring|x\d|xg)', pn, re.IGNORECASE):
            if re.search(r'(hold|solo|single)', pn, re.IGNORECASE):
                notes = pn

    pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%?\s*$', line_no_parens)
    percentage = None
    song_part = line_no_parens
    if pct_match:
        percentage = pct_match.group(1)
        song_part = line_no_parens[:pct_match.start()].strip()

    if not song_part or len(song_part) < 2:
        return None

    artist = ""
    title = song_part

    dash_match = re.match(r'^(.+?)\s*[-–—]\s*(.*)$', song_part)
    if dash_match:
        left = dash_match.group(1).strip()
        right = dash_match.group(2).strip()
        if right and left and len(right) > 0:
            artist = left
            title = right
        elif not right or right.strip() == '':
            return None

    if not title or title == "-" or title.strip() == '':
        return None

    return {
        "primary_artist": artist,
        "title": title,
        "publishing_percentage": percentage or "",
        "notes": notes,
    }


def parse_grouped_artist_songs(lines: List[str], start_idx: int) -> Tuple[List[Dict[str, str]], int]:
    results = []
    artist_match = re.match(r'^(.+?)\s*\((\d+)\s+songs?\)\s*[-–—]?\s*$', lines[start_idx], re.IGNORECASE)
    if not artist_match:
        return results, start_idx

    artist_name = artist_match.group(1).strip()
    expected_count = int(artist_match.group(2))
    idx = start_idx + 1

    while idx < len(lines) and len(results) < expected_count + 2:
        line = lines[idx].strip()
        if not line:
            idx += 1
            continue
        if re.match(r'^schedule\s+[ab]', line, re.IGNORECASE):
            break
        if re.match(r'^.+?\s*\(\d+\s+songs?\)', line, re.IGNORECASE):
            break

        parsed = parse_song_line(line, creator_name=None)
        if parsed:
            if not parsed["primary_artist"]:
                parsed["primary_artist"] = artist_name
            results.append(parsed)
        idx += 1

    return results, idx - 1


def parse_document_text(text: str) -> DocumentParseResult:
    result = DocumentParseResult()

    creator_name, bmi_ipi, bmi_id, pro_name = parse_creator_info(text)
    result.creator_name = creator_name
    result.bmi_ipi = bmi_ipi
    result.bmi_id = bmi_id
    result.pro_name = pro_name

    contract_terms = parse_contract_terms(text)
    result.publisher = contract_terms["publisher"]
    result.agreement_type = contract_terms["agreement_type"]
    result.effective_date = contract_terms["effective_date"]
    result.territory = contract_terms["territory"]
    result.term = contract_terms["term"]

    metadata_skip_patterns = [
        r'^(writer|publisher)\s*:',
        r'^cae\s*/?\s*ipi',
        r'^pro\s*:',
        r'^agreement(?:\s+type)?\s*:',
        r'^effective\s+date',
        r'^territory\s*:',
        r'^term\s*:',
        r'^total\s+(controlled|compositions|songs)',
        r'^page\s+\d',
        r'\bpage\s+\d+\b.*\|',
    ]

    lines = text.split('\n')
    current_section = "A"
    in_tabular_mode = False
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if any(re.search(p, line, re.IGNORECASE) for p in metadata_skip_patterns):
            i += 1
            continue

        if re.match(r'schedule\s+b', line, re.IGNORECASE):
            current_section = "B"
            in_tabular_mode = False
            i += 1
            continue
        if re.match(r'schedule\s+a', line, re.IGNORECASE):
            current_section = "A"
            in_tabular_mode = False
            i += 1
            continue
        if re.match(r'^pipeline', line, re.IGNORECASE) or re.match(r'^\(holds?\)', line, re.IGNORECASE):
            i += 1
            continue

        if is_tabular_header(line):
            in_tabular_mode = True
            i += 1
            continue

        if in_tabular_mode:
            tabular = parse_tabular_row(line)
            if tabular:
                target = result.schedule_a_songs if current_section == "A" else result.schedule_b_songs
                target.append(tabular)
                i += 1
                continue
            if re.match(r'^total\b', line, re.IGNORECASE) or re.match(r'^effective\s+date', line, re.IGNORECASE):
                in_tabular_mode = False
            i += 1
            continue

        grouped_match = re.match(r'^.+?\s*\(\d+\s+songs?\)', line, re.IGNORECASE)
        if grouped_match:
            grouped_songs, end_idx = parse_grouped_artist_songs(lines, i)
            target = result.schedule_a_songs if current_section == "A" else result.schedule_b_songs
            target.extend(grouped_songs)
            i = end_idx + 1
            continue

        parsed = parse_song_line(line, creator_name=creator_name)
        if parsed:
            if current_section == "A":
                result.schedule_a_songs.append(parsed)
            else:
                result.schedule_b_songs.append(parsed)

        i += 1

    total = len(result.schedule_a_songs) + len(result.schedule_b_songs)
    if total == 0:
        result.errors.append("No songs found in document. The document may not be in a recognized Schedule A format.")

    if result.creator_name:
        result.warnings.append(f"Detected creator: {result.creator_name}")
    if result.bmi_ipi:
        result.warnings.append(f"Detected {result.pro_name or 'PRO'} IPI#: {result.bmi_ipi}")

    return result


def parse_document(content: bytes, filename: str) -> DocumentParseResult:
    lower = filename.lower()

    if lower.endswith('.pdf'):
        try:
            tabular = extract_tabular_rows_from_pdf(content)
        except Exception as e:
            logger.warning(f"Column-aware PDF extraction failed for {filename}: {e}; falling back to text parser.")
            tabular = None
        if tabular and tabular.get("rows"):
            result = DocumentParseResult()
            header_text = tabular.get("header_text", "")
            creator_name, bmi_ipi, bmi_id, pro_name = parse_creator_info(header_text)
            result.creator_name = creator_name
            result.bmi_ipi = bmi_ipi
            result.bmi_id = bmi_id
            result.pro_name = pro_name
            contract_terms = parse_contract_terms(header_text)
            result.publisher = contract_terms["publisher"]
            result.agreement_type = contract_terms["agreement_type"]
            result.effective_date = contract_terms["effective_date"]
            result.territory = contract_terms["territory"]
            result.term = contract_terms["term"]
            result.schedule_a_songs = tabular["rows"]
            if creator_name:
                result.warnings.append(f"Detected creator: {creator_name}")
            if bmi_ipi:
                result.warnings.append(f"Detected {pro_name or 'PRO'} IPI#: {bmi_ipi}")
            return result

    try:
        if lower.endswith('.pdf'):
            text = extract_text_from_pdf(content)
        elif lower.endswith('.docx'):
            text = extract_text_from_docx(content)
        elif lower.endswith('.doc'):
            result = DocumentParseResult()
            result.errors.append("Legacy .doc format is not supported. Please save the file as .docx or .pdf and try again.")
            return result
        else:
            result = DocumentParseResult()
            result.errors.append(f"Unsupported file type: {filename}")
            return result
    except Exception as e:
        logger.error(f"Failed to extract text from {filename}: {e}")
        result = DocumentParseResult()
        result.errors.append(f"Failed to read document: {str(e)}")
        return result

    if not text or len(text.strip()) < 10:
        result = DocumentParseResult()
        result.errors.append("Document appears to be empty or could not be read.")
        return result

    return parse_document_text(text)


# ---------------------------------------------------------------------------
# Format-tolerant unified dispatcher
# ---------------------------------------------------------------------------

_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff")


def _result_from_ai(payload: Dict[str, Any], method_label: str) -> DocumentParseResult:
    """Build a DocumentParseResult from an AI extractor payload."""
    result = DocumentParseResult()
    result.extraction_method = method_label

    header = payload.get("header") or {}
    result.creator_name = header.get("creator_name") or None
    result.pro_name = header.get("pro_name") or None
    result.bmi_ipi = header.get("ipi") or None
    result.publisher = header.get("publisher") or None
    result.agreement_type = header.get("agreement_type") or None
    result.effective_date = header.get("effective_date") or None
    result.territory = header.get("territory") or None
    result.term = header.get("term") or None

    for row in payload.get("rows", []):
        result.schedule_a_songs.append(row)

    for w in payload.get("warnings", []):
        result.warnings.append(w)

    if result.creator_name:
        result.warnings.append(f"Detected creator: {result.creator_name}")
    if result.bmi_ipi:
        result.warnings.append(f"Detected {result.pro_name or 'PRO'} IPI#: {result.bmi_ipi}")

    if not result.schedule_a_songs:
        result.errors.append("AI extractor did not find any songs in the supplied document.")
    return result


def parse_document_unified(
    content: Optional[bytes],
    filename: Optional[str],
    pasted_text: Optional[str] = None,
    org_id: Optional[int] = None,
) -> DocumentParseResult:
    """Format-tolerant Schedule A ingestion.

    Routes inputs by extension/MIME and falls back to AI extraction when the
    deterministic parsers can't find any rows.
    Order of preference for rich PDFs:
        1. column-aware tabular extraction (high precision)
        2. text-based dash/grouped parser
        3. AI text extractor on extracted PDF text
        4. AI vision extractor on rendered page images
    """
    from .schedule_a_ai_extractor import (
        extract_from_text as ai_text,
        extract_from_images as ai_vision,
        render_pdf_pages_to_png,
    )

    lower = (filename or "").lower()

    # ---- Pasted free-form text ------------------------------------------------
    if pasted_text and not content:
        payload = ai_text(pasted_text, org_id=org_id)
        return _result_from_ai(payload, "ai_text")

    if content is None:
        result = DocumentParseResult()
        result.errors.append("No file or text supplied.")
        return result

    # ---- Image inputs ---------------------------------------------------------
    if any(lower.endswith(ext) for ext in _IMAGE_EXTS):
        payload = ai_vision([content], org_id=org_id)
        return _result_from_ai(payload, "ai_vision")

    # ---- PDF ------------------------------------------------------------------
    if lower.endswith(".pdf"):
        # 1. column-aware tabular extraction
        try:
            tabular = extract_tabular_rows_from_pdf(content)
        except Exception as e:
            logger.warning(f"Column-aware PDF extraction failed: {e}")
            tabular = None

        if tabular and tabular.get("rows"):
            result = DocumentParseResult()
            result.extraction_method = "tabular_pdf"
            header_text = tabular.get("header_text", "")
            cn, ipi, bid, pn = parse_creator_info(header_text)
            result.creator_name, result.bmi_ipi, result.bmi_id, result.pro_name = cn, ipi, bid, pn
            ct = parse_contract_terms(header_text)
            result.publisher = ct["publisher"]
            result.agreement_type = ct["agreement_type"]
            result.effective_date = ct["effective_date"]
            result.territory = ct["territory"]
            result.term = ct["term"]
            for r in tabular["rows"]:
                r.setdefault("_confidence", 0.95)
                r.setdefault("_source", "tabular pdf row")
            result.schedule_a_songs = tabular["rows"]
            if cn:
                result.warnings.append(f"Detected creator: {cn}")
            if ipi:
                result.warnings.append(f"Detected {pn or 'PRO'} IPI#: {ipi}")
            return result

        # 2. text-based parser
        try:
            text = extract_text_from_pdf(content)
        except Exception as e:
            text = ""
            logger.warning(f"PDF text extraction failed: {e}")

        if text and len(text.strip()) >= 10:
            text_result = parse_document_text(text)
            text_result.extraction_method = "text_pdf"
            for s in text_result.schedule_a_songs + text_result.schedule_b_songs:
                s.setdefault("_confidence", 0.85)
                s.setdefault("_source", "pdf text line")
            if text_result.schedule_a_songs or text_result.schedule_b_songs:
                return text_result

            # 3. AI text fallback when deterministic parser failed but we DO have text
            ai_payload = ai_text(text, org_id=org_id)
            if ai_payload.get("rows"):
                return _result_from_ai(ai_payload, "ai_text_pdf")

        # 4. AI vision fallback for scanned / image-only PDFs
        images = render_pdf_pages_to_png(content)
        if images:
            payload = ai_vision(images, org_id=org_id)
            return _result_from_ai(payload, "ai_vision_pdf")

        result = DocumentParseResult()
        result.errors.append("Could not extract any songs from this PDF (text, tabular, and vision passes all came up empty).")
        return result

    # ---- DOCX -----------------------------------------------------------------
    if lower.endswith(".docx"):
        try:
            text = extract_text_from_docx(content)
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            result = DocumentParseResult()
            result.errors.append(f"Failed to read Word document: {e}")
            return result
        text_result = parse_document_text(text)
        text_result.extraction_method = "text_docx"
        for s in text_result.schedule_a_songs + text_result.schedule_b_songs:
            s.setdefault("_confidence", 0.85)
            s.setdefault("_source", "docx line")
        if text_result.schedule_a_songs or text_result.schedule_b_songs:
            return text_result
        ai_payload = ai_text(text, org_id=org_id)
        if ai_payload.get("rows"):
            return _result_from_ai(ai_payload, "ai_text_docx")
        return text_result

    if lower.endswith(".doc"):
        result = DocumentParseResult()
        result.errors.append("Legacy .doc format is not supported. Please save the file as .docx or .pdf and try again.")
        return result

    # ---- Plain text / unknown extension --------------------------------------
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = ""
    if text.strip():
        payload = ai_text(text, org_id=org_id)
        return _result_from_ai(payload, "ai_text")

    result = DocumentParseResult()
    result.errors.append(f"Unsupported file type: {filename}")
    return result
