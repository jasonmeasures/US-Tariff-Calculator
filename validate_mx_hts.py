#!/usr/bin/env python3
"""
Validation Test for HTS 8543.70.98.60 from Mexico
Entry Date: March 27, 2025
"""

import sys
sys.path.append('backend')
from tariff_engine import calculate_duty

# Your specific validation request
HTS_CODE = '8543.70.98.60'
COUNTRY = 'MX'
ENTRY_DATE = '2025-03-27'
VALUE = 10000.00

print('=' * 80)
print('TARIFF VALIDATION - HTS 8543.70.98.60')
print('=' * 80)
print()
print(f'Input Parameters:')
print(f'  HTS Code:           {HTS_CODE}')
print(f'  Country of Origin:  Mexico ({COUNTRY})')
print(f'  Entry Date:         {ENTRY_DATE}')
print(f'  Entered Value:      ${VALUE:,.2f}')
print(f'  Transportation:     Ocean')
print()

# Calculate duty
result = calculate_duty(
    hts_code=HTS_CODE,
    country=COUNTRY,
    entry_date=ENTRY_DATE,
    value=VALUE,
    aluminum_percent=0.0,
    steel_percent=0.0,
    copper_percent=0.0,
    mode='ocean'
)

print('=' * 80)
print('CALCULATION RESULTS')
print('=' * 80)
print()
print(f'HTS Classification:')
print(f'  Normalized HTS:     {result.hts_code}')
print(f'  Chapter:            85 - Electrical machinery and equipment')
print(f'  Description:        Electric machines/apparatus NSPF')
print()
print(f'Duty Calculation:')
print(f'  Base MFN Rate:      {result.base_rate}%')
print(f'  Base Duty:          ${result.base_duty:,.2f}')
print()
print(f'Additional Tariffs:')
print(f'  Section 232:        None')
print(f'  Section 301:        Not applicable (COO: Mexico)')
print(f'  Overlay Duty:       ${result.overlay_duty:,.2f}')
print()
print(f'Fees & Charges:')
print(f'  MPF (0.3464%):      ${result.mpf:,.2f}')
print(f'  HMF (0.125%):       ${result.hmf:,.2f}')
print()
print(f'=' * 80)
print(f'TOTAL DUTY:          ${result.total_duty:,.2f} ({result.total_duty_rate}%)')
print(f'LANDED COST:         ${result.landed_cost:,.2f}')
print(f'=' * 80)
print()
print(f'Confidence Score:    {result.confidence}% ✅')
print()

if result.notes:
    print('Notes:')
    for note in result.notes:
        print(f'  • {note}')
    print()

print('=' * 80)
print('BREAKDOWN')
print('=' * 80)
print()
for item in result.breakdown:
    name = item['name'].ljust(30)
    amount = f"${item['amount']:>10,.2f}"

    if 'chapter99_code' in item and item['chapter99_code']:
        # Format Chapter 99 code
        ch99 = item['chapter99_code']
        ch99_formatted = f"{ch99[:4]}.{ch99[4:6]}.{ch99[6:8]}"
        print(f'{name} {amount}')
        print(f'  Chapter 99: {ch99_formatted}')
    else:
        print(f'{name} {amount}')

print()
print('=' * 80)
print('IMPORTANT NOTES')
print('=' * 80)
print()
print('⚠️  USMCA Preferential Treatment:')
print('    Mexico may qualify for DUTY-FREE entry under USMCA if:')
print('    • Product meets USMCA rules of origin requirements')
print('    • Valid USMCA certification is provided on entry')
print('    • Importer claims preferential treatment (Special Program "MX")')
print()
print('    If USMCA applies:')
print('    • Duty Rate: 0.0% (FREE)')
print('    • Total Duty: $0.00')
print('    • Landed Cost: $10,047.14 (value + fees only)')
print()
print('    Current calculation assumes MFN rate (no USMCA claim).')
print()
print('=' * 80)
