# IEEPA Reciprocal Tariff Implementation

## ✅ Status: **COMPLETE**

The US Tariff Calculator now includes full IEEPA (International Emergency Economic Powers Act) Reciprocal Tariff support with:

- Date-based rate application
- Country-specific rates
- Annex II HTS code exceptions (1,337 codes exempt)
- Chapter 99 derivative codes (9903.01.01, etc.)
- Proper implementation timeline from CSMS

---

## 📅 Implementation Timeline

### First Implementation: **April 5, 2025** (CSMS 64649265)
- **Global Rate:** 10%
- **Chapter 99:** 9903.01.01
- **Exemptions:** Canada, Mexico, Annex II HTS codes

### Subsequent Updates:
- **April 9, 2025:** China/HK/Macau 84% (CSMS 64687696)
- **April 10, 2025:** China/HK/Macau 125% (CSMS 64701128)
- **May 14, 2025:** China/HK/Macau reduced to 10% (CSMS 65029337)
- **August 27, 2025:** India 25% (CSMS 66027027)
- **August 6, 2025:** Brazil 40% (CSMS 65807735)
- **November 14, 2025:** Korea 15% (CSMS 66987366)
- **November 14, 2025:** Switzerland/Liechtenstein 15% (CSMS 67133044)

---

## 🌍 Country-Specific Rates (as of latest CSMS)

| Country | Rate | Chapter 99 Code | Effective Date | CSMS |
|---------|------|-----------------|----------------|------|
| **Canada** | **EXEMPT** | N/A | Always | 64649265 |
| **Mexico** | **EXEMPT** | N/A | Always | 64649265 |
| China/HK/Macau | 10% | 9903.01.0025 | 2025-11-10 | 66749380 |
| India | 25% | 9903.01.01 | 2025-08-27 | 66027027 |
| Brazil | 40% → 0% | 9903.01.01 | 2025-11-13 | 66871909 |
| South Korea | 15% | 9903.01.01 | 2025-11-14 | 66987366 |
| Switzerland | 15% | 9903.01.01 | 2025-11-14 | 67133044 |
| Liechtenstein | 15% | 9903.01.01 | 2025-11-14 | 67133044 |
| **All Others** | **10%** | 9903.01.01 | 2025-04-05 | 64649265 |

---

## 🛡️ Exemptions

### Country Exemptions
- **Canada (CA)**
- **Mexico (MX)**

### Annex II HTS Code Exemptions
**1,337 HTS codes** are exempt from IEEPA Reciprocal, including:
- Agricultural products
- Unavailable natural resources
- Civil aircraft parts
- Non-patented pharmaceuticals
- Certain essential oils
- Religious materials

### Product-Specific Exemptions
- Already subject to Section 232
- US content ≥20% of entered value
- In-transit goods
- Donations
- Informational materials
- Column 2 COO goods

---

## 💰 Calculation Examples

### Example 1: Mexico (EXEMPT)
```
HTS: 8543.70.98.60
Country: Mexico (MX)
Entry Date: 2025-03-27
Value: $10,000

Base MFN:           2.6% = $260
IEEPA Reciprocal:   N/A (EXEMPT)
─────────────────────────────────
Total Duty:         2.6% = $260
Landed Cost:        $10,307
```

### Example 2: India (25%)
```
HTS: 8543.70.98.60
Country: India (IN)
Entry Date: 2025-09-01
Value: $10,000

Base MFN:           2.6% = $260
IEEPA Reciprocal:   25.0% = $2,500
Chapter 99:         9903.01.01
─────────────────────────────────
Total Duty:         27.6% = $2,760
Landed Cost:        $13,067
```

### Example 3: Germany (10%)
```
HTS: 8543.70.98.60
Country: Germany (DE)
Entry Date: 2025-05-01
Value: $10,000

Base MFN:           2.6% = $260
IEEPA Reciprocal:   10.0% = $1,000
Chapter 99:         9903.01.01
─────────────────────────────────
Total Duty:         12.6% = $1,260
Landed Cost:        $11,567
```

### Example 4: China (125% → 10%)
```
HTS: 8543.70.98.60
Country: China (CN)
Entry Date: 2025-04-15
Value: $10,000

Base MFN:           2.6% = $260
IEEPA Reciprocal:   125.0% = $12,500
Chapter 99:         9903.01.0025
─────────────────────────────────
Total Duty:         127.6% = $12,760
Landed Cost:        $23,067

(Note: Rate reduced to 10% after May 14, 2025)
```

---

## 🧪 Test Results

All test cases **PASS** ✅:

