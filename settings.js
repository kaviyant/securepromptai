/**
 * SecurePrompt AI - Settings panel controller
 */

document.addEventListener('DOMContentLoaded', async () => {
  const backendUrlInput = document.getElementById('backend-url');
  const btnTestConn = document.getElementById('btn-test-conn');
  const testText = document.getElementById('test-text');
  const testLoader = document.getElementById('test-loader');
  const connResult = document.getElementById('conn-result');
  
  const sensitivitySlider = document.getElementById('sensitivity-slider');
  const sensitivityDisplay = document.getElementById('sensitivity-display');
  const offlineActionSelect = document.getElementById('opt-offline-action');
  const interceptionModeSelect = document.getElementById('opt-interception-mode');
  
  const btnSave = document.getElementById('btn-save-settings');
  const alertBanner = document.getElementById('alert-banner');
  const alertMessage = document.getElementById('alert-message');
  const alertClose = document.getElementById('alert-close');
  
  let currentSettings = null;
 
  // 1. Load Configurations from Chrome Storage
  async function loadSettings() {
    const result = await new Promise((resolve) => {
      chrome.storage.local.get([CONFIG.STORAGE_KEYS.SETTINGS], (res) => {
        resolve(res[CONFIG.STORAGE_KEYS.SETTINGS] || CONFIG.DEFAULT_SETTINGS);
      });
    });
    
    currentSettings = result;
    
    // Fill Form Inputs
    backendUrlInput.value = currentSettings.backendUrl || CONFIG.DEFAULT_BACKEND_URL;
    sensitivitySlider.value = currentSettings.sensitivityThreshold || 50;
    sensitivityDisplay.textContent = sensitivitySlider.value;
    offlineActionSelect.value = currentSettings.offlineFallback || 'WARN';
    interceptionModeSelect.value = currentSettings.interceptionMode || 'MANUAL';
    
    // Fill AI Site Checkbox Toggles
    for (const siteKey of Object.keys(CONFIG.SITES)) {
      const checkbox = document.getElementById(`site-${siteKey}`);
      if (checkbox) {
        // Set checkbox value, default to true if not configured
        checkbox.checked = currentSettings.sites[siteKey] !== false;
      }
    }
  }

  // Sync sensitivity display text
  sensitivitySlider.addEventListener('input', () => {
    sensitivityDisplay.textContent = sensitivitySlider.value;
  });

  // 2. Health check test connection to FastAPI Backend
  btnTestConn.addEventListener('click', async () => {
    const url = backendUrlInput.value.trim();
    if (!url) {
      showConnectionStatus(false, 'Please enter a valid URL.');
      return;
    }

    // Reset indicator
    connResult.className = 'conn-result hidden';
    testText.textContent = 'Testing...';
    testLoader.classList.remove('hidden');
    btnTestConn.disabled = true;

    try {
      // Send test fetch request to FastAPI backend health/scan endpoint.
      // We can hit root endpoint or '/api/scan' with empty payload.
      // Standard FastAPI endpoints usually return status/documentation, or we can try a GET on root.
      const healthUrl = `${url.replace(/\/+$/, '')}/`;
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000); // 4 seconds timeout

      const response = await fetch(healthUrl, {
        method: 'GET',
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      // Standard FastAPI root or 404/405/422 responses still prove the server is listening!
      if (response.status >= 200 && response.status < 500) {
        showConnectionStatus(true, `Connected successfully! (Server returned HTTP ${response.status})`);
      } else {
        showConnectionStatus(false, `Server responded with HTTP error ${response.status}`);
      }
    } catch (error) {
      console.warn('Backend connection health test failed:', error);
      showConnectionStatus(false, 'Connection failed. Ensure the FastAPI backend is running and CORS allows requests.');
    } finally {
      testText.textContent = 'Test Connection';
      testLoader.classList.add('hidden');
      btnTestConn.disabled = false;
    }
  });

  function showConnectionStatus(success, message) {
    connResult.textContent = message;
    connResult.className = `conn-result ${success ? 'success' : 'error'}`;
  }

  // 3. Save Settings to storage
  btnSave.addEventListener('click', () => {
    const backendUrl = backendUrlInput.value.trim();
    if (!backendUrl) {
      showAlert(false, 'API URL is required.');
      return;
    }

    // Retrieve checkbox values
    const siteSettings = {};
    for (const siteKey of Object.keys(CONFIG.SITES)) {
      const checkbox = document.getElementById(`site-${siteKey}`);
      if (checkbox) {
        siteSettings[siteKey] = checkbox.checked;
      }
    }

    const updatedSettings = {
      backendUrl: backendUrl,
      isEnabled: currentSettings.isEnabled, // preserve global enabled state
      sensitivityThreshold: parseInt(sensitivitySlider.value),
      interceptionMode: interceptionModeSelect.value,
      offlineFallback: offlineActionSelect.value,
      sites: siteSettings
    };

    chrome.storage.local.set({ [CONFIG.STORAGE_KEYS.SETTINGS]: updatedSettings }, () => {
      showAlert(true, 'Settings updated successfully!');
      currentSettings = updatedSettings;
    });
  });

  // 4. Alert notifications helper
  function showAlert(success, message) {
    alertMessage.textContent = message;
    alertBanner.className = `alert-banner ${success ? '' : 'error'}`;
    
    // Auto scroll to top to see banner
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Auto dismiss after 3.5s
    setTimeout(() => {
      alertBanner.classList.add('hidden');
    }, 3500);
  }

  alertClose.addEventListener('click', () => {
    alertBanner.classList.add('hidden');
  });

  // Run initialization
  await loadSettings();
});
