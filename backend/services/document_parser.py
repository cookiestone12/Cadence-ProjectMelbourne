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
        self.schedule_a_songs: List[Dict[str, str]] = []
        self.schedule_b_songs: List[Dict[str, str]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

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
            "is_document_import": True,
            "warnings": self.warnings,
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

    metadata_skip_patterns = [
        r'^(writer|publisher)\s*:',
        r'^cae\s*/?\s*ipi',
        r'^pro\s*:',
        r'^agreement\s*:',
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
