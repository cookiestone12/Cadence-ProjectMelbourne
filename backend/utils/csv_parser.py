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


def parse_csv_with_ai(csv_content: str, headers: List[str]) -> Dict[str, Any]:
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
        mapping_text = response.choices[0].message.content.strip()
        if mapping_text.startswith("```"):
            mapping_text = mapping_text.split("```")[1]
            if mapping_text.startswith("json"):
                mapping_text = mapping_text[4:]
        mapping = json.loads(mapping_text)
        return {"mapping": mapping, "success": True}
    except json.JSONDecodeError as e:
        return {"mapping": {}, "success": False, "error": f"Failed to parse AI response: {str(e)}"}


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
