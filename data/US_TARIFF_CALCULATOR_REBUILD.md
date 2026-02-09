# US Tariff Calculator - Complete System Architecture

## Overview

Universal tariff calculation platform (not Trump-specific) that:
1. Uses 79k HTS codes as foundation
2. Applies tariff overlays (Sec 232, 301, Reciprocal, etc.)
3. Validates entry data (7501) against expected
4. Validates commercial invoice data
5. Matches Flex

port's functionality but better

---

## Database Architecture

### Layer 1: Base HTS Rates (Foundation)
**Table: `base_hts_rates`** (79,338 codes)
- `hts_code` - 10-digit HTS  
- `column1_advalorem` - Base MFN duty rate
- `description` - Product description
- `special_program_indicator` - FTA eligibility

**Purpose:** Standard duty rates for all products

### Layer 2: Tariff Overlays (Additional Tariffs)
**Table: `tariff_overlays`** (76 programs)
- Section 232 (Steel, Aluminum, Auto, etc.)
- Section 301 (China)
- IEEPA Reciprocal Tariffs
- Country-specific programs

**Purpose:** Additional duties on top of base rates

### Layer 3: HTS to Overlay Mappings
**Table: `hts_overlay_mappings`** (10,460+ mappings)
- Which HTS codes are subject to which overlays
- Jurisdiction-specific (China, Japan, etc.)

---

## Calculation Flow

```
User Input:
├─ HTS Code: 8708.29.65.90
├─ Country: JP
├─ Entry Date: 2025-03-15
├─ Value: $10,000
└─ Aluminum %: 100%

↓

Step 1: Lookup Base Rate
├─ Query: base_hts_rates WHERE hts_code = '8708296590'
└─ Result: Base Rate = 2.5%

↓

Step 2: Check Applicable Overlays
├─ Query: hts_overlay_mappings + tariff_overlays
├─ Filter by: entry_date >= implementation_date
├─ Filter by: jurisdiction = 'Japan' OR 'All'
└─ Results:
    ├─ Sec 232 Aluminum: 25% (on aluminum content)
    └─ (No Section 301 for Japan)

↓

Step 3: Calculate Total Duty
├─ Base: $10,000 × 2.5% = $250
├─ Sec 232: $10,000 × 100% aluminum × 25% = $2,500
└─ Total: $2,750 (27.5% effective rate)

↓

Step 4: Add Fees
├─ MPF: Calculate based on entry date (FY-specific rates)
└─ HMF: $10,000 × 0.125% = $12.50

↓

Output:
├─ Total Duty Rate: 27.50%
├─ Duty Amount: $2,750
├─ MPF: $35
├─ HMF: $13
├─ Landed Cost: $12,798
├─ Citations: [Base HTS, CSMS #XXXXX, FRN XXXXX]
└─ Confidence: 95%
```

---

## Three Core Functions

### 1. Tariff Calculator (Like Flexport)
**Input:**
- HTS Code
- Country
- Entry Date
- Value
- Optional: Material composition

**Output:**
- Total duty rate
- Duty breakdown by program
- Fees (MPF, HMF)
- Landed cost
- Full citations

**Use Case:** Customer portal, quick quotes

---

### 2. Entry Validator (7501 Audit)
**Input:**
- 7501 Excel file (header row 5)

**Process:**
```python
for each line in 7501:
    # Extract filed data
    filed_hts = row['29. CD HTS US Code']
    filed_coo = row['27. CM Country Of Origin']
    filed_date = row['11. CS Import Date']
    filed_value = row['32. CM Item Entered Value']
    filed_duty = row['34. CD Ad Valorem Duty']
    
    # Calculate expected
    expected = calculate_tariff(filed_hts, filed_coo, filed_date, filed_value)
    
    # Compare
    variance = filed_duty - expected.duty_amount
    
    if abs(variance) > $1:
        flag_for_review(line, variance, expected.citation_chain)
```

**Output:**
- Line-by-line comparison
- Variances with root cause
- Total over/underpayment
- Optimization suggestions

