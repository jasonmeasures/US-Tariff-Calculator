# Mass Validation Guide - 7501 Entry Summary

## Quick Start

Upload your 7501 Entry Summary Excel file to validate all entries at once and compare against calculated duties.

---

## Using the API Endpoint

### Endpoint: `POST /api/validate-entry`

**Upload your 7501 Excel file:**

```bash
curl -X POST http://localhost:8000/api/validate-entry \
  -F "file=@path/to/your/7501_entry_summary.xlsx" \
  -o validation_results.json
```

---

## 7501 File Format

### Required Columns (Header at Row 6):

| Column Name | Description | Example |
|-------------|-------------|---------|
| 29. CD HTS US Code | 10-digit HTS code | 7318.22.00.00 |
| 27. CM Country Of Origin | 2-letter country code | JP, MX, CN |
| Entry Date | Date of entry | 2025-03-27 |
| Value (Line Item) | Entered value (USD) | 10000.00 |
| Duty Rate | Declared duty rate (%) | 25.00 |
| Duty Amount | Declared duty ($) | 2500.00 |

**Optional Columns (for Section 232 validation):**
- Aluminum Content (%)
- Steel Content (%)
- Copper Content (%)

---

## Response Format

```json
{
  "total_lines": 50,
  "processed_lines": 48,
  "total_variance": 1250.50,
  "results": [
    {
      "line": 1,
      "hts_code": "7318.22.00.00",
      "country": "JP",
      "entry_date": "2025-03-27",
      "declared_duty": 2500.00,
      "calculated_duty": 2500.00,
      "variance": 0.00,
      "variance_percent": 0.0,
      "confidence": 100,
      "status": "✅ MATCH"
    },
    {
      "line": 2,
      "hts_code": "8543.70.98.60",
      "country": "MX",
      "entry_date": "2025-03-07",
      "declared_duty": 260.00,
      "calculated_duty": 2760.00,
      "variance": 2500.00,
      "variance_percent": 961.5,
      "confidence": 100,
      "status": "❌ VARIANCE - IEEPA Mexico 25% missing?"
    }
  ]
}
```

---

## Using Python Script

Create `validate_entries.py`:

```python
#!/usr/bin/env python3
import requests
import json
import pandas as pd
from pathlib import Path

# Upload 7501 file
file_path = "path/to/7501_entry_summary.xlsx"

with open(file_path, 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/validate-entry',
        files={'file': f}
    )

results = response.json()

# Summary
print(f"Total Lines: {results['total_lines']}")
print(f"Processed: {results['processed_lines']}")
print(f"Total Variance: ${results['total_variance']:,.2f}")
print()

# Detailed results
variances = []
for item in results['results']:
    if 'error' in item:
        print(f"Line {item['line']}: ERROR - {item['error']}")
    else:
        variance_pct = abs(item['variance_percent'])
        if variance_pct > 1:  # More than 1% variance
            variances.append(item)
            print(f"Line {item['line']}: HTS {item['hts_code']} - Variance: ${item['variance']:,.2f} ({variance_pct:.1f}%)")

# Export to Excel
if variances:
    df = pd.DataFrame(variances)
    df.to_excel('validation_variances.xlsx', index=False)
    print(f"\nExported {len(variances)} variances to validation_variances.xlsx")
```

---

## Understanding Variances

### Common Variance Causes:

1. **IEEPA Reciprocal Missing:**
   ```
   Declared: $260 (MFN only)
   Calculated: $2,760 (MFN + IEEPA 25%)
   Variance: $2,500
   → Entry missing IEEPA Mexico tariff
   ```

2. **Section 232 Material Content:**
   ```
   Declared: $2,500 (25% steel tariff)
   Calculated: $0 (no steel percentage provided)
   Variance: -$2,500
   → Need to provide steel_percent in validation
   ```

3. **Date-Based Rate Changes:**
   ```
   Declared: $1,250 (old rate)
   Calculated: $2,500 (new rate after implementation date)
   Variance: $1,250
   → Rate changed between dates
   ```

4. **Chapter 99 Code Differences:**
   ```
   Declared: Used wrong derivative code
   Calculated: Correct Chapter 99 code
   → Different Chapter 99 provisions applied
   ```

---

## Enhanced Validation (with Material Content)

For Section 232 validation, prepare your Excel with additional columns:

### Enhanced 7501 Format:

| HTS Code | Country | Entry Date | Value | Aluminum % | Steel % | Copper % | Declared Duty |
|----------|---------|------------|-------|------------|---------|----------|---------------|
| 7318.22.00.00 | JP | 2025-03-27 | 10000 | 0 | 100 | 0 | 2500 |
| 8708.80.65.90 | JP | 2025-03-15 | 10000 | 100 | 0 | 0 | 2500 |
| 8543.70.98.60 | MX | 2025-03-07 | 10000 | 0 | 0 | 0 | 2760 |

**Modified column names to check:**
- `Aluminum Content (%)` or `Aluminum %`
- `Steel Content (%)` or `Steel %`
- `Copper Content (%)` or `Copper %`

---

