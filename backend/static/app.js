// State management
let currentScanData = null;
let networkInstance = null;

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileInfo = document.getElementById('file-info');
const btnUpload = document.getElementById('btn-upload');
const pathInput = document.getElementById('path-input');
const btnScanPath = document.getElementById('btn-scan-path');
const btnSampleScan = document.getElementById('btn-sample-scan');
const scannerLoader = document.getElementById('scanner-loader');
const resultsPanel = document.getElementById('results-panel');

// Tabs
const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanes = document.querySelectorAll('.tab-pane');

// Modal Elements
const smellModal = document.getElementById('smell-modal');
const modalOverlay = document.getElementById('modal-overlay');
const modalCloseBtn = document.getElementById('modal-close-btn');

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    setupDragAndDrop();
    setupTabSwitching();
    setupEventHandlers();
    setupModalHandlers();
});

// --- Event Handlers ---
function setupEventHandlers() {
    btnSampleScan.addEventListener('click', () => runScan('/api/sample'));

    btnScanPath.addEventListener('click', () => {
        const path = pathInput.value.trim();
        if (!path) {
            alert('Please enter a directory path first.');
            return;
        }
        runScan(`/api/scan-path?path=${encodeURIComponent(path)}`, 'POST');
    });

    btnUpload.addEventListener('click', () => {
        const file = fileInput.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        runScan('/api/scan-upload', 'POST', formData);
    });
}

function setupModalHandlers() {
    const closeModal = () => {
        smellModal.classList.add('hidden');
    };
    modalCloseBtn.addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', closeModal);
    
    // Close on Escape key
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !smellModal.classList.contains('hidden')) {
            closeModal();
        }
    });
}

// --- Drag & Drop ---
function setupDragAndDrop() {
    // Prevent defaults
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight drop zone
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelect();
        }
    });

    fileInput.addEventListener('change', handleFileSelect);
}

function handleFileSelect() {
    const file = fileInput.files[0];
    if (file) {
        if (!file.name.endsWith('.zip')) {
            alert('Only ZIP archives are supported.');
            fileInput.value = '';
            fileInfo.textContent = '';
            btnUpload.disabled = true;
            return;
        }
        fileInfo.textContent = `Selected: ${file.name} (${formatBytes(file.size)})`;
        btnUpload.disabled = false;
    } else {
        fileInfo.textContent = '';
        btnUpload.disabled = true;
    }
}

// --- Tab Switching ---
function setupTabSwitching() {
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');

            tabButtons.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            const targetPane = document.getElementById(tabId);
            if (targetPane) targetPane.classList.add('active');

            // Resize network graph when its tab becomes active, as vis needs correct client bounding rect
            if (tabId === 'tab-graph' && networkInstance) {
                setTimeout(() => {
                    networkInstance.fit();
                }, 100);
            }
        });
    });
}

// --- Running Scans ---
async function runScan(endpoint, method = 'GET', body = null) {
    // Show loader, hide results
    scannerLoader.classList.add('active');
    resultsPanel.classList.add('hidden');
    
    // Smooth scroll to loader
    scannerLoader.scrollIntoView({ behavior: 'smooth', block: 'center' });

    try {
        const options = { method };
        if (body) {
            options.body = body;
        } else if (method === 'POST') {
            // For POST requests without FormData, make content-type application/json if needed
            options.headers = { 'Accept': 'application/json' };
        }

        const response = await fetch(endpoint, options);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'An error occurred during the scan.');
        }

        currentScanData = data;
        displayResults(data);

    } catch (error) {
        console.error(error);
        alert(`Scan failed: ${error.message}`);
    } finally {
        scannerLoader.classList.remove('active');
    }
}

