# 7501 Entry Summary Column Mapping Reference

**For: KlearNow Duty Audit Tool**  
**Last Updated:** January 14, 2026  
**Purpose:** Column alignment between CBP 7501 Excel extracts and audit application

---

## Quick Reference

### Primary Calculation Fields

```python
# Required for duty calculation
row.get('29. CD HTS US Code')           # HTS classification
row.get('27. CM Country Of Origin')     # Country for tariff rules
row.get('11. CS Import Date')           # Date for rule selection
row.get('32. CM Item Entered Value')    # Value for calculation

# What was actually paid (for comparison)
row.get('34. CD Ad Valorem Duty')       # Actual duty paid
row.get('34. CD MPF Fee')               # Actual MPF paid
row.get('34. CD HMF Fee')               # Actual HMF paid
row.get('33. CD HTS US Rate')           # Filed rate percentage
```

---

## Complete Column Mapping

### Entry-Level Identification

| Excel Column | Field Type | Application Use | Notes |
|-------------|------------|-----------------|-------|
| `CS Shipment ID` | Internal ID | Tracking | KlearNow internal reference |
| `1. CS Entry Number` | Entry Number | Primary Key | Format: 98Q-1024114-5 |
| `2. CS Entry Type` | Entry Type | Classification | e.g., 01ABI/A (formal entry) |
| `3. CS Summary Date` | Summary Date | Reference | Date entry was filed |
| `6. CS Port Of Entry` | Port Code | Reference | CBP port (e.g., 3001) |
| `7. CS Entry Date` | Entry Date | Reference | Date goods arrived |

### Dates (Critical for Tariff Rules)

| Excel Column | Field Type | Application Use | Notes |
|-------------|------------|-----------------|-------|
| `11. CS Import Date` | **Import Date** | **PRIMARY** | **Used for tariff rule selection** |
| `14. CS Export Country` | Export Country | Reference | Where goods shipped from |
| `15. CS Export Date` | Export Date | Reference | When goods left origin |
| `17. CS IT Date` | IT Date | Reference | In-transit date |

**IMPORTANT:** `11. CS Import Date` determines which tariff rules apply:
- FY2024 vs FY2025 vs FY2026 MPF rates
- Section 232 effective dates
- IEEPA reciprocal tariff dates
- Country-specific agreement dates

### Line Item Identification

| Excel Column | Field Type | Application Use | Notes |
|-------------|------------|-----------------|-------|
| `27. CM Item Number` | Line Number | Multi-line tracking | Sequential line within entry |
| `27. CM Country Of Origin` | **Country Code** | **PRIMARY** | **Used for tariff rules (2-letter ISO)** |
| `27. CM Export Country Code` | Export Code | Reference | Alternative country field |

### HTS Classification

| Excel Column | Field Type | Application Use | Notes |
|-------------|------------|-----------------|-------|
| `29. CD HTS US Code` | **HTS Code** | **PRIMARY** | **10-digit classification** |
| `29. CD HTS Description` | Description | Reference | Product description from HTS |

**HTS Code Usage:**
- Lookup base MFN rate from HTS database
- Determine if auto parts (8708.xx)
- Check Section 232 applicability
- Identify Chapter 99 suspensions

### Values & Quantities

| Excel Column | Field Type | Application Use | Notes |
|-------------|------------|-----------------|-------|
| `32. CM Item Entered Value` | **Entered Value** | **PRIMARY** | **USD value for duty calculation** |
| `28. CM Recon Value` | Recon Value | Reference | Reconciliation value |
| `28. CM Value Addition Amount` | Value Addition | Reference | Added value |
| `35. CS Total Entered Value` | Total Value | Reference | Sum of all line items |

### Rates (What Was Filed)

| Excel Column | Field Type | Application Use | Notes |
|-------------|------------|-----------------|-------|
| `33. CD HTS US Rate` | Filed Rate | Comparison | Rate % that was filed with CBP |
| `33. CD Specific Rate` | Specific Rate | Reference | Non-ad valorem rate |
| `33. CD MPF Rate` | MPF Rate | Reference | MPF percentage filed |
| `33. CD HMF Rate` | HMF Rate | Reference | HMF percentage filed |

### Actual Duties & Fees (What Was Paid)

| Excel Column | Field Type | Application Use | Notes |
|-------------|------------|-----------------|-------|
| `34. CD Ad Valorem Duty` | **Actual Duty** | **PRIMARY COMPARISON** | **Compare to expected duty** |
| `34. CD MPF Fee` | **Actual MPF** | **PRIMARY COMPARISON** | **Compare to expected MPF** |
| `34. CD HMF Fee` | **Actual HMF** | **PRIMARY COMPARISON** | **Compare to expected HMF** |
| `34. CD Duty And Taxes` | Total Paid | Comparison | Sum of all duties/fees paid |
| `34. CD Specific Duty` | Specific Duty | Reference | Non-ad valorem duty paid |
| `34. CD Cotton Fee Amount` | Cotton Fee | Reference | Cotton fee if applicable |

