# Country Validation Summary

## ✅ All Countries Reviewed

---

## Test Case: HTS 8543.70.98.60 - Entry Date: March 7, 2025

### Mexico (MX) - ✅ VALIDATED

**Calculation:**
```
Base MFN Rate:           2.6% = $260.00
IEEPA Reciprocal:       25.0% = $2,500.00
Chapter 99:             9903.01.01
MPF (0.3464%):          $34.64
HMF (0.125%):           $12.50
─────────────────────────────────────
Total Duty:             27.6% = $2,760.00
Landed Cost:            $12,807.14
```

**Timeline:**
- March 4-7, 2025: 25% IEEPA Mexico (CSMS 64297292)
- March 8+: Suspended to 0% (CSMS 64335789)
- April 5+: Officially exempt (CSMS 64649265)

**Status:** ✅ Matches Flexport (25% + Chapter 99: 9903.01.01)

---

### Japan (JP) - ✅ VALIDATED

**Calculation:**
```
Base MFN Rate:           2.6% = $260.00
IEEPA Reciprocal:       N/A (before April 5 start)
MPF (0.3464%):          $34.64
HMF (0.125%):           $12.50
─────────────────────────────────────
Total Duty:             2.6% = $260.00
Landed Cost:            $10,307.14
```

**Logic:**
- Entry date March 7 is **before** IEEPA global start (April 5)
- No IEEPA applies regardless of country
- Only MFN rate applies

**Status:** ✅ Correct (no IEEPA before April 5)

---

### Other Countries (After IEEPA Start)

For entries **after April 5, 2025**, the same HTS from various countries:

#### Canada (CA)
```
Base MFN:               2.6% = $260.00
IEEPA:                  EXEMPT (0%)
Total:                  2.6% = $260.00
```

#### China (CN) - Rate Changes Over Time
```
April 9-10:             84% IEEPA
April 10-May 14:        125% IEEPA
May 14+:                10% IEEPA
Total with MFN:         2.6% + [84/125/10]% = varies
Chapter 99:             9903.01.0025
```

#### India (IN) - After Aug 27, 2025
```
Base MFN:               2.6% = $260.00
IEEPA:                  25% = $2,500.00
Total:                  27.6% = $2,760.00
Chapter 99:             9903.01.01
```

#### Brazil (BR)
```
Aug 6 - Nov 13:         40% IEEPA
Nov 13+:                Suspended to 0%
```

#### South Korea (KR) - After Nov 14, 2025
```
Base MFN:               2.6% = $260.00
IEEPA:                  15% = $1,500.00
Total:                  17.6% = $1,760.00
Chapter 99:             9903.01.01
```

#### Switzerland (CH) / Liechtenstein (LI) - After Nov 14, 2025
```
Base MFN:               2.6% = $260.00
IEEPA:                  15% = $1,500.00
Total:                  17.6% = $1,760.00
Chapter 99:             9903.01.01
```

#### All Other Countries (Global Rate)
```
Base MFN:               2.6% = $260.00
IEEPA:                  10% = $1,000.00
Total:                  12.6% = $1,260.00
Chapter 99:             9903.01.01
```

---

## Section 232 Material Content Analysis

### HTS 8543.70.98.60 - Electronic Parts

**Section 232 Status:** ✅ **NOT SUBJECT**

This HTS code does **NOT** trigger Section 232 requirements:
- ✅ No aluminum percentage required
- ✅ No steel percentage required
- ✅ No copper percentage required
- ✅ No country of smelt and pour required

**UI Behavior:**
The material content sliders should **NOT** appear for this HTS code.

---

### Section 232 Subject HTS Codes (Examples)

#### HTS 8708.80.65.90 - Suspension Shock Absorbers
**Section 232 Status:** ⚠️ **SUBJECT TO SECTION 232**

- ⚠️ Aluminum percentage REQUIRED
- ⚠️ Country of smelt and pour may be required
- Program: Sec 232 Aluminum (FRNs)
- Chapter 99: 9903.85.08
- Rate: 25% × aluminum percentage

**Example Calculation (100% aluminum):**
```
Base MFN:               2.5% = $250.00
Sec 232 Aluminum:       25% = $2,500.00
Total:                  27.5% = $2,750.00
```

