"""
US Tariff Calculator - Database Migration
Creates new tables for admin management and migrates IEEPA rates from hardcoded dict to database.
"""

import sqlite3
import os
import pandas as pd
from pathlib import Path
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "us_tariff_calculator.db")
DATA_DIR = Path(__file__).parent.parent / "data"


def create_admin_tables():
    """Create new tables for admin management system"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # IEEPA country rates (replaces hardcoded dict in ieepa_rates.py)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ieepa_country_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_code TEXT NOT NULL,
            effective_date TEXT NOT NULL,
            rate REAL NOT NULL,
            csms_reference TEXT,
            chapter99_code TEXT,
            notes TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT DEFAULT 'system'
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ieepa_country ON ieepa_country_rates(country_code, effective_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ieepa_active ON ieepa_country_rates(is_active)")

    # IEEPA Annex II exceptions (HTS and COO exemptions)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ieepa_annex_exceptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exception_type TEXT NOT NULL,
            value TEXT NOT NULL,
            source TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT DEFAULT 'system'
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_annex_type_value ON ieepa_annex_exceptions(exception_type, value)")

    # Audit log for all admin changes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rule_changes_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            user_id TEXT NOT NULL DEFAULT 'admin',
            action TEXT NOT NULL,
            table_name TEXT NOT NULL,
            record_id INTEGER,
            field_name TEXT,
            old_value TEXT,
            new_value TEXT,
            change_description TEXT,
            source TEXT DEFAULT 'manual',
            prompt_text TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON rule_changes_log(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_table ON rule_changes_log(table_name)")

    # Monitor alerts for CSMS/Federal Register tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitor_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            reference_number TEXT,
            title TEXT,
            published_date TEXT,
            summary TEXT,
            raw_content TEXT,
            relevance_score REAL DEFAULT 0.0,
            status TEXT NOT NULL DEFAULT 'new',
            suggested_changes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            reviewed_by TEXT,
            reviewed_at TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_monitor_status ON monitor_alerts(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_monitor_source ON monitor_alerts(source)")

    conn.commit()
    conn.close()
    print("  New admin tables created")


def add_overlay_columns():
    """Add is_active, created_at, updated_at, created_by to hts_overlay_mappings"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(hts_overlay_mappings)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    if 'is_active' not in existing_cols:
        cursor.execute("ALTER TABLE hts_overlay_mappings ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
        print("  Added is_active column to hts_overlay_mappings")

    if 'created_at' not in existing_cols:
        cursor.execute("ALTER TABLE hts_overlay_mappings ADD COLUMN created_at TEXT DEFAULT '2025-01-24'")
        print("  Added created_at column to hts_overlay_mappings")

    if 'updated_at' not in existing_cols:
        cursor.execute("ALTER TABLE hts_overlay_mappings ADD COLUMN updated_at TEXT DEFAULT '2025-01-24'")
        print("  Added updated_at column to hts_overlay_mappings")

    if 'created_by' not in existing_cols:
        cursor.execute("ALTER TABLE hts_overlay_mappings ADD COLUMN created_by TEXT DEFAULT 'system'")
        print("  Added created_by column to hts_overlay_mappings")

    conn.commit()
    conn.close()


def migrate_ieepa_rates():
    """Migrate hardcoded IEEPA rates from ieepa_rates.py to ieepa_country_rates table"""
    from ieepa_rates import IEEPA_RATES

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if already migrated
    cursor.execute("SELECT COUNT(*) FROM ieepa_country_rates")
    if cursor.fetchone()[0] > 0:
        print("  IEEPA rates already migrated, skipping")
        conn.close()
        return

    count = 0
    for country_code, rates in IEEPA_RATES.items():
        for entry in rates:
            effective_date, rate, csms, ch99 = entry
            cursor.execute("""
                INSERT INTO ieepa_country_rates
                (country_code, effective_date, rate, csms_reference, chapter99_code, created_by)
                VALUES (?, ?, ?, ?, ?, 'migration')
            """, (country_code, effective_date, rate, csms, ch99))
            count += 1

    conn.commit()
    conn.close()
    print(f"  Migrated {count} IEEPA rate entries from hardcoded dict")


def migrate_annex_exceptions():
    """Migrate Annex II HTS and COO exceptions from Excel to database"""
    excel_path = DATA_DIR / "Trump_Tariffs_Summary_20260122.xlsx"

    if not excel_path.exists():
        print(f"  Excel file not found: {excel_path}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if already migrated
    cursor.execute("SELECT COUNT(*) FROM ieepa_annex_exceptions")
    if cursor.fetchone()[0] > 0:
        print("  Annex exceptions already migrated, skipping")
        conn.close()
        return

    count = 0

    # Load HTS exceptions
    try:
        df_hts = pd.read_excel(excel_path, sheet_name='Recip Except (Annex II-HTS)')
        for hts in df_hts['Primary HTS']:
            if pd.notna(hts):
                normalized = str(hts).replace('.', '').replace('-', '').replace(' ', '').strip()
                if normalized:
                    cursor.execute("""
                        INSERT INTO ieepa_annex_exceptions (exception_type, value, source, created_by)
                        VALUES ('HTS', ?, 'Annex II-HTS', 'migration')
                    """, (normalized,))
                    count += 1
    except Exception as e:
        print(f"  Error loading HTS exceptions: {e}")

    # Load COO exceptions
    try:
        df_coo = pd.read_excel(excel_path, sheet_name='Recip Except (Annex II-COO)')
        for coo in df_coo['Merch Country of Origin']:
            if pd.notna(coo):
                countries = str(coo).split(',')
                for c in countries:
                    c = c.strip().upper()
                    if len(c) == 2:
                        cursor.execute("""
                            INSERT INTO ieepa_annex_exceptions (exception_type, value, source, created_by)
                            VALUES ('COO', ?, 'Annex II-COO', 'migration')
                        """, (c,))
                        count += 1
    except Exception as e:
        print(f"  Error loading COO exceptions: {e}")

    conn.commit()
    conn.close()
    print(f"  Migrated {count} Annex II exceptions to database")


def populate_program_metadata():
    """Populate the tariff_overlays table with program-level metadata"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if already populated
    cursor.execute("SELECT COUNT(*) FROM tariff_overlays")
    if cursor.fetchone()[0] > 0:
        print("  Program metadata already populated, skipping")
        conn.close()
        return

    programs = [
        ('Sec 232 Aluminum (FRNs)', 'GLOBAL', '2025-03-12', 25.0, 'aluminum', 'Section 232 on Aluminum and derivatives'),
        ('Sec 232 Steel (FRNs)', 'GLOBAL', '2025-03-12', 25.0, 'steel', 'Section 232 on Steel and derivatives'),
        ('Sec 232 Copper (FRNs)', 'GLOBAL', '2025-02-01', 25.0, 'copper', 'Section 232 on Copper'),
        ('Sec 232 Auto Parts (FRNs)', 'GLOBAL', '2025-02-01', 25.0, None, 'Section 232 on Auto Parts'),
        ('Sec 232 Auto Parts Self-Cert', 'GLOBAL', '2025-02-01', 25.0, None, 'Section 232 Auto Parts Self-Certification'),
        ('Sec 232 MHDV + Buses + Parts', 'GLOBAL', '2025-02-01', 25.0, None, 'Section 232 on Motor Heavy-Duty Vehicles'),
        ('Sec 232 Semiconductor', 'GLOBAL', '2025-02-01', 25.0, None, 'Section 232 on Semiconductors'),
        ('Sec 232 Wood Products', 'GLOBAL', '2025-02-01', 25.0, None, 'Section 232 on Wood Products'),
        ('Sec 301 (China)', 'CN', '2018-08-23', None, None, 'Section 301 China tariffs (variable rates by HTS)'),
        ('IEEPA Reciprocal', 'GLOBAL', '2025-04-05', 10.0, None, 'IEEPA Reciprocal Tariff (variable by country)'),
        ('Recip Except (Annex II-HTS)', 'GLOBAL', '2025-04-05', 0.0, None, 'HTS-level exemptions from reciprocal tariff'),
        ('Recip Except (Annex II-COO)', 'GLOBAL', '2025-04-05', 0.0, None, 'Country-level exemptions from reciprocal tariff'),
        ('Brazil Except (Annex I-HTS)', 'BR', '2025-08-06', 0.0, None, 'Brazil HTS exceptions'),
        ('Brazil Except (Civil Aircraft)', 'BR', '2025-08-06', 0.0, None, 'Brazil civil aircraft exceptions'),
        ('CH-LI Civil Aircraft Except', 'CH', '2025-11-14', 0.0, None, 'Switzerland/Liechtenstein civil aircraft exceptions'),
        ('CH-LI Ag Exceptions', 'CH', '2025-11-14', 0.0, None, 'Switzerland/Liechtenstein agriculture exceptions'),
        ('CH-LI Pharma Except', 'CH', '2025-11-14', 0.0, None, 'Switzerland/Liechtenstein pharma exceptions'),
        ('KR Civil Aircraft Except', 'KR', '2025-11-14', 0.0, None, 'South Korea civil aircraft exceptions'),
        ('KR Wood Furn Except', 'KR', '2025-11-14', 0.0, None, 'South Korea wood furniture exceptions'),
    ]

    for p in programs:
        cursor.execute("""
            INSERT INTO tariff_overlays (program_name, jurisdiction, implementation_date, duty_rate, material_basis, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, p)

    conn.commit()
    conn.close()
    print(f"  Populated {len(programs)} program metadata entries")


def verify_migration():
    """Verify migration completed successfully"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n=== MIGRATION VERIFICATION ===")

    cursor.execute("SELECT COUNT(*) FROM ieepa_country_rates")
    print(f"  IEEPA rates:        {cursor.fetchone()[0]} entries")

    cursor.execute("SELECT COUNT(DISTINCT country_code) FROM ieepa_country_rates")
    print(f"  IEEPA countries:    {cursor.fetchone()[0]} distinct")

    cursor.execute("SELECT COUNT(*) FROM ieepa_annex_exceptions WHERE exception_type='HTS'")
    print(f"  Annex II HTS:       {cursor.fetchone()[0]} exemptions")

    cursor.execute("SELECT COUNT(*) FROM ieepa_annex_exceptions WHERE exception_type='COO'")
    print(f"  Annex II COO:       {cursor.fetchone()[0]} exemptions")

    cursor.execute("SELECT COUNT(*) FROM tariff_overlays")
    print(f"  Program metadata:   {cursor.fetchone()[0]} programs")

    cursor.execute("SELECT COUNT(*) FROM rule_changes_log")
    print(f"  Audit log entries:  {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM monitor_alerts")
    print(f"  Monitor alerts:     {cursor.fetchone()[0]}")

    # Verify IEEPA data integrity - test China rates
    cursor.execute("""
        SELECT country_code, effective_date, rate, csms_reference
        FROM ieepa_country_rates
        WHERE country_code = 'CN'
        ORDER BY effective_date
    """)
    cn_rates = cursor.fetchall()
    print(f"\n  China IEEPA timeline ({len(cn_rates)} entries):")
    for r in cn_rates:
        print(f"    {r[1]}: {r[2]}% (CSMS {r[3]})")

    conn.close()


def run_migration():
    """Run the full migration"""
    print("=== US TARIFF CALCULATOR - ADMIN DATABASE MIGRATION ===\n")

    print("Step 1: Creating admin tables...")
    create_admin_tables()

    print("\nStep 2: Adding columns to hts_overlay_mappings...")
    add_overlay_columns()

    print("\nStep 3: Migrating IEEPA rates to database...")
    migrate_ieepa_rates()

    print("\nStep 4: Migrating Annex II exceptions...")
    migrate_annex_exceptions()

    print("\nStep 5: Populating program metadata...")
    populate_program_metadata()

    verify_migration()

    print("\n=== MIGRATION COMPLETE ===")


if __name__ == "__main__":
    run_migration()