### Entry Totals

| Excel Column | Field Type | Application Use | Notes |
|-------------|------------|-----------------|-------|
| `37. CS Totals Duty` | Entry Duty Total | Reference | Sum of duties for entry |
| `38. CS Totals Tax` | Entry Tax Total | Reference | Sum of taxes |
| `39. CS MPF Amount` | Entry MPF Total | Reference | Total MPF for entry |
| `39. CS Total Other Fees` | Other Fees | Reference | Other fees total |
| `40. CS Duty Grand Total` | **Grand Total** | **Comparison** | **Total amount paid** |

---

## Column Naming Convention

### Prefix Meanings

| Prefix | Meaning | Scope | Examples |
|--------|---------|-------|----------|
| **CS** | Customs Summary | Entry-level | CS Entry Number, CS Import Date |
| **CM** | Customs Merchandise | Line item-level | CM Item Number, CM Country Of Origin |
| **CD** | Customs Duty | Duty calculation | CD HTS US Code, CD Ad Valorem Duty |

### Number Prefixes

Numbers like `1.`, `27.`, `29.`, `34.` correspond to **CBP Form 7501 box numbers**.

Example:
- `29. CD HTS US Code` = Box 29 on CBP 7501 form
- `34. CD Ad Valorem Duty` = Box 34 on CBP 7501 form

---

## Usage in Backend Code

### Reading a Line Item

```python
# Extract primary fields
hts_code = str(row.get('29. CD HTS US Code', '')).strip()
country = str(row.get('27. CM Country Of Origin', '')).strip()
import_date = row.get('11. CS Import Date')
entered_value = float(row.get('32. CM Item Entered Value', 0))

# Extract actual values (what was paid)
actual_duty = float(row.get('34. CD Ad Valorem Duty', 0) or 0)
actual_mpf = float(row.get('34. CD MPF Fee', 0) or 0)
actual_hmf = float(row.get('34. CD HMF Fee', 0) or 0)
actual_rate = float(row.get('33. CD HTS US Rate', 0) or 0)
```

### Calculation Logic Flow

```python
# 1. Get HTS info
hts_info = get_hts_info(hts_code)
base_rate = hts_info['base_rate']

# 2. Get applicable tariffs based on date + country
tariffs = get_applicable_tariffs(import_date, country, hts_code)

# 3. Calculate expected duty
total_duty_rate = base_rate
for tariff in tariffs:
    total_duty_rate += tariff['additional_rate']

expected_duty = entered_value * (total_duty_rate / 100)

# 4. Calculate fees
expected_mpf = calculate_mpf(entered_value, import_date)
expected_hmf = entered_value * 0.00125

# 5. Compare to actual
duty_diff = abs(actual_duty - expected_duty)
status = 'MATCH' if duty_diff <= 1.0 else 'MISMATCH'
```

---

## File Format Requirements

### Standard 7501 Export Format

**Expected Structure:**
- File format: Excel (.xlsx)
- Header row: Row 5 (index 4)
- Data starts: Row 6
- Column names: Exactly as shown above (e.g., `29. CD HTS US Code`)

### Reading the File

```python
# Standard format
df = pd.read_excel(file, header=4)

# Verify required columns exist
required_cols = [
    '29. CD HTS US Code',
    '27. CM Country Of Origin', 
    '11. CS Import Date',
    '32. CM Item Entered Value'
]

missing = [col for col in required_cols if col not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")
```

### Alternative Format (Positional)

If file has NO named columns (only positions 0, 1, 2...):

```python
# Map by position
column_mapping = {
    0: '1. CS Entry Number',
    6: '29. CD HTS US Code',
    5: '32. CM Item Entered Value',
    3: '11. CS Import Date',
    4: '27. CM Country Of Origin'
}

df = pd.read_excel(file, header=0)
df = df.rename(columns=column_mapping)
```

---

## Tariff Calculation Matrix

### What Gets Applied When

| Tariff Type | Determined By | Date Field | Country Field | HTS Field |
|------------|---------------|------------|---------------|-----------|
| Base MFN Rate | HTS code | N/A | N/A | `29. CD HTS US Code` |
| Section 301 China | Country + HTS | `11. CS Import Date` | `27. CM Country Of Origin` | `29. CD HTS US Code` |
| Section 232 | Country + HTS | `11. CS Import Date` | `27. CM Country Of Origin` | `29. CD HTS US Code` |
| IEEPA Reciprocal | Country | `11. CS Import Date` | `27. CM Country Of Origin` | N/A |
| Country-Specific | Country | `11. CS Import Date` | `27. CM Country Of Origin` | N/A |
| MPF | Entry value + date | `11. CS Import Date` | N/A | N/A |
| HMF | Entry value | N/A | N/A | N/A |

