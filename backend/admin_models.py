"""
US Tariff Calculator - Admin API Models
Pydantic models for admin CRUD operations
"""

from pydantic import BaseModel
from typing import Optional, List, Dict


# === IEEPA Rate Models ===

class IEEPARateCreate(BaseModel):
    country_code: str
    effective_date: str
    rate: float
    csms_reference: Optional[str] = None
    chapter99_code: Optional[str] = None
    notes: Optional[str] = None


class IEEPARateUpdate(BaseModel):
    country_code: Optional[str] = None
    effective_date: Optional[str] = None
    rate: Optional[float] = None
    csms_reference: Optional[str] = None
    chapter99_code: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[int] = None


class IEEPARateResponse(BaseModel):
    id: int
    country_code: str
    effective_date: str
    rate: float
    csms_reference: Optional[str] = None
    chapter99_code: Optional[str] = None
    notes: Optional[str] = None
    is_active: int = 1
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None


class IEEPACountrySummary(BaseModel):
    country_code: str
    current_rate: float
    effective_date: str
    total_entries: int
    csms_reference: Optional[str] = None


# === Overlay Mapping Models ===

class OverlayCreate(BaseModel):
    hts_code: str
    program_name: str
    duty_rate: float
    jurisdiction: str = 'GLOBAL'
    effective_date: str = ''
    chapter99_code: Optional[str] = None
    tariff_basis: Optional[str] = None


class OverlayUpdate(BaseModel):
    hts_code: Optional[str] = None
    program_name: Optional[str] = None
    duty_rate: Optional[float] = None
    jurisdiction: Optional[str] = None
    effective_date: Optional[str] = None
    chapter99_code: Optional[str] = None
    tariff_basis: Optional[str] = None
    is_active: Optional[int] = None


class OverlayResponse(BaseModel):
    id: int
    hts_code: str
    program_name: str
    duty_rate: Optional[float] = None
    jurisdiction: Optional[str] = None
    effective_date: Optional[str] = None
    chapter99_code: Optional[str] = None
    tariff_basis: Optional[str] = None
    is_active: int = 1
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None


class PaginatedOverlays(BaseModel):
    items: List[OverlayResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ProgramSummary(BaseModel):
    program_name: str
    overlay_count: int
    jurisdiction: Optional[str] = None
    material_basis: Optional[str] = None
    duty_rate: Optional[float] = None
    implementation_date: Optional[str] = None
    notes: Optional[str] = None


# === Annex Exception Models ===

class AnnexExceptionCreate(BaseModel):
    exception_type: str  # 'HTS' or 'COO'
    value: str
    source: Optional[str] = None


class AnnexExceptionResponse(BaseModel):
    id: int
    exception_type: str
    value: str
    source: Optional[str] = None
    is_active: int = 1
    created_at: Optional[str] = None


# === Audit Log Models ===

class AuditLogEntry(BaseModel):
    id: int
    timestamp: str
    user_id: str
    action: str
    table_name: str
    record_id: Optional[int] = None
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_description: Optional[str] = None
    source: Optional[str] = None
    prompt_text: Optional[str] = None


# === AI Rule Prompt Models ===

class RulePromptRequest(BaseModel):
    prompt: str


class RuleChange(BaseModel):
    action: str  # CREATE, UPDATE, DEACTIVATE
    table: str   # ieepa_country_rates, hts_overlay_mappings, ieepa_annex_exceptions
    values: Dict
    filters: Optional[Dict] = None
    description: str


class RuleChangePreview(BaseModel):
    changes: List[RuleChange]
    summary: str
    warnings: List[str]
    confidence: int
    prompt_text: str


class RuleChangeConfirm(BaseModel):
    changes: List[RuleChange]
    prompt_text: str


# === Dashboard Stats ===

class AdminStats(BaseModel):
    total_programs: int
    total_overlays: int
    active_overlays: int
    total_ieepa_entries: int
    total_ieepa_countries: int
    total_annex_hts: int
    total_annex_coo: int
    recent_changes: int
    pending_alerts: int


# === Monitor Alert Models ===

class MonitorAlertResponse(BaseModel):
    id: int
    source: str
    reference_number: Optional[str] = None
    title: Optional[str] = None
    published_date: Optional[str] = None
    summary: Optional[str] = None
    relevance_score: float = 0.0
    status: str = 'new'
    suggested_changes: Optional[str] = None
    created_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None


class MonitorAlertUpdate(BaseModel):
    status: Optional[str] = None  # 'new', 'reviewed', 'applied', 'dismissed'
    reviewed_by: Optional[str] = None


class MonitorConfig(BaseModel):
    enabled: bool = True
    check_interval_hours: int = 4
    keywords: List[str] = [
        'IEEPA', 'Section 232', 'Section 301', 'reciprocal',
        'tariff', 'duty rate', 'Chapter 99', 'HTS'
    ]
