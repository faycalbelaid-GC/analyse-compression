let currentToken = localStorage.getItem("token");
let chartInstance = null;
let dashboardChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
    // Initial State Check
    if (currentToken) {
        showApp();
    } else {
        document.getElementById("auth-screen").classList.remove("hidden");
        document.getElementById("app-container").classList.add("hidden");
    }

    // SPA Navigation
    document.querySelectorAll(".nav-links li").forEach(link => {
        link.addEventListener("click", (e) => {
            document.querySelectorAll(".nav-links li").forEach(l => l.classList.remove("active"));
            e.currentTarget.classList.add("active");
            
            document.querySelectorAll(".view-section").forEach(sec => sec.classList.remove("active"));
            const targetId = e.currentTarget.getAttribute("data-target");
            document.getElementById(targetId).classList.add("active");
            
            if(targetId === "view-history") loadHistory();
            if(targetId === "view-projects") loadProjects();
            if(targetId === "view-analyze") loadProjectsForSelect();
        });
    });

    // Dark Mode
    document.getElementById("dark-mode-toggle").addEventListener("click", () => {
        document.body.classList.toggle("dark-mode");
    });

    // Auth
    let isLogin = true;
    document.getElementById("auth-toggle-btn").addEventListener("click", () => {
        isLogin = !isLogin;
        document.getElementById("auth-title").innerText = isLogin ? "Connexion" : "Inscription";
        document.getElementById("auth-submit").innerText = isLogin ? "Se Connecter" : "S'inscrire";
        document.getElementById("auth-toggle-btn").innerText = isLogin ? "Pas encore de compte ? S'inscrire" : "Déjà un compte ? Se connecter";
    });

    document.getElementById("auth-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("auth-email").value;
        const password = document.getElementById("auth-password").value;
        
        try {
            if (isLogin) {
                const formData = new URLSearchParams();
                formData.append('username', email);
                formData.append('password', password);
                
                const res = await fetch("/token", {
                    method: "POST",
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: formData
                });
                
                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.detail || "Identifiants incorrects");
                }
                const data = await res.json();
                currentToken = data.access_token;
                localStorage.setItem("token", currentToken);
                showApp();
            } else {
                const formData = new FormData();
                formData.append('email', email);
                formData.append('password', password);
                
                const res = await fetch("/register", { method: "POST", body: formData });
                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error("Erreur d'inscription: " + (errData.detail || res.statusText));
                }
                alert("Inscription réussie. Vous pouvez vous connecter.");
                isLogin = true;
                document.getElementById("auth-toggle-btn").click();
            }
        } catch (err) {
            alert(err.message);
        }
    });

    document.getElementById("logout-btn").addEventListener("click", () => {
        currentToken = null;
        localStorage.removeItem("token");
        window.location.reload();
    });

    // Projects
    document.getElementById("new-project-btn").addEventListener("click", () => {
        document.getElementById("new-project-form").classList.toggle("hidden");
    });
    document.getElementById("submit-project").addEventListener("click", async () => {
        const name = document.getElementById("proj-name").value;
        const desc = document.getElementById("proj-desc").value;
        const fd = new FormData();
        fd.append("name", name); fd.append("description", desc);
        await apiCall("/projects", "POST", fd);
        document.getElementById("new-project-form").classList.add("hidden");
        loadProjects();
    });

    // Analyze
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");

    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.style.borderColor = "var(--primary)"; });
    dropZone.addEventListener("dragleave", () => { dropZone.style.borderColor = "var(--border-color)"; });
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "var(--border-color)";
        if (e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
        }
    });
    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) handleFiles(fileInput.files);
    });

    document.getElementById("refresh-history").addEventListener("click", loadHistory);
});