## Validation Workflow

### Step 1: Prepare Your Data
```
1. Export 7501 Entry Summary from your system
2. Ensure header row is at row 6 (data starts row 7)
3. Verify column names match expected format
4. Add material content columns if validating Section 232
```

### Step 2: Upload for Validation
```bash
curl -X POST http://localhost:8000/api/validate-entry \
  -F "file=@7501_entries.xlsx" \
  > validation_results.json
```

### Step 3: Review Results
```python
import json
import pandas as pd

with open('validation_results.json') as f:
    data = json.load(f)

# Filter for significant variances (>$10 or >1%)
significant = [
    r for r in data['results']
    if 'variance' in r and (abs(r['variance']) > 10 or abs(r['variance_percent']) > 1)
]

# Create summary report
df = pd.DataFrame(significant)
print(f"\nFound {len(significant)} entries with significant variances")
print(df[['line', 'hts_code', 'country', 'variance', 'variance_percent']])
```

### Step 4: Investigate Variances
For each variance:
1. Check if HTS code is subject to new tariffs (Section 232, IEEPA)
2. Verify entry date vs implementation dates
3. Confirm material content percentages
4. Review Chapter 99 codes used

---

## Example Validation Run

### Input: 10 entries from March 2025
```
Line 1: HTS 7318.22.00.00, JP, 3/27/2025, $10,000
Line 2: HTS 8543.70.98.60, MX, 3/7/2025, $10,000
Line 3: HTS 8708.80.65.90, JP, 3/15/2025, $10,000
... (7 more entries)
```

### Expected Output:
```json
{
  "total_lines": 10,
  "processed_lines": 10,
  "total_variance": 5260.00,
  "summary": {
    "matches": 3,
    "minor_variances": 2,
    "major_variances": 5
  },
  "variance_breakdown": {
    "ieepa_missing": 1,
    "section232_material_missing": 2,
    "date_implementation": 1,
    "chapter99_difference": 1
  }
}
```

---

## Limitations & Notes

### Current Limitations:

1. **Material Content Assumption:**
   - If not provided in Excel, assumes 0%
   - Section 232 tariffs won't apply without material %
   - Solution: Add material content columns to 7501

2. **Transportation Mode:**
   - Defaults to "ocean" (includes HMF)
   - Air/truck/rail modes don't include HMF
   - Solution: Add mode column to 7501

3. **Date Format:**
   - Expects YYYY-MM-DD or Excel date format
   - May need date parsing adjustment

4. **Header Row:**
   - Expects header at row 6 (index 5)
   - Adjust with `header=N` parameter if different

---

## Advanced Usage

### Custom Validation Script

```python
#!/usr/bin/env python3
"""
Enhanced 7501 Validator with detailed reporting
"""
import requests
import pandas as pd
from datetime import datetime

def validate_7501(file_path, output_excel='validation_report.xlsx'):
    """Upload 7501 and generate detailed validation report"""

    # Upload file
    with open(file_path, 'rb') as f:
        response = requests.post(
            'http://localhost:8000/api/validate-entry',
            files={'file': f}
        )

    results = response.json()

    # Process results
    df_results = pd.DataFrame(results['results'])

    # Add status column
    df_results['status'] = df_results.apply(lambda r:
        '✅ MATCH' if abs(r.get('variance', 0)) < 1
        else '⚠️ MINOR' if abs(r.get('variance_percent', 0)) < 5
        else '❌ MAJOR', axis=1
    )

    # Create Excel with multiple sheets
    with pd.ExcelWriter(output_excel) as writer:
        # Summary sheet
        summary = pd.DataFrame({
            'Metric': [
                'Total Lines',
                'Processed',
                'Matches',
                'Minor Variances (<5%)',
                'Major Variances (≥5%)',
                'Total Variance ($)'
            ],
            'Value': [
                results['total_lines'],
                results['processed_lines'],
                len(df_results[df_results['status'] == '✅ MATCH']),
                len(df_results[df_results['status'] == '⚠️ MINOR']),
                len(df_results[df_results['status'] == '❌ MAJOR']),
                f"${results['total_variance']:,.2f}"
            ]
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)

        # All results
        df_results.to_excel(writer, sheet_name='All Entries', index=False)

        # Major variances only
        major = df_results[df_results['status'] == '❌ MAJOR']
        if len(major) > 0:
            major.to_excel(writer, sheet_name='Major Variances', index=False)

    print(f"✅ Validation complete: {output_excel}")
    print(f"   Total Lines: {results['total_lines']}")
    print(f"   Matches: {len(df_results[df_results['status'] == '✅ MATCH'])}")
    print(f"   Variances: {len(df_results[df_results['status'] != '✅ MATCH'])}")

if __name__ == '__main__':
    validate_7501('7501_entry_summary.xlsx')
```

---

## Next Steps

1. **Upload your 7501 file** to test the validation
2. **Review variances** to identify patterns
3. **Enhance source data** with material content if needed
4. **Iterate** - fix calculator issues or update entries

---

**Ready to validate?** Upload your 7501 Excel file and let's verify all entries at once!

