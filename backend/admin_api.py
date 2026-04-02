"""
US Tariff Calculator - Admin API
CRUD endpoints for managing tariff rules, IEEPA rates, overlays, and audit log.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import sqlite3
import os
import json
from datetime import datetime

from admin_models import (
    IEEPARateCreate, IEEPARateUpdate, IEEPARateResponse, IEEPACountrySummary,
    OverlayCreate, OverlayUpdate, OverlayResponse, PaginatedOverlays, ProgramSummary,
    AnnexExceptionCreate, AnnexExceptionResponse,
    AuditLogEntry, AdminStats,
    RulePromptRequest, RuleChangePreview, RuleChangeConfirm, RuleChange,
    MonitorAlertResponse, MonitorAlertUpdate, MonitorConfig,
)

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "us_tariff_calculator.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def log_change(conn, action: str, table_name: str, record_id: int = None,
               field_name: str = None, old_value: str = None, new_value: str = None,
               description: str = None, source: str = 'manual', prompt_text: str = None):
    """Write an entry to the audit log"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO rule_changes_log
        (action, table_name, record_id, field_name, old_value, new_value, change_description, source, prompt_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (action, table_name, record_id, field_name, old_value, new_value, description, source, prompt_text))


# ============================================================
# DASHBOARD STATS
# ============================================================

@admin_router.get("/stats", response_model=AdminStats)
def get_admin_stats():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tariff_overlays")
    total_programs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM hts_overlay_mappings")
    total_overlays = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM hts_overlay_mappings WHERE is_active = 1")
    active_overlays = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ieepa_country_rates WHERE is_active = 1")
    total_ieepa = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT country_code) FROM ieepa_country_rates WHERE is_active = 1")
    total_ieepa_countries = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ieepa_annex_exceptions WHERE exception_type='HTS' AND is_active=1")
    total_annex_hts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ieepa_annex_exceptions WHERE exception_type='COO' AND is_active=1")
    total_annex_coo = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM rule_changes_log WHERE timestamp > datetime('now', '-7 days')")
    recent_changes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM monitor_alerts WHERE status = 'new'")
    pending_alerts = cursor.fetchone()[0]

    conn.close()

    return AdminStats(
        total_programs=total_programs,
        total_overlays=total_overlays,
        active_overlays=active_overlays,
        total_ieepa_entries=total_ieepa,
        total_ieepa_countries=total_ieepa_countries,
        total_annex_hts=total_annex_hts,
        total_annex_coo=total_annex_coo,
        recent_changes=recent_changes,
        pending_alerts=pending_alerts,
    )


# ============================================================
# IEEPA RATES CRUD
# ============================================================

@admin_router.get("/ieepa/rates", response_model=List[IEEPARateResponse])
def list_ieepa_rates(
    country: Optional[str] = None,
    active_only: bool = True,
):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM ieepa_country_rates WHERE 1=1"
    params = []

    if active_only:
        query += " AND is_active = 1"
    if country:
        query += " AND country_code = ?"
        params.append(country.upper())

    query += " ORDER BY country_code, effective_date"
    cursor.execute(query, params)

    rows = cursor.fetchall()
    conn.close()
    return [IEEPARateResponse(**dict(r)) for r in rows]


@admin_router.get("/ieepa/countries", response_model=List[IEEPACountrySummary])
def list_ieepa_countries():
    """List all IEEPA countries with their current effective rate"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT country_code, COUNT(*) as total_entries
        FROM ieepa_country_rates
        WHERE is_active = 1
        GROUP BY country_code
        ORDER BY country_code
    """)
    countries = cursor.fetchall()

    results = []
    for row in countries:
        cc = row['country_code']
        # Get most recent rate for this country
        cursor.execute("""
            SELECT rate, effective_date, csms_reference
            FROM ieepa_country_rates
            WHERE country_code = ? AND is_active = 1
            ORDER BY effective_date DESC
            LIMIT 1
        """, (cc,))
        latest = cursor.fetchone()

        results.append(IEEPACountrySummary(
            country_code=cc,
            current_rate=latest['rate'] if latest else 0.0,
            effective_date=latest['effective_date'] if latest else '',
            total_entries=row['total_entries'],
            csms_reference=latest['csms_reference'] if latest else None,
        ))

    conn.close()
    return results