// --- Displaying Results ---
function displayResults(data) {
    // Update Header
    document.getElementById('project-title').textContent = `Project: ${data.project_name || 'Uploaded Project'}`;
    document.getElementById('project-path-text').textContent = data.project_path || 'Uploaded Zip Archive';
    
    const scanTime = data.statistics ? data.statistics.scan_time_seconds : 0;
    document.getElementById('scan-time-value').textContent = `${scanTime}s`;

    // Update Statistics Cards
    const debtScore = data.debt_report ? data.debt_report.total_score : 0;
    document.getElementById('stat-debt-score').textContent = debtScore;

    // Set debt level indicator
    const debtBadge = document.getElementById('debt-level-badge');
    if (debtScore < 10) {
        debtBadge.textContent = 'Low Technical Debt';
        debtBadge.className = 'stat-desc badge badge-low';
    } else if (debtScore <= 35) {
        debtBadge.textContent = 'Medium Technical Debt';
        debtBadge.className = 'stat-desc badge badge-medium';
    } else {
        debtBadge.textContent = 'High Technical Debt';
        debtBadge.className = 'stat-desc badge badge-high';
    }

    const classesCount = data.statistics ? (data.statistics.total_classes + data.statistics.total_interfaces) : 0;
    document.getElementById('stat-classes-count').textContent = classesCount;
    document.getElementById('stat-files-parsed').textContent = `${data.statistics?.parsed_files || 0} file(s) parsed successfully`;

    const couplingCount = data.statistics ? data.statistics.dependency_edges : 0;
    const circularCount = data.statistics ? data.statistics.circular_dependencies : 0;
    document.getElementById('stat-coupling-count').textContent = couplingCount;
    document.getElementById('stat-cyclic-count').textContent = `${circularCount} circular dependency chain(s)`;

    // Vulnerability summaries
    const outdatedCount = data.dependency_report?.outdated_dependencies?.length || 0;
    document.getElementById('stat-vulns-count').textContent = outdatedCount;
    
    const frameworks = data.dependency_report?.detected_frameworks || [];
    document.getElementById('stat-frameworks-detected').textContent = frameworks.length > 0 
        ? frameworks.join(', ') 
        : 'No major frameworks';

    // Reset and Render Tabs
    renderCodeSmellsTable(data.debt_report?.issues || []);
    renderFrameworkTags(frameworks);
    renderVulnerabilitiesTable(data.dependency_report?.outdated_dependencies || []);
    renderDependencyGraph(data);

    // Show panel
    resultsPanel.classList.remove('hidden');
    resultsPanel.scrollIntoView({ behavior: 'smooth' });
}

