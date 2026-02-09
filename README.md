# US Tariff Calculator

A comprehensive tariff calculator for US imports with support for Trump-era tariff overlays including Section 232 (Aluminum, Steel, Copper), Section 301 (China), and Reciprocal tariffs.

## Features

- 🎯 **79,338 HTS Codes** - Complete US Harmonized Tariff Schedule
- 📊 **16,189 Tariff Overlays** - Section 232, 301, Reciprocal, and country-specific exceptions
- 🧮 **Material-Based Calculations** - Aluminum, steel, and copper content adjustments
- 💰 **Full Cost Breakdown** - Base duty, overlays, MPF, HMF, and landed cost
- 🌐 **REST API** - FastAPI backend for integration
- 💻 **Web Interface** - Clean, modern UI for calculations

## Project Structure

```
us-tariff-calculator/
├── data/                           # Input data files
│   ├── hts_classification_us_new_wh_table cleaned.csv
│   ├── Trump_Tariffs_Summary_20260122.xlsx
│   ├── 7501_US_Entry_Summary_-_All_Data.xlsx
│   └── KX-072Q-11_invoice_tab.xlsx
├── backend/
│   ├── database_setup.py          # Load data into SQLite
│   ├── tariff_engine.py           # Core calculation logic
│   ├── api.py                     # FastAPI REST API
│   └── test_api.py                # API tests
├── frontend/
│   ├── index.html                 # Web UI
│   ├── styles.css                 # Styling
│   └── app.js                     # Frontend JavaScript
└── us_tariff_calculator.db        # SQLite database
```

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r backend/requirements.txt
```

### 2. Load Database (First Time Only)

```bash
python backend/database_setup.py
```

This will:
- Create SQLite database
- Load 79,338 HTS codes
- Load 16,189 tariff overlay mappings
- Takes ~30 seconds

### 3. Start API Server

```bash
python backend/api.py
```

API will be available at: http://localhost:8000

### 4. Open Web Interface

Open `frontend/index.html` in your browser, or:

```bash
open frontend/index.html
```

## Usage

### Web Interface

1. **Enter HTS Code** - 10-digit code (dots optional, e.g., 8708.80.65.90)
2. **Select Country** - Country of origin (2-letter code)
3. **Set Entry Date** - Date of import entry
4. **Enter Value** - USD value of goods
5. **Adjust Material Content** - Aluminum, steel, or copper percentage (0-100%)
6. **Select Transportation Mode** - Ocean (HMF applies), Air, Truck, or Rail
7. **Click Calculate** - View full breakdown

### Test Case

Click "Load Test Case" button to test with:
- HTS: 8708.80.65.90 (Auto parts)
- Country: JP (Japan)
- Value: $10,000
- Aluminum: 100%

**Expected Result:**
- Base MFN: 2.5% = $250
- Sec 232 Aluminum: 25% × 100% = $2,500
- Total Duty: $2,750 (27.5%)
- MPF: $34.64
- HMF: $12.50
- **Landed Cost: $12,797.14**

## API Endpoints

### POST /api/calculate

Calculate duty for a single entry.

**Request:**
```json
{
  "hts_code": "8708.80.65.90",
  "country": "JP",
  "entry_date": "2025-03-15",
  "value": 10000.0,
  "aluminum_percent": 100.0,
  "steel_percent": 0.0,
  "copper_percent": 0.0,
  "mode": "ocean"
}
```

**Response:**
```json
{
  "hts_code": "8708806590",
  "country": "JP",
  "total_duty_rate": 27.5,
  "total_duty": 2750.0,
  "mpf": 34.64,
  "hmf": 12.50,
  "landed_cost": 12797.14,
  "breakdown": [...],
  "confidence": 100,
  "notes": [...]
}
```

### POST /api/validate-entry

Upload 7501 Entry Summary Excel file for variance analysis.

**Parameters:**
- `file`: Excel file (multipart/form-data)

**Returns:** Variance report comparing declared vs. calculated duties

### POST /api/validate-ci

Upload Commercial Invoice Excel to calculate expected duties.

**Parameters:**
- `file`: Excel file (multipart/form-data)

**Returns:** Expected duties for all line items

### GET /health

Health check endpoint.

## Database Schema

### base_hts_rates
- `hts_code` (PK) - Normalized 10-digit HTS code
- `description` - Product description
- `column1_advalorem` - Base MFN duty rate (%)
- `special_program_indicator` - Special programs (GSP, etc.)
- `raw_hts_code` - Original HTS with dots

### hts_overlay_mappings
- `hts_code` (FK) - Links to base_hts_rates
- `program_name` - Tariff program (e.g., "Sec 232 Aluminum")
- `duty_rate` - Additional duty rate (%)
- `jurisdiction` - Country/region (e.g., "CN", "GLOBAL")
- `effective_date` - Implementation date

## Tariff Programs Included

- **Section 232** - Aluminum, Steel, Copper, Auto Parts, Semiconductors, Wood Products
- **Section 301** - China tariffs (10,460 HTS codes)
- **Reciprocal Tariffs** - Country-specific adjustments
- **Country Exceptions:**
  - Brazil (Civil Aircraft, General)
  - China/Liechtenstein (Civil Aircraft, Ag, Pharma)
  - South Korea (Civil Aircraft, Wood Furniture)
  - European Union (Auto Parts)
  - Japan (Auto Parts, Wood Products)

## Material Basis Calculations

Some tariffs apply to material content:

**Example: Sec 232 Aluminum (25%)**
- If product is 100% aluminum → 25% × 100% = 25% duty
- If product is 50% aluminum → 25% × 50% = 12.5% duty
- If product is 0% aluminum → 25% × 0% = 0% duty (no Sec 232 applies)

## MPF & HMF

### Merchandise Processing Fee (MPF)
- Rate: 0.3464% of entered value
- Minimum: $31.67
- Maximum: $614.35

### Harbor Maintenance Fee (HMF)
- Rate: 0.125% of entered value
- Only applies to **ocean** shipments
- No caps

## Testing

```bash
# Test calculator engine
python backend/tariff_engine.py

# Test API endpoints
python backend/test_api.py
```

## Technology Stack

- **Backend:** Python 3.13, FastAPI, SQLite, Pandas
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Database:** SQLite (23,596 HTS codes with rates, 16,189 overlay mappings)

## Data Sources

- **HTS Classification:** US ITC Harmonized Tariff Schedule (79,338 codes)
- **Trump Tariffs:** CSMS summary (20 tariff programs, 20 Excel sheets)
- **Test Data:** 7501 Entry Summary and Commercial Invoice samples

## Performance

- Database size: ~720 KB (SQLite)
- API response time: <100ms for single calculation
- Frontend load time: <1 second
- Database query time: <10ms per lookup

## Future Enhancements

- [ ] Batch processing for multiple entries
- [ ] Export results to PDF/Excel
- [ ] Historical tariff rate lookup
- [ ] Advanced filtering and search
- [ ] User authentication and saved calculations
- [ ] Real-time CSMS updates integration

## Support

For issues or questions, contact the development team or refer to:
- `/docs` - FastAPI interactive documentation
- `COLUMN_MAPPING_REFERENCE.md` - Field mapping reference

## License

Proprietary - KlearNow, Inc.

---

**Built with ❤️ by KlearNow**