async function apiCall(endpoint, method = "GET", body = null) {
    const headers = { "Authorization": `Bearer ${currentToken}` };
    const options = { method, headers };
    if (body) options.body = body;
    const res = await fetch(endpoint, options);
    if (res.status === 401) {
        localStorage.removeItem("token");
        window.location.reload();
    }
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

async function showApp() {
    document.getElementById("auth-screen").classList.add("hidden");
    document.getElementById("app-container").classList.remove("hidden");
    const user = await apiCall("/users/me");
    document.getElementById("user-name").innerText = user.email.split('@')[0];
    loadDashboard();
}

async function loadDashboard() {
    const history = await apiCall("/history");
    if(history.length === 0) return;
    
    // Build quick chart
    const labels = history.slice(0, 10).reverse().map(h => new Date(h.created_at).toLocaleDateString());
    const data = history.slice(0, 10).reverse().map(h => h.fc);
    
    const ctx = document.getElementById('dashboard-chart').getContext('2d');
    if(dashboardChartInstance) dashboardChartInstance.destroy();
    dashboardChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{ label: 'Résistance fc (MPa)', data: data, borderColor: '#4F46E5', tension: 0.3 }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

async function loadProjects() {
    const projects = await apiCall("/projects");
    const list = document.getElementById("projects-list");
    list.innerHTML = "";
    projects.forEach(p => {
        list.innerHTML += `
            <div class="card">
                <h3>${p.name}</h3>
                <p style="color: var(--text-muted); font-size:0.9rem;">${p.description || "Aucune description"}</p>
                <div style="margin-top:10px; font-size:0.8rem; color:var(--text-muted);">Créé le: ${new Date(p.created_at).toLocaleDateString()}</div>
            </div>
        `;
    });
}

async function loadProjectsForSelect() {
    const projects = await apiCall("/projects");
    const select = document.getElementById("param-project");
    select.innerHTML = '<option value="">-- Aucun --</option>';
    projects.forEach(p => {
        select.innerHTML += `<option value="${p.id}">${p.name}</option>`;
    });
}

async function loadHistory() {
    const tbody = document.querySelector("#history-table tbody");
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">Chargement...</td></tr>';
    
    try {
        const data = await apiCall('/history');
        tbody.innerHTML = '';
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">Aucun essai trouvé.</td></tr>';
            return;
        }
        
        data.forEach(row => {
            const date = new Date(row.created_at).toLocaleString('fr-FR');
            let statusBadge = '-';
            if(row.compliance_status === "Conforme") statusBadge = '<span class="badge success">Conforme</span>';
            if(row.compliance_status === "Non-conforme") statusBadge = '<span class="badge danger">Non-conforme</span>';
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${date}</td>
                <td>${row.filename}</td>
                <td>${row.project_name || '-'}</td>
                <td style="font-weight:bold; color:var(--primary);">${row.fc.toFixed(2)}</td>
                <td>${row.e_modulus ? row.e_modulus.toFixed(0) : '-'}</td>
                <td>${statusBadge}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="6" style="color:red;">Erreur de chargement.</td></tr>';
    }
}

async function handleFiles(files) {
    if (files.length === 0) return;
    
    document.getElementById("loading").classList.remove("hidden");
    document.getElementById("results").classList.add("hidden");
    document.getElementById("batch-results").classList.add("hidden");
    document.getElementById("anomaly-alert").classList.add("hidden");

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
    }
    
    const projSelect = document.getElementById("param-project");
    if(projSelect.value) {
        formData.append("project_id", projSelect.value);
        formData.append("project_name", projSelect.options[projSelect.selectedIndex].text);
    }
    
    formData.append("operator", document.getElementById("param-operator").value || "");
    formData.append("age_days", document.getElementById("param-age").value || "");
    formData.append("target_fc", document.getElementById("param-target-fc").value || "");
    formData.append("apply_smoothing", document.getElementById("param-smoothing").checked);

    try {
        if (files.length === 1) {
            // Single File Analysis
            formData.set("file", files[0]);
            formData.delete("files");
            
            const data = await apiCall('/analyze', "POST", formData);
            
            document.getElementById("res-fc").textContent = data.results.fc.toFixed(2);
            document.getElementById("res-e").textContent = data.results.E.toFixed(0);
            document.getElementById("res-toughness").textContent = data.results.toughness ? data.results.toughness.toFixed(2) : '--';
            document.getElementById("res-pred").textContent = data.results.fc_28_pred ? data.results.fc_28_pred.toFixed(2) : '--';
            
            const statusEl = document.getElementById("res-status");
            if(data.results.compliance_status === "Conforme") {
                statusEl.innerHTML = '<span class="badge success">Conforme</span>';
            } else if (data.results.compliance_status === "Non-conforme") {
                statusEl.innerHTML = '<span class="badge danger">Non-conforme</span>';
            } else {
                statusEl.textContent = '--';
            }

            if(data.results.anomaly_flag) {
                document.getElementById("anomaly-alert").classList.remove("hidden");
            }

            renderChart(data.results);
            
            document.getElementById("download-pdf").onclick = () => {
                const link = document.createElement('a');
                link.href = `data:application/pdf;base64,${data.pdf_base64}`;
                link.download = data.filename.replace('.csv', '_rapport.pdf');
                link.click();
            };

            document.getElementById("results").classList.remove("hidden");
        } else {
            // Batch Analysis
            const res = await fetch('/analyze-batch', {
                method: "POST",
                headers: { "Authorization": `Bearer ${currentToken}` },
                body: formData
            });
            if (!res.ok) throw new Error("Erreur lors du traitement par lot");
            
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            
            document.getElementById("download-zip").onclick = () => {
                const a = document.createElement('a');
                a.href = url;
                a.download = "resultats_batch.zip";
                a.click();
            };
            
            document.getElementById("batch-results").classList.remove("hidden");
        }
    } catch (err) {
        alert("Erreur : " + err.message);
    } finally {
        document.getElementById("loading").classList.add("hidden");
    }
}

function renderChart(results) {
    const ctx = document.getElementById('interactive-chart').getContext('2d');
    if (chartInstance) chartInstance.destroy();

    const dataPoints = results.strains_plot.map((strain, index) => ({
        x: strain,
        y: results.stresses_plot[index]
    }));

    const strainLine = [0, results.strains_plot[results.idx_end]];
    const stressLine = strainLine.map(x => results.m * x + results.c);
    const linePoints = strainLine.map((x, i) => ({ x: x, y: stressLine[i] }));

    chartInstance = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'Courbe Expérimentale',
                    data: dataPoints,
                    borderColor: '#4F46E5',
                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                    showLine: true,
                    tension: 0.1,
                    pointRadius: 0
                },
                {
                    label: `Module Young (${results.E.toFixed(0)} MPa)`,
                    data: linePoints,
                    borderColor: '#10B981',
                    borderDash: [5, 5],
                    showLine: true,
                    pointRadius: 0
                },
                {
                    label: `fc (${results.fc.toFixed(2)} MPa)`,
                    data: [{x: results.eps0, y: results.fc}],
                    backgroundColor: '#EF4444',
                    pointRadius: 6,
                    pointHoverRadius: 8
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: { title: { display: true, text: 'Déformation (-)' } },
                y: { title: { display: true, text: 'Contrainte (MPa)' } }
            },
            interaction: { mode: 'index', intersect: false }
        }
    });
}
