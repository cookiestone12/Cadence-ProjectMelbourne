import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI

EXPECTED_FIELDS = [
    "title",
    "primary_artist", 
    "isrc",
    "iswc",
    "project_title",
    "release_date",
    "label",
    "publishing_percentage",
    "master_percentage",
    "advance_amount",
    "recording_code",
    "notes"
]

FIELD_DESCRIPTIONS = {
    "title": "Song title/track name",
    "primary_artist": "Main artist or performer name",
    "isrc": "International Standard Recording Code (format: CC-XXX-YY-NNNNN)",
    "iswc": "International Standard Musical Work Code (format: T-NNNNNNNNN-C)",
    "project_title": "Album or project name",
    "release_date": "Release date (format: YYYY-MM-DD)",
    "label": "Record label name",
    "publishing_percentage": "Publishing share percentage (0-100)",
    "master_percentage": "Master share percentage (0-100)",
    "advance_amount": "Advance payment amount in dollars",
    "recording_code": "Internal recording/catalog code",
    "notes": "Additional notes or comments"
}


def parse_csv_with_ai(csv_content: str, headers: List[str], org_id: int = None) -> Dict[str, Any]:
    client = OpenAI(
        api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
        base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    )
    
    prompt = f"""You are a music catalog data parser. Analyze the provided CSV headers and map them to standardized field names.

The CSV has these headers: {headers}

Map each CSV header to ONE of these standardized fields (or null if no match):
{json.dumps(FIELD_DESCRIPTIONS, indent=2)}

IMPORTANT RULES:
1. Only map headers that clearly correspond to a field
2. Return null for headers that don't match any field
3. Be flexible with naming (e.g., "Song Name" -> "title", "Artist" -> "primary_artist")
4. Percentage fields should be identified even if named differently (e.g., "Pub %" -> "publishing_percentage")
5. Date fields can have various names like "Released", "Date", "Release"

Respond with a JSON object where:
- Keys are the original CSV headers (exactly as provided)
- Values are the mapped field names from the list above, or null

Example response:
{{"Song Name": "title", "Artist": "primary_artist", "Random Column": null}}

Respond ONLY with the JSON mapping object, no other text."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1000
    )

    try:
        usage = response.usage
        if usage:
            from ..services.ai_usage import log_ai_usage_standalone
            log_ai_usage_standalone(
                feature="csv_mapping",
                model="gpt-4o-mini",
                input_tokens=usage.prompt_tokens or 0,
                output_tokens=usage.completion_tokens or 0,
                org_id=org_id,
            )
    except Exception as ai_log_err:
        import logging
        logging.getLogger("cadence").warning(f"Failed to log AI usage for CSV mapping: {ai_log_err}")

    try:
        mapping_text = response.choices[0].message.content.strip()
        if mapping_text.startswith("```"):
            mapping_text = mapping_text.split("```")[1]
            if mapping_text.startswith("json"):
                mapping_text = mapping_text[4:]
        mapping = json.loads(mapping_text)
        return {"mapping": mapping, "success": True}
    except json.JSONDecodeError as e:
        fallback = create_fallback_mapping(headers)
        return {"mapping": fallback, "success": False, "error": f"AI mapping failed, using fallback: {str(e)}"}
    except Exception as e:
        fallback = create_fallback_mapping(headers)
        return {"mapping": fallback, "success": False, "error": f"AI mapping unavailable, using fallback: {str(e)}"}


def create_fallback_mapping(headers: List[str]) -> Dict[str, Optional[str]]:
    """Create basic column mapping based on common header patterns."""
    mapping = {}
    
    common_patterns = {
        "title": [
            "title", "song", "track", "song title", "track name", "song name",
            "work title", "work", "composition", "music title", "track title",
            "song/track", "name", "work name", "comp", "composition title",
            "musical work", "original title", "recording title"
        ],
        "primary_artist": [
            "artist", "writer", "performer", "main artist", "artist name",
            "primary artist", "featured artist", "lead artist", "singer",
            "recording artist", "artists", "performers", "creator", "author"
        ],
        "isrc": ["isrc", "isrc code", "isrc #", "isrc number"],
        "iswc": ["iswc", "iswc code", "iswc #", "iswc number"],
        "project_title": [
            "album", "project", "release", "project title", "album name",
            "album title", "ep", "lp", "mixtape", "collection", "release title"
        ],
        "release_date": [
            "date", "release date", "released", "release", "date released",
            "release_date", "rel date", "original release", "first release"
        ],
        "label": ["label", "record label", "label name", "distributor", "publisher"],
        "publishing_percentage": [
            "publishing", "pub %", "pub", "publishing %", "pub share", 
            "publishing share", "pub pct", "publishing pct", "writer share",
            "songwriter share", "controlled", "ownership", "ownership %"
        ],
        "master_percentage": [
            "master", "master %", "master share", "royalty %", "royalty",
            "master pct", "recording share", "sound recording"
        ],
        "advance_amount": [
            "advance", "advance $", "advance amount", "payment", "advance amt",
            "recoupable", "advance paid"
        ],
        "recording_code": [
            "code", "recording code", "catalog", "catalog number", "catalog #",
            "internal code", "ref", "reference", "id", "song id", "track id"
        ],
        "notes": ["notes", "comments", "note", "comment", "remarks", "memo"],
    }
    
    header_lower_map = {h.lower().strip(): h for h in headers}
    
    for field, patterns in common_patterns.items():
        for pattern in patterns:
            if pattern in header_lower_map:
                original_header = header_lower_map[pattern]
                if original_header not in mapping:
                    mapping[original_header] = field
                break
    
    for header in headers:
        if header not in mapping:
            header_lower = header.lower().strip()
            for field, patterns in common_patterns.items():
                for pattern in patterns:
                    if pattern in header_lower or header_lower in pattern:
                        if header not in mapping:
                            mapping[header] = field
                        break
                if header in mapping:
                    break
    
    for header in headers:
        if header not in mapping:
            mapping[header] = None
    
    return mapping


def infer_field_from_sample_data(sample_values: List[str]) -> Optional[str]:
    """Infer the field type based on sample data values."""
    import re
    
    non_empty = [v for v in sample_values if v and v.strip()]
    if not non_empty:
        return None
    
    for val in non_empty[:5]:
        if re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{7}$', val.replace('-', '')):
            return "isrc"
        if re.match(r'^T-?\d{9,10}-?\d?$', val):
            return "iswc"
    
    for val in non_empty[:5]:
        if re.match(r'^\d{4}-\d{2}-\d{2}$', val):
            return "release_date"
        if re.match(r'^\d{1,2}/\d{1,2}/\d{2,4}$', val):
            return "release_date"
    
    for val in non_empty[:5]:
        cleaned = val.replace('%', '').replace('$', '').replace(',', '').strip()
        try:
            num = float(cleaned)
            if 0 <= num <= 100 and '%' in val:
                return "publishing_percentage"
        except:
            pass
    
    return None


def infer_mapping_from_data(headers: List[str], rows: List[Dict[str, str]], existing_mapping: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    """Improve mapping by inferring field types from sample data when headers are generic."""
    improved_mapping = existing_mapping.copy()
    
    generic_headers = [h for h in headers if h.startswith("Column_") and existing_mapping.get(h) is None]
    
    if not generic_headers:
        return improved_mapping
    
    sample_rows = rows[:10] if len(rows) >= 10 else rows
    
    title_candidates = []
    for header in generic_headers:
        samples = [row.get(header, "") for row in sample_rows]
        non_empty = [s for s in samples if s and s.strip()]
        
        if non_empty:
            avg_len = sum(len(s) for s in non_empty) / len(non_empty)
            all_text = all(isinstance(s, str) and not s.replace('.', '').replace('-', '').isdigit() for s in non_empty)
            if all_text and 3 < avg_len < 100:
                title_candidates.append((header, avg_len, len(non_empty)))
    
    mapped_fields = set(v for v in improved_mapping.values() if v)
    
    for header in generic_headers:
        if improved_mapping.get(header) is not None:
            continue
            
        samples = [row.get(header, "") for row in sample_rows]
        inferred = infer_field_from_sample_data(samples)
        
        if inferred and inferred not in mapped_fields:
            improved_mapping[header] = inferred
            mapped_fields.add(inferred)
    
    if "title" not in mapped_fields and title_candidates:
        title_candidates.sort(key=lambda x: (-x[2], x[1]))
        best_candidate = title_candidates[0][0]
        improved_mapping[best_candidate] = "title"
        mapped_fields.add("title")
    
    if "primary_artist" not in mapped_fields:
        for header in generic_headers:
            if improved_mapping.get(header) is not None:
                continue
            samples = [row.get(header, "") for row in sample_rows]
            non_empty = [s for s in samples if s and s.strip()]
            if non_empty:
                avg_len = sum(len(s) for s in non_empty) / len(non_empty)
                all_text = all(isinstance(s, str) and not s.replace('.', '').replace('-', '').isdigit() for s in non_empty)
                if all_text and 2 < avg_len < 50:
                    improved_mapping[header] = "primary_artist"
                    break
    
    return improved_mapping


def apply_mapping_to_rows(rows: List[Dict[str, str]], mapping: Dict[str, Optional[str]]) -> List[Dict[str, Any]]:
    mapped_rows = []
    
    for row in rows:
        mapped_row = {}
        for csv_header, field_name in mapping.items():
            if field_name and csv_header in row:
                value = row[csv_header].strip() if row[csv_header] else None
                
                if field_name in ["publishing_percentage", "master_percentage", "advance_amount"]:
                    try:
                        if value:
                            value = value.replace("%", "").replace("$", "").replace(",", "").strip()
                            value = float(value) if value else None
                    except ValueError:
                        value = None
                        
                mapped_row[field_name] = value
                
        if mapped_row.get("title"):
            mapped_rows.append(mapped_row)
    
    return mapped_rows


def validate_mapped_data(mapped_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid_rows = []
    invalid_rows = []
    
    for idx, row in enumerate(mapped_rows):
        errors = []
        
        if not row.get("title"):
            errors.append("Missing required field: title")
        
        if row.get("isrc"):
            isrc = row["isrc"]
            if len(isrc) < 10:
                errors.append(f"Invalid ISRC format: {isrc}")
                
        if row.get("iswc"):
            iswc = row["iswc"]
            if not (iswc.startswith("T-") or iswc.startswith("T")):
                errors.append(f"Invalid ISWC format: {iswc}")
        
        if row.get("publishing_percentage"):
            try:
                pct = float(row["publishing_percentage"])
                if pct < 0 or pct > 100:
                    errors.append(f"Publishing percentage out of range: {pct}")
            except (ValueError, TypeError):
                errors.append(f"Invalid publishing percentage: {row['publishing_percentage']}")
                
        if row.get("master_percentage"):
            try:
                pct = float(row["master_percentage"])
                if pct < 0 or pct > 100:
                    errors.append(f"Master percentage out of range: {pct}")
            except (ValueError, TypeError):
                errors.append(f"Invalid master percentage: {row['master_percentage']}")
        
        if errors:
            invalid_rows.append({"row_index": idx, "data": row, "errors": errors})
        else:
            valid_rows.append(row)
    
    return {
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "total": len(mapped_rows),
        "valid_count": len(valid_rows),
        "invalid_count": len(invalid_rows)
    }
