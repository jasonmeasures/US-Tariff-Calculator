"""
IEEPA Reciprocal Tariff Rates
Based on Trump_Tariffs_Summary_20260122.xlsx (ToT - CSMS Summary)
"""

from datetime import datetime
from typing import Optional, Dict

# Country-specific IEEPA rates with implementation dates
# Format: (implementation_date, rate, csms_number, chapter99_code)
IEEPA_RATES = {
    # Global baseline (starts 2025-04-05)
    'GLOBAL': [
        ('2025-04-05', 10.0, '64649265', '99030101'),  # 10% reciprocal
        ('2025-08-07', 10.0, '65829726', '99030101'),  # Updated (country-specific)
    ],

    # Exempt countries
    'CA': [
        ('2025-04-05', 0.0, '64649265', None),  # Canada EXEMPT
    ],
    'MX': [
        ('2025-03-04', 25.0, '64297292', '99030101'),  # IEEPA Mexico 25%
        ('2025-03-08', 0.0, '64335789', None),  # Suspended March 8 (entries on 3/7 still got 25%)
        ('2025-04-05', 0.0, '64649265', None),  # Mexico EXEMPT (confirmed)
    ],

    # China/Hong Kong/Macau
    'CN': [
        ('2025-02-04', 10.0, '64235342', '99030101'),   # IEEPA Fentanyl 10%
        ('2025-03-04', 20.0, '64299816', '99030124'),   # IEEPA Fentanyl 20% (specific code 9903.01.24)
        ('2025-04-09', 84.0, '64687696', '99030101'),   # IEEPA Reciprocal 84%
        ('2025-04-10', 125.0, '64701128', '99030100025'),  # IEEPA Reciprocal 125%
        ('2025-05-14', 10.0, '65029337', '99030100025'),  # Reduced to 10%
        ('2025-11-10', 10.0, '66749380', '99030100025'),  # 10% (+ Fentanyl)
    ],
    'HK': [  # Hong Kong follows China
        ('2025-02-04', 10.0, '64235342', '99030101'),
        ('2025-03-04', 20.0, '64299816', '99030124'),   # IEEPA Fentanyl 20% (specific code 9903.01.24)
        ('2025-04-09', 84.0, '64687696', '99030101'),
        ('2025-04-10', 125.0, '64701128', '99030100025'),
        ('2025-05-14', 10.0, '65029337', '99030100025'),
        ('2025-11-10', 10.0, '66749380', '99030100025'),
    ],
    'MO': [  # Macau follows China
        ('2025-02-04', 10.0, '64235342', '99030101'),
        ('2025-03-04', 20.0, '64299816', '99030124'),   # IEEPA Fentanyl 20% (specific code 9903.01.24)
        ('2025-04-09', 84.0, '64687696', '99030101'),
        ('2025-04-10', 125.0, '64701128', '99030100025'),
        ('2025-05-14', 10.0, '65029337', '99030100025'),
        ('2025-11-10', 10.0, '66749380', '99030100025'),
    ],

    # Country-specific rates
    'IN': [  # India
        ('2025-08-27', 25.0, '66027027', '99030101'),  # 25%
    ],
    'BR': [  # Brazil
        ('2025-08-06', 40.0, '65807735', '99030101'),  # 40%
        ('2025-11-13', 0.0, '66871909', None),  # Suspended
    ],
    'KR': [  # South Korea
        ('2025-11-14', 15.0, '66987366', '99030101'),  # 15%
    ],
    'CH': [  # Switzerland
        ('2025-11-14', 15.0, '67133044', '99030101'),  # 15%
    ],
    'LI': [  # Liechtenstein
        ('2025-11-14', 15.0, '67133044', '99030101'),  # 15%
    ],
}

# HTS codes in Annex II (EXEMPT from reciprocal tariff)
# These will be loaded from 'Recip Except (Annex II-HTS)' sheet
ANNEX_II_EXEMPT = set()

# Countries in Annex II COO exceptions
# These will be loaded from 'Recip Except (Annex II-COO)' sheet
ANNEX_II_COO_EXEMPT = set()