// --- Render Code Smells ---
function renderCodeSmellsTable(issues) {
    const tbody = document.getElementById('smells-tbody');
    tbody.innerHTML = '';

    if (issues.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                    <i class="fa-solid fa-circle-check" style="color: var(--accent-emerald); font-size: 1.5rem; margin-bottom: 0.5rem; display: block;"></i>
                    No design or code smells detected! Your code is clean.
                </td>
            </tr>
        `;
        return;
    }

    issues.forEach(issue => {
        const tr = document.createElement('tr');
        
        // Severity Badge
        const severityClass = `badge-${issue.severity.toLowerCase()}`;
        
        tr.innerHTML = `
            <td><strong>${escapeHtml(issue.rule)}</strong></td>
            <td><code class="code-block">${escapeHtml(issue.class_name)}</code></td>
            <td>${issue.line_number}</td>
            <td><span class="text-glow">${issue.metric_value}</span></td>
            <td><span class="badge ${severityClass}">${escapeHtml(issue.severity)}</span></td>
            <td><button class="btn-view-detail" data-id="${escapeHtml(issue.rule)}-${escapeHtml(issue.class_name)}-${issue.line_number}">View Detail</button></td>
        `;

        // Add event listener to view detail
        tr.querySelector('.btn-view-detail').addEventListener('click', () => {
            showSmellDetail(issue);
        });

        tbody.appendChild(tr);
    });
}

function showSmellDetail(issue) {
    document.getElementById('modal-smell-title').textContent = `${issue.rule} Smell Detail`;
    
    const severityBadge = document.getElementById('modal-smell-severity');
    severityBadge.className = `badge badge-${issue.severity.toLowerCase()}`;
    severityBadge.textContent = issue.severity;

    document.getElementById('modal-smell-class').textContent = issue.class_name;
    document.getElementById('modal-smell-line').textContent = issue.line_number;
    document.getElementById('modal-smell-desc').textContent = issue.message;
    
    const remediationText = document.getElementById('modal-smell-remediation');
    if (issue.suggestion) {
        document.getElementById('modal-remediation-section').classList.remove('hidden');
        remediationText.textContent = issue.suggestion;
    } else {
        document.getElementById('modal-remediation-section').classList.add('hidden');
    }

    smellModal.classList.remove('hidden');
}

// --- Render Frameworks and Vulnerabilities ---
function renderFrameworkTags(frameworks) {
    const container = document.getElementById('framework-tags');
    container.innerHTML = '';
    
    if (frameworks.length === 0) {
        container.innerHTML = `<span class="text-muted">No specific frameworks detected.</span>`;
        return;
    }

    frameworks.forEach(fw => {
        const tag = document.createElement('span');
        tag.className = 'framework-tag';
        tag.textContent = fw;
        container.appendChild(tag);
    });
}

function renderVulnerabilitiesTable(vulns) {
    const tbody = document.getElementById('vulns-tbody');
    tbody.innerHTML = '';

    const buildTool = currentScanData.dependency_report?.build_tool || 'N/A';
    document.getElementById('build-tool-badge').textContent = buildTool;

    if (vulns.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                    <i class="fa-solid fa-shield-halved" style="color: var(--accent-emerald); font-size: 1.5rem; margin-bottom: 0.5rem; display: block;"></i>
                    No known vulnerable/outdated dependencies detected.
                </td>
            </tr>
        `;
        return;
    }

    vulns.forEach(v => {
        const tr = document.createElement('tr');
        
        // Critical or High styling
        const severityLower = v.severity.toLowerCase();
        const severityClass = severityLower === 'critical' ? 'badge-high' : `badge-${severityLower}`;
        
        tr.innerHTML = `
            <td>
                <strong>${escapeHtml(v.group)}</strong><span style="color: var(--text-muted);">:</span>${escapeHtml(v.artifact)}
            </td>
            <td><span class="badge ${severityClass}">${escapeHtml(v.severity)}</span></td>
            <td><code class="code-block">${escapeHtml(v.current_version)}</code></td>
            <td><code class="code-block" style="color: var(--accent-emerald);">${escapeHtml(v.minimum_safe_version)}</code></td>
            <td><span class="dependency-reason">${escapeHtml(v.reason)}</span></td>
        `;

        tbody.appendChild(tr);
    });
}

