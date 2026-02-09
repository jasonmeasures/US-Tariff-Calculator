// US Tariff Calculator - Frontend JavaScript

const API_BASE = 'http://localhost:8000';

// Check Section 232 requirements when HTS code is entered
async function checkSection232Requirements(htsCode) {
    if (!htsCode || htsCode.trim() === '') {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/check-section232/${htsCode}`);
        const result = await response.json();

        const materialSection = document.getElementById('material-content-section');
        const aluminumContainer = document.getElementById('aluminum-slider-container');
        const steelContainer = document.getElementById('steel-slider-container');
        const copperContainer = document.getElementById('copper-slider-container');
        const noteDiv = document.getElementById('section232-note');

        if (result.requires_section232) {
            // Show material content section
            materialSection.style.display = 'block';

            // Show only required materials
            aluminumContainer.style.display = result.materials.includes('aluminum') ? 'block' : 'none';
            steelContainer.style.display = result.materials.includes('steel') ? 'block' : 'none';
            copperContainer.style.display = result.materials.includes('copper') ? 'block' : 'none';

            // Show note about country of smelt/pour
            if (result.note) {
                noteDiv.textContent = '⚠️ ' + result.note;
                noteDiv.style.display = 'block';
            } else {
                noteDiv.style.display = 'none';
            }
        } else {
            // Hide entire material section
            materialSection.style.display = 'none';
        }
    } catch (error) {
        console.error('Error checking Section 232 requirements:', error);
        // On error, hide material sliders (safe default for most HTS codes)
        document.getElementById('material-content-section').style.display = 'none';
    }
}

// Add event listener to HTS code field
document.getElementById('hts-code').addEventListener('blur', function() {
    checkSection232Requirements(this.value.trim());
});

// Also check on input after a delay (debounce)
let htsCheckTimeout;
document.getElementById('hts-code').addEventListener('input', function() {
    clearTimeout(htsCheckTimeout);
    htsCheckTimeout = setTimeout(() => {
        if (this.value.trim().length >= 8) {
            checkSection232Requirements(this.value.trim());
        }
    }, 500);
});

// Update range value displays
document.getElementById('aluminum-percent').addEventListener('input', (e) => {
    document.getElementById('aluminum-value').textContent = e.target.value;
});

document.getElementById('steel-percent').addEventListener('input', (e) => {
    document.getElementById('steel-value').textContent = e.target.value;
});

document.getElementById('copper-percent').addEventListener('input', (e) => {
    document.getElementById('copper-value').textContent = e.target.value;
});

// Test case button
document.getElementById('test-case-btn').addEventListener('click', () => {
    document.getElementById('hts-code').value = '8708.80.65.90';
    document.getElementById('country').value = 'JP';
    document.getElementById('entry-date').value = '2025-03-15';
    document.getElementById('value').value = '10000';
    document.getElementById('aluminum-percent').value = '100';
    document.getElementById('aluminum-value').textContent = '100';
    document.getElementById('steel-percent').value = '0';
    document.getElementById('steel-value').textContent = '0';
    document.getElementById('copper-percent').value = '0';
    document.getElementById('copper-value').textContent = '0';
    document.getElementById('mode').value = 'ocean';

    // Trigger Section 232 check for test case
    checkSection232Requirements('8708.80.65.90');
});

// Form submission
document.getElementById('calculator-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    // Get form values
    const payload = {
        hts_code: document.getElementById('hts-code').value.trim(),
        country: document.getElementById('country').value,
        entry_date: document.getElementById('entry-date').value,
        value: parseFloat(document.getElementById('value').value),
        aluminum_percent: parseFloat(document.getElementById('aluminum-percent').value),
        steel_percent: parseFloat(document.getElementById('steel-percent').value),
        copper_percent: parseFloat(document.getElementById('copper-percent').value),
        mode: document.getElementById('mode').value
    };

    // Show loading state
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Calculating...';
    submitBtn.disabled = true;

    try {
        // Call API
        const response = await fetch(`${API_BASE}/api/calculate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const result = await response.json();

        // Display results
        displayResults(result);

        // Scroll to results
        document.getElementById('results-card').scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Error:', error);
        alert('Error calculating duty. Please check your inputs and try again.');
    } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
});

function displayResults(result) {
    // Show results card
    document.getElementById('results-card').style.display = 'block';

    // Display summary
    document.getElementById('duty-rate').textContent = `${result.total_duty_rate.toFixed(2)}%`;
    document.getElementById('total-duty').textContent = formatCurrency(result.total_duty);

    // Display breakdown
    const breakdownContainer = document.getElementById('breakdown-items');
    breakdownContainer.innerHTML = '';

    result.breakdown.forEach(item => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'breakdown-item';

        const leftDiv = document.createElement('div');

        const nameDiv = document.createElement('div');
        nameDiv.className = 'breakdown-name';
        nameDiv.textContent = item.name;

        const descDiv = document.createElement('div');
        descDiv.className = 'breakdown-description';

        if (item.material_basis && item.material_percent) {
            descDiv.textContent = `${item.rate}% × ${item.material_percent}% ${item.material_basis} = ${item.effective_rate.toFixed(2)}%`;
        } else {
            descDiv.textContent = item.description || '';
        }

        leftDiv.appendChild(nameDiv);
        leftDiv.appendChild(descDiv);

        // Add Chapter 99 code if present (like Flexport)
        if (item.chapter99_code && item.chapter99_code !== '') {
            const ch99Div = document.createElement('div');
            ch99Div.className = 'breakdown-chapter99';
            ch99Div.textContent = formatChapter99(item.chapter99_code);
            ch99Div.style.color = '#667eea';
            ch99Div.style.fontSize = '13px';
            ch99Div.style.marginTop = '4px';
            ch99Div.style.fontWeight = '500';
            leftDiv.appendChild(ch99Div);
        }

        const amountDiv = document.createElement('div');
        amountDiv.className = 'breakdown-amount';
        amountDiv.textContent = formatCurrency(item.amount);

        itemDiv.appendChild(leftDiv);
        itemDiv.appendChild(amountDiv);
        breakdownContainer.appendChild(itemDiv);
    });

    // Display landed cost
    document.getElementById('landed-cost').textContent = formatCurrency(result.landed_cost);

    // Display confidence
    document.getElementById('confidence-value').textContent = `${result.confidence}%`;

    // Display notes if any
    if (result.notes && result.notes.length > 0) {
        document.getElementById('notes-section').style.display = 'block';
        const notesList = document.getElementById('notes-list');
        notesList.innerHTML = '';

        result.notes.forEach(note => {
            const li = document.createElement('li');
            li.textContent = note;
            notesList.appendChild(li);
        });
    } else {
        document.getElementById('notes-section').style.display = 'none';
    }
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

function formatChapter99(code) {
    // Format Chapter 99 code like Flexport: 9903.85.08
    if (code.length === 8) {
        return `${code.substring(0, 4)}.${code.substring(4, 6)}.${code.substring(6, 8)}`;
    }
    return code;
}
