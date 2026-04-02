"""
US Tariff Calculator - FastAPI Backend
REST API for tariff calculations and entry validation
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import pandas as pd
from io import BytesIO
from dataclasses import asdict

from tariff_engine import calculate_duty, CalculationResult, get_ieepa_rate
from admin_api import admin_router
import sqlite3
import os

app = FastAPI(title="US Tariff Calculator API", version="1.0.0")

# Mount admin router
app.include_router(admin_router)

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "us_tariff_calculator.db")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CalculateRequest(BaseModel):
    hts_code: str
    country: str
    entry_date: str
    value: float
    aluminum_percent: Optional[float] = 0.0
    steel_percent: Optional[float] = 0.0
    copper_percent: Optional[float] = 0.0
    mode: Optional[str] = 'ocean'


class CalculateResponse(BaseModel):
    hts_code: str
    country: str
    entry_date: str
    entered_value: float
    base_rate: float
    total_duty_rate: float
    base_duty: float
    overlay_duty: float
    total_duty: float
    mpf: float
    hmf: float
    landed_cost: float
    breakdown: List[Dict]
    confidence: int
    notes: List[str]
    citations: List[str]


@app.get("/")
def read_root():
    return {
        "message": "US Tariff Calculator API",
        "version": "1.0.0",
        "endpoints": [
            "POST /api/calculate - Calculate duty for single entry",
            "POST /api/validate-entry - Upload 7501 Excel and validate",
            "POST /api/validate-ci - Upload CI Excel and calculate expected duties",
            "GET /health - Health check"
        ]
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/debug/ieepa")
def debug_ieepa():
    """Debug endpoint to check if IEEPA is loaded"""
    return {
        "ieepa_loaded": get_ieepa_rate is not None,
        "test_cn_rate": get_ieepa_rate('CN', '2025-03-27', '8537109170') if get_ieepa_rate else None
    }


@app.get("/api/check-section232/{hts_code}")
def check_section232_requirement(hts_code: str):
    """
    Check if an HTS code requires Section 232 material content data

    Returns:
    {
        "requires_section232": true/false,
        "materials": ["aluminum", "steel", "copper"],
        "programs": [list of applicable Section 232 programs]
    }
    """
    try:
        # Normalize HTS code
        normalized_hts = hts_code.replace('.', '').replace('-', '').replace(' ', '').strip()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check for Section 232 overlays (try 10-digit first)
        cursor.execute('''
            SELECT program_name, tariff_basis
            FROM hts_overlay_mappings
            WHERE hts_code = ?
            AND program_name LIKE '%232%'
        ''', (normalized_hts,))

        results = cursor.fetchall()

        # If no match and HTS is 10-digit, try 8-digit fallback
        if not results and len(normalized_hts) >= 8:
            hts_8digit = normalized_hts[:8]
            cursor.execute('''
                SELECT program_name, tariff_basis
                FROM hts_overlay_mappings
                WHERE hts_code = ?
                AND program_name LIKE '%232%'
            ''', (hts_8digit,))
            results = cursor.fetchall()

        conn.close()

        if not results:
            return {
                "hts_code": hts_code,
                "requires_section232": False,
                "materials": [],
                "programs": []
            }

        # Determine which materials are required
        materials = []
        programs = []

        for program, basis in results:
            programs.append(program)

            if 'Aluminum' in program:
                materials.append('aluminum')
            elif 'Steel' in program:
                materials.append('steel')
            elif 'Copper' in program:
                materials.append('copper')

        # Remove duplicates
        materials = list(set(materials))

        return {
            "hts_code": hts_code,
            "requires_section232": True,
            "materials": materials,
            "programs": programs,
            "note": "Country of smelt and pour may be required (can differ from COO)"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/calculate", response_model=CalculateResponse)
def calculate_single_duty(request: CalculateRequest):
    """
    Calculate duty for a single entry

    Example request:
    {
        "hts_code": "8708.80.65.90",
        "country": "JP",
        "entry_date": "2025-03-15",
        "value": 10000.0,
        "aluminum_percent": 100.0,
        "mode": "ocean"
    }
    """
    try:
        result = calculate_duty(
            hts_code=request.hts_code,
            country=request.country,
            entry_date=request.entry_date,
            value=request.value,
            aluminum_percent=request.aluminum_percent,
            steel_percent=request.steel_percent,
            copper_percent=request.copper_percent,
            mode=request.mode
        )

        return CalculateResponse(**asdict(result))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/validate-entry")
async def validate_7501_entry(file: UploadFile = File(...)):
    """
    Upload 7501 Entry Summary Excel file and validate duties

    The file should have header row at row 5 (data starts at row 6)
    Required columns:
    - 29. CD HTS US Code
    - 27. CM Country Of Origin
    - 7. CS Entry Date
    - 32. CM Item Entered Value
    - 33. CD HTS US Rate
    - 34. CD Ad Valorem Duty
    """
    try:
        # Read Excel file
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents), header=5)

        results = []
        total_variance = 0.0

        for idx, row in df.iterrows():
            try:
                # Extract fields (using actual 7501 column names)
                hts_code = str(row.get('29. CD HTS US Code', ''))
                country = str(row.get('27. CM Country Of Origin', ''))
                item_number = row.get('27. CM Item Number', '')
                description = str(row.get('29. CD HTS Description', ''))[:50]

                # Try both column name formats
                entry_date_raw = row.get('7. CS Entry Date', row.get('Entry Date', ''))

                # Normalize entry date to YYYY-MM-DD format
                if pd.notna(entry_date_raw):
                    if isinstance(entry_date_raw, pd.Timestamp):
                        entry_date = entry_date_raw.strftime('%Y-%m-%d')
                    else:
                        entry_date = str(entry_date_raw).split(' ')[0]  # Remove timestamp if present
                else:
                    entry_date = ''

                declared_value = float(row.get('32. CM Item Entered Value', row.get('Value (Line Item)', 0)))
                declared_rate = float(row.get('33. CD HTS US Rate', row.get('Duty Rate', 0)))
                declared_duty = float(row.get('34. CD Ad Valorem Duty', row.get('Duty Amount', 0)))

                if not hts_code or hts_code == 'nan':
                    continue

                # Calculate expected duty
                calc_result = calculate_duty(
                    hts_code=hts_code,
                    country=country,
                    entry_date=entry_date,
                    value=declared_value,
                    aluminum_percent=0.0,  # Would need material composition data
                    mode='ocean'
                )

                # Calculate variance
                variance = calc_result.total_duty - declared_duty
                variance_pct = (variance / declared_duty * 100) if declared_duty > 0 else 0

                # Extract breakdown details
                breakdown_str = ' | '.join([
                    f"{b['name']}: {b['rate']}% = ${b['amount']:.2f}"
                    for b in calc_result.breakdown
                ])

                # Get Chapter 99 codes if any
                chapter99_codes = [
                    b.get('chapter99_code', '')
                    for b in calc_result.breakdown
                    if b.get('chapter99_code')
                ]

                results.append({
                    'line': idx + 1,
                    'item_number': item_number,
                    'hts_code': hts_code,
                    'description': description,
                    'country': country,
                    'entry_date': entry_date,
                    'entered_value': declared_value,
                    'declared_rate': declared_rate * 100,  # Convert to percentage
                    'declared_duty': declared_duty,
                    'base_rate': calc_result.base_rate,
                    'calculated_rate': calc_result.total_duty_rate,
                    'calculated_duty': calc_result.total_duty,
                    'variance': variance,
                    'variance_percent': variance_pct,
                    'confidence': calc_result.confidence,
                    'breakdown': breakdown_str,
                    'chapter99_codes': ', '.join(chapter99_codes) if chapter99_codes else '',
                    'notes': ' | '.join(calc_result.notes) if calc_result.notes else '',
                    'is_chapter99': hts_code.startswith('9903')
                })

                total_variance += abs(variance)

            except Exception as e:
                results.append({
                    'line': idx + 1,
                    'error': str(e)
                })

        return {
            'total_lines': len(df),
            'processed_lines': len(results),
            'total_variance': total_variance,
            'results': results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.post("/api/validate-ci")
async def validate_commercial_invoice(file: UploadFile = File(...)):
    """
    Upload Commercial Invoice Excel and calculate expected duties

    Required columns:
    - HTS Code
    - Country of Origin
    - Value
    - Description
    """
    try:
        # Read Excel file
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))

        results = []
        total_duty = 0.0

        for idx, row in df.iterrows():
            try:
                # Extract fields (flexible column matching)
                hts_code = str(row.get('HTS Code', row.get('HTS', row.get('HS Code', ''))))
                country = str(row.get('Country of Origin', row.get('Country', row.get('COO', ''))))
                value = float(row.get('Value', row.get('Amount', row.get('Price', 0))))
                description = str(row.get('Description', row.get('Item Description', '')))

                if not hts_code or hts_code == 'nan':
                    continue

                # Calculate duty
                calc_result = calculate_duty(
                    hts_code=hts_code,
                    country=country,
                    entry_date='2025-02-01',  # Default to current
                    value=value,
                    mode='ocean'
                )

                results.append({
                    'line': idx + 1,
                    'hts_code': calc_result.hts_code,
                    'country': country,
                    'description': description,
                    'value': value,
                    'duty_rate': calc_result.total_duty_rate,
                    'duty_amount': calc_result.total_duty,
                    'mpf': calc_result.mpf,
                    'hmf': calc_result.hmf,
                    'landed_cost': calc_result.landed_cost,
                    'breakdown': calc_result.breakdown
                })

                total_duty += calc_result.total_duty

            except Exception as e:
                results.append({
                    'line': idx + 1,
                    'error': str(e)
                })

        return {
            'total_lines': len(df),
            'processed_lines': len(results),
            'total_duty': total_duty,
            'results': results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
