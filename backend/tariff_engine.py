"""
US Tariff Calculator - Engine
Core calculation logic for duty, MPF, HMF, and landed cost
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import os
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "us_tariff_calculator.db")

# Load IEEPA rates - prefer DB-backed, fallback to hardcoded
def get_ieepa_rate_from_db(country: str, entry_date: str, hts_code: str) -> Optional[Dict]:
    """
    Database-backed IEEPA rate lookup.
    Reads from ieepa_country_rates and ieepa_annex_exceptions tables.
    Returns dict with rate, chapter99_code, csms, notes, or None if not applicable.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Normalize HTS code
    hts_normalized = hts_code.replace('.', '').replace('-', '').replace(' ', '').strip()

    # Check Annex II HTS exemption
    cursor.execute("""
        SELECT 1 FROM ieepa_annex_exceptions
        WHERE exception_type = 'HTS' AND value = ? AND is_active = 1
    """, (hts_normalized,))
    if cursor.fetchone():
        conn.close()
        return None

    # Also check 8-digit prefix
    if len(hts_normalized) >= 8:
        cursor.execute("""
            SELECT 1 FROM ieepa_annex_exceptions
            WHERE exception_type = 'HTS' AND value = ? AND is_active = 1
        """, (hts_normalized[:8],))
        if cursor.fetchone():
            conn.close()
            return None

    # Check Annex II COO exemption
    cursor.execute("""
        SELECT 1 FROM ieepa_annex_exceptions
        WHERE exception_type = 'COO' AND value = ? AND is_active = 1
    """, (country.upper(),))
    if cursor.fetchone():
        conn.close()
        return None

    # Parse entry date
    try:
        entry_date_clean = str(entry_date).split(' ')[0]
    except:
        conn.close()
        return None

    # Try country-specific rate first
    cursor.execute("""
        SELECT rate, csms_reference, chapter99_code, effective_date, notes
        FROM ieepa_country_rates
        WHERE country_code = ? AND effective_date <= ? AND is_active = 1
        ORDER BY effective_date DESC
        LIMIT 1
    """, (country.upper(), entry_date_clean))

    result = cursor.fetchone()

    if not result:
        # Fallback to GLOBAL
        cursor.execute("""
            SELECT rate, csms_reference, chapter99_code, effective_date, notes
            FROM ieepa_country_rates
            WHERE country_code = 'GLOBAL' AND effective_date <= ? AND is_active = 1
            ORDER BY effective_date DESC
            LIMIT 1
        """, (entry_date_clean,))
        result = cursor.fetchone()

    conn.close()

    if not result or result[0] == 0:
        return None

    return {
        'rate': result[0],
        'csms': result[1],
        'chapter99_code': result[2],
        'implementation_date': result[3],
        'notes': result[4] or f'IEEPA Reciprocal - CSMS {result[1]}'
    }


def _init_ieepa():
    """Initialize IEEPA rate function - prefer DB, fallback to hardcoded"""
    # Check if DB has IEEPA rates
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ieepa_country_rates WHERE is_active = 1")
        count = cursor.fetchone()[0]
        conn.close()
        if count > 0:
            return get_ieepa_rate_from_db
    except:
        pass

    # Fallback to hardcoded module
    try:
        from ieepa_rates import get_ieepa_rate as _hardcoded_ieepa, load_annex_ii_exceptions
        excel_path = Path(__file__).parent.parent / "data" / "Trump_Tariffs_Summary_20260122.xlsx"
        if excel_path.exists():
            load_annex_ii_exceptions(str(excel_path))
        return _hardcoded_ieepa
    except ImportError:
        return None

get_ieepa_rate = _init_ieepa()


@dataclass
class DutyBreakdown:
    """Breakdown of a single duty component"""
    name: str
    rate: float
    amount: float
    description: str
    material_basis: Optional[str] = None
    material_percent: Optional[float] = None


@dataclass
class CalculationResult:
    """Complete tariff calculation result"""
    hts_code: str
    country: str
    entry_date: str
    entered_value: float

    # Rates
    base_rate: float
    total_duty_rate: float

    # Amounts
    base_duty: float
    overlay_duty: float
    total_duty: float
    mpf: float
    hmf: float
    landed_cost: float

    # Breakdown
    breakdown: List[Dict]
    confidence: int
    notes: List[str]
    citations: List[str]


def calculate_mpf(entered_value: float, is_informal: bool = False) -> float:
    """
    Calculate Merchandise Processing Fee (MPF)
    Rate: 0.3464% of entered value
    Minimum: $31.67, Maximum: $614.35
    Informal entries (<$2,500): $2.22, $6.66, or $9.99 depending on mode
    """
    if is_informal:
        return 2.22  # Simplified for now

    mpf_rate = 0.003464
    mpf_amount = entered_value * mpf_rate

    # Apply min/max caps
    mpf_amount = max(31.67, min(mpf_amount, 614.35))

    return round(mpf_amount, 2)


