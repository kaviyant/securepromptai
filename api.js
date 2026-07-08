/**
 * SecurePrompt AI - API Communication Module
 */

const Api = {
  /**
   * Sends the prompt and metadata to the FastAPI backend for scanning.
   * @param {string} promptText The user's input prompt
   * @param {string} siteKey The identified website key (e.g., 'chatgpt')
   * @param {string} url The full webpage URL
   * @returns {Promise<object>} The scan result object
   */
  async scanPrompt(promptText, siteKey, url) {
    try {
      // 1. Fetch current settings from chrome storage
      const settings = await new Promise((resolve) => {
        chrome.storage.local.get([CONFIG.STORAGE_KEYS.SETTINGS], (result) => {
          resolve(result[CONFIG.STORAGE_KEYS.SETTINGS] || CONFIG.DEFAULT_SETTINGS);
        });
      });

      // If protection is disabled globally, allow immediately
      if (!settings.isEnabled || !settings.sites[siteKey]) {
        return {
          risk_score: 0,
          risk_level: 'None',
          action: CONFIG.ACTIONS.ALLOW,
          sanitized_prompt: promptText,
          reason: 'Protection disabled for this site or globally.'
        };
      }

      // 2. Gather metadata
      const sessionId = await Utils.getOrCreateSessionId();
      const browserInfo = Utils.getBrowserMetadata();
      const timestamp = Date.now();
      
      const payload = {
        prompt: promptText,
        website: url,
        timestamp: timestamp,
        session_id: sessionId,
        browser_info: browserInfo
      };

      const backendUrl = settings.backendUrl || CONFIG.DEFAULT_BACKEND_URL;
      const scanUrl = `${backendUrl.replace(/\/+$/, '')}${CONFIG.SCAN_ENDPOINT}`;

      // 3. Perform network call with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

      const response = await fetch(scanUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      
      // Validate action is correct, default to ALLOW if invalid
      if (!result.action || !Object.values(CONFIG.ACTIONS).includes(result.action)) {
        result.action = CONFIG.ACTIONS.ALLOW;
      }
      
      return result;

    } catch (error) {
      console.error('SecurePrompt AI scan API failed:', error);
      
      // Fallback: If backend is down, we notify the user.
      // To prevent disrupting work entirely, we return a fallback response.
      // We can warn the user that scan failed (offline), allowing them to proceed or wait.
      return {
        risk_score: 0,
        risk_level: 'Unknown',
        action: CONFIG.ACTIONS.WARN,
        sanitized_prompt: promptText,
        reason: 'Backend connection failed. Could not scan prompt for security violations.',
        error: error.message,
        isOfflineFallback: true
      };
    }
  }
};

// Export to global scope or module exports
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Api;
} else {
  globalThis.Api = Api;
}