// --- Render Dependency Graph ---
function renderDependencyGraph(data) {
    const container = document.getElementById('network-graph');
    
    // Clear sidebar selection
    document.getElementById('no-node-selected-msg').classList.remove('hidden');
    document.getElementById('node-metrics-info').classList.add('hidden');

    const graphStats = data.statistics?.graph;
    if (!graphStats || !data.classes || data.classes.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; color: var(--text-muted); padding: 4rem;">
                No dependency graph metrics available.
            </div>
        `;
        return;
    }

    const classesMap = {};
    data.classes.forEach(cls => {
        classesMap[cls.package + '.' + cls.name] = cls;
    });

    const coupling = graphStats.coupling_metrics || {};
    const nodesArray = [];
    const edgesArray = [];

    // Create Nodes
    Object.keys(coupling).forEach(fqn => {
        const metric = coupling[fqn];
        const parts = fqn.split('.');
        const shortName = parts[parts.length - 1];
        
        // Size proportional to afferent coupling (incoming edges)
        const size = 15 + (metric.afferent_coupling * 5);
        
        // Color based on Instability Index (0 = stable = cyan, 1 = unstable = red/pink)
        const instability = metric.instability;
        const color = getInstabilityColor(instability);

        nodesArray.push({
            id: fqn,
            label: shortName,
            title: fqn,
            shape: 'dot',
            size: size,
            color: {
                background: color,
                border: '#1e293b',
                highlight: {
                    background: color,
                    border: '#f8fafc'
                }
            },
            font: {
                color: '#f8fafc',
                face: 'Inter',
                size: 12
            },
            borderWidth: 2,
            shadow: {
                enabled: true,
                color: 'rgba(0,0,0,0.4)',
                size: 8,
                x: 0,
                y: 4
            }
        });
    });

    // Create Edges
    const rawEdges = data.dependencies || [];
    rawEdges.forEach(edge => {
        edgesArray.push({
            from: edge.from,
            to: edge.to,
            arrows: 'to',
            color: {
                color: 'rgba(99, 102, 241, 0.4)',
                highlight: '#6366f1',
                hover: '#a855f7'
            },
            label: edge.type !== 'calls' ? edge.type : '',
            font: {
                color: '#64748b',
                face: 'Inter',
                size: 9,
                align: 'middle'
            },
            width: 1.5,
            smooth: {
                type: 'cubicBezier',
                roundness: 0.4
            }
        });
    });

    const nodes = new vis.DataSet(nodesArray);
    const edges = new vis.DataSet(edgesArray);

    const graphData = { nodes, edges };
    const options = {
        interaction: {
            hover: true,
            tooltipDelay: 200,
            navigationButtons: true
        },
        physics: {
            stabilization: {
                iterations: 150,
                fit: true
            },
            barnesHut: {
                gravitationalConstant: -2000,
                centralGravity: 0.3,
                springLength: 95,
                springConstant: 0.04
            }
        }
    };

    networkInstance = new vis.Network(container, graphData, options);

    // Click handler on nodes
    networkInstance.on('click', (params) => {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            showNodeDetails(nodeId, coupling[nodeId]);
        } else {
            // Hide details
            document.getElementById('no-node-selected-msg').classList.remove('hidden');
            document.getElementById('node-metrics-info').classList.add('hidden');
        }
    });
}

function showNodeDetails(fqn, metric) {
    if (!metric) return;
    
    document.getElementById('no-node-selected-msg').classList.add('hidden');
    document.getElementById('node-metrics-info').classList.remove('hidden');

    document.getElementById('selected-class-name').textContent = fqn;
    
    const parts = fqn.split('.');
    parts.pop();
    const pkg = parts.join('.');
    document.getElementById('selected-class-pkg').textContent = pkg || '(default)';

    document.getElementById('selected-class-ca').textContent = metric.afferent_coupling;
    document.getElementById('selected-class-ce').textContent = metric.efferent_coupling;
    
    const instability = metric.instability;
    document.getElementById('selected-class-instability').textContent = instability.toFixed(2);
    
    // Instability fill
    const fill = document.getElementById('instability-fill');
    fill.style.width = `${instability * 100}%`;

    // Instability explanation
    const desc = document.getElementById('instability-desc');
    if (instability === 0 && metric.afferent_coupling > 0) {
        desc.textContent = "This class is fully STABLE (I = 0). Many classes depend on it, but it depends on nothing. Changing this class requires care because of ripple effects.";
    } else if (instability === 1 && metric.efferent_coupling > 0) {
        desc.textContent = "This class is fully UNSTABLE (I = 1). It depends on other classes but has no dependants. It is very easy to modify without impacting other files.";
    } else if (metric.afferent_coupling === 0 && metric.efferent_coupling === 0) {
        desc.textContent = "This class is isolated. It has no afferent or efferent dependencies.";
    } else {
        desc.textContent = `This class has moderate instability (I = ${instability.toFixed(2)}). It is partially stable: it calls other modules and is also called by other modules.`;
    }
}

// Helper: map instability (0-1) to cyan/purple/pink gradient
function getInstabilityColor(instability) {
    // 0 = stable (pure cyan #06b6d4)
    // 1 = unstable (rose #f43f5e)
    // Interpolate RGB:
    // Cyan: rgb(6, 182, 212)
    // Rose: rgb(244, 63, 94)
    const r = Math.round(6 + (244 - 6) * instability);
    const g = Math.round(182 + (63 - 182) * instability);
    const b = Math.round(212 + (94 - 212) * instability);
    return `rgb(${r}, ${g}, ${b})`;
}

// --- Utilities ---
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