@admin_router.get("/ieepa/rates/{rate_id}", response_model=IEEPARateResponse)
def get_ieepa_rate(rate_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ieepa_country_rates WHERE id = ?", (rate_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="IEEPA rate not found")
    return IEEPARateResponse(**dict(row))


@admin_router.post("/ieepa/rates", response_model=IEEPARateResponse)
def create_ieepa_rate(data: IEEPARateCreate):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO ieepa_country_rates
        (country_code, effective_date, rate, csms_reference, chapter99_code, notes, created_by)
        VALUES (?, ?, ?, ?, ?, ?, 'admin')
    """, (data.country_code.upper(), data.effective_date, data.rate,
          data.csms_reference, data.chapter99_code, data.notes))

    new_id = cursor.lastrowid

    log_change(conn, 'CREATE', 'ieepa_country_rates', new_id,
               description=f"Created IEEPA rate: {data.country_code} at {data.rate}% effective {data.effective_date}")

    conn.commit()

    cursor.execute("SELECT * FROM ieepa_country_rates WHERE id = ?", (new_id,))
    row = cursor.fetchone()
    conn.close()
    return IEEPARateResponse(**dict(row))


@admin_router.put("/ieepa/rates/{rate_id}", response_model=IEEPARateResponse)
def update_ieepa_rate(rate_id: int, data: IEEPARateUpdate):
    conn = get_db()
    cursor = conn.cursor()

    # Get current values
    cursor.execute("SELECT * FROM ieepa_country_rates WHERE id = ?", (rate_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="IEEPA rate not found")

    existing_dict = dict(existing)

    # Build dynamic update
    updates = {}
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            updates[field] = value

    if not updates:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")

    updates['updated_at'] = datetime.now().isoformat()

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [rate_id]

    cursor.execute(f"UPDATE ieepa_country_rates SET {set_clause} WHERE id = ?", values)

    # Audit log
    for field, new_val in updates.items():
        if field != 'updated_at':
            old_val = existing_dict.get(field)
            if str(old_val) != str(new_val):
                log_change(conn, 'UPDATE', 'ieepa_country_rates', rate_id,
                           field_name=field, old_value=str(old_val), new_value=str(new_val),
                           description=f"Updated {field}: {old_val} -> {new_val}")

    conn.commit()

    cursor.execute("SELECT * FROM ieepa_country_rates WHERE id = ?", (rate_id,))
    row = cursor.fetchone()
    conn.close()
    return IEEPARateResponse(**dict(row))


@admin_router.delete("/ieepa/rates/{rate_id}")
def deactivate_ieepa_rate(rate_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ieepa_country_rates WHERE id = ?", (rate_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="IEEPA rate not found")

    cursor.execute("""
        UPDATE ieepa_country_rates
        SET is_active = 0, updated_at = datetime('now')
        WHERE id = ?
    """, (rate_id,))

    log_change(conn, 'DEACTIVATE', 'ieepa_country_rates', rate_id,
               description=f"Deactivated IEEPA rate: {existing['country_code']} {existing['rate']}% ({existing['effective_date']})")

    conn.commit()
    conn.close()
    return {"status": "deactivated", "id": rate_id}


# ============================================================
# OVERLAY MAPPINGS CRUD
# ============================================================

@admin_router.get("/overlays", response_model=PaginatedOverlays)
def list_overlays(
    program: Optional[str] = None,
    hts: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    active_only: bool = True,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    conn = get_db()
    cursor = conn.cursor()

    where_clauses = []
    params = []

    if active_only:
        where_clauses.append("is_active = 1")
    if program:
        where_clauses.append("program_name LIKE ?")
        params.append(f"%{program}%")
    if hts:
        hts_normalized = hts.replace('.', '').replace('-', '').replace(' ', '')
        where_clauses.append("hts_code LIKE ?")
        params.append(f"{hts_normalized}%")
    if jurisdiction:
        where_clauses.append("(jurisdiction = ? OR jurisdiction = 'GLOBAL')")
        params.append(jurisdiction.upper())

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Count total
    cursor.execute(f"SELECT COUNT(*) FROM hts_overlay_mappings WHERE {where_sql}", params)
    total = cursor.fetchone()[0]

    # Get page
    offset = (page - 1) * per_page
    cursor.execute(
        f"SELECT * FROM hts_overlay_mappings WHERE {where_sql} ORDER BY program_name, hts_code LIMIT ? OFFSET ?",
        params + [per_page, offset]
    )
    rows = cursor.fetchall()
    conn.close()

    pages = (total + per_page - 1) // per_page

    return PaginatedOverlays(
        items=[OverlayResponse(**dict(r)) for r in rows],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@admin_router.get("/overlays/programs", response_model=List[ProgramSummary])
def list_overlay_programs():
    """List distinct programs with counts and metadata"""
    conn = get_db()
    cursor = conn.cursor()

    # Get overlay counts by program
    cursor.execute("""
        SELECT program_name, COUNT(*) as overlay_count
        FROM hts_overlay_mappings
        WHERE is_active = 1
        GROUP BY program_name
        ORDER BY program_name
    """)
    overlay_counts = {row['program_name']: row['overlay_count'] for row in cursor.fetchall()}

    # Get program metadata
    cursor.execute("SELECT * FROM tariff_overlays ORDER BY program_name")
    programs = cursor.fetchall()

    conn.close()

    results = []
    for p in programs:
        pname = p['program_name']
        results.append(ProgramSummary(
            program_name=pname,
            overlay_count=overlay_counts.get(pname, 0),
            jurisdiction=p['jurisdiction'],
            material_basis=p['material_basis'],
            duty_rate=p['duty_rate'],
            implementation_date=p['implementation_date'],
            notes=p['notes'],
        ))

    return results


@admin_router.get("/overlays/{overlay_id}", response_model=OverlayResponse)
def get_overlay(overlay_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hts_overlay_mappings WHERE id = ?", (overlay_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Overlay not found")
    return OverlayResponse(**dict(row))


@admin_router.post("/overlays", response_model=OverlayResponse)
def create_overlay(data: OverlayCreate):
    conn = get_db()
    cursor = conn.cursor()

    hts_normalized = data.hts_code.replace('.', '').replace('-', '').replace(' ', '')

    cursor.execute("""
        INSERT INTO hts_overlay_mappings
        (hts_code, program_name, duty_rate, jurisdiction, effective_date, chapter99_code, tariff_basis,
         is_active, created_at, updated_at, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'), 'admin')
    """, (hts_normalized, data.program_name, data.duty_rate, data.jurisdiction,
          data.effective_date, data.chapter99_code, data.tariff_basis))

    new_id = cursor.lastrowid

    log_change(conn, 'CREATE', 'hts_overlay_mappings', new_id,
               description=f"Created overlay: {data.program_name} for HTS {hts_normalized} at {data.duty_rate}%")

    conn.commit()

    cursor.execute("SELECT * FROM hts_overlay_mappings WHERE id = ?", (new_id,))
    row = cursor.fetchone()
    conn.close()
    return OverlayResponse(**dict(row))


@admin_router.put("/overlays/{overlay_id}", response_model=OverlayResponse)
def update_overlay(overlay_id: int, data: OverlayUpdate):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM hts_overlay_mappings WHERE id = ?", (overlay_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Overlay not found")

    existing_dict = dict(existing)

    updates = {}
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if field == 'hts_code':
                value = value.replace('.', '').replace('-', '').replace(' ', '')
            updates[field] = value

    if not updates:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")

    updates['updated_at'] = datetime.now().isoformat()

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [overlay_id]

    cursor.execute(f"UPDATE hts_overlay_mappings SET {set_clause} WHERE id = ?", values)

    for field, new_val in updates.items():
        if field != 'updated_at':
            old_val = existing_dict.get(field)
            if str(old_val) != str(new_val):
                log_change(conn, 'UPDATE', 'hts_overlay_mappings', overlay_id,
                           field_name=field, old_value=str(old_val), new_value=str(new_val),
                           description=f"Updated overlay {overlay_id} {field}: {old_val} -> {new_val}")

    conn.commit()

    cursor.execute("SELECT * FROM hts_overlay_mappings WHERE id = ?", (overlay_id,))
    row = cursor.fetchone()
    conn.close()
    return OverlayResponse(**dict(row))


@admin_router.delete("/overlays/{overlay_id}")
def deactivate_overlay(overlay_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM hts_overlay_mappings WHERE id = ?", (overlay_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Overlay not found")

    cursor.execute("""
        UPDATE hts_overlay_mappings
        SET is_active = 0, updated_at = datetime('now')
        WHERE id = ?
    """, (overlay_id,))

    log_change(conn, 'DEACTIVATE', 'hts_overlay_mappings', overlay_id,
               description=f"Deactivated overlay: {existing['program_name']} HTS {existing['hts_code']}")

    conn.commit()
    conn.close()
    return {"status": "deactivated", "id": overlay_id}


# ============================================================
# ANNEX II EXCEPTIONS
# ============================================================

@admin_router.get("/annex-exceptions", response_model=List[AnnexExceptionResponse])
def list_annex_exceptions(
    exception_type: Optional[str] = None,
    active_only: bool = True,
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
):
    conn = get_db()
    cursor = conn.cursor()

    where_clauses = []
    params = []

    if active_only:
        where_clauses.append("is_active = 1")
    if exception_type:
        where_clauses.append("exception_type = ?")
        params.append(exception_type.upper())

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    offset = (page - 1) * per_page

    cursor.execute(
        f"SELECT * FROM ieepa_annex_exceptions WHERE {where_sql} ORDER BY exception_type, value LIMIT ? OFFSET ?",
        params + [per_page, offset]
    )
    rows = cursor.fetchall()
    conn.close()
    return [AnnexExceptionResponse(**dict(r)) for r in rows]


@admin_router.post("/annex-exceptions", response_model=AnnexExceptionResponse)
def create_annex_exception(data: AnnexExceptionCreate):
    conn = get_db()
    cursor = conn.cursor()

    value = data.value.upper().replace('.', '').replace('-', '').replace(' ', '') if data.exception_type == 'HTS' else data.value.upper()

    cursor.execute("""
        INSERT INTO ieepa_annex_exceptions (exception_type, value, source, created_by)
        VALUES (?, ?, ?, 'admin')
    """, (data.exception_type.upper(), value, data.source))

    new_id = cursor.lastrowid
    log_change(conn, 'CREATE', 'ieepa_annex_exceptions', new_id,
               description=f"Created Annex exception: {data.exception_type} = {value}")
    conn.commit()

    cursor.execute("SELECT * FROM ieepa_annex_exceptions WHERE id = ?", (new_id,))
    row = cursor.fetchone()
    conn.close()
    return AnnexExceptionResponse(**dict(row))


@admin_router.delete("/annex-exceptions/{exception_id}")
def deactivate_annex_exception(exception_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ieepa_annex_exceptions WHERE id = ?", (exception_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Exception not found")

    cursor.execute("UPDATE ieepa_annex_exceptions SET is_active = 0 WHERE id = ?", (exception_id,))
    log_change(conn, 'DEACTIVATE', 'ieepa_annex_exceptions', exception_id,
               description=f"Deactivated Annex exception: {existing['exception_type']} = {existing['value']}")
    conn.commit()
    conn.close()
    return {"status": "deactivated", "id": exception_id}


# ============================================================
# AUDIT LOG
# ============================================================

@admin_router.get("/audit-log", response_model=List[AuditLogEntry])
def list_audit_log(
    table_name: Optional[str] = None,
    action: Optional[str] = None,
    source: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    conn = get_db()
    cursor = conn.cursor()

    where_clauses = []
    params = []

    if table_name:
        where_clauses.append("table_name = ?")
        params.append(table_name)
    if action:
        where_clauses.append("action = ?")
        params.append(action)
    if source:
        where_clauses.append("source = ?")
        params.append(source)
    if from_date:
        where_clauses.append("timestamp >= ?")
        params.append(from_date)
    if to_date:
        where_clauses.append("timestamp <= ?")
        params.append(to_date)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    cursor.execute(
        f"SELECT * FROM rule_changes_log WHERE {where_sql} ORDER BY timestamp DESC LIMIT ?",
        params + [limit]
    )
    rows = cursor.fetchall()
    conn.close()
    return [AuditLogEntry(**dict(r)) for r in rows]


# ============================================================
# AI RULE PROMPT
# ============================================================

@admin_router.post("/parse-rule-prompt", response_model=RuleChangePreview)
def parse_rule_prompt(request: RulePromptRequest):
    """Parse a natural language rule change description into structured changes"""
    from rule_parser import parse_rule_prompt as parse_prompt
    result = parse_prompt(request.prompt)
    return RuleChangePreview(**result)


@admin_router.post("/apply-rule-changes")
def apply_rule_changes(request: RuleChangeConfirm):
    """Apply confirmed rule changes to the database"""
    conn = get_db()
    cursor = conn.cursor()

    applied = []

    for change in request.changes:
        try:
            if change.table == 'ieepa_country_rates':
                if change.action == 'CREATE':
                    cursor.execute("""
                        INSERT INTO ieepa_country_rates
                        (country_code, effective_date, rate, csms_reference, chapter99_code, notes, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, 'ai_prompt')
                    """, (
                        change.values.get('country_code', ''),
                        change.values.get('effective_date', ''),
                        change.values.get('rate', 0),
                        change.values.get('csms_reference'),
                        change.values.get('chapter99_code'),
                        change.values.get('notes'),
                    ))
                    record_id = cursor.lastrowid
                    log_change(conn, 'CREATE', 'ieepa_country_rates', record_id,
                               description=change.description, source='ai_prompt', prompt_text=request.prompt_text)
                    applied.append({"action": "CREATE", "table": "ieepa_country_rates", "id": record_id})

                elif change.action == 'UPDATE' and change.filters:
                    # Build update
                    set_parts = []
                    set_values = []
                    for k, v in change.values.items():
                        set_parts.append(f"{k} = ?")
                        set_values.append(v)
                    set_parts.append("updated_at = datetime('now')")

                    where_parts = []
                    where_values = []
                    for k, v in change.filters.items():
                        where_parts.append(f"{k} = ?")
                        where_values.append(v)

                    cursor.execute(
                        f"UPDATE ieepa_country_rates SET {', '.join(set_parts)} WHERE {' AND '.join(where_parts)}",
                        set_values + where_values
                    )
                    log_change(conn, 'UPDATE', 'ieepa_country_rates',
                               description=change.description, source='ai_prompt', prompt_text=request.prompt_text)
                    applied.append({"action": "UPDATE", "table": "ieepa_country_rates", "rows": cursor.rowcount})

                elif change.action == 'DEACTIVATE' and change.filters:
                    where_parts = []
                    where_values = []
                    for k, v in change.filters.items():
                        where_parts.append(f"{k} = ?")
                        where_values.append(v)

                    cursor.execute(
                        f"UPDATE ieepa_country_rates SET is_active = 0, updated_at = datetime('now') WHERE {' AND '.join(where_parts)}",
                        where_values
                    )
                    log_change(conn, 'DEACTIVATE', 'ieepa_country_rates',
                               description=change.description, source='ai_prompt', prompt_text=request.prompt_text)
                    applied.append({"action": "DEACTIVATE", "table": "ieepa_country_rates", "rows": cursor.rowcount})

            elif change.table == 'hts_overlay_mappings':
                if change.action == 'CREATE':
                    hts_code = change.values.get('hts_code', '').replace('.', '').replace('-', '')
                    cursor.execute("""
                        INSERT INTO hts_overlay_mappings
                        (hts_code, program_name, duty_rate, jurisdiction, effective_date, chapter99_code, tariff_basis,
                         is_active, created_at, updated_at, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'), 'ai_prompt')
                    """, (
                        hts_code,
                        change.values.get('program_name', ''),
                        change.values.get('duty_rate', 0),
                        change.values.get('jurisdiction', 'GLOBAL'),
                        change.values.get('effective_date', ''),
                        change.values.get('chapter99_code'),
                        change.values.get('tariff_basis'),
                    ))
                    record_id = cursor.lastrowid
                    log_change(conn, 'CREATE', 'hts_overlay_mappings', record_id,
                               description=change.description, source='ai_prompt', prompt_text=request.prompt_text)
                    applied.append({"action": "CREATE", "table": "hts_overlay_mappings", "id": record_id})

                elif change.action == 'DEACTIVATE' and change.filters:
                    where_parts = []
                    where_values = []
                    for k, v in change.filters.items():
                        if k == 'hts_code':
                            v = v.replace('.', '').replace('-', '')
                        where_parts.append(f"{k} = ?")
                        where_values.append(v)

                    cursor.execute(
                        f"UPDATE hts_overlay_mappings SET is_active = 0, updated_at = datetime('now') WHERE {' AND '.join(where_parts)}",
                        where_values
                    )
                    log_change(conn, 'DEACTIVATE', 'hts_overlay_mappings',
                               description=change.description, source='ai_prompt', prompt_text=request.prompt_text)
                    applied.append({"action": "DEACTIVATE", "table": "hts_overlay_mappings", "rows": cursor.rowcount})

        except Exception as e:
            applied.append({"action": change.action, "table": change.table, "error": str(e)})

    conn.commit()
    conn.close()

    return {
        "status": "applied",
        "changes_applied": len([a for a in applied if 'error' not in a]),
        "changes_failed": len([a for a in applied if 'error' in a]),
        "details": applied,
    }


# ============================================================
# MONITOR ALERTS
# ============================================================

@admin_router.get("/monitor/alerts", response_model=List[MonitorAlertResponse])
def list_monitor_alerts(
    status: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    conn = get_db()
    cursor = conn.cursor()

    where_clauses = []
    params = []

    if status:
        where_clauses.append("status = ?")
        params.append(status)
    if source:
        where_clauses.append("source = ?")
        params.append(source)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    cursor.execute(
        f"SELECT * FROM monitor_alerts WHERE {where_sql} ORDER BY created_at DESC LIMIT ?",
        params + [limit]
    )
    rows = cursor.fetchall()
    conn.close()
    return [MonitorAlertResponse(**dict(r)) for r in rows]


@admin_router.put("/monitor/alerts/{alert_id}", response_model=MonitorAlertResponse)
def update_monitor_alert(alert_id: int, data: MonitorAlertUpdate):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM monitor_alerts WHERE id = ?", (alert_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Alert not found")

    updates = {}
    if data.status:
        updates['status'] = data.status
    if data.reviewed_by:
        updates['reviewed_by'] = data.reviewed_by
    if data.status in ('reviewed', 'applied', 'dismissed'):
        updates['reviewed_at'] = datetime.now().isoformat()

    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [alert_id]
        cursor.execute(f"UPDATE monitor_alerts SET {set_clause} WHERE id = ?", values)
        conn.commit()

    cursor.execute("SELECT * FROM monitor_alerts WHERE id = ?", (alert_id,))
    row = cursor.fetchone()
    conn.close()
    return MonitorAlertResponse(**dict(row))


@admin_router.post("/monitor/check-now")
def trigger_monitor_check():
    """Trigger an immediate check for new CSMS/Federal Register notices"""
    try:
        from monitor import run_check
        results = run_check()
        return {"status": "completed", "results": results}
    except ImportError:
        return {"status": "error", "message": "Monitor module not yet available"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
