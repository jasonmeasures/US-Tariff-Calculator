# Chapter 99 Derivative HTS Codes

## Overview

The tariff calculator now displays **Chapter 99 derivative HTS codes** for Section 232 and other overlay tariffs, matching the functionality shown in Flexport's tariff simulator.

## What are Chapter 99 Codes?

Chapter 99 of the Harmonized Tariff Schedule contains special classification provisions for temporary modifications, including:

- **Section 232 tariffs** (national security)
- **Section 301 tariffs** (China trade actions)
- **Other temporary duty modifications**

When an overlay tariff applies to a product, CBP requires the importer to report **both**:
1. **Primary HTS code** (e.g., 8708.80.65.90) - The normal classification
2. **Chapter 99 derivative code** (e.g., 9903.85.08) - The overlay tariff provision

## Example: HTS 8708.80.65.90

### Primary Classification
- **HTS:** 8708.80.65.90
- **Description:** Suspension shock absorbers (auto parts)
- **Base Duty:** 2.5%

### Section 232 Aluminum Overlay
- **Chapter 99 Code:** 9903.85.08
- **Description:** Section 232 Aluminum New Derivative Products
- **Additional Duty:** 25% (material-based)
- **Tariff Basis:** 50% of Aluminum Value (non-UK) / 25% of Aluminum Value (UK)

### Total Duty (100% aluminum content)
```
Primary:  8708.80.65.90 @ 2.5%  = $250
Overlay:  9903.85.08    @ 25%   = $2,500
                        ─────────────
Total:                   27.5%  = $2,750
```

## Display in Calculator

The calculator now shows Chapter 99 codes in the breakdown, formatted like Flexport:

```
Line 1
Value: $10,000

8708.80.65.90                          2.5%      $250
9903.85.08                             25%       $2,500
Section 232 Aluminum New Derivative Products
```

## Database Schema

### hts_overlay_mappings table

| Column | Type | Description |
|--------|------|-------------|
| hts_code | TEXT | Primary HTS code (normalized) |
| program_name | TEXT | Tariff program name |
| duty_rate | REAL | Additional duty rate (%) |
| jurisdiction | TEXT | Country or "GLOBAL" |
| **chapter99_code** | TEXT | Derivative Chapter 99 code |
| **tariff_basis** | TEXT | Material basis description |

### Sample Query

```sql
SELECT
    hts_code,
    program_name,
    duty_rate,
    chapter99_code,
    tariff_basis
FROM hts_overlay_mappings
WHERE hts_code = '8708806590';
```

**Result:**
```
HTS Code:      8708806590
Program:       Sec 232 Aluminum (FRNs)
Duty Rate:     25.0%
Chapter 99:    99038508
Tariff Basis:  50% of Aluminum Value (non-UK) / 25% of Aluminum Value (UK)
```

## API Response

### POST /api/calculate

```json
{
  "breakdown": [
    {
      "name": "Base MFN Rate",
      "rate": 2.5,
      "amount": 250.0,
      "description": "Column 1 duty: 2.5%"
    },
    {
      "name": "Sec 232 Aluminum (FRNs)",
      "rate": 25.0,
      "effective_rate": 25.0,
      "amount": 2500.0,
      "description": "25.0% × 100.0% aluminum",
      "material_basis": "aluminum",
      "material_percent": 100.0,
      "chapter99_code": "99038508",
      "tariff_basis": "50% of Aluminum Value (non-UK) / 25% of Aluminum Value (UK)"
    }
  ]
}
```

## Common Chapter 99 Codes

### Section 232 (National Security)

| Chapter 99 Code | Description | Material |
|-----------------|-------------|----------|
| 9903.85.08 | Sec 232 Aluminum (non-UK) | Aluminum |
| 9903.85.15 | Sec 232 Aluminum (UK) | Aluminum |
| 9903.80.01 | Sec 232 Steel (general) | Steel |
| 9903.88.01 | Sec 232 Auto Parts | Various |

### Section 301 (China)

| Chapter 99 Code | Description | List |
|-----------------|-------------|------|
| 9903.88.01 | China List 1 | 25% |
| 9903.88.02 | China List 2 | 25% |
| 9903.88.03 | China List 3 | 25% |
| 9903.88.04 | China List 4A | Various |

## Frontend Display

The web interface now displays Chapter 99 codes below the overlay name:

```
Breakdown:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Base MFN Rate                    $250.00

Sec 232 Aluminum (FRNs)          $2,500.00
  25% × 100% aluminum = 25%
  9903.85.08                     ← Chapter 99 code

MPF                              $34.64
HMF                              $12.50
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Duty                       $2,750.00
Landed Cost                      $12,797.14
```

## How It Works

### 1. Data Loading

The database loader extracts Chapter 99 codes from the Excel sheets:

```python
# From Trump_Tariffs_Summary_20260122.xlsx
# Column: "Sec 232 (Aluminum)"
# Value: "99038508 (non-UK) / 99038515 (UK)"

ch99_str = row['Sec 232 (Aluminum)']
# Parse: "99038508" (first code before slash)
chapter99_code = ch99_str.split('/')[0].strip().split()[0]
```

### 2. Calculation Engine

The tariff engine retrieves Chapter 99 codes when querying overlays:

```python
overlays = get_applicable_overlays(hts_code, country, entry_date)

for overlay in overlays:
    chapter99_code = overlay.get('chapter99_code', '')
    tariff_basis = overlay.get('tariff_basis', '')

    breakdown.append({
        'name': program,
        'rate': rate,
        'amount': amount,
        'chapter99_code': chapter99_code,  # Include in breakdown
        'tariff_basis': tariff_basis
    })
```

### 3. Frontend Formatting

JavaScript formats the 8-digit code with dots:

```javascript
function formatChapter99(code) {
    // 99038508 → 9903.85.08
    if (code.length === 8) {
        return `${code.substring(0, 4)}.${code.substring(4, 6)}.${code.substring(6, 8)}`;
    }
    return code;
}
```

## Benefits

✅ **CBP Compliance** - Shows both primary and derivative codes as required
✅ **Customs Entry Preparation** - Users know which codes to report
✅ **Transparency** - Clear indication of which tariff programs apply
✅ **Flexport Parity** - Matches industry-standard display format
✅ **Reference Lookup** - Users can research specific Chapter 99 provisions

## Usage Example

```python
from tariff_engine import calculate_duty

result = calculate_duty(
    hts_code="8708.80.65.90",
    country="JP",
    entry_date="2025-03-15",
    value=10000.0,
    aluminum_percent=100.0
)

for item in result.breakdown:
    if 'chapter99_code' in item and item['chapter99_code']:
        print(f"Primary: {result.hts_code}")
        print(f"Chapter 99: {item['chapter99_code']}")
        print(f"Program: {item['name']}")
        print(f"Rate: {item['rate']}%")
        print(f"Basis: {item['tariff_basis']}")
```

**Output:**
```
Primary: 8708806590
Chapter 99: 99038508
Program: Sec 232 Aluminum (FRNs)
Rate: 25.0%
Basis: 50% of Aluminum Value (non-UK) / 25% of Aluminum Value (UK)
```

## References

- **USITC Tariff Database:** https://hts.usitc.gov
- **Chapter 99 Provisions:** https://hts.usitc.gov/view/chapter?release=2025HTSARev1&chapter=99
- **Section 232 Information:** Federal Register Notices (FRNs)
- **Flexport Tariff Simulator:** https://www.flexport.com/tariff-simulator/

---

**Updated:** January 2025
**Feature:** Chapter 99 derivative HTS codes now displayed in all calculations
