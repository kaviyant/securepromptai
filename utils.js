/**
 * SecurePrompt AI - Utility Functions
 */

const Utils = {
  /**
   * Generates a unique UUID v4 string
   * @returns {string}
   */
  generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  },

  /**
   * Gets or creates a persistent session ID
   * @returns {Promise<string>}
   */
  async getOrCreateSessionId() {
    return new Promise((resolve) => {
      chrome.storage.local.get(['session_id'], (result) => {
        if (result.session_id) {
          resolve(result.session_id);
        } else {
          const newSessionId = Utils.generateUUID();
          chrome.storage.local.set({ session_id: newSessionId }, () => {
            resolve(newSessionId);
          });
        }
      });
    });
  },

  /**
   * Identifies the current AI site from the browser URL
   * @param {string} url
   * @returns {string|null} site key (e.g. 'chatgpt', 'gemini') or null if not matched
   */
  getSiteKeyFromUrl(url) {
    if (!url) return null;
    try {
      const parsedUrl = new URL(url);
      const host = parsedUrl.hostname;
      
      for (const [key, siteInfo] of Object.entries(CONFIG.SITES)) {
        if (siteInfo.domains.some(domain => host === domain || host.endsWith('.' + domain))) {
          return key;
        }
      }
    } catch (e) {
      console.error('Failed to parse URL for site detection:', e);
    }
    return null;
  },

  /**
   * Retrieves browser and system metadata
   * @returns {object} Metadata object
   */
  getBrowserMetadata() {
    const userAgent = navigator.userAgent;
    let browserName = 'Unknown Browser';
    let browserVersion = 'Unknown';
    
    if (userAgent.indexOf('Chrome') > -1 && userAgent.indexOf('Edg') === -1) {
      browserName = 'Chrome';
      const match = userAgent.match(/Chrome\/([0-9.]+)/);
      if (match) browserVersion = match[1];
    } else if (userAgent.indexOf('Edg') > -1) {
      browserName = 'Edge';
      const match = userAgent.match(/Edg\/([0-9.]+)/);
      if (match) browserVersion = match[1];
    } else if (userAgent.indexOf('Safari') > -1 && userAgent.indexOf('Chrome') === -1) {
      browserName = 'Safari';
      const match = userAgent.match(/Version\/([0-9.]+)/);
      if (match) browserVersion = match[1];
    } else if (userAgent.indexOf('Firefox') > -1) {
      browserName = 'Firefox';
      const match = userAgent.match(/Firefox\/([0-9.]+)/);
      if (match) browserVersion = match[1];
    }

    let osName = 'Unknown OS';
    if (userAgent.indexOf('Win') > -1) osName = 'Windows';
    else if (userAgent.indexOf('Mac') > -1) osName = 'macOS';
    else if (userAgent.indexOf('X11') > -1) osName = 'UNIX';
    else if (userAgent.indexOf('Linux') > -1) osName = 'Linux';

    return {
      browser: browserName,
      browserVersion: browserVersion,
      os: osName,
      userAgent: userAgent
    };
  },

  /**
   * Format a date to a readable local string
   * @param {number|string} timestamp 
   * @returns {string}
   */
  formatDateTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }) + ' ' + date.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  },

  /**
   * Escape HTML special characters to prevent XSS
   * @param {string} text 
   * @returns {string}
   */
  escapeHtml(text) {
    if (!text) return '';
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  },

  /**
   * Highlights specified sensitive terms in a text, outputting safe HTML
   * @param {string} text The original text
   * @param {string[]|string} sensitiveTerms Terms to highlight or single pattern
   * @returns {string} Safe HTML with matching terms wrapped in highlighting tags
   */
  highlightSensitiveText(text, sensitiveTerms) {
    if (!text) return '';
    const safeText = Utils.escapeHtml(text);
    
    if (!sensitiveTerms || (Array.isArray(sensitiveTerms) && sensitiveTerms.length === 0)) {
      return safeText;
    }
    
    // Normalize to an array of strings
    const terms = Array.isArray(sensitiveTerms) 
      ? sensitiveTerms 
      : [sensitiveTerms];
      
    // Filter and sort terms by length descending to prevent shorter sub-terms 
    // from breaking HTML tags or larger matches
    const sortedTerms = terms
      .map(t => typeof t === 'string' ? t.trim() : String(t))
      .filter(t => t.length > 0)
      .sort((a, b) => b.length - a.length);

    if (sortedTerms.length === 0) {
      return safeText;
    }

    // Build regex to match terms (escaped for safety)
    const escapedTerms = sortedTerms.map(t => t.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&'));
    // Match outside already created HTML tags if any (though safeText is raw text at first)
    try {
      const regex = new RegExp(`(${escapedTerms.join('|')})`, 'gi');
      return safeText.replace(regex, '<span class="sp-highlight">$1</span>');
    } catch (e) {
      console.error('Failed to compile highlight regex:', e);
      return safeText;
    }
  }
};

// Export to global scope or module exports
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Utils;
} else {
  globalThis.Utils = Utils;
}
