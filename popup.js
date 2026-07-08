/**
 * SecurePrompt AI - Action Popup controller
 */

document.addEventListener('DOMContentLoaded', async () => {
  const globalToggle = document.getElementById('global-toggle');
  const statusText = document.getElementById('status-text');
  const siteToggle = document.getElementById('site-toggle');
  const siteName = document.getElementById('site-name');
  const siteIndicator = document.getElementById('site-indicator');
  
  const statScans = document.getElementById('stat-scans');
  const statBlocked = document.getElementById('stat-blocked');
  const statWarned = document.getElementById('stat-warned');
  
  const btnHistory = document.getElementById('btn-history');
  const btnSettings = document.getElementById('btn-settings');

  let currentSettings = null;
  let activeTabSiteKey = null;

  // 1. Fetch current settings and statistics
  async function init() {
    // Load settings from storage
    const result = await new Promise((resolve) => {
      chrome.storage.local.get([CONFIG.STORAGE_KEYS.SETTINGS], (res) => {
        resolve(res[CONFIG.STORAGE_KEYS.SETTINGS] || CONFIG.DEFAULT_SETTINGS);
      });
    });
    currentSettings = result;

    // Apply settings to UI
    globalToggle.checked = currentSettings.isEnabled;
    updateGlobalStatusText(currentSettings.isEnabled);

    // Get Active Tab to configure Site Specific Toggle
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs.length > 0 && tabs[0].url) {
        const tab = tabs[0];
        activeTabSiteKey = Utils.getSiteKeyFromUrl(tab.url);
        
        if (activeTabSiteKey) {
          const siteInfo = CONFIG.SITES[activeTabSiteKey];
          siteName.textContent = siteInfo.name;
          siteIndicator.className = 'site-dot active';
          
          // Set site toggle state
          siteToggle.disabled = false;
          siteToggle.checked = currentSettings.sites[activeTabSiteKey] !== false;
        } else {
          // Not an AI site
          try {
            const parsedUrl = new URL(tab.url);
            siteName.textContent = parsedUrl.hostname || 'Unrecognized Webpage';
          } catch(e) {
            siteName.textContent = 'Unsupported Page';
          }
          siteIndicator.className = 'site-dot';
          siteToggle.checked = false;
          siteToggle.disabled = true;
        }
      } else {
        siteName.textContent = 'No Active Website';
        siteIndicator.className = 'site-dot';
        siteToggle.checked = false;
        siteToggle.disabled = true;
      }
    });

    // Fetch Stats from background
    chrome.runtime.sendMessage({ action: 'getStats' }, (stats) => {
      if (stats) {
        statScans.textContent = stats.totalScans || 0;
        statBlocked.textContent = stats.totalBlocked || 0;
        // Total warnings triggers
        statWarned.textContent = stats.totalWarned || 0;
      }
    });
  }

  function updateGlobalStatusText(enabled) {
    if (enabled) {
      statusText.textContent = 'Active';
      statusText.className = 'status-value active';
    } else {
      statusText.textContent = 'Paused';
      statusText.className = 'status-value inactive';
    }
  }

  // 2. Event Listeners for Toggles

  globalToggle.addEventListener('change', () => {
    const isEnabled = globalToggle.checked;
    updateGlobalStatusText(isEnabled);
    
    currentSettings.isEnabled = isEnabled;
    chrome.storage.local.set({ [CONFIG.STORAGE_KEYS.SETTINGS]: currentSettings });
  });

  siteToggle.addEventListener('change', () => {
    if (!activeTabSiteKey) return;
    
    currentSettings.sites[activeTabSiteKey] = siteToggle.checked;
    chrome.storage.local.set({ [CONFIG.STORAGE_KEYS.SETTINGS]: currentSettings });
  });

  // 3. Navigation Actions

  btnSettings.addEventListener('click', () => {
    if (chrome.runtime.openOptionsPage) {
      chrome.runtime.openOptionsPage();
    } else {
      chrome.tabs.create({ url: chrome.runtime.getURL('settings.html') });
    }
  });

  btnHistory.addEventListener('click', () => {
    chrome.tabs.create({ url: chrome.runtime.getURL('history.html') });
  });

  // Run initialization
  await init();
});
