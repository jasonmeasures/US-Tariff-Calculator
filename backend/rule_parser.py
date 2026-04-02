"""
US Tariff Calculator - Rule Parser
Parses natural language rule change descriptions into structured database changes.
Uses regex pattern matching first, falls back to Claude API if available and needed.
"""

import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import os

# Country name to code mapping
COUNTRY_MAP = {
    'china': 'CN', 'chinese': 'CN',
    'hong kong': 'HK', 'hongkong': 'HK',
    'macau': 'MO', 'macao': 'MO',
    'mexico': 'MX', 'mexican': 'MX',
    'canada': 'CA', 'canadian': 'CA',
    'japan': 'JP', 'japanese': 'JP',
    'south korea': 'KR', 'korea': 'KR', 'korean': 'KR',
    'india': 'IN', 'indian': 'IN',
    'brazil': 'BR', 'brazilian': 'BR',
    'germany': 'DE', 'german': 'DE',
    'france': 'FR', 'french': 'FR',
    'italy': 'IT', 'italian': 'IT',
    'united kingdom': 'GB', 'uk': 'GB', 'britain': 'GB', 'british': 'GB',
    'vietnam': 'VN', 'vietnamese': 'VN',
    'taiwan': 'TW', 'taiwanese': 'TW',
    'thailand': 'TH', 'thai': 'TH',
    'switzerland': 'CH', 'swiss': 'CH',
    'liechtenstein': 'LI',
    'global': 'GLOBAL', 'all countries': 'GLOBAL', 'worldwide': 'GLOBAL',
}

# Program name normalization
PROGRAM_MAP = {
    'ieepa': 'IEEPA Reciprocal',
    'ieepa reciprocal': 'IEEPA Reciprocal',
    'reciprocal': 'IEEPA Reciprocal',
    'reciprocal tariff': 'IEEPA Reciprocal',
    'section 232 aluminum': 'Sec 232 Aluminum (FRNs)',
    'sec 232 aluminum': 'Sec 232 Aluminum (FRNs)',
    '232 aluminum': 'Sec 232 Aluminum (FRNs)',
    'section 232 steel': 'Sec 232 Steel (FRNs)',
    'sec 232 steel': 'Sec 232 Steel (FRNs)',
    '232 steel': 'Sec 232 Steel (FRNs)',
    'section 232 copper': 'Sec 232 Copper (FRNs)',
    'sec 232 copper': 'Sec 232 Copper (FRNs)',
    '232 copper': 'Sec 232 Copper (FRNs)',
    'section 232 auto': 'Sec 232 Auto Parts (FRNs)',
    'sec 232 auto': 'Sec 232 Auto Parts (FRNs)',
    '232 auto': 'Sec 232 Auto Parts (FRNs)',
    'section 232 semiconductor': 'Sec 232 Semiconductor',
    'sec 232 semiconductor': 'Sec 232 Semiconductor',
    '232 semiconductor': 'Sec 232 Semiconductor',
    'section 301': 'Sec 301 (China)',
    'sec 301': 'Sec 301 (China)',
    '301': 'Sec 301 (China)',
}

# Month name mapping
MONTHS = {
    'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
    'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
    'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
    'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12,
}


def parse_date(date_str: str) -> Optional[str]:
    """Parse various date formats into YYYY-MM-DD"""
    date_str = date_str.strip().lower()

    # Handle relative dates
    if date_str in ('today', 'now', 'immediately', 'immediate', 'effective immediately'):
        return datetime.now().strftime('%Y-%m-%d')
    if date_str == 'tomorrow':
        return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    # Try YYYY-MM-DD
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        pass

    # Try "Month Day, Year" or "Month Day Year"
    match = re.match(r'(\w+)\s+(\d{1,2}),?\s*(\d{4})?', date_str)
    if match:
        month_str, day, year = match.groups()
        month = MONTHS.get(month_str.lower())
        if month:
            year = int(year) if year else datetime.now().year
            return f"{year}-{month:02d}-{int(day):02d}"

    # Try "Day Month Year"
    match = re.match(r'(\d{1,2})\s+(\w+),?\s*(\d{4})?', date_str)
    if match:
        day, month_str, year = match.groups()
        month = MONTHS.get(month_str.lower())
        if month:
            year = int(year) if year else datetime.now().year
            return f"{year}-{month:02d}-{int(day):02d}"

    # Try MM/DD/YYYY
    try:
        dt = datetime.strptime(date_str, '%m/%d/%Y')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        pass

    return None


