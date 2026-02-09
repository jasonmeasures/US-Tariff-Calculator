# Server Status

## ✅ Both Servers Running

---

## Backend API Server

**Status:** ✅ Running
**PID:** `cat logs/api.pid`
**Port:** 8000
**URL:** http://localhost:8000
**Logs:** `tail -f logs/api.log`

### Endpoints Available:

1. **GET /health**
   - Health check endpoint
   - Returns: `{"status": "healthy"}`

2. **GET /api/check-section232/{hts_code}** ⭐ NEW
   - Check if HTS requires Section 232 material content
   - Example: http://localhost:8000/api/check-section232/8543.70.98.60
   - Returns:
     ```json
     {
       "hts_code": "8543.70.98.60",
       "requires_section232": false,
       "materials": [],
       "programs": []
     }
     ```

3. **POST /api/calculate**
   - Calculate duty for single entry
   - Request body:
     ```json
     {
       "hts_code": "8543.70.98.60",
       "country": "MX",
       "entry_date": "2025-03-07",
       "value": 10000.0,
       "aluminum_percent": 0.0,
       "steel_percent": 0.0,
       "copper_percent": 0.0,
       "mode": "ocean"
     }
     ```

4. **POST /api/validate-entry**
   - Upload 7501 Entry Summary Excel for validation

5. **POST /api/validate-ci**
   - Upload Commercial Invoice Excel for duty calculation

### Recent Updates Applied:

- ✅ Mexico IEEPA rate corrected (25% for March 7, 2025)
- ✅ Section 232 check endpoint added
- ✅ IEEPA rates updated with correct dates
- ✅ Chapter 99 codes included in all responses

---

## Frontend Server

**Status:** ✅ Running
**PID:** `cat logs/frontend.pid`
**Port:** 3000
**URL:** http://localhost:3000
**Logs:** `tail -f logs/frontend.log`

### Features:

- HTS code lookup with auto-formatting
- Country selection dropdown
- Entry date picker
- Material content sliders (aluminum, steel, copper)
- Real-time duty calculation
- Chapter 99 code display
- Detailed breakdown with fees

### Next Enhancement Needed:

**Conditional Material Content Display**

The frontend should call `/api/check-section232/{hts_code}` when user enters HTS and only show material sliders if required.

**Implementation:**
```javascript
// In app.js, add this function
async function checkHtsRequirements(htsCode) {
    const response = await fetch(`http://localhost:8000/api/check-section232/${htsCode}`);
    const result = await response.json();

    const materialSection = document.getElementById('material-content-section');

    if (result.requires_section232) {
        // Show material sliders
        materialSection.style.display = 'block';

        // Show only required materials
        document.getElementById('aluminum-slider').style.display =
            result.materials.includes('aluminum') ? 'block' : 'none';
        document.getElementById('steel-slider').style.display =
            result.materials.includes('steel') ? 'block' : 'none';
        document.getElementById('copper-slider').style.display =
            result.materials.includes('copper') ? 'block' : 'none';

        // Show note about country of smelt/pour
        if (result.note) {
            showNote(result.note);
        }
    } else {
        // Hide entire material section
        materialSection.style.display = 'none';
    }
}

// Call on HTS code blur/change
document.getElementById('hts-code').addEventListener('blur', function() {
    const htsCode = this.value;
    if (htsCode) {
        checkHtsRequirements(htsCode);
    }
});
```

---

## Testing Commands

### Test Backend Health:
```bash
curl http://localhost:8000/health
```

### Test Section 232 Check:
```bash
# Should return false (no Section 232)
curl http://localhost:8000/api/check-section232/8543.70.98.60

# Should return true (requires aluminum)
curl http://localhost:8000/api/check-section232/8708.80.65.90
```

### Test Duty Calculation (Mexico March 7):
```bash
curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "hts_code": "8543.70.98.60",
    "country": "MX",
    "entry_date": "2025-03-07",
    "value": 10000.0,
    "mode": "ocean"
  }'
```

Expected result: 27.6% (2.6% MFN + 25% IEEPA)

### Test Frontend:
```bash
open http://localhost:3000
```

---

## Restart Commands

### Restart Backend:
```bash
kill $(cat logs/api.pid)
source venv/bin/activate
nohup python backend/api.py > logs/api.log 2>&1 &
echo $! > logs/api.pid
```

### Restart Frontend:
```bash
kill $(cat logs/frontend.pid)
cd frontend && nohup python3 -m http.server 3000 > ../logs/frontend.log 2>&1 &
echo $! > ../logs/frontend.pid
```

### Restart Both:
```bash
kill $(cat logs/api.pid) $(cat logs/frontend.pid)
source venv/bin/activate
nohup python backend/api.py > logs/api.log 2>&1 &
echo $! > logs/api.pid
cd frontend && nohup python3 -m http.server 3000 > ../logs/frontend.log 2>&1 &
echo $! > ../logs/frontend.pid
cd ..
echo "✅ Both servers restarted"
```

---

## Stop Commands

### Stop Both Servers:
```bash
kill $(cat logs/api.pid) $(cat logs/frontend.pid)
echo "✅ Both servers stopped"
```

---

## Current Configuration

- **Database:** us_tariff_calculator.db (79,338 HTS codes, 16,189 overlays)
- **IEEPA Rates:** Updated with Mexico 25% (March 4-7, 2025)
- **Section 232:** Conditional check endpoint available
- **Chapter 99 Codes:** Displayed in all calculations
- **Virtual Environment:** venv/ (with all dependencies)

---

**Last Updated:** January 25, 2026
**Status:** ✅ Fully Operational
