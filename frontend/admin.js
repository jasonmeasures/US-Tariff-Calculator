/**
 * US Tariff Calculator - Admin Panel JavaScript
 * Handles tabs, CRUD operations, AI prompt, audit log, and alerts.
 */

const API_BASE = 'http://localhost:8000';

// State
let currentOverlayPage = 1;
let overlayPerPage = 50;
let currentPreview = null;
let programsList = [];

// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadStats();
    loadIEEPARates();
    loadPrograms();
    loadAuditLog();
    loadAlerts();

    // Filter listeners
    document.getElementById('ieepa-country-filter').addEventListener('change', loadIEEPARates);
    document.getElementById('overlay-program-filter').addEventListener('change', () => { currentOverlayPage = 1; loadOverlays(); });
    document.getElementById('overlay-hts-search').addEventListener('input', debounce(() => { currentOverlayPage = 1; loadOverlays(); }, 400));
    document.getElementById('overlay-jurisdiction-filter').addEventListener('change', () => { currentOverlayPage = 1; loadOverlays(); });
    document.getElementById('audit-table-filter').addEventListener('change', loadAuditLog);
    document.getElementById('audit-source-filter').addEventListener('change', loadAuditLog);
    document.getElementById('alert-status-filter').addEventListener('change', loadAlerts);
});

function debounce(fn, ms) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

// ============================================================
// TABS
// ============================================================

function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;

            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(`tab-${tabId}`).classList.add('active');

            // Lazy load overlays on first tab switch
            if (tabId === 'overlays' && document.getElementById('overlay-tbody').querySelector('.loading')) {
                loadOverlays();
            }
        });
    });
}

// ============================================================
// DASHBOARD STATS
// ============================================================

async function loadStats() {
    try {
        const res = await fetch(`${API_BASE}/api/admin/stats`);
        const data = await res.json();

        document.getElementById('stat-programs').textContent = data.total_programs;
        document.getElementById('stat-overlays').textContent = data.active_overlays.toLocaleString();
        document.getElementById('stat-ieepa').textContent = data.total_ieepa_entries;
        document.getElementById('stat-countries').textContent = data.total_ieepa_countries;
        document.getElementById('stat-changes').textContent = data.recent_changes;
        document.getElementById('stat-alerts').textContent = data.pending_alerts;

        if (data.pending_alerts > 0) {
            const badge = document.getElementById('alert-badge');
            badge.textContent = data.pending_alerts;
            badge.style.display = 'inline';
        }
    } catch (e) {
        console.error('Failed to load stats:', e);
    }
}

// ============================================================
// IEEPA RATES
// ============================================================