def resolve_country(text: str) -> Optional[str]:
    """Resolve country name or code to 2-letter ISO code"""
    text_lower = text.strip().lower()

    # Direct code (2 letters)
    if len(text_lower) == 2 and text_lower.isalpha():
        return text_lower.upper()

    # Name lookup
    for name, code in COUNTRY_MAP.items():
        if name in text_lower:
            return code

    return None


def resolve_program(text: str) -> Optional[str]:
    """Resolve program description to canonical name"""
    text_lower = text.strip().lower()
    for key, value in PROGRAM_MAP.items():
        if key in text_lower:
            return value
    return None


def parse_rule_prompt(prompt: str) -> Dict:
    """
    Parse a natural language rule change description into structured changes.

    Returns dict with:
        changes: List of RuleChange dicts
        summary: Human-readable summary
        warnings: List of potential issues
        confidence: 0-100 confidence score
        prompt_text: Original prompt
    """
    changes = []
    warnings = []
    confidence = 0

    prompt_lower = prompt.lower().strip()

    # ============================================================
    # PATTERN 1: IEEPA rate changes
    # "Set/Change China IEEPA to 35% starting/on/effective March 1, 2025"
    # ============================================================
    ieepa_patterns = [
        # "Set China IEEPA to 35% starting March 1"
        r"(?:set|change|update|increase|decrease|raise|lower)\s+(?:the\s+)?(\w[\w\s]*?)\s+(?:ieepa|reciprocal)(?:\s+(?:rate|tariff))?\s+(?:to|at)\s+(\d+(?:\.\d+)?)\s*%\s*(?:(?:starting|on|effective|from|beginning)\s+(.+?))?(?:\.|$|,|\s+(?:and|also|per|csms))",
        # "IEEPA for China to 35% on March 1"
        r"(?:ieepa|reciprocal)(?:\s+(?:rate|tariff))?\s+(?:for|on)\s+(\w[\w\s]*?)\s+(?:to|at)\s+(\d+(?:\.\d+)?)\s*%\s*(?:(?:starting|on|effective|from)\s+(.+?))?(?:\.|$|,)",
        # "35% IEEPA on China starting March 1"
        r"(\d+(?:\.\d+)?)\s*%\s+(?:ieepa|reciprocal)(?:\s+(?:rate|tariff))?\s+(?:for|on)\s+(\w[\w\s]*?)(?:\s+(?:starting|on|effective|from)\s+(.+?))?(?:\.|$|,)",
    ]

    for pattern in ieepa_patterns:
        matches = re.finditer(pattern, prompt_lower, re.IGNORECASE)
        for match in matches:
            groups = match.groups()

            if pattern == ieepa_patterns[2]:
                # Swapped: rate first, then country
                rate_str, country_str, date_str = groups
            else:
                country_str, rate_str, date_str = groups

            country_code = resolve_country(country_str)
            rate = float(rate_str)
            effective_date = parse_date(date_str) if date_str else datetime.now().strftime('%Y-%m-%d')

            if country_code:
                changes.append({
                    'action': 'CREATE',
                    'table': 'ieepa_country_rates',
                    'values': {
                        'country_code': country_code,
                        'effective_date': effective_date,
                        'rate': rate,
                        'csms_reference': None,
                        'chapter99_code': '99030101',
                        'notes': f'Admin rule change from prompt',
                    },
                    'filters': None,
                    'description': f"Add IEEPA rate: {country_code} at {rate}% effective {effective_date}",
                })
                confidence = max(confidence, 90)
            else:
                warnings.append(f"Could not resolve country: '{country_str}'")
                confidence = max(confidence, 40)

    # ============================================================
    # PATTERN 2: IEEPA suspension
    # "Suspend Brazil IEEPA" / "Exempt Mexico from IEEPA"
    # ============================================================
    suspend_patterns = [
        r"(?:suspend|remove|exempt|pause|halt|stop)\s+(?:the\s+)?(\w[\w\s]*?)\s+(?:from\s+)?(?:ieepa|reciprocal)(?:\s+(?:tariff|rate))?(?:\s+(?:starting|on|effective|from)\s+(.+?))?(?:\.|$|,)",
        r"(?:suspend|remove|exempt|pause)\s+(?:ieepa|reciprocal)(?:\s+(?:tariff|rate))?\s+(?:for|on|from)\s+(\w[\w\s]*?)(?:\s+(?:starting|on|effective)\s+(.+?))?(?:\.|$|,)",
    ]

    for pattern in suspend_patterns:
        matches = re.finditer(pattern, prompt_lower, re.IGNORECASE)
        for match in matches:
            country_str, date_str = match.groups()
            country_code = resolve_country(country_str)
            effective_date = parse_date(date_str) if date_str else datetime.now().strftime('%Y-%m-%d')

            if country_code:
                changes.append({
                    'action': 'CREATE',
                    'table': 'ieepa_country_rates',
                    'values': {
                        'country_code': country_code,
                        'effective_date': effective_date,
                        'rate': 0.0,
                        'csms_reference': None,
                        'chapter99_code': None,
                        'notes': 'Suspended via admin prompt',
                    },
                    'filters': None,
                    'description': f"Suspend IEEPA for {country_code}: 0% effective {effective_date}",
                })
                confidence = max(confidence, 85)

    # ============================================================
    # PATTERN 3: Section 232/301 overlay changes
    # "Add Section 232 Steel at 25% for HTS 7318.22.00"
    # "Change Section 301 rate for HTS 8543.70.98 to 50%"
    # ============================================================
    overlay_patterns = [
        # "Add Section 232 Steel at 25% for HTS 7318.22.00"
        r"(?:add|create|new)\s+(?:a\s+)?(?:section|sec)\s*(\d+)\s+(\w+)(?:\s+(?:overlay|tariff|rate))?\s+(?:at|of)\s+(\d+(?:\.\d+)?)\s*%\s+(?:for\s+)?(?:hts\s+)?([0-9.]+)",
        # "Set Section 232 Aluminum to 50%"
        r"(?:set|change|update)\s+(?:section|sec)\s*(\d+)\s+(\w+)(?:\s+(?:overlay|tariff|rate))?\s+(?:to|at)\s+(\d+(?:\.\d+)?)\s*%",
    ]

    for i, pattern in enumerate(overlay_patterns):
        matches = re.finditer(pattern, prompt_lower, re.IGNORECASE)
        for match in matches:
            groups = match.groups()

            if i == 0:  # Add new overlay for specific HTS
                section_num, material, rate_str, hts_code = groups
                program = resolve_program(f"section {section_num} {material}")
                hts_normalized = hts_code.replace('.', '').replace('-', '')

                if program:
                    changes.append({
                        'action': 'CREATE',
                        'table': 'hts_overlay_mappings',
                        'values': {
                            'hts_code': hts_normalized,
                            'program_name': program,
                            'duty_rate': float(rate_str),
                            'jurisdiction': 'GLOBAL',
                            'effective_date': datetime.now().strftime('%Y-%m-%d'),
                        },
                        'filters': None,
                        'description': f"Add {program} overlay for HTS {hts_code} at {rate_str}%",
                    })
                    confidence = max(confidence, 85)

            elif i == 1:  # Change rate for a program
                section_num, material, rate_str = groups
                program = resolve_program(f"section {section_num} {material}")

                if program:
                    warnings.append(f"Bulk rate change for {program} - this will affect all HTS codes under this program")
                    changes.append({
                        'action': 'UPDATE',
                        'table': 'hts_overlay_mappings',
                        'values': {'duty_rate': float(rate_str)},
                        'filters': {'program_name': program, 'is_active': 1},
                        'description': f"Update all {program} overlays to {rate_str}%",
                    })
                    confidence = max(confidence, 75)

    # ============================================================
    # PATTERN 4: Deactivate overlay
    # "Remove Section 301 for HTS 85437098"
    # ============================================================
    deactivate_pattern = r"(?:remove|deactivate|delete|disable)\s+(?:section|sec)\s*(\d+)(?:\s+(\w+))?\s+(?:for\s+)?(?:hts\s+)?([0-9.]+)"
    matches = re.finditer(deactivate_pattern, prompt_lower, re.IGNORECASE)
    for match in matches:
        section_num, material, hts_code = match.groups()
        material = material or ''
        program = resolve_program(f"section {section_num} {material}".strip())
        hts_normalized = hts_code.replace('.', '').replace('-', '')

        filters = {'hts_code': hts_normalized}
        if program:
            filters['program_name'] = program

        changes.append({
            'action': 'DEACTIVATE',
            'table': 'hts_overlay_mappings',
            'values': {},
            'filters': filters,
            'description': f"Deactivate {program or f'Section {section_num}'} overlay for HTS {hts_code}",
        })
        confidence = max(confidence, 80)

    # ============================================================
    # PATTERN 5: CSMS reference extraction
    # "per CSMS 12345678" or "CSMS# 12345678"
    # ============================================================
    csms_match = re.search(r'(?:per\s+)?csms\s*#?\s*(\d{7,8})', prompt_lower)
    if csms_match and changes:
        csms_ref = csms_match.group(1)
        for change in changes:
            if change['table'] == 'ieepa_country_rates':
                change['values']['csms_reference'] = csms_ref
                change['description'] += f" (CSMS {csms_ref})"

    # ============================================================
    # If no patterns matched, try Claude API fallback
    # ============================================================
    if not changes:
        api_result = try_claude_api_fallback(prompt)
        if api_result:
            return api_result
        else:
            warnings.append("Could not parse the prompt. Try a simpler format like: 'Set China IEEPA to 35% starting March 1, 2025'")
            confidence = 0

    # Build summary
    if changes:
        summary = f"{len(changes)} change(s): " + "; ".join(c['description'] for c in changes)
    else:
        summary = "No changes detected"

    # Add generic warnings
    if not any('csms' in str(c.get('values', {})).lower() for c in changes if c['table'] == 'ieepa_country_rates'):
        for c in changes:
            if c['table'] == 'ieepa_country_rates' and c['action'] == 'CREATE':
                warnings.append("No CSMS reference provided - consider adding one for audit trail")

    return {
        'changes': changes,
        'summary': summary,
        'warnings': warnings,
        'confidence': confidence,
        'prompt_text': prompt,
    }


