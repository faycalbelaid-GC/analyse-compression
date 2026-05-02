const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const loading = document.getElementById('loading');
const resultsDiv = document.getElementById('results');
const batchResultsDiv = document.getElementById('batch-results');
const errorDiv = document.getElementById('error-message');
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

let currentPdfBase64 = null;
let currentFilename = null;
let chartInstance = null;

// Tab logic
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.target).classList.add('active');
        if (btn.dataset.target === 'tab-history') loadHistory();
    });
});

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault(); dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
});
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleFiles(e.target.files);
});

async function handleFiles(files) {
    const fileArray = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.csv'));
    if (fileArray.length === 0) {
        showError("Veuillez sélectionner au moins un fichier CSV."); return;
    }

    dropZone.classList.add('hidden');
    resultsDiv.classList.add('hidden');
    batchResultsDiv.classList.add('hidden');
    errorDiv.classList.add('hidden');
    loading.classList.remove('hidden');

    const formData = new FormData();
    formData.append('project', document.getElementById('param-project').value);
    formData.append('operator', document.getElementById('param-operator').value);
    formData.append('apply_smoothing', document.getElementById('param-smoothing').checked);
    formData.append('e_start', document.getElementById('param-estart').value);
    formData.append('e_end', document.getElementById('param-eend').value);

    try {
        if (fileArray.length === 1) {
            formData.append('file', fileArray[0]);
            const response = await fetch('/analyze', { method: 'POST', body: formData });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Erreur serveur.");
            displaySingleResult(data);
        } else {
            fileArray.forEach(f => formData.append('files', f));
            const response = await fetch('/analyze-batch', { method: 'POST', body: formData });
            if (!response.ok) throw new Error("Erreur serveur lors du batch.");
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = "resultats_batch.zip";
            document.body.appendChild(link);
            link.click();
            link.remove();
            
            loading.classList.add('hidden');
            batchResultsDiv.classList.remove('hidden');
        }
    } catch (err) {
        showError(err.message);
    }
}

function displaySingleResult(data) {
    const res = data.results;
    document.getElementById('res-fc').innerText = res.fc.toFixed(2);
    document.getElementById('res-e').innerText = res.E.toFixed(0);
    document.getElementById('res-eps0').innerText = res.eps0.toFixed(4);
    document.getElementById('res-epsu').innerText = res.eps_u.toFixed(4);
    document.getElementById('result-title').innerText = "Essai : " + data.filename;
    
    currentPdfBase64 = data.pdf_base64;
    currentFilename = data.filename.replace('.csv', '');
    
    drawChart(res.strains_plot, res.stresses_plot, res.E, res.fc, res.eps0, res.m, res.c, res.idx_end);

    loading.classList.add('hidden');
    resultsDiv.classList.remove('hidden');
}

function drawChart(strains, stresses, E, fc, eps0, m, c, idx_end) {
    const ctx = document.getElementById('interactive-chart').getContext('2d');
    if (chartInstance) chartInstance.destroy();

    const dataPoints = strains.map((s, i) => ({ x: s, y: stresses[i] }));
    const eLine = [{ x: 0, y: c }, { x: strains[idx_end], y: m * strains[idx_end] + c }];
    
    chartInstance = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Courbe Expérimentale',
                data: dataPoints,
                showLine: true,
                borderColor: '#4F46E5',
                backgroundColor: 'transparent',
                pointRadius: 0,
                borderWidth: 2
            }, {
                label: 'Module Young',
                data: eLine,
                showLine: true,
                borderColor: '#10B981',
                borderDash: [5, 5],
                pointRadius: 0,
                borderWidth: 2
            }, {
                label: 'Pic (fc)',
                data: [{x: eps0, y: fc}],
                backgroundColor: '#EF4444',
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: { title: { display: true, text: 'Déformation (-)' }, type: 'linear', position: 'bottom' },
                y: { title: { display: true, text: 'Contrainte (MPa)' } }
            },
            interaction: { mode: 'index', intersect: false }
        }
    });
}

function showError(msg) {
    errorDiv.innerText = msg;
    errorDiv.classList.remove('hidden');
    loading.classList.add('hidden');
    dropZone.classList.remove('hidden');
}

document.getElementById('download-pdf').addEventListener('click', () => {
    if (!currentPdfBase64) return;
    const link = document.createElement('a');
    link.href = "data:application/pdf;base64," + currentPdfBase64;
    link.download = `rapport_${currentFilename}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
});

document.querySelectorAll('.reset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        resultsDiv.classList.add('hidden');
        batchResultsDiv.classList.add('hidden');
        dropZone.classList.remove('hidden');
        fileInput.value = '';
    });
});

document.getElementById('refresh-history').addEventListener('click', loadHistory);

async function loadHistory() {
    try {
        const response = await fetch('/history');
        const records = await response.json();
        const tbody = document.querySelector('#history-table tbody');
        tbody.innerHTML = '';
        records.forEach(r => {
            const date = new Date(r.created_at).toLocaleString();
            tbody.innerHTML += `<tr>
                <td>${date}</td>
                <td>${r.filename}</td>
                <td>${r.project_name || '-'}</td>
                <td>${r.fc ? r.fc.toFixed(2) : '-'}</td>
                <td>${r.e_modulus ? r.e_modulus.toFixed(0) : '-'}</td>
            </tr>`;
        });
    } catch (e) { console.error("Erreur historique", e); }
}
