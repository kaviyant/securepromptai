/**
 * SecurePrompt AI - Service Worker (background.js)
 * Version: 1.0.1 (Cache flush reload trigger)
 * Coordinates extension lifecycle, settings initialization, API scanning,
 * bypasses page-level CSP policies, and manages audit history logs.
 */

// Import required utilities and configurations
importScripts('config.js', 'utils.js', 'api.js');

// Initialize default settings on installation
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    chrome.storage.local.set({
      [CONFIG.STORAGE_KEYS.SETTINGS]: CONFIG.DEFAULT_SETTINGS,
      [CONFIG.STORAGE_KEYS.HISTORY]: [],
      'stats': {
        totalScans: 0,
        totalAllowed: 0,
        totalWarned: 0,
        totalBlocked: 0
      }
    }, () => {
      console.log('SecurePrompt AI initialized successfully.');
    });
  }
});

// Handle messages from Content Scripts and UI Panels
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'scanPrompt') {
    handleScanRequest(request, sendResponse);
    return true; // Keep message channel open for asynchronous response
  }
  
  if (request.action === 'getStats') {
    chrome.storage.local.get(['stats'], (result) => {
      sendResponse(result.stats || { totalScans: 0, totalAllowed: 0, totalWarned: 0, totalBlocked: 0 });
    });
    return true;
  }
  
  if (request.action === 'clearHistory') {
    chrome.storage.local.set({ [CONFIG.STORAGE_KEYS.HISTORY]: [] }, () => {
      // Reset stats counter
      chrome.storage.local.set({
        'stats': { totalScans: 0, totalAllowed: 0, totalWarned: 0, totalBlocked: 0 }
      }, () => {
        sendResponse({ success: true });
      });
    });
    return true;
  }
});

/**
 * Executes a prompt scan and records transaction details in the audit log.
 * @param {object} request The message payload
 * @param {function} sendResponse Callback to return scanning results
 */
async function handleScanRequest(request, sendResponse) {
  const { promptText, siteKey, url } = request;
  
  try {
    // 1. Perform the API call via our api.js module (runs in background context to bypass host page CSP)
    const scanResult = await Api.scanPrompt(promptText, siteKey, url);
    
    // If it's an allow/warn/block action, write it to history
    await saveScanToHistory({
      promptText,
      siteKey,
      url,
      scanResult
    });

    sendResponse({ success: true, result: scanResult });
  } catch (error) {
    console.error('Background processing error:', error);
    sendResponse({
      success: false,
      error: error.message,
      result: {
        risk_score: 0,
        risk_level: 'Unknown',
        action: CONFIG.ACTIONS.WARN,
        sanitized_prompt: promptText,
        reason: 'Error occurred during scan communication: ' + error.message,
        isOfflineFallback: true
      }
    });
  }
}

/**
 * Saves a scan transaction to the audit history list in chrome.storage.local.
 * Updates global security stats as well.
 * @param {object} data
 */
async function saveScanToHistory({ promptText, siteKey, url, scanResult }) {
  return new Promise((resolve) => {
    chrome.storage.local.get([CONFIG.STORAGE_KEYS.HISTORY, 'stats'], (result) => {
      const history = result[CONFIG.STORAGE_KEYS.HISTORY] || [];
      const stats = result.stats || { totalScans: 0, totalAllowed: 0, totalWarned: 0, totalBlocked: 0 };
      
      const newRecord = {
        id: Utils.generateUUID(),
        timestamp: Date.now(),
        website: new URL(url).hostname,
        siteKey: siteKey,
        originalPrompt: promptText,
        sanitizedPrompt: scanResult.sanitized_prompt || promptText,
        riskScore: scanResult.risk_score || 0,
        riskLevel: scanResult.risk_level || 'None',
        action: scanResult.action,
        reason: scanResult.reason || '',
        flaggedTerms: scanResult.flagged_terms || [],
        isOfflineFallback: !!scanResult.isOfflineFallback
      };
      
      // Add to beginning of history list
      history.unshift(newRecord);
      
      // Limit audit log to latest 500 records to save memory
      if (history.length > 500) {
        history.pop();
      }

      // Update statistics
      stats.totalScans += 1;
      if (scanResult.action === CONFIG.ACTIONS.ALLOW) {
        stats.totalAllowed += 1;
      } else if (scanResult.action === CONFIG.ACTIONS.WARN) {
        stats.totalWarned += 1;
      } else if (scanResult.action === CONFIG.ACTIONS.BLOCK) {
        stats.totalBlocked += 1;
      }

      chrome.storage.local.set({
        [CONFIG.STORAGE_KEYS.HISTORY]: history,
        'stats': stats
      }, () => {
        resolve();
      });
    });
  });
}