def try_claude_api_fallback(prompt: str) -> Optional[Dict]:
    """
    If ANTHROPIC_API_KEY is set, use Claude API for complex prompt parsing.
    Returns None if API is not available or fails.
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = """You are a US tariff rules interpreter. Given a natural language description
of a tariff rule change, return a JSON object with structured changes.

Available tables and their fields:
- ieepa_country_rates: country_code (2-letter ISO), effective_date (YYYY-MM-DD), rate (number), csms_reference, chapter99_code, notes
- hts_overlay_mappings: hts_code (10-digit no dots), program_name, duty_rate (number), jurisdiction, effective_date, chapter99_code, tariff_basis

Valid program names:
- Sec 232 Aluminum (FRNs), Sec 232 Steel (FRNs), Sec 232 Copper (FRNs)
- Sec 232 Auto Parts (FRNs), Sec 232 Semiconductor, Sec 232 MHDV + Buses + Parts
- Sec 301 (China), IEEPA Reciprocal

Return ONLY valid JSON in this format:
{
  "changes": [
    {
      "action": "CREATE|UPDATE|DEACTIVATE",
      "table": "table_name",
      "filters": {"field": "value"},
      "values": {"field": "value"},
      "description": "human readable description"
    }
  ],
  "summary": "overall description",
  "warnings": ["any concerns"],
  "confidence": 85
}"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        result_text = response.content[0].text

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            result = json.loads(json_match.group())
            result['prompt_text'] = prompt
            return result

    except ImportError:
        pass
    except Exception as e:
        print(f"Claude API fallback failed: {e}")

    return None


if __name__ == "__main__":
    # Test the parser
    test_prompts = [
        "Set China IEEPA to 35% starting March 1, 2025",
        "Suspend Brazil IEEPA effective immediately",
        "Add Section 232 Steel at 25% for HTS 7318.22.00",
        "Set India IEEPA to 30% on April 15, 2025 per CSMS 67200000",
        "Increase China IEEPA to 50% starting January 1, 2026 and suspend Brazil reciprocal",
    ]

    for prompt in test_prompts:
        print(f"\n{'='*60}")
        print(f"PROMPT: {prompt}")
        print(f"{'='*60}")
        result = parse_rule_prompt(prompt)
        print(f"Summary: {result['summary']}")
        print(f"Confidence: {result['confidence']}%")
        if result['warnings']:
            print(f"Warnings: {result['warnings']}")
        for c in result['changes']:
            print(f"  -> {c['action']} {c['table']}: {c['description']}")
