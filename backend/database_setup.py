"""
US Tariff Calculator - Database Setup
Loads HTS codes and tariff overlay programs into SQLite database
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime
from pathlib import Path

DB_PATH = "us_tariff_calculator.db"
DATA_DIR = Path(__file__).parent.parent / "data"


def create_database():
    """Create SQLite database with schema for HTS codes and tariff overlays"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Base HTS rates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS base_hts_rates (
            hts_code TEXT PRIMARY KEY,
            description TEXT,
            column1_advalorem REAL,
            special_program_indicator TEXT,
            raw_hts_code TEXT,
            indent_level INTEGER
        )
    """)

    # Tariff overlay programs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tariff_overlays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_name TEXT NOT NULL,
            jurisdiction TEXT,
            implementation_date TEXT,
            duty_rate REAL,
            duty_rate_text TEXT,
            csms_reference TEXT,
            notes TEXT,
            material_basis TEXT
        )
    """)

    # HTS to overlay mappings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hts_overlay_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hts_code TEXT NOT NULL,
            program_name TEXT NOT NULL,
            duty_rate REAL,
            jurisdiction TEXT,
            effective_date TEXT,
            chapter99_code TEXT,
            tariff_basis TEXT,
            FOREIGN KEY (hts_code) REFERENCES base_hts_rates(hts_code)
        )
    """)

    # Create indexes for fast lookup
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hts_code ON base_hts_rates(hts_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_overlay_program ON tariff_overlays(program_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mapping_hts ON hts_overlay_mappings(hts_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mapping_program ON hts_overlay_mappings(program_name)")

    conn.commit()
    conn.close()
    print("✓ Database schema created")


def normalize_hts_code(hts_code):
    """Remove dots, dashes, and spaces from HTS code"""
    if pd.isna(hts_code):
        return None
    return str(hts_code).replace('.', '').replace('-', '').replace(' ', '').strip()


def load_hts_codes():
    """Load 79,338 HTS codes from CSV file"""
    csv_path = DATA_DIR / "hts_classification_us_new_wh_table cleaned.csv"

    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        return

    print(f"Loading HTS codes from {csv_path.name}...")
    df = pd.read_csv(csv_path)

    print(f"Found {len(df)} records in CSV")
    print(f"Columns: {list(df.columns)}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Process and insert HTS codes
    records_inserted = 0
    records_skipped = 0

    for idx, row in df.iterrows():
        try:
            raw_hts = row.get('HTS Code', row.get('HTS Number', row.get('hts_code', '')))
            normalized_hts = normalize_hts_code(raw_hts)

            if not normalized_hts:
                records_skipped += 1
                continue

            description = row.get('description', row.get('Description', ''))
            column1_rate = row.get('column1_advalorem', row.get('Column 1 Rate of Duty', ''))
            special_indicator = row.get('special_program_indicator', row.get('Special', ''))
            indent = row.get('indent_level', row.get('Indent', 0))

            # Parse ad valorem rate
            advalorem = 0.0
            if pd.notna(column1_rate):
                # Rate is already a float in the CSV
                try:
                    advalorem = float(column1_rate)
                except:
                    # Try parsing as string with %
                    rate_str = str(column1_rate)
                    if '%' in rate_str:
                        try:
                            advalorem = float(rate_str.replace('%', '').strip().split()[0])
                        except:
                            advalorem = 0.0
                    else:
                        advalorem = 0.0

            cursor.execute("""
                INSERT OR REPLACE INTO base_hts_rates
                (hts_code, description, column1_advalorem, special_program_indicator, raw_hts_code, indent_level)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (normalized_hts, description, advalorem, special_indicator, raw_hts, indent))

            records_inserted += 1

            if records_inserted % 5000 == 0:
                print(f"  Progress: {records_inserted:,} records inserted...")
                conn.commit()

        except Exception as e:
            print(f"  Error on row {idx}: {e}")
            records_skipped += 1

    conn.commit()
    conn.close()

    print(f"✓ HTS codes loaded: {records_inserted:,} inserted, {records_skipped:,} skipped")


