# Section 232 Date Rules Analysis

## User Question

**Have we properly updated the 232 tables for all countries with appropriate date rules?**

**Test Case:**
- HTS: 7318.15.20.65
- COO: Japan (JP)
- Entry Date: March 27, 2025
- Export Date: March 10, 2025

---

## Current Database Status

### Section 232 Steel
```
Program: Sec 232 Steel (FRNs)
Jurisdiction: GLOBAL
Rate: 25.0%
Effective Date: 2025-02-01
HTS Codes: 561
Chapter 99: 99038190 (recently added)
```

**Issue:** Only ONE entry with single effective date, no country-specific or date-based variations.

---

## CSMS Timeline (From Trump_Tariffs_Summary_20260122.xlsx)

### Section 232 Steel Implementation Dates:

| CSMS | Implementation Date | Jurisdiction | Rate | Notes |
|------|---------------------|--------------|------|-------|
| 64348411 | **2025-03-12** | Global | 0.25 (25%?) | Initial implementation |
| 64384423 | **2025-03-12** | Global | 0.25 (25%?) | Confirmation |
| 65236374 | **2025-06-04** | Global | 25% (UK) 50% (other) | UK distinction added |
| 65405824 | **2025-06-23** | Global | 0.5 (50%?) | Rate change? |
| 65441222 | **2025-06-23** | Global | 25% (UK), 50% (other) | UK vs others |

---

## Interpretation Challenges

### 1. Rate Format Ambiguity

**CSMS shows:**
- "0.25" - Could be 25% or 0.25%
- "25% (UK) 50% (other)" - Two different rates?
- "0.5" - Could be 50% or 0.5%

**Tariff Basis Note:**
> "50% of Steel Value (non-UK) / 25% of Steel Value (UK)"

**Two Possible Interpretations:**

#### Interpretation A: Basis Multiplier
- **Non-UK:** 25% tariff × 50% basis = 12.5% effective
- **UK:** 25% tariff × 25% basis = 6.25% effective

#### Interpretation B: Direct Rate
- **Non-UK:** 50% tariff on steel content
- **UK:** 25% tariff on steel content

---

## Test Case Analysis

### Entry: March 27, 2025, Japan, HTS 7318.15.20.65, 100% Steel

**Timeline Position:**
- Export: March 10 (before CSMS 64348411)
- Entry: March 27 (after CSMS 64348411, before CSMS 65236374)

**Expected Behavior:**
1. **If March 12 is the start date:** Apply 25% (uniform for all countries)
2. **If June 4 distinction applies retroactively:** Need UK vs non-UK split

**Current Calculator:**
```
Rate: 25%
Duty: $2,500
Applies uniformly to all countries
```

---

## What We Need to Validate

### 1. Flexport Comparison

**For HTS 7318.15.20.65, Japan, March 27, 2025:**
- What rate does Flexport show?
- What Chapter 99 code?
- Does it mention UK vs non-UK distinction?

### 2. Date-Based Implementation

**Questions:**
- Does Section 232 Steel apply before March 12, 2025?
- What rate applies March 12 - June 3?
- What rate applies after June 4?

### 3. Country-Specific Rules

**Questions:**
- Is UK the only country with different treatment?
- Are there other exemptions (like Canada/Mexico)?
- Does "export date" matter vs "entry date"?

---

## Database Schema Limitations

### Current Schema:
```sql
CREATE TABLE hts_overlay_mappings (
    hts_code TEXT,
    program_name TEXT,
    duty_rate REAL,
    jurisdiction TEXT,
    effective_date TEXT,
    chapter99_code TEXT,
    tariff_basis TEXT
)
```

**Problem:** One row per HTS+Program+Jurisdiction
- Can't easily store multiple date ranges
- Can't store rate changes over time
- No support for "basis multiplier" vs "direct rate"

---

## Recommended Fixes

### Short Term (Validate Current Implementation)

1. **Check Flexport for March 27, 2025:**
   - Confirm expected rate for Japan
   - Verify Chapter 99 code
   - Check if 25% is correct

2. **Document Date Ranges:**
   - Before March 12: No Sec 232 Steel? Or different rate?
   - March 12 - June 3: 25% uniform
   - June 4+: UK split

3. **Add Implementation Date Check:**
   ```python
   if entry_date < '2025-03-12':
       # No Section 232 Steel applies
       return None
   elif entry_date < '2025-06-04':
       # Uniform 25% for all countries
       return {'rate': 25.0, 'chapter99_code': '99038190'}
   else:
       # UK distinction
       if country == 'GB':
           return {'rate': 25.0, 'basis_multiplier': 0.25}
       else:
           return {'rate': 25.0, 'basis_multiplier': 0.50}
   ```

### Long Term (Full Implementation)

1. **Add Date-Based Rate Support:**
   - Store multiple rows per HTS with different effective dates
   - Query: Find most recent rate before entry date

2. **Add UK-Specific Entries:**
   - Jurisdiction: 'GB' with different rate/basis
   - Separate Chapter 99 codes for UK (9903.91.98, etc.)

3. **Implement Basis Multiplier:**
   - Store basis percentage in database
   - Calculate: duty_rate × material_percent × basis_multiplier
   - Example: 25% × 100% steel × 50% basis = 12.5%

---

## Current Test Results

### Japan, March 27, 2025:
```
Current Calculator:
  Rate: 25%
  Duty: $2,500 (on $10,000)
  Chapter 99: 9903.81.90

Expected (if basis multiplier applies):
  Rate: 25% × 50% basis = 12.5%
  Duty: $1,250 (on $10,000)
  Chapter 99: 9903.81.90
```

**Question:** Which is correct? Need Flexport validation.

---

## Action Items

1. ✅ **Fixed:** 8-digit HTS fallback (allows 10-digit input)
2. ✅ **Fixed:** Added Chapter 99 code 9903.81.90 to all Sec 232 Steel
3. ⚠️ **Pending:** Validate rate interpretation (25% direct vs 12.5% with basis)
4. ⚠️ **Pending:** Implement date-based rate changes (March 12, June 4)
5. ⚠️ **Pending:** Add UK-specific rates and Chapter 99 codes
6. ⚠️ **Pending:** Check export date vs entry date logic

---

## Questions for User

1. **What does Flexport show for HTS 7318.15.20.65, Japan, March 27, 2025?**
   - Is it 25% or 12.5%?
   - Which Chapter 99 code?

2. **Does the "basis multiplier" apply?**
   - Should we calculate: 25% × steel_percent × 50% = 12.5%?
   - Or just: 25% × steel_percent = 25%?

3. **Do we need to implement date ranges?**
   - March 12 start date?
   - June 4 UK distinction?

4. **Export date vs entry date:**
   - You mentioned export date 3/10/2025
   - Entry date 3/27/2025
   - Which one determines the tariff rate?

---

**Status:** Awaiting validation
**Priority:** High - affects all Section 232 Steel calculations
**Impact:** 561 HTS codes, potentially wrong rates