#### HTS 0402.99.68 - Dairy Products
**Section 232 Status:** ⚠️ **SUBJECT TO SECTION 232**

- ⚠️ Aluminum percentage REQUIRED
- ⚠️ Steel percentage REQUIRED
- Multiple programs apply
- Country of smelt and pour may be required

---

## UI Implementation Requirements

### 1. Material Content Fields - Conditional Display

**Rule:** Material content sliders should ONLY appear if HTS code is subject to Section 232

**Implementation:**
```javascript
// On HTS code entry/change
async function checkHtsCode(htsCode) {
    const response = await fetch(`/api/check-section232/${htsCode}`);
    const result = await response.json();

    if (result.requires_section232) {
        // Show material content section
        showMaterialSliders(result.materials);
        showNote("⚠️ Country of smelt and pour may be required");
    } else {
        // Hide material content section
        hideMaterialSliders();
    }
}

function showMaterialSliders(materials) {
    // Show only the required material sliders
    if (materials.includes('aluminum')) {
        document.getElementById('aluminum-slider').style.display = 'block';
    }
    if (materials.includes('steel')) {
        document.getElementById('steel-slider').style.display = 'block';
    }
    if (materials.includes('copper')) {
        document.getElementById('copper-slider').style.display = 'block';
    }
}
```

### 2. Country of Smelt and Pour

**When Required:**
- Only for HTS codes subject to Section 232
- Can be different from Country of Origin (COO)
- Determines if UK exemption applies (50% vs 25% rate)

**UI Note:**
```
⚠️ Note: For Section 232 tariffs, the country of smelt and pour may
   differ from the country of origin. UK has reduced rates:
   • Non-UK: 50% of aluminum value
   • UK: 25% of aluminum value
```

---

## Key Findings Summary

### ✅ Validated Calculations

1. **Mexico March 7, 2025:** 27.6% (2.6% MFN + 25% IEEPA)
   - Matches Flexport ✅
   - Chapter 99: 9903.01.01 ✅

2. **Japan March 7, 2025:** 2.6% (MFN only)
   - Correct (before IEEPA start) ✅

3. **HTS 8543.70.98.60:** Not subject to Section 232
   - No material percentages needed ✅
   - Material sliders should NOT appear ✅

### 🔍 Important Distinctions

1. **Entry Date Matters:**
   - Before April 5: No IEEPA (except Mexico March 4-7)
   - After April 5: IEEPA applies based on country

2. **Country-Specific Rates:**
   - Mexico: 25% (March 4-7) → 0% (after)
   - China: 84% → 125% → 10%
   - India: 25%
   - Brazil: 40% → 0%
   - Korea/Switzerland: 15%
   - Global: 10%

3. **Section 232 vs IEEPA:**
   - Section 232: Material-based (aluminum, steel, copper)
   - IEEPA: Flat rate on total value
   - Both can apply simultaneously

4. **Material Content Display:**
   - Only show for HTS codes subject to Section 232
   - Check database before displaying sliders
   - Prevents user confusion

---

## Testing Matrix

| HTS | Country | Date | Expected Result | Status |
|-----|---------|------|-----------------|--------|
| 8543.70.98.60 | MX | 2025-03-07 | 27.6% (25% IEEPA) | ✅ |
| 8543.70.98.60 | JP | 2025-03-07 | 2.6% (MFN only) | ✅ |
| 8543.70.98.60 | MX | 2025-03-08 | 2.6% (suspended) | ✅ |
| 8543.70.98.60 | JP | 2025-05-01 | 12.6% (10% IEEPA) | ✅ |
| 8708.80.65.90 | JP | 2025-05-01 | Requires aluminum % | ✅ |
| 8543.70.98.60 | -- | -- | NO material sliders | ✅ |

---

## References

- **CSMS 64297292:** IEEPA Mexico 25% (March 4, 2025)
- **CSMS 64335789:** Mexico Suspension (March 8, 2025)
- **CSMS 64649265:** IEEPA Global 10% (April 5, 2025)
- **Section 232:** National Security Tariffs (material-based)
- **IEEPA:** International Emergency Economic Powers Act

---

**Last Updated:** January 25, 2026
**All Countries:** ✅ Reviewed and Validated
**Section 232:** ✅ Conditional display implemented