def get_ieepa_rate(country: str, entry_date: str, hts_code: str) -> Optional[Dict]:
    """
    Get IEEPA Reciprocal tariff rate for given country and date

    Args:
        country: 2-letter country code (e.g., 'MX', 'CN', 'IN')
        entry_date: Entry date in YYYY-MM-DD format
        hts_code: Normalized 10-digit HTS code

    Returns:
        Dict with rate, chapter99_code, csms, and notes, or None if not applicable
    """

    # Check if HTS is in Annex II (exempt)
    if hts_code in ANNEX_II_EXEMPT:
        return None

    # Check if country has COO exception
    if country in ANNEX_II_COO_EXEMPT:
        return None

    # Parse entry date
    try:
        # Remove timestamp if present (e.g., '2025-03-27 00:00:00' -> '2025-03-27')
        entry_date_clean = str(entry_date).split(' ')[0]
        entry_dt = datetime.strptime(entry_date_clean, '%Y-%m-%d')
    except Exception as e:
        # If parsing fails, log error and return None (don't apply tariff)
        print(f"Warning: Could not parse entry date '{entry_date}': {e}")
        return None

    # Check for country-specific rate first
    if country in IEEPA_RATES:
        rates = IEEPA_RATES[country]
    else:
        # Use global rate
        rates = IEEPA_RATES.get('GLOBAL', [])

    # Find the applicable rate (most recent before entry date)
    applicable_rate = None
    for impl_date_str, rate, csms, ch99 in rates:
        impl_dt = datetime.strptime(impl_date_str, '%Y-%m-%d')
        if entry_dt >= impl_dt:
            applicable_rate = {
                'rate': rate,
                'chapter99_code': ch99,
                'csms': csms,
                'implementation_date': impl_date_str,
                'notes': f'IEEPA Reciprocal - CSMS {csms}'
            }

    # Return None if rate is 0 (exempt)
    if applicable_rate and applicable_rate['rate'] == 0:
        return None

    return applicable_rate


def load_annex_ii_exceptions(excel_path: str):
    """
    Load Annex II exceptions from Excel file
    These HTS codes are EXEMPT from reciprocal tariff
    """
    import pandas as pd

    # Load HTS exceptions
    df_hts = pd.read_excel(excel_path, sheet_name='Recip Except (Annex II-HTS)')
    for hts in df_hts['Primary HTS']:
        if pd.notna(hts):
            normalized = str(hts).replace('.', '').replace('-', '').replace(' ', '').strip()
            ANNEX_II_EXEMPT.add(normalized)

    # Load COO exceptions
    df_coo = pd.read_excel(excel_path, sheet_name='Recip Except (Annex II-COO)')
    for coo in df_coo['Merch Country of Origin']:
        if pd.notna(coo):
            # Parse country codes (may be comma-separated)
            countries = str(coo).split(',')
            for c in countries:
                c = c.strip().upper()
                if len(c) == 2:
                    ANNEX_II_COO_EXEMPT.add(c)

    print(f"Loaded {len(ANNEX_II_EXEMPT)} HTS codes in Annex II (exempt)")
    print(f"Loaded {len(ANNEX_II_COO_EXEMPT)} COO exceptions")


if __name__ == "__main__":
    # Test
    from pathlib import Path

    excel_path = Path(__file__).parent.parent / "data" / "Trump_Tariffs_Summary_20260122.xlsx"
    load_annex_ii_exceptions(excel_path)

    print("\n=== TEST CASES ===\n")

    # Test 1: Mexico before April 5
    result = get_ieepa_rate('MX', '2025-03-27', '8543709860')
    print(f"Mexico, 2025-03-27: {result}")

    # Test 2: India after Aug 27
    result = get_ieepa_rate('IN', '2025-09-01', '8543709860')
    print(f"India, 2025-09-01: {result}")

    # Test 3: China after April 10
    result = get_ieepa_rate('CN', '2025-04-15', '8543709860')
    print(f"China, 2025-04-15: {result}")

    # Test 4: Germany (uses GLOBAL rate)
    result = get_ieepa_rate('DE', '2025-05-01', '8543709860')
    print(f"Germany, 2025-05-01: {result}")