def load_tariff_overlays():
    """Load tariff overlay programs from Excel file (all sheets)"""
    excel_path = DATA_DIR / "Trump_Tariffs_Summary_20260122.xlsx"

    if not excel_path.exists():
        print(f"❌ File not found: {excel_path}")
        return

    print(f"Loading tariff overlays from {excel_path.name}...")

    # Read all sheets
    xls = pd.ExcelFile(excel_path)
    print(f"Found sheets: {xls.sheet_names}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total_programs = 0
    total_mappings = 0

    # Process each sheet with specific logic
    for sheet_name in xls.sheet_names:
        print(f"\n  Processing sheet: {sheet_name}")
        df = pd.read_excel(excel_path, sheet_name=sheet_name)

        print(f"    Columns: {list(df.columns)[:5]}...")
        print(f"    Rows: {len(df)}")

        # Determine program name and duty rate column
        program_name = sheet_name.strip()

        # Detect material basis from sheet name
        material_basis = None
        if 'aluminum' in program_name.lower() or 'alum' in program_name.lower():
            material_basis = 'aluminum'
        elif 'steel' in program_name.lower():
            material_basis = 'steel'
        elif 'copper' in program_name.lower():
            material_basis = 'copper'

        for idx, row in df.iterrows():
            try:
                # Get Primary HTS code
                hts_code_raw = row.get('Primary HTS', row.get('HTS', row.get('HTS Code', '')))

                if pd.isna(hts_code_raw) or str(hts_code_raw).strip() == '':
                    continue

                normalized_hts = normalize_hts_code(hts_code_raw)
                if not normalized_hts:
                    continue

                # Determine duty rate based on sheet type
                duty_rate = 0.0
                duty_rate_text = ''
                jurisdiction = 'GLOBAL'
                chapter99_code = ''
                tariff_basis = ''

                # Extract Chapter 99 derivative code if present
                if 'Sec 232' in sheet_name:
                    # Get Chapter 99 code from sheet-specific columns
                    ch99_col = row.get('Sec 232 (Aluminum)', row.get('Sec 232 (Steel)', row.get('Sec 232 (Copper)', '')))
                    if pd.notna(ch99_col):
                        ch99_str = str(ch99_col)
                        # Parse "99038508 (non-UK) / 99038515 (UK)" format
                        if '/' in ch99_str:
                            # Get non-UK code (first one)
                            chapter99_code = ch99_str.split('/')[0].strip().split()[0]
                        elif ch99_str.isdigit() and len(ch99_str) == 8:
                            chapter99_code = ch99_str

                    # Get tariff basis
                    tariff_basis = str(row.get('Tariff Basis', ''))

                if 'Sec 232' in sheet_name:
                    # Section 232 tariffs
                    if 'Aluminum' in sheet_name:
                        duty_rate = 25.0
                        duty_rate_text = '25%'
                    elif 'Steel' in sheet_name:
                        duty_rate = 25.0
                        duty_rate_text = '25%'
                    elif 'Copper' in sheet_name:
                        duty_rate = 25.0
                        duty_rate_text = '25%'
                    elif 'Auto Parts' in sheet_name:
                        rate_col = row.get('Duty Rate', row.get('Sec 232 \n(Auto Parts)', ''))
                        if pd.notna(rate_col):
                            duty_rate_text = str(rate_col)
                            if '%' in duty_rate_text:
                                try:
                                    duty_rate = float(duty_rate_text.replace('%', '').strip())
                                except:
                                    duty_rate = 25.0
                    elif 'Semiconductor' in sheet_name:
                        rate_col = row.get('Tariff Rate', '')
                        if pd.notna(rate_col):
                            duty_rate_text = str(rate_col)
                            if '%' in duty_rate_text:
                                try:
                                    duty_rate = float(duty_rate_text.replace('%', '').strip())
                                except:
                                    duty_rate = 25.0
                    else:
                        # Default Sec 232 rate
                        duty_rate = 25.0
                        duty_rate_text = '25%'

                elif 'Sec 301' in sheet_name:
                    # China tariffs
                    rate_col = row.get('Duty Rate', '')
                    jurisdiction = 'CN'
                    if pd.notna(rate_col):
                        duty_rate_text = str(rate_col)
                        if '%' in duty_rate_text:
                            try:
                                duty_rate = float(duty_rate_text.replace('%', '').strip())
                            except:
                                duty_rate = 0.0

                elif 'Recip' in sheet_name:
                    # Reciprocal tariffs
                    rate_col = row.get('Reciprocal Tariff, Adjusted', row.get('Reciprocal Exception', ''))
                    if pd.notna(rate_col):
                        duty_rate_text = str(rate_col)
                        if '%' in duty_rate_text:
                            try:
                                duty_rate = float(duty_rate_text.replace('%', '').strip())
                            except:
                                duty_rate = 0.0

                    # Get country from sheet
                    country_col = row.get('Countries and Territories', row.get('Merch Country of Origin', ''))
                    if pd.notna(country_col):
                        jurisdiction = str(country_col).strip()

                elif 'Brazil' in sheet_name:
                    jurisdiction = 'BR'
                    duty_rate = 10.0  # Brazil reciprocal exception
                    duty_rate_text = '10%'

                elif 'CH-LI' in sheet_name:
                    # China/Liechtenstein exceptions
                    ch_rate = row.get('Reciprocal Exception (CH)', '')
                    if pd.notna(ch_rate):
                        jurisdiction = 'CN'
                        duty_rate_text = str(ch_rate)
                        if duty_rate_text.lower() == 'exempt' or duty_rate_text.lower() == 'free':
                            duty_rate = 0.0
                        elif '%' in duty_rate_text:
                            try:
                                duty_rate = float(duty_rate_text.replace('%', '').strip())
                            except:
                                duty_rate = 0.0

                elif 'KR' in sheet_name:
                    jurisdiction = 'KR'
                    rate_col = row.get('Tariff\\ Exception', '')
                    if pd.notna(rate_col):
                        duty_rate_text = str(rate_col)
                        if duty_rate_text.lower() == 'exempt' or duty_rate_text.lower() == 'free':
                            duty_rate = 0.0
                        elif '%' in duty_rate_text:
                            try:
                                duty_rate = float(duty_rate_text.replace('%', '').strip())
                            except:
                                duty_rate = 0.0

                # Insert HTS mapping
                cursor.execute("""
                    INSERT INTO hts_overlay_mappings
                    (hts_code, program_name, duty_rate, jurisdiction, effective_date, chapter99_code, tariff_basis)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (normalized_hts, program_name, duty_rate, jurisdiction, '2025-02-01', chapter99_code, tariff_basis))

                total_mappings += 1

                if total_mappings % 1000 == 0:
                    print(f"    Progress: {total_mappings:,} mappings created...")
                    conn.commit()

            except Exception as e:
                print(f"    Error on row {idx}: {e}")

        conn.commit()
        total_programs += 1

    conn.close()

    print(f"\n✓ Tariff overlays loaded: {total_programs} programs, {total_mappings:,} HTS mappings")


def verify_database():
    """Query database to verify data loaded correctly"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Count HTS codes
    cursor.execute("SELECT COUNT(*) FROM base_hts_rates")
    hts_count = cursor.fetchone()[0]

    # Count overlay programs
    cursor.execute("SELECT COUNT(*) FROM tariff_overlays")
    overlay_count = cursor.fetchone()[0]

    # Count mappings
    cursor.execute("SELECT COUNT(*) FROM hts_overlay_mappings")
    mapping_count = cursor.fetchone()[0]

    print(f"\n=== DATABASE SUMMARY ===")
    print(f"HTS Codes: {hts_count:,}")
    print(f"Tariff Programs: {overlay_count:,}")
    print(f"HTS-Overlay Mappings: {mapping_count:,}")

    # Sample query: Test case HTS 8708.80.65.90
    test_hts = "8708806590"
    print(f"\n=== SAMPLE QUERY: HTS {test_hts} ===")

    cursor.execute("""
        SELECT hts_code, description, column1_advalorem, raw_hts_code
        FROM base_hts_rates
        WHERE hts_code = ?
    """, (test_hts,))

    result = cursor.fetchone()
    if result:
        print(f"HTS Code: {result[0]}")
        print(f"Description: {result[1]}")
        print(f"Base Rate: {result[2]}%")
        print(f"Raw HTS: {result[3]}")
    else:
        print(f"❌ HTS code {test_hts} not found in database")

    # Check overlays for this HTS
    cursor.execute("""
        SELECT program_name, duty_rate, jurisdiction, effective_date
        FROM hts_overlay_mappings
        WHERE hts_code = ?
    """, (test_hts,))

    overlays = cursor.fetchall()
    if overlays:
        print(f"\nApplicable Overlays:")
        for overlay in overlays:
            print(f"  • {overlay[0]}: {overlay[1]}% ({overlay[2]})")
    else:
        print(f"\nNo overlays found for this HTS code")

    conn.close()


if __name__ == "__main__":
    print("=== US TARIFF CALCULATOR - DATABASE SETUP ===\n")

    # Step 1: Create database schema
    create_database()

    # Step 2: Load HTS codes
    load_hts_codes()

    # Step 3: Load tariff overlays
    load_tariff_overlays()

    # Step 4: Verify data
    verify_database()

    print("\n✓ Database setup complete!")
