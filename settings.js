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
  
  // Document Indexer Elements
  const adminTokenInput = document.getElementById('admin-token');
  const docNameInput = document.getElementById('doc-name');
  const docFileInput = document.getElementById('doc-file');
  const btnUploadDoc = document.getElementById('btn-upload-doc');
  const uploadText = document.getElementById('upload-text');
  const uploadLoader = document.getElementById('upload-loader');
  const uploadResult = document.getElementById('upload-result');
  
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
    adminTokenInput.value = currentSettings.adminToken || '';
    
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
      adminToken: adminTokenInput.value.trim(),
      sites: siteSettings
    };

    chrome.storage.local.set({ [CONFIG.STORAGE_KEYS.SETTINGS]: updatedSettings }, () => {
      showAlert(true, 'Settings updated successfully!');
      currentSettings = updatedSettings;
    });
  });

  // 3b. Upload and Index Document via FastAPI Backend
  btnUploadDoc.addEventListener('click', async () => {
    const url = backendUrlInput.value.trim();
    const token = adminTokenInput.value.trim();
    const docName = docNameInput.value.trim();
    const file = docFileInput.files[0];

    if (!url) {
      showUploadStatus(false, 'Please test/verify your Backend URL first.');
      return;
    }
    if (!token) {
      showUploadStatus(false, 'Please enter your Admin Authorization Token.');
      return;
    }
    if (!file) {
      showUploadStatus(false, 'Please select a document file to upload.');
      return;
    }

    // Reset status
    uploadResult.className = 'conn-result hidden';
    uploadText.textContent = 'Uploading...';
    uploadLoader.classList.remove('hidden');
    btnUploadDoc.disabled = true;

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Build target URL
      let uploadUrl = `${url.replace(/\/+$/, '')}/api/documents/index`;
      if (docName) {
        uploadUrl += `?doc_id=${encodeURIComponent(docName)}`;
      }

      const response = await fetch(uploadUrl, {
        method: 'POST',
        headers: {
          'Authorization': token.startsWith('Bearer ') ? token : `Bearer ${token}`
        },
        body: formData
      });

      const resData = await response.json();

      if (response.ok) {
        showUploadStatus(true, `Success: ${resData.message || 'Document indexed successfully!'}`);
        docFileInput.value = ''; // clear file input
        docNameInput.value = ''; // clear name input
      } else {
        // If server returns error details as array (validation failures)
        const errorMsg = typeof resData.detail === 'string' ? resData.detail : JSON.stringify(resData.detail);
        showUploadStatus(false, `Upload failed: ${errorMsg || 'Server error'}`);
      }
    } catch (error) {
      console.error('Document upload failed:', error);
      showUploadStatus(false, 'Connection failed. Please ensure the backend is running and CORS is configured.');
    } finally {
      uploadText.textContent = 'Upload & Index Document';
      uploadLoader.classList.add('hidden');
      btnUploadDoc.disabled = false;
    }
  });

  function showUploadStatus(success, message) {
    uploadResult.textContent = message;
    uploadResult.className = `conn-result ${success ? 'success' : 'error'}`;
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
