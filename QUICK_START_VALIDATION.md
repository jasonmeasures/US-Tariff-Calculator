# Quick Start - Mass Validation

## ✅ Ready to Validate All Entries at Once!

---

## Method 1: Simple Python Script (Recommended)

### Step 1: Prepare Your 7501 File

Your Excel file should have these columns:
- `29. CD HTS US Code` - The HTS code
- `27. CM Country Of Origin` - 2-letter country code
- `Entry Date` - Date of entry
- `Value (Line Item)` - Entered value
- `Duty Rate` - Declared rate (%)
- `Duty Amount` - Declared duty ($)

**Optional (for Section 232):**
- `Steel Content (%)` or `Steel %`
- `Aluminum Content (%)` or `Aluminum %`
- `Copper Content (%)` or `Copper %`

### Step 2: Run Validation

```bash
python validate_7501.py path/to/your/7501_file.xlsx
```

**Example:**
```bash
python validate_7501.py data/march_2025_entries.xlsx
```

### Step 3: Review Report

The script generates `validation_report.xlsx` with:
- **Summary** sheet - Overall statistics
- **All Entries** sheet - Complete results
- **Major Variances** sheet - Entries with ≥5% variance
- **Minor Variances** sheet - Entries with <5% variance

---

## Method 2: Direct API Call

### Using curl:

```bash
curl -X POST http://localhost:8000/api/validate-entry \
  -F "file=@your_7501_file.xlsx" \
  -o results.json
```

### Using Python:

```python
import requests

with open('7501_file.xlsx', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/validate-entry',
        files={'file': f}
    )

results = response.json()
print(f"Total variance: ${results['total_variance']:,.2f}")
```

---

## What to Expect

### Sample Console Output:

```
📤 Uploading: march_2025_entries.xlsx
   Size: 45,231 bytes

✅ Validation complete!

================================================================================
SUMMARY
================================================================================
Total Lines:     50
Processed:       48
Total Variance:  $12,500.00

✅ Matches:      35
⚠️  Minor (<5%):  8
❌ Major (≥5%):  5

================================================================================
MAJOR VARIANCES (≥5%)
================================================================================

Line 7: HTS 8543.70.98.60 - MX
  Declared:   $    260.00
  Calculated: $  2,760.00
  Variance:   $  2,500.00 (961.5%)

Line 12: HTS 7318.22.00.00 - JP
  Declared:   $      0.00
  Calculated: $  2,500.00 (inf%)

... and 3 more variances

================================================================================
GENERATING EXCEL REPORT
================================================================================
✅ Report saved: validation_report.xlsx
```

---

## Common Variance Patterns

### 1. IEEPA Mexico (25% Missing)
```
HTS: 8543.70.98.60
Country: MX
Date: March 7, 2025
Declared: $260 (MFN only)
Calculated: $2,760 (MFN + IEEPA 25%)
→ Add IEEPA reciprocal to entry
```

### 2. Section 232 Steel (Material Content)
```
HTS: 7318.22.00.00
Country: JP
Date: March 27, 2025
Declared: $2,500 (with steel %)
Calculated: $0 (no steel % in file)
→ Add steel percentage column to Excel
```

### 3. Section 232 Aluminum
```
HTS: 8708.80.65.90
Country: JP
Date: March 15, 2025
Declared: $2,500 (with aluminum %)
Calculated: $250 (no aluminum % in file)
→ Add aluminum percentage column to Excel
```

### 4. Date-Based Implementation
```
HTS: Various
Country: Various
Date: Before vs after implementation
Declared: Old rate
Calculated: New rate
→ Verify implementation dates
```

---

## Understanding the Report

### Status Indicators:

- **✅ MATCH** - Variance < $1 or < 1%
- **⚠️ MINOR** - Variance < 5% (likely rounding)
- **❌ MAJOR** - Variance ≥ 5% (needs investigation)

### Excel Report Sheets:

1. **Summary** - Quick statistics
   - Total lines processed
   - Match rate percentage
   - Total variance amount

2. **All Entries** - Every line item
   - Declared vs calculated
   - Variance amount and %
   - Confidence score

3. **Major Variances** - Focus here first
   - Entries with significant differences
   - Likely issues with tariff programs

4. **Minor Variances** - Review if needed
   - Small differences (rounding, fees)
   - Usually acceptable

---

## Troubleshooting

### Backend Not Running?
```bash
cd /Users/jasonmeasures/Development/us-tariff-calculator
source venv/bin/activate
python backend/api.py
```

### Wrong Column Names?
The script expects:
- `29. CD HTS US Code` (not "HTS Code")
- `27. CM Country Of Origin` (not "Country")
- `Entry Date` (not "Date")

Check your Excel headers match exactly.

### Header Row Issues?
7501 files typically have header at **row 6** (index 5).

If your file is different, modify the API call:
```python
df = pd.read_excel(BytesIO(contents), header=5)  # Change 5 to your row
```

---

## Example Workflow

### Day 1: Initial Validation
```bash
python validate_7501.py march_entries.xlsx
# Review validation_report.xlsx
# Identify 15 entries with variances
```

### Day 2: Add Material Content
```
1. Open march_entries.xlsx
2. Add column: "Steel Content (%)"
3. Fill in steel percentages for Section 232 items
4. Re-run validation
```

```bash
python validate_7501.py march_entries_updated.xlsx
# Variances reduced to 5 entries
```

### Day 3: Final Review
```
1. Review remaining 5 variances
2. Confirm IEEPA dates vs entry dates
3. Verify Chapter 99 codes
4. Sign off on validation
```

---

## Advanced: Custom Validation

For specific checks, create a custom script:

```python
import requests
import pandas as pd

# Load your 7501 data
df = pd.read_excel('7501_file.xlsx', header=5)

# Filter for specific date range
march_entries = df[df['Entry Date'].between('2025-03-01', '2025-03-31')]

# Validate only these entries
results = []
for idx, row in march_entries.iterrows():
    payload = {
        'hts_code': row['29. CD HTS US Code'],
        'country': row['27. CM Country Of Origin'],
        'entry_date': str(row['Entry Date']),
        'value': float(row['Value (Line Item)']),
        'steel_percent': float(row.get('Steel Content (%)', 0)),
        'mode': 'ocean'
    }

    response = requests.post(
        'http://localhost:8000/api/calculate',
        json=payload
    )

    result = response.json()
    results.append({
        'line': idx + 1,
        'hts': payload['hts_code'],
        'declared': float(row['Duty Amount']),
        'calculated': result['total_duty'],
        'variance': result['total_duty'] - float(row['Duty Amount'])
    })

# Export results
pd.DataFrame(results).to_excel('custom_validation.xlsx')
```

---

## Ready?

**Upload your 7501 file and let's validate everything at once!**

```bash
python validate_7501.py your_7501_file.xlsx
```

**Questions about the results?** Share the validation report and I'll help interpret the variances.

