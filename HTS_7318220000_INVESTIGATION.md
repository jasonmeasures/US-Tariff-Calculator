# Investigation: HTS 7318.22.00.00 - Chapter 99 Code 9903.81.90

## User Question

**HTS:** 7318.22.00.00
**COO:** Japan (JP)
**Entry Date:** March 1, 2025
**Issue:** Why didn't Chapter 99 code 9903.81.90 get applied?

---

## Investigation Results

### Current Calculation ✅

```
HTS Code:       7318.22.00.00
Country:        Japan
Entry Date:     2025-03-01
Base MFN Rate:  0.0%
Total Duty:     $0.00

Breakdown:
  Base MFN Rate:  0.0% = $0.00
  MPF:            0.3% = $34.64
  HMF:            0.1% = $12.50
  Total:          $47.14
```

**No overlays applied** - Calculator shows only base rate and fees.

---

## Database Check

### 1. HTS Overlay Mappings
```sql
SELECT * FROM hts_overlay_mappings WHERE hts_code = '7318220000'
```
**Result:** ❌ **NO overlays found**

### 2. Section 232 Steel Programs
Checked for any Section 232 steel overlays in database:
- ✅ Section 232 Steel overlays exist for other HTS codes
- ❌ HTS 7318220000 is NOT in the overlay mappings

---

## Excel Source Data Check

### File: `Trump_Tariffs_Summary_20260122.xlsx`
### Sheet: `Sec 232 Steel (FRNs)`

**Search:** HTS 7318.22.00.00
**Result:** ❌ **NOT FOUND**

Sample HTS codes found in Sec 232 Steel sheet:
- 04029968
- 04029970
- 04029990
- 2106909998
- etc.

**Conclusion:** HTS 7318.22.00.00 is **NOT included** in the Section 232 Steel (FRNs) program according to the source data.

---

## HTS Code Information

**HTS:** 7318.22.00.00
**Description:** Other washers
**Chapter:** 73 - Articles of iron or steel
**Heading:** 7318 - Screws, bolts, nuts, coach-screws, screw hooks, rivets, cotters, cotter-pins, washers
**Base MFN Rate:** 0.0% (Free)

---

## Chapter 99 Code Analysis

### What is 9903.81.90?

Chapter 99 code **9903.81.90** is typically associated with:
- Section 232 steel additional duties
- Applied to steel articles and derivatives
- Rate: Usually 25%

### Why it's NOT applied here:

1. **HTS 7318.22.00.00 is NOT in the Section 232 Steel program**
   - Not listed in `Sec 232 Steel (FRNs)` Excel sheet
   - Not in database `hts_overlay_mappings` table

2. **Source data determines applicability**
   - The Trump_Tariffs_Summary_20260122.xlsx file is the authoritative source
   - HTS codes must be explicitly listed to have Section 232 apply

3. **Calculator is working correctly**
   - No overlay = No Chapter 99 code
   - This is the expected behavior

---

## Possible Explanations

### 1. Different HTS Code?
- **7318.21** vs **7318.22**?
- Spring washers vs other washers may have different treatment

### 2. Different Entry Date?
- Section 232 implementation dates vary
- March 1, 2025 may be before certain provisions take effect

### 3. Specific Jurisdiction?
- Some Section 232 measures are country-specific
- Japan may have different treatment

### 4. Product-Specific Exclusion?
- Certain products within 7318.22 may be excluded
- Need more specific 10-digit HTS code

### 5. Flexport Showing Different Scenario?
- Flexport may be using:
  - Different HTS code (similar but not identical)
  - Different entry date
  - Different material composition assumptions
  - Steel content percentage > 0%

---

## Verification Steps

To confirm whether 9903.81.90 should apply, we need:

### 1. Flexport Comparison
- **Exact screenshot** showing:
  - Full 10-digit HTS code
  - Country of origin
  - Entry date
  - Chapter 99 code displayed
  - Any material composition percentages

### 2. USITC HTS Database
- Check official HTS: https://hts.usitc.gov
- Look up 7318.22.00.00
- See if any Chapter 99 derivatives apply

### 3. CBP CSMS Messages
- Search for Section 232 steel CSMS covering 7318.22
- CSMS messages may clarify scope

### 4. Material Composition
- If washers contain steel, Section 232 may apply
- Need to specify steel percentage in calculator

---

## Test with Steel Percentage

Let me test if specifying steel content triggers Section 232:

```bash
curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "hts_code": "7318.22.00.00",
    "country": "JP",
    "entry_date": "2025-03-01",
    "value": 10000.0,
    "steel_percent": 100.0,
    "mode": "ocean"
  }'
```

**Result:** Still 0% - HTS not in Section 232 program even with 100% steel.

This confirms: **HTS 7318.22.00.00 is not subject to Section 232 steel tariffs per the source data.**

---

## Recommendation

### If Chapter 99 code 9903.81.90 SHOULD apply:

1. **Verify the HTS code** - May be a different code (e.g., 7318.21.00.00)

2. **Check Flexport's inputs** - Ensure:
   - Exact same HTS (10 digits)
   - Exact same COO
   - Exact same entry date

3. **Update source data if needed:**
   - Add HTS 7318220000 to `Sec 232 Steel (FRNs)` Excel sheet
   - Include Chapter 99 code: 99038190
   - Specify rate: 25%
   - Re-run database loader

4. **Provide documentation:**
   - CSMS message number
   - Federal Register Notice (FRN)
   - Official CBP guidance

---

## Current Status

✅ **Calculator is working correctly** based on available data
✅ **No overlays exist** for HTS 7318220000 in source Excel
✅ **No Chapter 99 code** should be applied per current data

❓ **Need clarification:**
- Where was 9903.81.90 shown to apply?
- What were the exact inputs used?
- Is this a data gap or expected behavior?

---

**Investigated:** January 25, 2026
**Status:** Awaiting user clarification on expected Chapter 99 code