**Use Case:** Post-filing audit, PSC candidates

---

### 3. CI Validator (Pre-Filing Check)
**Input:**
- Commercial Invoice Excel/PDF
- Columns: SKU, Description, HTS, COO, Qty, Value

**Process:**
```python
for each CI line:
    # Calculate expected duty
    expected = calculate_tariff(ci_hts, ci_coo, today, ci_value)
    
    # Check for optimization
    optimization = psc_optimizer.analyze(ci_line)
    
    if optimization.duty_savings > 0:
        suggest_psc_split(ci_line, optimization)
```

**Output:**
- Expected duty for each line
- Total duty liability
- PSC optimization opportunities
- Entry filing guidance

**Use Case:** Pre-filing review, customer quotes

---

## API Endpoints

### `/api/calculate-duty`
Single HTS lookup (like Flexport)

**Request:**
```json
{
  "hts_code": "8708296590",
  "country": "JP",
  "entry_date": "2025-03-15",
  "value": 10000,
  "aluminum_percentage": 100
}
```

**Response:**
```json
{
  "total_duty_rate": 0.275,
  "duty_amount": 2750.00,
  "mpf": 35.00,
  "hmf": 12.50,
  "landed_cost": 12797.50,
  "breakdown": [
    {
      "program": "Base MFN Rate",
      "rate": 0.025,
      "amount": 250.00,
      "citation": "HTS 8708.29.65.90"
    },
    {
      "program": "Sec 232 Aluminum",
      "rate": 0.25,
      "amount": 2500.00,
      "citation": "CSMS #65936570"
    }
  ],
  "confidence": 0.95
}
```

### `/api/validate-entry`
7501 file upload

**Request:** Multipart form with Excel file

**Response:**
```json
{
  "entry_number": "98Q-1024387-7",
  "total_lines": 92,
  "variances_found": 12,
  "total_overpayment": 1250.00,
  "total_underpayment": 0,
  "lines": [
    {
      "line_number": 1,
      "hts": "8708296590",
      "filed_duty": 3000.00,
      "expected_duty": 2750.00,
      "variance": 250.00,
      "status": "OVERPAID",
      "root_cause": "Sec 232 rate applied incorrectly",
      "psc_eligible": true
    }
  ]
}
```

### `/api/validate-ci`
Commercial Invoice upload

**Request:** Multipart form with Excel/CSV file

**Response:**
```json
{
  "total_lines": 331,
  "total_value": 125000.00,
  "expected_duty": 34250.00,
  "optimization_opportunities": 15,
  "potential_savings": 2500.00,
  "lines": [
    {
      "line_number": 1,
      "sku": "010410600",
      "hts": "7318158069",
      "expected_duty": 0.00,
      "optimization": {
        "type": "PSC_SPLIT",
        "savings": 150.00,
        "recommendation": "Split into metal/non-metal components"
      }
    }
  ]
}
```

---

## UI Components (Match Your Cursor Design)

### Header
```
┌────────────────────────────────────────────────────────┐
│  🔷 US Tariff Calculator                              │
│  AI-Native Customs Intelligence Platform by KlearNow  │
└────────────────────────────────────────────────────────┘
```

### Dashboard Cards
```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ TOTAL       │ RECENT      │ AFFECTED    │  Live       │
│ CHANGES     │ (7 DAYS)    │ HTS CODES   │  SYSTEM     │
│             │             │             │  STATUS     │
│    76       │    3        │   12,435    │             │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

### 🔍 HTS Code Lookup
Input: HTS Code → Instant results

### 💰 Duty Calculator  
Input: HTS + Country + Value → Full breakdown

### 📊 Recent Tariff Changes
Timeline of latest updates

---

## File Structure

```
us-tariff-calculator/
├── backend/
│   ├── database/
│   │   └── us_tariff_calculator.db
│   ├── tariff_engine.py          # Core calculation engine
│   ├── entry_validator.py        # 7501 audit logic
│   ├── ci_validator.py            # CI validation
│   └── api.py                     # FastAPI endpoints
├── frontend/
│   ├── index.html                 # Main dashboard
│   ├── calculator.html            # Duty calculator
│   ├── validator.html             # Entry/CI validator
│   └── styles.css                 # Dark blue theme
└── data/
    ├── base_hts_rates.csv         # 79k codes
    ├── tariff_overlays.csv        # 76 programs
    └── hts_mappings.csv           # 10k+ mappings
