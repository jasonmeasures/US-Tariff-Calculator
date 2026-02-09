#!/usr/bin/env python3
"""
Section 232 Requirement Checker
Determines if an HTS code requires material content percentages
"""

import sqlite3
import sys

DB_PATH = "us_tariff_calculator.db"


def check_section232_requirement(hts_code):
    """
    Check if HTS code requires Section 232 material content data

    Returns dict with:
    - requires_section232: bool
    - materials: list of required materials (aluminum, steel, copper)
    - programs: list of Section 232 programs that apply
    """
    # Normalize HTS code
    normalized_hts = hts_code.replace('.', '').replace('-', '').replace(' ', '').strip()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check for Section 232 overlays
    cursor.execute('''
        SELECT program_name, tariff_basis
        FROM hts_overlay_mappings
        WHERE hts_code = ?
        AND program_name LIKE '%232%'
    ''', (normalized_hts,))

    results = cursor.fetchall()
    conn.close()

    if not results:
        return {
            "hts_code": hts_code,
            "requires_section232": False,
            "materials": [],
            "programs": []
        }

    # Determine which materials are required
    materials = []
    programs = []

    for program, basis in results:
        programs.append(program)

        if 'Aluminum' in program:
            materials.append('aluminum')
        elif 'Steel' in program:
            materials.append('steel')
        elif 'Copper' in program:
            materials.append('copper')

    # Remove duplicates
    materials = list(set(materials))

    return {
        "hts_code": hts_code,
        "requires_section232": True,
        "materials": materials,
        "programs": programs,
        "note": "⚠️  Country of smelt and pour may be required (can differ from COO)"
    }


if __name__ == "__main__":
    print('=' * 80)
    print('SECTION 232 REQUIREMENT CHECKER')
    print('=' * 80)
    print()

    # Test cases
    test_cases = [
        "8543.70.98.60",  # Electronic parts (your example)
        "8708.80.65.90",  # Suspension shock absorbers (aluminum)
        "0402.99.68",     # Dairy products with aluminum
        "7308.90.30.00",  # Steel structures
    ]

    for hts in test_cases:
        result = check_section232_requirement(hts)

        hts_formatted = f"{hts[:4]}.{hts[4:6]}.{hts[6:8]}.{hts[8:]}" if '.' not in hts and len(hts.replace('.','')) >= 8 else hts

        print(f"HTS Code: {hts_formatted}")
        print(f"  Requires Section 232: {'YES ⚠️' if result['requires_section232'] else 'NO ✅'}")

        if result['requires_section232']:
            print(f"  Materials Required: {', '.join(result['materials']).title()}")
            print(f"  Programs:")
            for prog in result['programs']:
                print(f"    • {prog}")
            if 'note' in result:
                print(f"  {result['note']}")
        else:
            print(f"  ✅ No material percentages needed")
            print(f"  ✅ No country of smelt and pour needed")

        print()

    print('=' * 80)
    print('UI IMPLEMENTATION NOTES')
    print('=' * 80)
    print()
    print('The material content fields should ONLY appear when:')
    print('  1. User enters an HTS code')
    print('  2. System checks if HTS requires Section 232')
    print('  3. If YES: Show aluminum/steel/copper percentage sliders')
    print('  4. If NO: Hide material content section entirely')
    print()
    print('This prevents confusion for users entering HTS codes that')
    print('do not require material composition data.')
    print('=' * 80)
