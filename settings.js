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
  
  // Document Verification Elements
  const docVerifyToggle = document.getElementById('opt-doc-verify');
  const restrictedFilesInput = document.getElementById('restricted-files');
  
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
    if (backendUrlInput) backendUrlInput.value = currentSettings.backendUrl || CONFIG.DEFAULT_BACKEND_URL;
    if (sensitivitySlider) {
      sensitivitySlider.value = currentSettings.sensitivityThreshold || 50;
      if (sensitivityDisplay) sensitivityDisplay.textContent = sensitivitySlider.value;
    }
    if (offlineActionSelect) offlineActionSelect.value = currentSettings.offlineFallback || 'WARN';
    if (interceptionModeSelect) interceptionModeSelect.value = currentSettings.interceptionMode || 'MANUAL';
    
    if (docVerifyToggle) {
      docVerifyToggle.checked = currentSettings.enableDocumentVerification !== false;
    }
    if (restrictedFilesInput) {
      const fileList = Array.isArray(currentSettings.restrictedFiles) ? currentSettings.restrictedFiles : [];
      restrictedFilesInput.value = fileList.join('\n');
    }
    
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
  if (sensitivitySlider) {
    sensitivitySlider.addEventListener('input', () => {
      if (sensitivityDisplay) sensitivityDisplay.textContent = sensitivitySlider.value;
    });
  }

  // 2. Health check test connection to FastAPI Backend
  if (btnTestConn) {
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
        const healthUrl = `${url.replace(/\/+$/, '')}/`;
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 4000); // 4 seconds timeout

        const response = await fetch(healthUrl, {
          method: 'GET',
          signal: controller.signal
        });

        clearTimeout(timeoutId);

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
  }

  function showConnectionStatus(success, message) {
    if (connResult) {
      connResult.textContent = message;
      connResult.className = `conn-result ${success ? 'success' : 'error'}`;
    }
  }

  // 3. Save Settings to storage
  if (btnSave) {
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

      const restrictedFilesList = (restrictedFilesInput?.value || '')
        .split(/[\n,]/)
        .map(f => f.trim())
        .filter(f => f.length > 0);

      const updatedSettings = {
        backendUrl: backendUrl,
        isEnabled: currentSettings ? currentSettings.isEnabled : true, // preserve global enabled state
        sensitivityThreshold: parseInt(sensitivitySlider.value),
        interceptionMode: interceptionModeSelect.value,
        offlineFallback: offlineActionSelect.value,
        enableDocumentVerification: docVerifyToggle ? docVerifyToggle.checked : true,
        restrictedFiles: restrictedFilesList,
        sites: siteSettings
      };

      chrome.storage.local.set({ [CONFIG.STORAGE_KEYS.SETTINGS]: updatedSettings }, () => {
        showAlert(true, 'Settings updated successfully!');
        currentSettings = updatedSettings;
      });
    });
  }



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