### Expected vs Actual Comparison

```
┌─────────────────────────────────────────────┐
│ Expected Calculation                        │
├─────────────────────────────────────────────┤
│ 1. Base Rate (from HTS)                     │
│ 2. + Section 301 (if CN/HK/MO)             │
│ 3. + Section 232 (if applicable)           │
│ 4. + IEEPA Reciprocal (by country)         │
│ 5. = Total Duty Rate                       │
│ 6. × Entered Value = Expected Duty         │
│ 7. + MPF (date-based formula)              │
│ 8. + HMF (0.125% of value)                 │
│ 9. = Expected Total                        │
└─────────────────────────────────────────────┘
                  ↓ COMPARE ↓
┌─────────────────────────────────────────────┐
│ Actual (from 7501)                          │
├─────────────────────────────────────────────┤
│ • 34. CD Ad Valorem Duty                    │
│ • 34. CD MPF Fee                            │
│ • 34. CD HMF Fee                            │
│ • 34. CD Duty And Taxes                     │
└─────────────────────────────────────────────┘
```

---

## Common Issues & Solutions

### Issue 1: Column Not Found

**Error:** `KeyError: '29. CD HTS US Code'`

**Cause:** Column name mismatch between file and code

**Solution:**
```python
# Check actual column names
print(df.columns.tolist())

# Verify format
assert '29. CD HTS US Code' in df.columns
```

### Issue 2: Empty/NaN Values

**Error:** `ValueError: could not convert string to float: ''`

**Solution:**
```python
# Always provide defaults and handle None
entered_value = float(row.get('32. CM Item Entered Value', 0) or 0)
actual_duty = float(row.get('34. CD Ad Valorem Duty', 0) or 0)
```

### Issue 3: Date Format Issues

**Error:** Dates not parsing correctly

**Solution:**
```python
def parse_date(date_str):
    if isinstance(date_str, datetime):
        return date_str.date()
    if pd.isna(date_str) or date_str is None:
        return None
    try:
        return pd.to_datetime(date_str).date()
    except:
        return None
```

### Issue 4: Country Code Variations

**Problem:** Country codes may be 2-letter or 3-digit

**Solution:**
```python
# Normalize to 2-letter ISO
country_map = {
    '036': 'AU',  # Australia
    '392': 'JP',  # Japan
    '156': 'CN',  # China
    # ... etc
}

country = str(row.get('27. CM Country Of Origin', '')).strip()
if country.isdigit():
    country = country_map.get(country, country)
```

---

## Testing

### Verify Column Mapping

```python
import pandas as pd

# Load test file
df = pd.read_excel('test_7501.xlsx', header=4)

# Check all required columns exist
required = [
    '1. CS Entry Number',
    '11. CS Import Date',
    '27. CM Country Of Origin',
    '29. CD HTS US Code',
    '32. CM Item Entered Value',
    '34. CD Ad Valorem Duty',
    '34. CD MPF Fee',
    '34. CD HMF Fee'
]

for col in required:
    assert col in df.columns, f"Missing: {col}"
    
print("✓ All required columns present")

# Verify data types
assert df['11. CS Import Date'].dtype == 'datetime64[ns]'
assert df['32. CM Item Entered Value'].dtype in ['float64', 'int64']

print("✓ Data types correct")
```

---

## Quick Checklist

**Before Running Audit:**
- [ ] File is Excel (.xlsx) format
- [ ] Header is on row 5 (Python index 4)
- [ ] All required columns present (see Required Columns below)
- [ ] `11. CS Import Date` is date format
- [ ] `32. CM Item Entered Value` is numeric
- [ ] `27. CM Country Of Origin` is 2-letter ISO code
- [ ] `29. CD HTS US Code` is 10-digit numeric

**Required Columns:**
```
✓ 1. CS Entry Number
✓ 11. CS Import Date
✓ 27. CM Country Of Origin
✓ 29. CD HTS US Code
✓ 32. CM Item Entered Value
✓ 34. CD Ad Valorem Duty
✓ 34. CD MPF Fee
✓ 34. CD HMF Fee
```

---

## Backend File Locations

**Column mapping is hardcoded in:**
- `/backend/app.py` (lines 130-260)
- Function: `calculate_expected_duty(row)`

**To update column mapping:**
1. Edit `app.py` line 130+
2. Update all `row.get('COLUMN_NAME')` references
3. Update `required_cols` list in validation
4. Test with sample file
5. Update this documentation

---

## Support

**Questions?**  
Contact: Jason Measures (jason@klearnow.com)

**Last Verified:**  
January 14, 2026 with KlearNow 7501 export format v2.1