def calculate_hmf(entered_value: float, mode: str = 'ocean') -> float:
    """
    Calculate Harbor Maintenance Fee (HMF)
    Rate: 0.125% of entered value
    Only applies to ocean shipments
    """
    if mode.lower() != 'ocean':
        return 0.0

    hmf_rate = 0.00125
    return round(entered_value * hmf_rate, 2)


def get_base_rate(hts_code: str) -> Tuple[float, str, bool]:
    """
    Get base MFN duty rate for HTS code
    Returns: (rate, description, found)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT column1_advalorem, description
        FROM base_hts_rates
        WHERE hts_code = ?
    """, (hts_code,))

    result = cursor.fetchone()
    conn.close()

    if result:
        rate = result[0] if result[0] is not None else 0.0
        description = result[1] or "No description"
        return rate, description, True

    return 0.0, "HTS code not found", False


def get_applicable_overlays(
    hts_code: str,
    country: str,
    entry_date: str
) -> List[Dict]:
    """
    Get all applicable tariff overlays for given HTS, country, and date
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    overlays = []

    # Try exact match first (10-digit)
    cursor.execute("""
        SELECT DISTINCT
            m.program_name,
            m.duty_rate,
            m.jurisdiction,
            m.effective_date,
            m.chapter99_code,
            m.tariff_basis
        FROM hts_overlay_mappings m
        WHERE m.hts_code = ?
        AND (m.jurisdiction = ? OR m.jurisdiction = 'GLOBAL')
        AND m.is_active = 1
    """, (hts_code, country.upper()))

    for row in cursor.fetchall():
        overlays.append({
            'program_name': row[0],
            'duty_rate': row[1],
            'jurisdiction': row[2],
            'effective_date': row[3],
            'chapter99_code': row[4] or '',
            'tariff_basis': row[5] or ''
        })

    # Also try 8-digit match (for Section 301, Section 232, etc.)
    # Many tariff programs use 8-digit HTS classifications
    if len(hts_code) >= 8:
        hts_8digit = hts_code[:8]
        cursor.execute("""
            SELECT DISTINCT
                m.program_name,
                m.duty_rate,
                m.jurisdiction,
                m.effective_date,
                m.chapter99_code,
                m.tariff_basis
            FROM hts_overlay_mappings m
            WHERE m.hts_code = ?
            AND (m.jurisdiction = ? OR m.jurisdiction = 'GLOBAL')
            AND m.is_active = 1
        """, (hts_8digit, country.upper()))

        for row in cursor.fetchall():
            # Check if this overlay is already in the list (to avoid duplicates)
            overlay_key = (row[0], row[1], row[2])  # program_name, duty_rate, jurisdiction
            if not any(o['program_name'] == row[0] and o['duty_rate'] == row[1]
                      for o in overlays):
                overlays.append({
                    'program_name': row[0],
                    'duty_rate': row[1],
                    'jurisdiction': row[2],
                    'effective_date': row[3],
                    'chapter99_code': row[4] or '',
                    'tariff_basis': row[5] or ''
                })

    conn.close()
    return overlays


def determine_material_basis(program_name: str) -> Optional[str]:
    """Determine if overlay requires material basis calculation"""
    program_lower = program_name.lower()

    if 'aluminum' in program_lower or 'alum' in program_lower:
        return 'aluminum'
    elif 'steel' in program_lower:
        return 'steel'
    elif 'copper' in program_lower:
        return 'copper'

    return None


def calculate_duty(
    hts_code: str,
    country: str,
    entry_date: str,
    value: float,
    aluminum_percent: float = 0.0,
    steel_percent: float = 0.0,
    copper_percent: float = 0.0,
    mode: str = 'ocean'
) -> CalculationResult:
    """
    Calculate total duty for an import entry

    Args:
        hts_code: 10-digit HTS code (normalized, no dots)
        country: 2-letter country code (e.g., 'JP', 'CN')
        entry_date: Entry date in YYYY-MM-DD format
        value: Entered value in USD
        aluminum_percent: Aluminum content percentage (0-100)
        steel_percent: Steel content percentage (0-100)
        copper_percent: Copper content percentage (0-100)
        mode: Transportation mode ('ocean', 'air', 'truck', 'rail')

    Returns:
        CalculationResult with full breakdown
    """

    # Normalize inputs
    hts_code = hts_code.replace('.', '').replace('-', '').replace(' ', '').strip()
    country = country.upper()

    # Initialize results
    breakdown = []
    notes = []
    citations = []
    confidence = 100

    # 1. Get base rate
    base_rate, hts_description, found = get_base_rate(hts_code)

    if not found:
        notes.append(f"HTS code {hts_code} not found in database")
        confidence = 50

    base_duty = round(value * (base_rate / 100), 2)

    breakdown.append({
        'name': 'Base MFN Rate',
        'rate': base_rate,
        'amount': base_duty,
        'description': f'Column 1 duty: {base_rate}%'
    })

    citations.append(f"HTS {hts_code}: {hts_description}")

    # 2. Get applicable overlays
    all_overlays = get_applicable_overlays(hts_code, country, entry_date)

    # Filter overlays by effective date and keep only the most recent for each program type
    entry_dt = datetime.strptime(entry_date.split(' ')[0], '%Y-%m-%d')

    # Group overlays by base program name (strip date suffixes like "Mar12", "Jun04")
    from collections import defaultdict
    programs_by_base = defaultdict(list)

    for overlay in all_overlays:
        program = overlay['program_name']
        effective_date = overlay.get('effective_date', '')

        # Check if tariff is effective on entry date
        if effective_date:
            try:
                effective_dt = datetime.strptime(effective_date, '%Y-%m-%d')

                # Skip overlay if entry date is before effective date
                if entry_dt < effective_dt:
                    continue

                # Add effective date to overlay for sorting
                overlay['_effective_dt'] = effective_dt
            except Exception as e:
                # If date parsing fails, log and skip this overlay
                print(f"Warning: Could not parse dates for overlay '{program}': {e}")
                continue
        else:
            overlay['_effective_dt'] = datetime(2000, 1, 1)  # Default to old date if no effective date

        # Group by base program name (e.g., "Sec 232 Aluminum (FRNs)" regardless of suffix)
        base_program = program.rsplit(' ', 1)[0] if program.split()[-1] in ['Mar12', 'Jun04', 'Apr09'] else program
        programs_by_base[base_program].append(overlay)

    # For each program type, keep only the most recent effective overlay
    overlays = []
    for base_program, program_overlays in programs_by_base.items():
        # Sort by effective date descending and take the most recent
        most_recent = sorted(program_overlays, key=lambda x: x['_effective_dt'], reverse=True)[0]
        overlays.append(most_recent)

    overlay_duty = 0.0

    for overlay in overlays:
        program = overlay['program_name']
        rate = overlay['duty_rate']
        jurisdiction = overlay['jurisdiction']
        chapter99_code = overlay.get('chapter99_code', '')
        tariff_basis = overlay.get('tariff_basis', '')

        # Check if material basis applies
        material_basis = determine_material_basis(program)

        if material_basis:
            # Apply material percentage
            material_pct = 0.0

            if material_basis == 'aluminum':
                material_pct = aluminum_percent
            elif material_basis == 'steel':
                material_pct = steel_percent
            elif material_basis == 'copper':
                material_pct = copper_percent

            # Effective rate = overlay rate × material percentage
            effective_rate = rate * (material_pct / 100)
            amount = round(value * (effective_rate / 100), 2)

            breakdown.append({
                'name': program,
                'rate': rate,
                'effective_rate': effective_rate,
                'amount': amount,
                'description': f'{rate}% × {material_pct}% {material_basis}',
                'material_basis': material_basis,
                'material_percent': material_pct,
                'chapter99_code': chapter99_code,
                'tariff_basis': tariff_basis
            })

            notes.append(f"{program}: {rate}% applied to {material_pct}% {material_basis} content")

        else:
            # No material basis - apply full rate
            amount = round(value * (rate / 100), 2)

            breakdown.append({
                'name': program,
                'rate': rate,
                'amount': amount,
                'description': f'{program}: {rate}%',
                'chapter99_code': chapter99_code,
                'tariff_basis': tariff_basis
            })

        overlay_duty += amount
        citations.append(f"{program} ({jurisdiction}): {rate}%")

    # 2b. Check for IEEPA Reciprocal Tariff
    # CRITICAL: Per CSMS 64649265 and 64680374, IEEPA Reciprocal is EXEMPT when Section 232 applies
    # Exception: "subject to Sec 232"
    # Use Chapter 99 code 9903.01.33 at 0% when Section 232 tariffs are applied

    if get_ieepa_rate:
        ieepa_result = get_ieepa_rate(country, entry_date, hts_code)
        if ieepa_result:
            # Check if Section 232 was applied
            has_section_232 = any(
                'Sec 232' in b.get('name', '')
                for b in breakdown
                if b.get('amount', 0) > 0
            )

            if has_section_232:
                # Section 232 applies → IEEPA Reciprocal is EXEMPT
                # Use Chapter 99 code 9903.01.33 (IEEPA Reciprocal 232 Exclusion) at 0%
                breakdown.append({
                    'name': 'IEEPA Reciprocal (232 Exclusion)',
                    'rate': 0.0,
                    'amount': 0.0,
                    'description': 'IEEPA Reciprocal: 0% (Section 232 Exclusion)',
                    'chapter99_code': '99030133',
                    'tariff_basis': 'CSMS 64649265 - Exempt when subject to Sec 232'
                })

                notes.append(
                    f"IEEPA Reciprocal EXEMPT: Section 232 tariff applies, "
                    f"therefore IEEPA excluded per CSMS 64649265 (Chapter 99: 9903.01.33 at 0%)"
                )
            else:
                # No Section 232 → Apply normal IEEPA Reciprocal rate
                ieepa_rate = ieepa_result['rate']
                ieepa_ch99 = ieepa_result['chapter99_code']
                ieepa_csms = ieepa_result['csms']
                ieepa_amount = round(value * (ieepa_rate / 100), 2)

                breakdown.append({
                    'name': 'IEEPA Reciprocal',
                    'rate': ieepa_rate,
                    'amount': ieepa_amount,
                    'description': f'IEEPA Reciprocal: {ieepa_rate}%',
                    'chapter99_code': ieepa_ch99,
                    'tariff_basis': f'CSMS {ieepa_csms}'
                })

                overlay_duty += ieepa_amount
                citations.append(f"IEEPA Reciprocal (CSMS {ieepa_csms}): {ieepa_rate}%")
                notes.append(f"IEEPA Reciprocal tariff: {ieepa_rate}% (Chapter 99: {ieepa_ch99})")

    # 3. Calculate total duty
    total_duty_rate = base_rate + sum([
        b.get('effective_rate', b.get('rate', 0))
        for b in breakdown[1:]  # Skip base rate
    ])
    total_duty = base_duty + overlay_duty

    # 4. Calculate MPF and HMF
    mpf = calculate_mpf(value)
    hmf = calculate_hmf(value, mode)

    breakdown.append({
        'name': 'MPF',
        'rate': 0.3464,
        'amount': mpf,
        'description': f'Merchandise Processing Fee (0.3464%, min $31.67, max $614.35)'
    })

    if hmf > 0:
        breakdown.append({
            'name': 'HMF',
            'rate': 0.125,
            'amount': hmf,
            'description': f'Harbor Maintenance Fee (0.125%, ocean only)'
        })

    # 5. Calculate landed cost
    landed_cost = value + total_duty + mpf + hmf

    return CalculationResult(
        hts_code=hts_code,
        country=country,
        entry_date=entry_date,
        entered_value=value,
        base_rate=base_rate,
        total_duty_rate=total_duty_rate,
        base_duty=base_duty,
        overlay_duty=overlay_duty,
        total_duty=total_duty,
        mpf=mpf,
        hmf=hmf,
        landed_cost=landed_cost,
        breakdown=[b for b in breakdown],
        confidence=confidence,
        notes=notes,
        citations=citations
    )


def format_result(result: CalculationResult) -> str:
    """Format calculation result as readable text"""
    output = []
    output.append(f"=== DUTY CALCULATION ===")
    output.append(f"HTS Code: {result.hts_code}")
    output.append(f"Country: {result.country}")
    output.append(f"Entry Date: {result.entry_date}")
    output.append(f"Entered Value: ${result.entered_value:,.2f}")
    output.append(f"")
    output.append(f"DUTY RATE: {result.total_duty_rate:.2f}%")
    output.append(f"TOTAL DUTY: ${result.total_duty:,.2f}")
    output.append(f"")
    output.append(f"Breakdown:")

    for item in result.breakdown:
        if 'material_basis' in item and item['material_basis']:
            output.append(
                f"  • {item['name']}: {item['rate']}% × {item['material_percent']}% {item['material_basis']} "
                f"= {item['effective_rate']:.2f}% = ${item['amount']:,.2f}"
            )
        else:
            output.append(f"  • {item['name']}: ${item['amount']:,.2f}")

    output.append(f"")
    output.append(f"LANDED COST: ${result.landed_cost:,.2f}")
    output.append(f"")
    output.append(f"Confidence: {result.confidence}%")

    if result.notes:
        output.append(f"")
        output.append(f"Notes:")
        for note in result.notes:
            output.append(f"  • {note}")

    return "\n".join(output)


if __name__ == "__main__":
    # Test case from requirements
    print("=== TEST CASE ===")
    print("Input: HTS 8708.80.65.90, Country JP, Date 2025-03-15, Value $10,000, Aluminum 100%")
    print("Expected: Base 2.5% ($250) + Sec 232 Aluminum 25% ($2,500) = 27.5% ($2,750 duty)")
    print()

    result = calculate_duty(
        hts_code="8708.80.65.90",
        country="JP",
        entry_date="2025-03-15",
        value=10000.0,
        aluminum_percent=100.0,
        mode='ocean'
    )

    print(format_result(result))