| Test | Country | Date | Expected | Actual | Status |
|------|---------|------|----------|--------|--------|
| 1 | Mexico | 2025-03-27 | 2.6% ($260) | 2.6% ($260) | ✅ |
| 2 | India | 2025-09-01 | 27.6% ($2,760) | 27.6% ($2,760) | ✅ |
| 3 | Germany | 2025-05-01 | 12.6% ($1,260) | 12.6% ($1,260) | ✅ |
| 4 | China | 2025-04-15 | 127.6% ($12,760) | 127.6% ($12,760) | ✅ |

---

## 🔍 How It Works

### 1. Date Check
- Calculator checks entry date against IEEPA implementation dates
- If entry date < April 5, 2025 → **No IEEPA applies**
- If entry date ≥ April 5, 2025 → Proceed to country check

### 2. Country Check
- **Canada/Mexico** → Always exempt
- **China/HK/Macau** → Use China-specific rate timeline
- **India/Brazil/Korea/etc.** → Use country-specific rate
- **All others** → Use global 10% rate

### 3. Annex II Check
- Check if HTS code is in Annex II exceptions list (1,337 codes)
- If in Annex II → **No IEEPA applies**
- If not in Annex II → Apply reciprocal rate

### 4. Rate Application
- Get applicable rate for country and date
- Calculate: `IEEPA Duty = Value × Rate / 100`
- Add to overlay duties
- Include Chapter 99 code in breakdown

---

## 📊 API Response Format

```json
{
  "breakdown": [
    {
      "name": "Base MFN Rate",
      "rate": 2.6,
      "amount": 260.0
    },
    {
      "name": "IEEPA Reciprocal",
      "rate": 25.0,
      "amount": 2500.0,
      "description": "IEEPA Reciprocal: 25.0%",
      "chapter99_code": "99030101",
      "tariff_basis": "CSMS 66027027"
    }
  ],
  "total_duty_rate": 27.6,
  "total_duty": 2760.0,
  "notes": [
    "IEEPA Reciprocal tariff: 25.0% (Chapter 99: 99030101)"
  ]
}
```

---

## 📁 Implementation Files

| File | Purpose |
|------|---------|
| `backend/ieepa_rates.py` | Rate lookup logic, date checking, Annex II |
| `backend/tariff_engine.py` | Integration with main calculator |
| `data/Trump_Tariffs_Summary_20260122.xlsx` | Source data (CSMS summary) |

---

## 🚀 Usage

### Python API
```python
from tariff_engine import calculate_duty

result = calculate_duty(
    hts_code="8543.70.98.60",
    country="IN",  # India
    entry_date="2025-09-01",
    value=10000.0
)

print(f"IEEPA Rate: {result.total_duty_rate}%")
print(f"Total Duty: ${result.total_duty:,.2f}")
# Output: IEEPA Rate: 27.6%
#         Total Duty: $2,760.00
```

### REST API
```bash
curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "hts_code": "8543.70.98.60",
    "country": "IN",
    "entry_date": "2025-09-01",
    "value": 10000.0
  }'
```

### Web Interface
1. Enter HTS: `8543.70.98.60`
2. Select Country: India
3. Set Entry Date: `09/01/2025`
4. Enter Value: `10000`
5. Click **Calculate**
6. See IEEPA Reciprocal in breakdown with Chapter 99 code

---

## ⚠️ Important Notes

### Mexico Validation (Your Request)
For your specific validation:
- **HTS:** 8543.70.98.60
- **Country:** Mexico (MX)
- **Entry Date:** March 27, 2025

**Result:** ✅ **2.6% MFN only (No IEEPA)**

**Reasons:**
1. Entry date (March 27) is **before** IEEPA implementation (April 5)
2. Mexico is **exempt** from IEEPA anyway
3. HTS 8543.70.98.60 is **not** in Annex II

**Calculator is CORRECT!** ✅

### Date Sensitivity
The IEEPA rate is **highly date-dependent**:
- Same HTS, same country, **different dates** = **different rates**
- Example: China on April 9 (84%) vs April 15 (125%) vs May 20 (10%)

### Annex II Updates
Annex II exceptions are updated periodically:
- CSMS 64724565 (April 5): Initial Annex II
- CSMS 66151866 (Sept 8): HTS codes added/removed
- CSMS 66814923 (Nov 13): Agricultural imports added
- CSMS 66492057 (Oct 14): Chapter 44 codes removed

---

## 📚 References

- **CSMS Summary:** `Trump_Tariffs_Summary_20260122.xlsx` (ToT - CSMS Summary sheet)
- **Annex II HTS:** Recip Except (Annex II-HTS) sheet (1,337 codes)
- **Annex II COO:** Recip Except (Annex II-COO) sheet (98 entries)
- **IEEPA Authority:** International Emergency Economic Powers Act
- **Chapter 99:** HTS Chapter 99 - Special Classification Provisions

---

**Last Updated:** January 24, 2026
**Status:** ✅ Fully Operational
**Coverage:** 1,337 Annex II exceptions + All country rates
