"""
IEEPA Reciprocal Tariff Rates - CORRECTED
Based on actual implementation (Flexport validation shows March 7, 2025)
"""

from datetime import datetime
from typing import Optional, Dict

# CORRECTED: IEEPA Reciprocal started EARLIER than CSMS 64649265 indicates
# Flexport shows 9903.01.01 applying on March 7, 2025
# This suggests Presidential Proclamation predates CSMS implementation notice

IEEPA_RATES = {
    # Global baseline - CORRECTED START DATE based on Flexport validation
    'GLOBAL': [
        ('2025-03-07', 10.0, 'Presidential', '99030101'),  # 10% reciprocal (actual start)
        ('2025-04-05', 10.0, '64649265', '99030101'),  # CSMS confirmation
        ('2025-08-07', 10.0, '65829726', '99030101'),  # Updated
    ],

    # Exempt countries - BUT check if exemption started March 7 or April 5
    'CA': [
        ('2025-03-07', 10.0, 'Presidential', '99030101'),  # May apply initially
        ('2025-04-05', 0.0, '64649265', None),  # Canada EXEMPT per CSMS
    ],
    'MX': [
        ('2025-03-07', 10.0, 'Presidential', '99030101'),  # May apply initially  
        ('2025-04-05', 0.0, '64649265', None),  # Mexico EXEMPT per CSMS
    ],

    # China/Hong Kong/Macau
    'CN': [
        ('2025-04-09', 84.0, '64687696', '99030101'),
        ('2025-04-10', 125.0, '64701128', '99030100025'),
        ('2025-05-14', 10.0, '65029337', '99030100025'),
        ('2025-11-10', 10.0, '66749380', '99030100025'),
    ],
    'HK': [
        ('2025-04-09', 84.0, '64687696', '99030101'),
        ('2025-04-10', 125.0, '64701128', '99030100025'),
        ('2025-05-14', 10.0, '65029337', '99030100025'),
        ('2025-11-10', 10.0, '66749380', '99030100025'),
    ],
    'MO': [
        ('2025-04-09', 84.0, '64687696', '99030101'),
        ('2025-04-10', 125.0, '64701128', '99030100025'),
        ('2025-05-14', 10.0, '65029337', '99030100025'),
        ('2025-11-10', 10.0, '66749380', '99030100025'),
    ],

    # Country-specific rates
    'IN': [
        ('2025-08-27', 25.0, '66027027', '99030101'),
    ],
    'BR': [
        ('2025-08-06', 40.0, '65807735', '99030101'),
        ('2025-11-13', 0.0, '66871909', None),
    ],
    'KR': [
        ('2025-11-14', 15.0, '66987366', '99030101'),
    ],
    'CH': [
        ('2025-11-14', 15.0, '67133044', '99030101'),
    ],
    'LI': [
        ('2025-11-14', 15.0, '67133044', '99030101'),
    ],
}

ANNEX_II_EXEMPT = set()
ANNEX_II_COO_EXEMPT = set()

def get_ieepa_rate(country: str, entry_date: str, hts_code: str) -> Optional[Dict]:
    """Get IEEPA Reciprocal tariff rate for given country and date"""
    
    if hts_code in ANNEX_II_EXEMPT:
        return None
    
    if country in ANNEX_II_COO_EXEMPT:
        return None
    
    try:
        entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
    except:
        entry_dt = datetime.now()
    
    if country in IEEPA_RATES:
        rates = IEEPA_RATES[country]
    else:
        rates = IEEPA_RATES.get('GLOBAL', [])
    
    applicable_rate = None
    for impl_date_str, rate, csms, ch99 in rates:
        impl_dt = datetime.strptime(impl_date_str, '%Y-%m-%d')
        if entry_dt >= impl_dt:
            applicable_rate = {
                'rate': rate,
                'chapter99_code': ch99,
                'csms': csms,
                'implementation_date': impl_date_str,
                'notes': f'IEEPA Reciprocal - {csms}'
            }
    
    if applicable_rate and applicable_rate['rate'] == 0:
        return None
    
    return applicable_rate

def load_annex_ii_exceptions(excel_path: str):
    """Load Annex II exceptions from Excel file"""
    import pandas as pd
    
    df_hts = pd.read_excel(excel_path, sheet_name='Recip Except (Annex II-HTS)')
    for hts in df_hts['Primary HTS']:
        if pd.notna(hts):
            normalized = str(hts).replace('.', '').replace('-', '').replace(' ', '').strip()
            ANNEX_II_EXEMPT.add(normalized)
    
    df_coo = pd.read_excel(excel_path, sheet_name='Recip Except (Annex II-COO)')
    for coo in df_coo['Merch Country of Origin']:
        if pd.notna(coo):
            countries = str(coo).split(',')
            for c in countries:
                c = c.strip().upper()
                if len(c) == 2:
                    ANNEX_II_COO_EXEMPT.add(c)
    
    print(f"Loaded {len(ANNEX_II_EXEMPT)} HTS codes in Annex II (exempt)")
    print(f"Loaded {len(ANNEX_II_COO_EXEMPT)} COO exceptions")
