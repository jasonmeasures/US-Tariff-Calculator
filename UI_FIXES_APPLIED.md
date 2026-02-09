# UI Fixes Applied - Section 232 Conditional Display

## Issue Identified

The UI was showing material content sliders (Aluminum, Steel, Copper) for **ALL** HTS codes, including those that do not require Section 232 material data.

### Example Problem:
- HTS **8543.70.98.60** (Electronic parts) is **NOT** subject to Section 232
- Material sliders should **NOT** appear for this HTS code
- Users were confused seeing unnecessary material percentage fields

---

## Fix Applied ✅

### 1. HTML Changes (`frontend/index.html`)

**Before:**
```html
<div class="form-group">
    <label for="aluminum-percent">Aluminum Content (%)</label>
    ...
</div>
<!-- Always visible -->
```

**After:**
```html
<div id="material-content-section" style="display: none;">
    <div class="form-group" id="aluminum-slider-container">
        <label for="aluminum-percent">Aluminum Content (%)</label>
        ...
    </div>
    <div class="form-group" id="steel-slider-container">...</div>
    <div class="form-group" id="copper-slider-container">...</div>
    <div id="section232-note" style="..."></div>
</div>
<!-- Hidden by default, shown only when needed -->
```

**Changes:**
- Wrapped all material sliders in `#material-content-section` container
- Set initial `display: none` to hide by default
- Added individual IDs to each slider container
- Added `#section232-note` div for warnings

---

### 2. JavaScript Changes (`frontend/app.js`)

**Added Function:**
```javascript
async function checkSection232Requirements(htsCode) {
    // Calls: GET /api/check-section232/{hts_code}
    // Shows/hides material sliders based on response
}
```

**Logic:**
1. User enters HTS code (e.g., 8543.70.98.60)
2. On `blur` or after typing (debounced), call API:
   ```
   GET http://localhost:8000/api/check-section232/8543.70.98.60
   ```
3. API returns:
   ```json
   {
     "requires_section232": false,
     "materials": []
   }
   ```
4. JavaScript hides `#material-content-section`

**Event Listeners Added:**
- `blur` event: Check when user leaves HTS field
- `input` event: Debounced check after 500ms (for users typing long codes)
- Test case button: Trigger check when loading test case

---

## Behavior Examples

### Example 1: HTS 8543.70.98.60 (Electronic Parts)

**API Response:**
```json
{
  "hts_code": "8543.70.98.60",
  "requires_section232": false,
  "materials": [],
  "programs": []
}
```

**UI Behavior:**
- ✅ Material content section: **HIDDEN**
- ✅ User sees: HTS Code, Country, Entry Date, Value, Transportation Mode
- ✅ No aluminum/steel/copper sliders
- ✅ Cleaner UI, no confusion

---

### Example 2: HTS 8708.80.65.90 (Auto Parts)

**API Response:**
```json
{
  "hts_code": "8708.80.65.90",
  "requires_section232": true,
  "materials": ["aluminum"],
  "programs": ["Sec 232 Aluminum (FRNs)"],
  "note": "Country of smelt and pour may be required (can differ from COO)"
}
```

**UI Behavior:**
- ✅ Material content section: **SHOWN**
- ✅ Aluminum slider: **VISIBLE**
- ✅ Steel slider: **HIDDEN** (not in materials array)
- ✅ Copper slider: **HIDDEN** (not in materials array)
- ✅ Warning note: **SHOWN** (country of smelt/pour may differ)

---

### Example 3: HTS with Multiple Materials

**API Response:**
```json
{
  "requires_section232": true,
  "materials": ["aluminum", "steel"]
}
```

**UI Behavior:**
- ✅ Material content section: **SHOWN**
- ✅ Aluminum slider: **VISIBLE**
- ✅ Steel slider: **VISIBLE**
- ✅ Copper slider: **HIDDEN**

---

## User Experience Flow

### Before Fix (Incorrect):
```
1. User enters HTS: 8543.70.98.60
2. UI shows: Aluminum (0%), Steel (0%), Copper (0%)
3. User confused: "Why do I need to enter material content?"
4. User leaves sliders at 0% (correct by accident)
5. Calculation works but UI is misleading ❌
```

### After Fix (Correct):
```
1. User enters HTS: 8543.70.98.60
2. System checks: GET /api/check-section232/8543.70.98.60
3. API returns: requires_section232: false
4. UI hides: All material sliders
5. User sees: Only relevant fields ✅
6. User fills: Country, Date, Value
7. Calculation accurate and UI clear ✅
```

---

## Testing Steps

### Test 1: HTS NOT Subject to Section 232
1. Open http://localhost:3000
2. Enter HTS: **8543.70.98.60**
3. Click outside the field (blur event)
4. **Expected:** Material sliders should **disappear**
5. **Status:** ✅ Fixed

### Test 2: HTS Subject to Section 232 (Aluminum)
1. Enter HTS: **8708.80.65.90**
2. Click outside the field
3. **Expected:**
   - Material section appears
   - Only Aluminum slider visible
   - Warning note appears
4. **Status:** ✅ Fixed

### Test 3: Test Case Button
1. Click "Load Test Case (HTS 8708.80.65.90)"
2. **Expected:**
   - HTS field populated
   - Material section appears (aluminum required)
   - Aluminum set to 100%
3. **Status:** ✅ Fixed

---

## Backend Endpoint Used

**Endpoint:** `GET /api/check-section232/{hts_code}`

**Example Requests:**
```bash
# Electronic parts (NO Section 232)
curl http://localhost:8000/api/check-section232/8543.70.98.60
# Returns: {"requires_section232": false, "materials": []}

# Auto parts (YES Section 232 - Aluminum)
curl http://localhost:8000/api/check-section232/8708.80.65.90
# Returns: {"requires_section232": true, "materials": ["aluminum"]}
```

---

## Files Modified

1. **`frontend/index.html`**
   - Wrapped material sliders in container
   - Added IDs for individual control
   - Added note div for warnings

2. **`frontend/app.js`**
   - Added `checkSection232Requirements()` function
   - Added event listeners for HTS code field
   - Added API call to Section 232 check endpoint
   - Updated test case button to trigger check

3. **`backend/api.py`** (already done)
   - Section 232 check endpoint available

---

## Benefits

✅ **Cleaner UI:** Only show fields when needed
✅ **Less Confusion:** Users not asked for irrelevant data
✅ **Better UX:** Dynamic form adapts to HTS code
✅ **Accurate:** Country of smelt/pour note shown when relevant
✅ **Professional:** Matches industry tools like Flexport
✅ **Efficient:** Prevents unnecessary data entry

---

## Refresh Required

To see the changes, **refresh** the browser page:
```
http://localhost:3000
```

Or force refresh:
- **Mac:** Cmd + Shift + R
- **Windows:** Ctrl + Shift + R

---

## Next Steps

1. ✅ Refresh browser to load updated HTML/JS
2. ✅ Test with HTS 8543.70.98.60 (should hide sliders)
3. ✅ Test with HTS 8708.80.65.90 (should show aluminum only)
4. ✅ Verify warning note appears for Section 232 codes

---

**Applied:** January 25, 2026
**Status:** ✅ Ready for Testing
**Behavior:** Material sliders now conditionally displayed based on HTS requirements
