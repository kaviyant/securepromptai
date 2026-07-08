// SecurePrompt AI - Admin Dashboard Client JS

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize Icons
    lucide.createIcons();

    // 2. Tab Navigation Swapping
    const navItems = document.querySelectorAll(".nav-item");
    const tabPanes = document.querySelectorAll(".tab-pane");
    const tabTitle = document.getElementById("current-tab-title");
    const tabSubtitle = document.getElementById("current-tab-subtitle");

    const tabMeta = {
        "overview": { title: "Security Overview", subtitle: "Real-time prompt firewall statistics and audit logs." },
        "history": { title: "Prompt Logs", subtitle: "Full list of verified, sanitized, and blocked user prompts." },
        "threats": { title: "Insider Threat Alerts", subtitle: "Anomaly telemetry logs compiled via Scikit-Learn ML." },
        "shadow-ai": { title: "Shadow AI Auditing", subtitle: "Usage analytics and restricted site domain telemetry." },
        "policies": { title: "Firewall Policies", subtitle: "Configure global rules, PII filters, and block thresholds." }
    };

    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const tabName = item.getAttribute("data-tab");

            // Deactivate all
            navItems.forEach(n => n.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));

            // Activate current
            item.classList.add("active");
            document.getElementById(`tab-${tabName}`).classList.add("active");

            // Update Header Meta
            if (tabMeta[tabName]) {
                tabTitle.textContent = tabMeta[tabName].title;
                tabSubtitle.textContent = tabMeta[tabName].subtitle;
            }
        });
    });

    // Overview Tab Link redirection
    document.querySelector(".view-all-link").addEventListener("click", (e) => {
        e.preventDefault();
        const tabLink = e.target.getAttribute("data-tab-link");
        document.querySelector(`.nav-item[data-tab="${tabLink}"]`).click();
    });

    // 3. Initialize Chart.js Graphs
    const riskCtx = document.getElementById('riskChart').getContext('2d');
    const deptCtx = document.getElementById('departmentChart').getContext('2d');
    const shadowCtx = document.getElementById('shadowAiChart').getContext('2d');
    const dataCtx = document.getElementById('dataVolumeChart').getContext('2d');

    const charts = {
        risk: new Chart(riskCtx, {
            type: 'doughnut',
            data: {
                labels: ['Low Risk', 'Medium Risk', 'High Risk', 'Critical Risk'],
                datasets: [{
                    data: [150, 45, 12, 3],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#7c3aed'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { color: '#858da8' } } }
            }
        }),
        dept: new Chart(deptCtx, {
            type: 'bar',
            data: {
                labels: ['Engineering', 'Finance', 'HR', 'Legal', 'Marketing'],
                datasets: [{
                    label: 'Scans Count',
                    data: [110, 40, 25, 10, 35],
                    backgroundColor: '#6366f1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#858da8' }, grid: { display: false } },
                    y: { ticks: { color: '#858da8' }, grid: { color: '#242946' } }
                }
            }
        }),
        shadow: new Chart(shadowCtx, {
            type: 'pie',
            data: {
                labels: ['ChatGPT', 'Gemini', 'Claude', 'Copilot', 'Grok'],
                datasets: [{
                    data: [120, 50, 40, 25, 15],
                    backgroundColor: ['#06b6d4', '#10b981', '#f59e0b', '#6366f1', '#a855f7'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { color: '#858da8' } } }
            }
        }),
        volume: new Chart(dataCtx, {
            type: 'bar',
            data: {
                labels: ['Engineering', 'Finance', 'HR', 'Legal', 'Marketing'],
                datasets: [{
                    label: 'KB Uploaded',
                    data: [420, 150, 80, 45, 110],
                    backgroundColor: '#06b6d4'
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#858da8' }, grid: { color: '#242946' } },
                    y: { ticks: { color: '#858da8' }, grid: { display: false } }
                }
            }
        })
    };

    // 4. API Fetch Functions

    async function fetchDashboardStats() {
        try {
            const res = await fetch("/api/dashboard/stats");
            if (!res.ok) return;
            const data = await res.json();
            
            // Set stats values
            document.getElementById("stat-total-scans").textContent = data.total_scans || 250;
            document.getElementById("stat-total-blocks").textContent = data.total_violations || 15;
            document.getElementById("stat-block-rate").textContent = (data.block_rate || 6.0) + "%";

            // Update charts if data returned
            if (data.charts) {
                if (data.charts.risk) {
                    charts.risk.data.datasets[0].data = data.charts.risk;
                    charts.risk.update();
                }
                if (data.charts.dept) {
                    charts.dept.data.labels = Object.keys(data.charts.dept);
                    charts.dept.data.datasets[0].data = Object.values(data.charts.dept);
                    charts.dept.update();
                }
            }

            // Render Recent Alerts list
            const alertsBody = document.getElementById("overview-alerts-body");
            if (data.recent_alerts && data.recent_alerts.length > 0) {
                alertsBody.innerHTML = "";
                data.recent_alerts.forEach(alert => {
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${new Date(alert.timestamp).toLocaleTimeString()}</td>
                        <td>${alert.user_email}</td>
                        <td><strong>${alert.alert_type}</strong></td>
                        <td><span class="status-badge ${alert.severity.toLowerCase() === 'critical' ? 'blocked' : 'warned'}">${alert.severity}</span></td>
                        <td>${alert.reasons ? alert.reasons.join(', ') : 'Anomalous submission flagged.'}</td>
                    `;
                    alertsBody.appendChild(row);
                });
            }
        } catch (e) {
            console.error("Failed to load overview data:", e);
        }
    }

    async function fetchHistoryLogs() {
        try {
            const res = await fetch("/api/history");
            if (!res.ok) return;
            const logs = await res.json();
            
            const tableBody = document.getElementById("history-table-body");
            tableBody.innerHTML = "";
            
            if (logs.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="6" class="text-center">No prompt logs found.</td></tr>`;
                return;
            }

            logs.forEach(log => {
                const row = document.createElement("tr");
                const dateStr = new Date(log.timestamp).toLocaleString();
                const statusBadge = log.blocked 
                    ? '<span class="status-badge blocked">BLOCKED</span>' 
                    : (log.sanitized ? '<span class="status-badge warned">SANITIZED</span>' : '<span class="status-badge allowed">ALLOWED</span>');
                
                row.innerHTML = `
                    <td>${dateStr}</td>
                    <td>${log.user_email}</td>
                    <td>${log.department || 'Operations'}</td>
                    <td><span class="text-uppercase">${log.site_key || 'ChatGPT'}</span></td>
                    <td>${log.prompt_length || (log.originalPrompt ? log.originalPrompt.length : 0)} chars</td>
                    <td>${statusBadge}</td>
                `;
                tableBody.appendChild(row);
            });
        } catch (e) {
            console.error("Failed to load history logs:", e);
        }
    }

    async function fetchThreatAlerts() {
        try {
            const res = await fetch("/api/alerts");
            if (!res.ok) return;
            const alerts = await res.json();
            
            const tableBody = document.getElementById("threats-table-body");
            tableBody.innerHTML = "";
            document.getElementById("alerts-count-badge").textContent = alerts.length;

            if (alerts.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="6" class="text-center">No security alerts flagged.</td></tr>`;
                return;
            }

            alerts.forEach(alert => {
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${new Date(alert.timestamp).toLocaleString()}</td>
                    <td>${alert.user_email}</td>
                    <td><strong>${alert.alert_type}</strong></td>
                    <td><span class="status-badge blocked">${alert.score} / 100</span></td>
                    <td><span class="status-badge warned">${alert.resolved ? 'RESOLVED' : 'ACTIVE'}</span></td>
                    <td><button class="btn btn-secondary btn-sm resolve-btn" data-id="${alert._id}">Resolve</button></td>
                `;
                tableBody.appendChild(row);
            });
            
            // Add resolve triggers
            document.querySelectorAll(".resolve-btn").forEach(btn => {
                btn.addEventListener("click", async (e) => {
                    const alertId = e.target.getAttribute("data-id");
                    await fetch(`/api/alerts/${alertId}/resolve`, { method: "POST" });
                    fetchThreatAlerts();
                });
            });

        } catch (e) {
            console.error("Failed to load alerts:", e);
        }
    }

    async function fetchShadowAiSummary() {
        try {
            const res = await fetch("/api/shadow-ai/summary");
            if (!res.ok) return;
            const data = await res.json();

            if (data.platforms) {
                charts.shadow.data.labels = Object.keys(data.platforms);
                charts.shadow.data.datasets[0].data = Object.values(data.platforms);
                charts.shadow.update();
            }

            if (data.departments) {
                charts.volume.data.labels = Object.keys(data.departments);
                charts.volume.data.datasets[0].data = Object.values(data.departments);
                charts.volume.update();
            }
        } catch (e) {
            console.error("Failed to load shadow AI summaries:", e);
        }
    }

    async function fetchFirewallSettings() {
        try {
            const res = await fetch("/api/settings");
            if (!res.ok) return;
            const settingsList = await res.json();
            
            settingsList.forEach(s => {
                if (s.key === "firewall_mode") {
                    document.getElementById("setting-firewall-mode").value = s.value;
                } else if (s.key === "auto_sanitize") {
                    document.getElementById("setting-auto-sanitize").checked = s.value;
                } else if (s.key === "risk_threshold") {
                    document.getElementById("setting-risk-threshold").value = s.value;
                }
            });
        } catch (e) {
            console.error("Failed to load settings configurations:", e);
        }
    }

    // 5. Save settings configurations
    document.getElementById("save-settings-btn").addEventListener("click", async () => {
        const payload = [
            { key: "firewall_mode", value: document.getElementById("setting-firewall-mode").value },
            { key: "auto_sanitize", value: document.getElementById("setting-auto-sanitize").checked },
            { key: "risk_threshold", value: parseInt(document.getElementById("setting-risk-threshold").value) }
        ];

        try {
            const res = await fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                alert("Firewall settings saved successfully!");
            }
        } catch (e) {
            console.error("Failed to save settings configurations:", e);
        }
    });

    // 6. Hook Global actions
    document.getElementById("refresh-data-btn").addEventListener("click", () => {
        fetchDashboardStats();
        fetchHistoryLogs();
        fetchThreatAlerts();
        fetchShadowAiSummary();
        fetchFirewallSettings();
    });

    // Download audit reports click
    document.getElementById("download-audit-btn").addEventListener("click", () => {
        window.open("/api/reports/shadow-ai/pdf");
    });

    // Bootstrap values on start
    document.getElementById("refresh-data-btn").click();
});
