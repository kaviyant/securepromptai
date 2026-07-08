/**
 * SecurePrompt AI - History page controller
 */

document.addEventListener('DOMContentLoaded', async () => {
  const logsTbody = document.getElementById('logs-tbody');
  const emptyState = document.getElementById('empty-state');
  const searchInput = document.getElementById('search-input');
  const filterSite = document.getElementById('filter-site');
  const filterRisk = document.getElementById('filter-risk');
  const btnClearLogs = document.getElementById('btn-clear-logs');
  
  const detailModal = document.getElementById('detail-modal');
  const modalClose = document.getElementById('modal-close');
  const modalContent = document.getElementById('modal-body-content');

  let auditRecords = [];

  // 1. Load History Logs from Storage
  async function loadLogs() {
    return new Promise((resolve) => {
      chrome.storage.local.get([CONFIG.STORAGE_KEYS.HISTORY], (result) => {
        auditRecords = result[CONFIG.STORAGE_KEYS.HISTORY] || [];
        resolve(auditRecords);
      });
    });
  }

  // 2. Render Audit Table rows with filters applied
  function renderTable() {
    const searchQuery = searchInput.value.trim().toLowerCase();
    const siteFilter = filterSite.value;
    const riskFilter = filterRisk.value;

    // Filter records
    const filteredRecords = auditRecords.filter(record => {
      // 1. Text Search Filter (original prompt or violation reason)
      const matchesSearch = !searchQuery || 
        record.originalPrompt.toLowerCase().includes(searchQuery) ||
        (record.reason && record.reason.toLowerCase().includes(searchQuery));
      
      // 2. Site Filter
      const matchesSite = siteFilter === 'all' || record.siteKey === siteFilter;
      
      // 3. Risk Level Filter
      let matchesRisk = true;
      if (riskFilter !== 'all') {
        if (riskFilter === 'None') {
          matchesRisk = record.riskLevel === 'None' || record.riskLevel === 'Unknown' || record.action === CONFIG.ACTIONS.ALLOW;
        } else {
          matchesRisk = record.riskLevel.toLowerCase() === riskFilter.toLowerCase();
        }
      }

      return matchesSearch && matchesSite && matchesRisk;
    });

    // Populate rows
    logsTbody.innerHTML = '';
    
    if (filteredRecords.length === 0) {
      emptyState.classList.remove('hidden');
      document.querySelector('.audit-table').style.display = 'none';
      return;
    }

    emptyState.classList.add('hidden');
    document.querySelector('.audit-table').style.display = 'table';

    filteredRecords.forEach(record => {
      const tr = document.createElement('tr');
      tr.id = `row-${record.id}`;
      
      const siteName = CONFIG.SITES[record.siteKey]?.name || record.website || 'Unknown AI';
      const formattedTime = Utils.formatDateTime(record.timestamp);
      
      // Badges classes
      const riskClass = `badge-${record.riskLevel.toLowerCase()}`;
      const actionClass = `action-${record.action.toLowerCase()}`;
      
      // Truncated prompt
      const promptSummary = record.originalPrompt.length > 50 
        ? Utils.escapeHtml(record.originalPrompt.substring(0, 50)) + '...'
        : Utils.escapeHtml(record.originalPrompt);

      tr.innerHTML = `
        <td class="timestamp-col">${formattedTime}</td>
        <td><span class="site-badge">${siteName}</span></td>
        <td><span class="risk-badge ${riskClass}">${record.riskLevel}</span></td>
        <td><span class="action-text ${actionClass}">${record.action}</span></td>
        <td class="prompt-summary">${promptSummary}</td>
        <td>
          <button class="btn-view" data-id="${record.id}">View Details</button>
        </td>
      `;
      
      logsTbody.appendChild(tr);
    });

    // Attach click events to "View Details" buttons
    document.querySelectorAll('.btn-view').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = e.target.getAttribute('data-id');
        openDetailModal(id);
      });
    });
  }

  // 3. Open Log Details Dialog
  function openDetailModal(id) {
    const record = auditRecords.find(r => r.id === id);
    if (!record) return;

    const siteName = CONFIG.SITES[record.siteKey]?.name || record.website || 'Unknown AI';
    const formattedTime = Utils.formatDateTime(record.timestamp);
    const riskClass = `badge-${record.riskLevel.toLowerCase()}`;
    const actionClass = `action-${record.action.toLowerCase()}`;

    // Highlight flagged terms in the original prompt preview
    const flaggedTerms = record.flaggedTerms || [];
    const highlightedPromptHtml = Utils.highlightSensitiveText(record.originalPrompt, flaggedTerms);

    // Build system info metadata string
    const browserStr = record.browserInfo 
      ? `${record.browserInfo.browser} v${record.browserInfo.browserVersion} (${record.browserInfo.os})`
      : 'Unknown Browser';

    let reasonBannerHtml = '';
    if (record.action !== CONFIG.ACTIONS.ALLOW) {
      reasonBannerHtml = `
        <div class="detail-block-reason">
          <h4>Violation Warning Reason</h4>
          <p>${Utils.escapeHtml(record.reason || 'Potential sensitive data exposure detected.')}</p>
        </div>
      `;
    } else if (record.isOfflineFallback) {
      reasonBannerHtml = `
        <div class="detail-block-reason offline-warning">
          <h4>Offline Mode Fallback</h4>
          <p>The backend was unreachable during this scan. Submissions were allowed via the offline policy.</p>
        </div>
      `;
    }

    modalContent.innerHTML = `
      <!-- Metadata Grid -->
      <div class="detail-grid-meta">
        <div class="meta-item">
          <span>Date / Time</span>
          <p>${formattedTime}</p>
        </div>
        <div class="meta-item">
          <span>AI Platform</span>
          <p>${siteName}</p>
        </div>
        <div class="meta-item">
          <span>Security Verdict</span>
          <p>
            <span class="risk-badge ${riskClass}">${record.riskLevel}</span>
            <span class="action-text ${actionClass}" style="margin-left: 8px;">${record.action}</span>
          </p>
        </div>
        <div class="meta-item" style="grid-column: span 2;">
          <span>Client System Details</span>
          <p>${browserStr}</p>
        </div>
        <div class="meta-item">
          <span>Audit Session ID</span>
          <p style="font-family: monospace; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${record.id}">${record.id}</p>
        </div>
      </div>

      <!-- Violation Reason If Any -->
      ${reasonBannerHtml}

      <!-- Side-by-Side Prompt Comparison -->
      <div class="prompt-comparison">
        <div class="comparison-box">
          <label>Original Prompt Submission</label>
          <div class="comparison-content flagged">${highlightedPromptHtml}</div>
        </div>
        <div class="comparison-box">
          <label>Sanitized Output Sent to AI</label>
          <div class="comparison-content sanitized">${Utils.escapeHtml(record.sanitizedPrompt)}</div>
        </div>
      </div>
    `;

    detailModal.classList.remove('hidden');
  }

  // Close modal click handlers
  modalClose.addEventListener('click', () => {
    detailModal.classList.add('hidden');
  });

  detailModal.addEventListener('click', (e) => {
    if (e.target === detailModal) {
      detailModal.classList.add('hidden');
    }
  });

  // 4. Clear Audit Logs handler
  btnClearLogs.addEventListener('click', () => {
    const confirmed = confirm('Are you sure you want to permanently clear all security audit logs? This action cannot be undone.');
    if (confirmed) {
      chrome.runtime.sendMessage({ action: 'clearHistory' }, (response) => {
        if (response && response.success) {
          auditRecords = [];
          renderTable();
        }
      });
    }
  });

  // 5. Setup search and filter listeners
  searchInput.addEventListener('input', renderTable);
  filterSite.addEventListener('change', renderTable);
  filterRisk.addEventListener('change', renderTable);

  // Initialize page logs loading
  await loadLogs();
  renderTable();
});
