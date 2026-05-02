const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const loading = document.getElementById('loading');
const resultsDiv = document.getElementById('results');
const errorDiv = document.getElementById('error-message');
let currentPdfBase64 = null;
let currentFilename = null;

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault(); dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleFile(e.target.files[0]);
});

async function handleFile(file) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
        showError("Veuillez sélectionner un fichier CSV."); return;
    }

    dropZone.classList.add('hidden');
    resultsDiv.classList.add('hidden');
    errorDiv.classList.add('hidden');
    loading.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.detail || "Une erreur est survenue.");
        
        displayResults(data);
    } catch (err) {
        showError(err.message);
    } finally {
        loading.classList.add('hidden');
    }
}

function displayResults(data) {
    const res = data.results;
    document.getElementById('res-fc').innerText = res.fc.toFixed(2);
    document.getElementById('res-e').innerText = res.E.toFixed(0);
    document.getElementById('res-eps0').innerText = res.eps0.toFixed(4);
    document.getElementById('res-epsu').innerText = res.eps_u.toFixed(4);
    
    document.getElementById('plot-img').src = "data:image/png;base64," + data.plot_base64;
    
    currentPdfBase64 = data.pdf_base64;
    currentFilename = data.filename.replace('.csv', '');
    
    resultsDiv.classList.remove('hidden');
}

function showError(msg) {
    errorDiv.innerText = msg;
    errorDiv.classList.remove('hidden');
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

document.getElementById('reset-btn').addEventListener('click', () => {
    resultsDiv.classList.add('hidden');
    dropZone.classList.remove('hidden');
    fileInput.value = '';
});