async function loadIEEPARates() {
    const tbody = document.getElementById('ieepa-tbody');
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Loading IEEPA rates</td></tr>';

    const country = document.getElementById('ieepa-country-filter').value;
    let url = `${API_BASE}/api/admin/ieepa/rates?active_only=false`;
    if (country) url += `&country=${country}`;

    try {
        const res = await fetch(url);
        const rates = await res.json();

        // Populate country filter (once)
        const filter = document.getElementById('ieepa-country-filter');
        if (filter.options.length <= 1) {
            const countries = [...new Set(rates.map(r => r.country_code))].sort();
            countries.forEach(cc => {
                const opt = document.createElement('option');
                opt.value = cc;
                opt.textContent = cc;
                filter.appendChild(opt);
            });
        }

        if (rates.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No IEEPA rates found</td></tr>';
            return;
        }

        // Group by country
        const grouped = {};
        rates.forEach(r => {
            if (!grouped[r.country_code]) grouped[r.country_code] = [];
            grouped[r.country_code].push(r);
        });

        let html = '';
        for (const [cc, group] of Object.entries(grouped).sort()) {
            // Sort by date desc
            group.sort((a, b) => b.effective_date.localeCompare(a.effective_date));

            html += `<tr class="country-group-header"><td colspan="7">${cc} (${group.length} entries)</td></tr>`;

            group.forEach(r => {
                const statusClass = r.is_active ? 'status-active' : 'status-inactive';
                const statusText = r.is_active ? 'Active' : 'Inactive';
                html += `
                    <tr id="ieepa-row-${r.id}" data-id="${r.id}">
                        <td class="country-cell">${r.country_code}</td>
                        <td>${r.effective_date}</td>
                        <td class="rate-cell">${r.rate}%</td>
                        <td>${r.csms_reference || '-'}</td>
                        <td>${r.chapter99_code || '-'}</td>
                        <td class="${statusClass}">${statusText}</td>
                        <td>
                            <button class="btn-sm btn-edit" onclick="editIEEPARow(${r.id})">Edit</button>
                            ${r.is_active ? `<button class="btn-sm btn-deactivate" onclick="deactivateIEEPA(${r.id})">Deactivate</button>` : ''}
                        </td>
                    </tr>
                `;
            });
        }

        tbody.innerHTML = html;
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Error loading: ${e.message}</td></tr>`;
    }
}

function editIEEPARow(id) {
    const row = document.getElementById(`ieepa-row-${id}`);
    const cells = row.querySelectorAll('td');

    const country = cells[0].textContent;
    const date = cells[1].textContent;
    const rate = cells[2].textContent.replace('%', '');
    const csms = cells[3].textContent === '-' ? '' : cells[3].textContent;
    const ch99 = cells[4].textContent === '-' ? '' : cells[4].textContent;

    cells[1].innerHTML = `<input type="date" value="${date}" class="inline-edit">`;
    cells[2].innerHTML = `<input type="number" value="${rate}" step="0.1" style="width:70px" class="inline-edit">`;
    cells[3].innerHTML = `<input type="text" value="${csms}" style="width:90px" class="inline-edit">`;
    cells[4].innerHTML = `<input type="text" value="${ch99}" style="width:90px" class="inline-edit">`;
    cells[6].innerHTML = `
        <button class="btn-sm btn-save" onclick="saveIEEPARow(${id})">Save</button>
        <button class="btn-sm btn-cancel" onclick="loadIEEPARates()">Cancel</button>
    `;
}

async function saveIEEPARow(id) {
    const row = document.getElementById(`ieepa-row-${id}`);
    const inputs = row.querySelectorAll('input');

    const data = {
        effective_date: inputs[0].value,
        rate: parseFloat(inputs[1].value),
        csms_reference: inputs[2].value || null,
        chapter99_code: inputs[3].value || null,
    };

    try {
        const res = await fetch(`${API_BASE}/api/admin/ieepa/rates/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (res.ok) {
            showToast('IEEPA rate updated', 'success');
            loadIEEPARates();
            loadStats();
            loadAuditLog();
        } else {
            const err = await res.json();
            showToast(`Error: ${err.detail}`, 'error');
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

async function deactivateIEEPA(id) {
    if (!confirm('Deactivate this IEEPA rate? The calculator will no longer use it.')) return;

    try {
        const res = await fetch(`${API_BASE}/api/admin/ieepa/rates/${id}`, { method: 'DELETE' });
        if (res.ok) {
            showToast('IEEPA rate deactivated', 'success');
            loadIEEPARates();
            loadStats();
            loadAuditLog();
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

function showAddIEEPAModal() {
    document.getElementById('modal-add-ieepa').classList.add('active');
}

async function submitNewIEEPA() {
    const data = {
        country_code: document.getElementById('new-ieepa-country').value.toUpperCase(),
        effective_date: document.getElementById('new-ieepa-date').value,
        rate: parseFloat(document.getElementById('new-ieepa-rate').value),
        csms_reference: document.getElementById('new-ieepa-csms').value || null,
        chapter99_code: document.getElementById('new-ieepa-ch99').value || null,
        notes: document.getElementById('new-ieepa-notes').value || null,
    };

    if (!data.country_code || !data.effective_date || isNaN(data.rate)) {
        showToast('Please fill in Country, Date, and Rate', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/admin/ieepa/rates`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (res.ok) {
            showToast('IEEPA rate created', 'success');
            closeModal('modal-add-ieepa');
            loadIEEPARates();
            loadStats();
            loadAuditLog();
        } else {
            const err = await res.json();
            showToast(`Error: ${err.detail}`, 'error');
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

// ============================================================
// OVERLAY MAPPINGS
// ============================================================

async function loadOverlays() {
    const tbody = document.getElementById('overlay-tbody');
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Loading overlays</td></tr>';

    const program = document.getElementById('overlay-program-filter').value;
    const hts = document.getElementById('overlay-hts-search').value;
    const jurisdiction = document.getElementById('overlay-jurisdiction-filter').value;

    let url = `${API_BASE}/api/admin/overlays?page=${currentOverlayPage}&per_page=${overlayPerPage}`;
    if (program) url += `&program=${encodeURIComponent(program)}`;
    if (hts) url += `&hts=${encodeURIComponent(hts)}`;
    if (jurisdiction) url += `&jurisdiction=${encodeURIComponent(jurisdiction)}`;

    try {
        const res = await fetch(url);
        const data = await res.json();

        // Populate program filter (once)
        const filter = document.getElementById('overlay-program-filter');
        if (filter.options.length <= 1 && programsList.length > 0) {
            programsList.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.program_name;
                opt.textContent = `${p.program_name} (${p.overlay_count})`;
                filter.appendChild(opt);
            });
        }

        if (data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No overlays found</td></tr>';
            document.getElementById('overlay-pagination').innerHTML = '';
            return;
        }

        let html = '';
        data.items.forEach(o => {
            const htsFmt = formatHTS(o.hts_code);
            html += `
                <tr id="overlay-row-${o.id}">
                    <td style="font-family:monospace">${htsFmt}</td>
                    <td>${o.program_name}</td>
                    <td class="rate-cell">${o.duty_rate != null ? o.duty_rate + '%' : '-'}</td>
                    <td>${o.jurisdiction || '-'}</td>
                    <td>${o.effective_date || '-'}</td>
                    <td style="font-family:monospace">${o.chapter99_code || '-'}</td>
                    <td>
                        <button class="btn-sm btn-edit" onclick="editOverlayRow(${o.id})">Edit</button>
                        <button class="btn-sm btn-deactivate" onclick="deactivateOverlay(${o.id})">Deactivate</button>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
        renderOverlayPagination(data);
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Error: ${e.message}</td></tr>`;
    }
}

function renderOverlayPagination(data) {
    const container = document.getElementById('overlay-pagination');
    const { page, pages, total } = data;

    let html = `<button ${page <= 1 ? 'disabled' : ''} onclick="goOverlayPage(${page - 1})">&laquo; Prev</button>`;
    html += `<span class="page-info">Page ${page} of ${pages} (${total.toLocaleString()} total)</span>`;
    html += `<button ${page >= pages ? 'disabled' : ''} onclick="goOverlayPage(${page + 1})">Next &raquo;</button>`;
    container.innerHTML = html;
}

function goOverlayPage(page) {
    currentOverlayPage = page;
    loadOverlays();
}

function editOverlayRow(id) {
    const row = document.getElementById(`overlay-row-${id}`);
    const cells = row.querySelectorAll('td');

    const rate = cells[2].textContent.replace('%', '');
    const jurisdiction = cells[3].textContent === '-' ? '' : cells[3].textContent;
    const effectiveDate = cells[4].textContent === '-' ? '' : cells[4].textContent;
    const ch99 = cells[5].textContent === '-' ? '' : cells[5].textContent;

    cells[2].innerHTML = `<input type="number" value="${rate}" step="0.1" style="width:70px" class="inline-edit">`;
    cells[3].innerHTML = `<input type="text" value="${jurisdiction}" style="width:70px" class="inline-edit">`;
    cells[4].innerHTML = `<input type="date" value="${effectiveDate}" class="inline-edit">`;
    cells[5].innerHTML = `<input type="text" value="${ch99}" style="width:90px" class="inline-edit">`;
    cells[6].innerHTML = `
        <button class="btn-sm btn-save" onclick="saveOverlayRow(${id})">Save</button>
        <button class="btn-sm btn-cancel" onclick="loadOverlays()">Cancel</button>
    `;
}

async function saveOverlayRow(id) {
    const row = document.getElementById(`overlay-row-${id}`);
    const inputs = row.querySelectorAll('input');

    const data = {
        duty_rate: parseFloat(inputs[0].value),
        jurisdiction: inputs[1].value || null,
        effective_date: inputs[2].value || null,
        chapter99_code: inputs[3].value || null,
    };

    try {
        const res = await fetch(`${API_BASE}/api/admin/overlays/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (res.ok) {
            showToast('Overlay updated', 'success');
            loadOverlays();
            loadStats();
            loadAuditLog();
        } else {
            const err = await res.json();
            showToast(`Error: ${err.detail}`, 'error');
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

async function deactivateOverlay(id) {
    if (!confirm('Deactivate this overlay? It will no longer be used in calculations.')) return;

    try {
        const res = await fetch(`${API_BASE}/api/admin/overlays/${id}`, { method: 'DELETE' });
        if (res.ok) {
            showToast('Overlay deactivated', 'success');
            loadOverlays();
            loadStats();
            loadAuditLog();
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

function showAddOverlayModal() {
    // Populate program dropdown
    const select = document.getElementById('new-overlay-program');
    if (select.options.length <= 1 && programsList.length > 0) {
        programsList.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.program_name;
            opt.textContent = p.program_name;
            select.appendChild(opt);
        });
    }
    document.getElementById('modal-add-overlay').classList.add('active');
}

async function submitNewOverlay() {
    const data = {
        hts_code: document.getElementById('new-overlay-hts').value,
        program_name: document.getElementById('new-overlay-program').value,
        duty_rate: parseFloat(document.getElementById('new-overlay-rate').value),
        jurisdiction: document.getElementById('new-overlay-jurisdiction').value || 'GLOBAL',
        effective_date: document.getElementById('new-overlay-date').value || '',
        chapter99_code: document.getElementById('new-overlay-ch99').value || null,
    };

    if (!data.hts_code || !data.program_name || isNaN(data.duty_rate)) {
        showToast('Please fill in HTS, Program, and Rate', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/admin/overlays`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (res.ok) {
            showToast('Overlay created', 'success');
            closeModal('modal-add-overlay');
            loadOverlays();
            loadStats();
            loadAuditLog();
        } else {
            const err = await res.json();
            showToast(`Error: ${err.detail}`, 'error');
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

// ============================================================
// PROGRAMS
// ============================================================

async function loadPrograms() {
    const grid = document.getElementById('programs-grid');

    try {
        const res = await fetch(`${API_BASE}/api/admin/overlays/programs`);
        programsList = await res.json();

        if (programsList.length === 0) {
            grid.innerHTML = '<div class="empty-state">No programs found</div>';
            return;
        }

        let html = '';
        programsList.forEach(p => {
            const rateText = p.duty_rate != null ? `${p.duty_rate}%` : 'Variable';
            const materialBadge = p.material_basis
                ? `<span style="display:inline-block;background:#eef2ff;color:#667eea;padding:2px 8px;border-radius:4px;font-size:11px;margin-top:4px;">${p.material_basis}</span>`
                : '';

            html += `
                <div class="stat-card" style="cursor:pointer;text-align:left;padding:18px;" onclick="viewProgramOverlays('${p.program_name.replace(/'/g, "\\'")}')">
                    <div style="font-size:15px;font-weight:600;color:#1e3a5f;margin-bottom:6px;">${p.program_name}</div>
                    <div style="font-size:13px;color:#666;">
                        <div>${p.overlay_count.toLocaleString()} overlays</div>
                        <div>Rate: ${rateText}</div>
                        <div>Jurisdiction: ${p.jurisdiction || '-'}</div>
                        ${materialBadge}
                    </div>
                </div>
            `;
        });

        grid.innerHTML = html;
    } catch (e) {
        grid.innerHTML = `<div class="empty-state">Error: ${e.message}</div>`;
    }
}

function viewProgramOverlays(programName) {
    // Switch to overlays tab with this program filtered
    document.getElementById('overlay-program-filter').value = programName;
    currentOverlayPage = 1;

    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    document.querySelector('[data-tab="overlays"]').classList.add('active');
    document.getElementById('tab-overlays').classList.add('active');

    loadOverlays();
}

// ============================================================
// AI RULE PROMPT
// ============================================================

async function parseRulePrompt() {
    const prompt = document.getElementById('rule-prompt').value.trim();
    if (!prompt) {
        showToast('Enter a rule change description', 'error');
        return;
    }

    const btn = document.getElementById('parse-btn');
    btn.disabled = true;
    btn.textContent = 'Parsing...';

    try {
        const res = await fetch(`${API_BASE}/api/admin/parse-rule-prompt`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt }),
        });

        const preview = await res.json();
        currentPreview = preview;
        renderPreview(preview);
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Parse Changes';
    }
}

function renderPreview(preview) {
    const panel = document.getElementById('preview-panel');
    const changesDiv = document.getElementById('preview-changes');
    const warningsDiv = document.getElementById('preview-warnings');
    const confidenceBadge = document.getElementById('preview-confidence');

    // Confidence
    let confClass = 'confidence-high';
    if (preview.confidence < 70) confClass = 'confidence-low';
    else if (preview.confidence < 85) confClass = 'confidence-medium';
    confidenceBadge.className = `confidence-badge ${confClass}`;
    confidenceBadge.textContent = `${preview.confidence}% confidence`;

    // Changes
    let changesHtml = '';
    if (preview.changes.length === 0) {
        changesHtml = '<div class="empty-state">No changes detected. Try a more specific prompt.</div>';
    } else {
        preview.changes.forEach((c, i) => {
            const values = c.values || {};
            let details = Object.entries(values)
                .filter(([k, v]) => v !== null && k !== 'notes')
                .map(([k, v]) => `<strong>${k}:</strong> ${v}`)
                .join(' &bull; ');

            changesHtml += `
                <div class="change-item">
                    <div class="change-action">${c.action} &rarr; ${c.table}</div>
                    <div class="change-desc">${c.description}</div>
                    <div class="change-detail">${details}</div>
                </div>
            `;
        });
    }
    changesDiv.innerHTML = changesHtml;

    // Warnings
    if (preview.warnings && preview.warnings.length > 0) {
        warningsDiv.innerHTML = preview.warnings.map(w => `<div class="warning-item">${w}</div>`).join('');
        warningsDiv.style.display = 'block';
    } else {
        warningsDiv.style.display = 'none';
    }

    panel.classList.add('active');
}

function cancelPreview() {
    document.getElementById('preview-panel').classList.remove('active');
    currentPreview = null;
}

async function applyRuleChanges() {
    if (!currentPreview || currentPreview.changes.length === 0) {
        showToast('No changes to apply', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/admin/apply-rule-changes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                changes: currentPreview.changes,
                prompt_text: currentPreview.prompt_text,
            }),
        });

        const result = await res.json();

        if (result.changes_applied > 0) {
            showToast(`${result.changes_applied} change(s) applied successfully`, 'success');
            cancelPreview();
            document.getElementById('rule-prompt').value = '';
            loadStats();
            loadIEEPARates();
            loadAuditLog();
        } else {
            showToast('No changes were applied', 'error');
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

// ============================================================
// AUDIT LOG
// ============================================================

async function loadAuditLog() {
    const tbody = document.getElementById('audit-tbody');
    const tableName = document.getElementById('audit-table-filter').value;
    const source = document.getElementById('audit-source-filter').value;

    let url = `${API_BASE}/api/admin/audit-log?limit=100`;
    if (tableName) url += `&table_name=${tableName}`;
    if (source) url += `&source=${source}`;

    try {
        const res = await fetch(url);
        const entries = await res.json();

        if (entries.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No audit entries yet</td></tr>';
            return;
        }

        let html = '';
        entries.forEach(e => {
            const tableLabel = e.table_name.replace(/_/g, ' ');
            const sourceLabel = e.source === 'ai_prompt' ? 'AI Prompt' : e.source === 'manual' ? 'Manual' : e.source || 'System';
            const desc = e.change_description || `${e.action} on ${e.table_name}`;
            const timestamp = e.timestamp ? new Date(e.timestamp + 'Z').toLocaleString() : '-';

            html += `
                <tr>
                    <td style="white-space:nowrap;font-size:12px;">${timestamp}</td>
                    <td><span style="font-weight:600;color:#667eea;">${e.action}</span></td>
                    <td style="font-size:12px;">${tableLabel}</td>
                    <td>${desc}</td>
                    <td style="font-size:12px;">${sourceLabel}</td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-state">Error: ${e.message}</td></tr>`;
    }
}

// ============================================================
// ALERTS
// ============================================================

async function loadAlerts() {
    const tbody = document.getElementById('alert-tbody');
    const status = document.getElementById('alert-status-filter').value;

    let url = `${API_BASE}/api/admin/monitor/alerts?limit=50`;
    if (status) url += `&status=${status}`;

    try {
        const res = await fetch(url);
        const alerts = await res.json();

        if (alerts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No alerts yet. Click "Check Now" to scan for new CSMS/FR notices.</td></tr>';
            return;
        }

        let html = '';
        alerts.forEach(a => {
            const relClass = a.relevance_score >= 80 ? 'relevance-high' : a.relevance_score >= 50 ? 'relevance-medium' : 'relevance-low';
            const statusClass = `alert-${a.status}`;

            html += `
                <tr>
                    <td style="white-space:nowrap;font-size:12px;">${a.published_date || a.created_at || '-'}</td>
                    <td>${a.source}</td>
                    <td style="font-family:monospace;">${a.reference_number || '-'}</td>
                    <td>${a.title || '-'}</td>
                    <td class="${relClass}">${a.relevance_score}%</td>
                    <td class="${statusClass}">${a.status}</td>
                    <td>
                        ${a.status === 'new' ? `
                            <button class="btn-sm btn-edit" onclick="applyAlert(${a.id}, '${(a.suggested_changes || '').replace(/'/g, "\\'")}')">Apply</button>
                            <button class="btn-sm btn-deactivate" onclick="dismissAlert(${a.id})">Dismiss</button>
                        ` : ''}
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Error: ${e.message}</td></tr>`;
    }
}

async function triggerMonitorCheck() {
    showToast('Checking for new CSMS/FR notices...', 'success');
    try {
        const res = await fetch(`${API_BASE}/api/admin/monitor/check-now`, { method: 'POST' });
        const result = await res.json();
        if (result.status === 'completed') {
            showToast('Monitor check complete', 'success');
        } else {
            showToast(result.message || 'Monitor check done', 'success');
        }
        loadAlerts();
        loadStats();
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

function applyAlert(alertId, suggestedText) {
    // Switch to AI prompt tab and pre-fill
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    document.querySelector('[data-tab="prompt"]').classList.add('active');
    document.getElementById('tab-prompt').classList.add('active');

    if (suggestedText) {
        document.getElementById('rule-prompt').value = suggestedText;
    }

    // Mark alert as reviewed
    fetch(`${API_BASE}/api/admin/monitor/alerts/${alertId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'reviewed' }),
    });
}

async function dismissAlert(alertId) {
    try {
        await fetch(`${API_BASE}/api/admin/monitor/alerts/${alertId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'dismissed' }),
        });
        showToast('Alert dismissed', 'success');
        loadAlerts();
        loadStats();
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

// ============================================================
// UTILITIES
// ============================================================

function formatHTS(code) {
    if (!code || code.length < 4) return code;
    // Format: 8708.80.65.90
    const c = code.replace(/[^0-9]/g, '');
    if (c.length === 10) return `${c.slice(0,4)}.${c.slice(4,6)}.${c.slice(6,8)}.${c.slice(8,10)}`;
    if (c.length === 8) return `${c.slice(0,4)}.${c.slice(4,6)}.${c.slice(6,8)}`;
    return code;
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

function showToast(message, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3500);
}

// Close modals on backdrop click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
    }
});