```

---

## Data Update Process

### When New Tariff Announced

1. **Manual Entry (For Now)**
```python
cursor.execute('''
    INSERT INTO tariff_overlays (
        program_name, jurisdiction, implementation_date,
        duty_rate, csms_reference
    ) VALUES (?, ?, ?, ?, ?)
''', ('New Program', 'China', '2026-02-01', '0.10', 'CSMS #XXXXX'))
```

2. **HTS Mapping**
```python
cursor.execute('''
    INSERT INTO hts_overlay_mappings (
        hts_code, program_name, duty_rate
    ) VALUES (?, ?, ?)
''', ('8708296590', 'New Program', 0.10))
```

3. **Auto-Refresh Calculator**
- System automatically picks up new rules
- Applies to calculations dated after implementation_date

### Automated CSMS Ingestion (Phase 2)
- Parse CSMS messages with Claude API
- Extract structured data
- Auto-update database
- Send notifications

---

## Key Differences vs. Flexport

| Feature | Flexport | KlearNow Platform |
|---------|----------|-------------------|
| HTS Coverage | Partial | Full 79k codes |
| Base Rates | Static | Live database |
| Overlays | Sec 301 only | All 76+ programs |
| Hierarchy | ❌ Additive | ✅ Proper sequencing |
| Material Basis | ❌ No | ✅ % aluminum/steel |
| Retroactivity | ❌ Not tracked | ✅ Flagged |
| Citations | Basic | Full CSMS/FRN chain |
| Entry Validation | ❌ No | ✅ 7501 audit |
| CI Pre-Check | ❌ No | ✅ Pre-filing validation |
| PSC Optimization | ❌ No | ✅ AI-powered splits |
| Updates | Manual | Database-driven |

---

## Implementation Plan

### Phase 1: Core Calculator (Week 1)
- [x] Database created
- [ ] Basic tariff engine
- [ ] Single HTS lookup API
- [ ] Web UI (calculator page)

### Phase 2: Entry Validator (Week 2)
- [ ] 7501 file parser
- [ ] Line-by-line comparison
- [ ] Variance reporting
- [ ] Web UI (validator page)

### Phase 3: CI Validator (Week 3)
- [ ] CI file parser
- [ ] Expected duty calculation
- [ ] PSC optimization suggestions
- [ ] Web UI (pre-filing check)

### Phase 4: Advanced Features (Week 4)
- [ ] AI learning feedback loop
- [ ] Historical accuracy tracking
- [ ] Customer-specific profiles
- [ ] Automated CSMS ingestion

---

## Immediate Next Steps

1. **Complete Tariff Engine**
   - Port logic from tariff_engine.py
   - Adapt to new database schema
   - Add material basis calculations

2. **Build Entry Validator**
   - Read 7501 with header row 5
   - Extract key columns per COLUMN_MAPPING_REFERENCE.md
   - Compare filed vs. expected
   - Generate variance report

3. **Create UI**
   - Match dark blue theme from your Cursor design
   - Implement HTS lookup
   - Implement duty calculator
   - Add file upload for validation

4. **Deploy**
   - API on port 8000
   - Frontend on port 3000
   - Database on same server

---

## Questions to Resolve

1. **Full HTS Load**: Should I load all 79k codes or keep subset?
2. **Overlay Completion**: Need all sheets from Trump Tariffs spreadsheet?
3. **UI Framework**: React or plain HTML/JS?
4. **Hosting**: Docker container or direct deploy?
5. **Authentication**: Public calculator or login required?

---

**Status:** Foundation complete, ready to build calculator engine.

**Contact:** Ready for implementation discussion.
