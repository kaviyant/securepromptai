/**
 * SecurePrompt AI - Content Script (content.js)
 * Intercepts user prompt submission, injects isolated Shadow DOM overlay for UX states,
 * and programmatically handles allowance/sanitization.
 */

(async () => {
  // 1. Identify site and check if supported
  const siteKey = Utils.getSiteKeyFromUrl(window.location.href);
  if (!siteKey) return; // Exit if website is not supported
  
  console.log(`[SecurePrompt AI] Extension active on ${CONFIG.SITES[siteKey].name}`);

  // 2. Active State Flags
  let isApprovedPrompt = false;
  let currentSettings = null;
  let shadowRoot = null;
  let overlayElement = null;
  let activeInputEl = null;
  let activeSubmitEl = null;

  // 3. Fetch Initial Settings
  async function loadSettings() {
    return new Promise((resolve) => {
      chrome.storage.local.get([CONFIG.STORAGE_KEYS.SETTINGS], (result) => {
        currentSettings = result[CONFIG.STORAGE_KEYS.SETTINGS] || CONFIG.DEFAULT_SETTINGS;
        resolve(currentSettings);
      });
    });
  }
  
  await loadSettings();

  // Listen for storage changes to update settings dynamically
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'local' && changes[CONFIG.STORAGE_KEYS.SETTINGS]) {
      currentSettings = changes[CONFIG.STORAGE_KEYS.SETTINGS].newValue;
    }
  });

  // 4. Initialize Shadow DOM Overlay UI
  function initOverlay() {
    if (shadowRoot) return;

    // Create host container
    const container = document.createElement('div');
    container.id = 'secure-prompt-ai-root';
    // Position fixed to cover entire viewport, highest z-index
    container.style.position = 'fixed';
    container.style.top = '0';
    container.style.left = '0';
    container.style.width = '100vw';
    container.style.height = '100vh';
    container.style.zIndex = '2147483647'; // Max z-index
    container.style.pointerEvents = 'none'; // Only allow clicks on modal content
    
    document.body.appendChild(container);

    // Attach open Shadow DOM for style isolation
    shadowRoot = container.attachShadow({ mode: 'open' });

    // Inject Stylesheet
    const styleEl = document.createElement('style');
    styleEl.textContent = getOverlayStyles();
    shadowRoot.appendChild(styleEl);

    // Inject Modal Structure
    overlayElement = document.createElement('div');
    overlayElement.id = 'sp-overlay';
    overlayElement.className = 'sp-overlay hidden';
    overlayElement.innerHTML = `
      <div class="sp-backdrop"></div>
      <div class="sp-modal-container">
        <div class="sp-modal">
          <div id="sp-modal-content"></div>
        </div>
      </div>
    `;
    shadowRoot.appendChild(overlayElement);
  }

  // 5. DOM Resolution Heuristics
  
  /**
   * Check if element is the AI site's prompt input
   */
  function isInputElement(el) {
    if (!el) return false;
    const siteConfig = CONFIG.SITES[siteKey];
    
    // Check configured selectors
    for (const selector of siteConfig.inputSelectors) {
      if (el.matches && el.matches(selector)) return true;
    }

    // Generic heuristics
    const tagName = el.tagName;
    const isTextarea = tagName === 'TEXTAREA';
    const isEditable = el.getAttribute('contenteditable') === 'true';
    const isTextboxRole = el.getAttribute('role') === 'textbox';
    const isSearchbox = el.id === 'searchbox' || el.name === 'q';

    return isTextarea || isEditable || isTextboxRole || isSearchbox;
  }

  /**
   * Travel up parent nodes to identify the submit button
   */
  function findSubmitButton(targetEl) {
    if (!targetEl) return null;
    const siteConfig = CONFIG.SITES[siteKey];
    
    let el = targetEl;
    let depth = 0;
    
    // Traverse up to 6 nodes to find a clickable button
    while (el && depth < 6 && el !== document.body) {
      // Check configured selectors
      for (const selector of siteConfig.submitSelectors) {
        if (el.matches && el.matches(selector)) {
          return el;
        }
      }

      // Generic heuristics
      const tagName = el.tagName;
      const role = el.getAttribute('role');
      const ariaLabel = el.getAttribute('aria-label') || '';
      const title = el.getAttribute('title') || '';
      
      const isButtonTag = tagName === 'BUTTON';
      const isButtonRole = role === 'button';
      const hasSendLabel = /send|submit|submit-prompt|generate|run/i.test(ariaLabel) || /send|submit/i.test(title);
      
      if (isButtonTag || isButtonRole || hasSendLabel) {
        // Exclude inputs, scroll buttons or unrelated actions
        if (!['INPUT', 'TEXTAREA'].includes(tagName)) {
          return el;
        }
      }
      
      el = el.parentElement;
      depth++;
    }
    
    return null;
  }

  /**
   * Find prompt input text in the DOM
   */
  function getInputValue(inputEl) {
    if (!inputEl) return '';
    if (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT') {
      return inputEl.value;
    }
    if (inputEl.getAttribute('contenteditable') === 'true') {
      // Clean up extra spaces/newlines if needed, but innerText preserves line breaks
      return inputEl.innerText;
    }
    return inputEl.textContent || '';
  }

  /**
   * Inject sanitized prompt into editor field in a framework-safe way
   */
  function setInputValue(inputEl, text) {
    if (!inputEl) return;
    
    if (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT') {
      inputEl.value = text;
      inputEl.dispatchEvent(new Event('input', { bubbles: true }));
      inputEl.dispatchEvent(new Event('change', { bubbles: true }));
    } else if (inputEl.getAttribute('contenteditable') === 'true') {
      inputEl.focus();
      try {
        // Clear everything first
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(inputEl);
        selection.removeAllRanges();
        selection.addRange(range);
        
        // Execute insertText command (best compatibility for contenteditable frameworks like React/DraftJS/Lexical)
        document.execCommand('insertText', false, text);
      } catch (e) {
        console.warn('execCommand failed, falling back to direct DOM manipulation', e);
        inputEl.innerText = text;
        inputEl.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }
  }

  /**
   * Scan DOM to find the active prompt input box on the page.
   * Handles multi-input contexts in long chat histories.
   */
  function findAssociatedInput(submitBtn = null) {
    const siteConfig = CONFIG.SITES[siteKey];
    
    // 1. Proximity check: If we have the clicked submit button, search inside its parent container
    if (submitBtn) {
      let parent = submitBtn.parentElement;
      let depth = 0;
      while (parent && depth < 4 && parent !== document.body) {
        for (const selector of siteConfig.inputSelectors) {
          const el = parent.querySelector(selector);
          if (el) return el;
        }
        parent = parent.parentElement;
        depth++;
      }
    }

    // 2. Focus check: If the user is actively focusing a text input field, use it
    if (document.activeElement && isInputElement(document.activeElement)) {
      return document.activeElement;
    }

    // 3. Fallback: Query all inputs and select the LAST one (which is the main chat input at the bottom)
    for (const selector of siteConfig.inputSelectors) {
      const els = document.querySelectorAll(selector);
      if (els.length > 0) {
        return els[els.length - 1]; // Return bottom-most input element
      }
    }
    
    // 4. Generic broad fallbacks
    const textareas = document.querySelectorAll('textarea');
    if (textareas.length > 0) return textareas[textareas.length - 1];
    
    const editables = document.querySelectorAll('div[contenteditable="true"]');
    if (editables.length > 0) return editables[editables.length - 1];
    
    return null;
  }

  // 6. UI Rendering Controllers (Shadow DOM)

  function showOverlay(state, data = {}) {
    initOverlay();
    
    // Auto-detect theme from host website DOM or settings
    const isDark = document.documentElement.classList.contains('dark') || 
                  document.body.classList.contains('dark') || 
                  document.documentElement.getAttribute('data-theme') === 'dark' ||
                  window.matchMedia('(prefers-color-scheme: dark)').matches;
                  
    overlayElement.className = `sp-overlay ${isDark ? 'dark-theme' : 'light-theme'}`;
    containerElement().style.pointerEvents = 'auto'; // Block host page clicks

    const contentBox = shadowRoot.getElementById('sp-modal-content');
    contentBox.innerHTML = '';

    if (state === 'LOADING') {
      contentBox.innerHTML = `
        <div class="sp-loading-container">
          <div class="sp-loader"></div>
          <h3>SecurePrompt AI</h3>
          <p>Scanning prompt for sensitive details...</p>
        </div>
      `;
    } else if (state === 'WARN') {
      const badgeClass = `badge-${data.risk_level.toLowerCase()}`;
      contentBox.innerHTML = `
        <div class="sp-modal-header">
          <div class="sp-warning-icon">⚠️</div>
          <div>
            <h3>Security Warning</h3>
            <p>Risk Score: <span class="sp-risk-badge ${badgeClass}">${data.risk_score}/100 (${data.risk_level})</span></p>
          </div>
        </div>
        <div class="sp-modal-body">
          <p class="sp-reason-title">Violation Reason:</p>
          <p class="sp-reason">${Utils.escapeHtml(data.reason || 'Potential sensitive data exposure detected.')}</p>
          
          <p class="sp-reason-title">Sanitized Suggestion:</p>
          <div class="sp-prompt-preview">${Utils.escapeHtml(data.sanitized_prompt)}</div>
        </div>
        <div class="sp-modal-footer">
          <button id="sp-btn-cancel" class="sp-btn btn-secondary">Cancel</button>
          <button id="sp-btn-sanitize" class="sp-btn btn-primary">Sanitize & Send</button>
          <button id="sp-btn-continue" class="sp-btn btn-danger">Continue Anyway</button>
        </div>
      `;

      // Set up Warning Action Handlers
      shadowRoot.getElementById('sp-btn-cancel').onclick = () => hideOverlay();
      
      shadowRoot.getElementById('sp-btn-sanitize').onclick = () => {
        if (activeInputEl) {
          setInputValue(activeInputEl, data.sanitized_prompt);
        }
        hideOverlay();
        submitApprovedPrompt();
      };
      
      shadowRoot.getElementById('sp-btn-continue').onclick = () => {
        hideOverlay();
        submitApprovedPrompt();
      };
      
    } else if (state === 'BLOCK') {
      const badgeClass = `badge-${data.risk_level.toLowerCase()}`;
      const highlightedHtml = Utils.highlightSensitiveText(data.prompt, data.flagged_terms || []);
      
      contentBox.innerHTML = `
        <div class="sp-modal-header">
          <div class="sp-block-icon">🚫</div>
          <div>
            <h3>Prompt Blocked</h3>
            <p>Risk Score: <span class="sp-risk-badge ${badgeClass}">${data.risk_score}/100 (${data.risk_level})</span></p>
          </div>
        </div>
        <div class="sp-modal-body">
          <p class="sp-reason-title">Block Reason:</p>
          <p class="sp-reason">${Utils.escapeHtml(data.reason || 'This prompt contains sensitive data and has been blocked.')}</p>
          
          <p class="sp-reason-title">Detected Sensitive Content:</p>
          <div class="sp-prompt-preview highlight-mode">${highlightedHtml}</div>
        </div>
        <div class="sp-modal-footer">
          <button id="sp-btn-edit" class="sp-btn btn-primary">Edit Prompt</button>
        </div>
      `;

      shadowRoot.getElementById('sp-btn-edit').onclick = () => {
        hideOverlay();
        if (activeInputEl) activeInputEl.focus();
      };
    }
  }

  function hideOverlay() {
    if (overlayElement) {
      overlayElement.classList.add('hidden');
    }
    const container = containerElement();
    if (container) {
      container.style.pointerEvents = 'none'; // Re-enable clicking host page
    }
  }

  function containerElement() {
    return document.getElementById('secure-prompt-ai-root');
  }

  /**
   * Submits prompt with temporary bypass active
   */
  function submitApprovedPrompt() {
    isApprovedPrompt = true;
    
    // Find active submit button if not cached, or find associated send
    let submitBtn = activeSubmitEl || findSubmitButton(activeInputEl);
    if (!submitBtn) {
      // Find generic page submit button
      const siteConfig = CONFIG.SITES[siteKey];
      for (const selector of siteConfig.submitSelectors) {
        submitBtn = document.querySelector(selector);
        if (submitBtn) break;
      }
    }

    if (submitBtn) {
      console.log('[SecurePrompt AI] Re-submitting approved prompt.');
      submitBtn.click();
    } else {
      console.warn('[SecurePrompt AI] Submit button not found. Please click Send manually.');
    }
    
    // Reset bypass on next tick to intercept future prompts
    setTimeout(() => {
      isApprovedPrompt = false;
      activeInputEl = null;
      activeSubmitEl = null;
    }, 150);
  }

  // 7. Core Interception Handler

  async function handleIntercept(promptText, inputEl, submitEl = null) {
    if (!promptText.trim()) return; // Ignore empty inputs
    
    // Check if security is enabled globally or for current site
    if (!currentSettings || !currentSettings.isEnabled || !currentSettings.sites[siteKey]) {
      isApprovedPrompt = true;
      if (submitEl) submitEl.click();
      setTimeout(() => { isApprovedPrompt = false; }, 50);
      return;
    }

    // Cache elements for callback actions
    activeInputEl = inputEl;
    activeSubmitEl = submitEl;

    // Show loading overlay
    showOverlay('LOADING');

    // Send scan request to background worker with context-invalidation fail-safes
    try {
      if (typeof chrome === 'undefined' || !chrome.runtime || !chrome.runtime.id) {
        throw new Error("Extension context invalidated");
      }
      chrome.runtime.sendMessage({
        action: 'scanPrompt',
        promptText: promptText,
        siteKey: siteKey,
        url: window.location.href
      }, (response) => {
        if (chrome.runtime.lastError) {
          console.error('[SecurePrompt AI] IPC Communication Error:', chrome.runtime.lastError);
          hideOverlay();
          submitApprovedPrompt(); // Fallback: allow to avoid blocking user completely
          return;
        }

        if (!response || !response.success) {
          console.warn('[SecurePrompt AI] Scan failed, falling back to bypass.', response?.error);
          hideOverlay();
          submitApprovedPrompt();
          return;
        }

        const scanResult = response.result;
        const mode = currentSettings.interceptionMode || 'MANUAL';
      
        if (scanResult.action === CONFIG.ACTIONS.ALLOW) {
          hideOverlay();
          submitApprovedPrompt();
        } else {
          // Warnings or blocks triggered by sensitive data
          if (mode === 'AUTO_SEND') {
            // Autofill sanitized prompt and send immediately without user interaction
            if (activeInputEl) {
              setInputValue(activeInputEl, scanResult.sanitized_prompt);
            }
            hideOverlay();
            // Give React/Lexical framework time to digest input event changes before clicking submit
            setTimeout(() => {
              submitApprovedPrompt();
            }, 100);
          } else if (mode === 'AUTO_REVIEW') {
            // Autofill sanitized prompt and return control to user to review and send manually
            if (activeInputEl) {
              setInputValue(activeInputEl, scanResult.sanitized_prompt);
              activeInputEl.focus();
            }
            hideOverlay();
          } else {
            // MANUAL mode: Show warning/blocking modal dialogues
            if (scanResult.action === CONFIG.ACTIONS.WARN) {
              showOverlay('WARN', scanResult);
            } else if (scanResult.action === CONFIG.ACTIONS.BLOCK) {
              showOverlay('BLOCK', {
                ...scanResult,
                prompt: promptText
              });
            }
          }
        }
      });
    } catch (error) {
      console.warn('[SecurePrompt AI] Scan skipped due to invalidated context. Please refresh your browser tab.', error);
      hideOverlay();
      submitApprovedPrompt(); // Fallback to avoid locking client input interface
    }
  }

  // 8. Event Listeners (Capturing Phase Delegation)

  // Intercept keyboard submissions (Enter/Ctrl+Enter)
  document.addEventListener('keydown', (event) => {
    // If the prompt is currently bypassed, skip interception
    if (isApprovedPrompt) return;

    const target = event.target;
    if (!isInputElement(target)) return;

    const isEnter = event.key === 'Enter';
    const isShift = event.shiftKey;
    const isCtrl = event.ctrlKey;
    
    // Determine site specific submit triggers
    // Standard rule: Enter submits, Shift+Enter adds newline
    let shouldSubmit = isEnter && !isShift;
    
    // If Copilot/OpenRouter require Ctrl+Enter, we can check that.
    // Generally, standard enter is used on AI chats.
    if (shouldSubmit) {
      const promptText = getInputValue(target);
      if (!promptText.trim()) return; // Don't intercept empty prompts
      
      // Stop the host website from immediately submitting
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      
      handleIntercept(promptText, target);
    }
  }, true); // Use capturing phase to execute BEFORE host site listeners

  // Intercept click submissions
  document.addEventListener('click', (event) => {
    if (isApprovedPrompt) return;

    const submitBtn = findSubmitButton(event.target);
    if (!submitBtn) return;

    const inputEl = findAssociatedInput(submitBtn);
    if (!inputEl) return;

    const promptText = getInputValue(inputEl);
    if (!promptText.trim()) return;

    // Intercept click event
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    handleIntercept(promptText, inputEl, submitBtn);
  }, true); // Capturing phase!

  // 9. shadow DOM CSS styling template
  function getOverlayStyles() {
    return `
      :host {
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      }
      .sp-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 2147483647;
        transition: opacity 0.3s ease;
      }
      .sp-overlay.hidden {
        opacity: 0;
        pointer-events: none;
      }
      .sp-backdrop {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(15, 23, 42, 0.4);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
      }
      
      /* Theme Configurations */
      .light-theme {
        --bg-modal: #ffffff;
        --text-main: #0f172a;
        --text-sub: #475569;
        --border-color: #e2e8f0;
        --btn-secondary-bg: #f1f5f9;
        --btn-secondary-hover: #e2e8f0;
        --btn-secondary-text: #0f172a;
        --preview-bg: #f8fafc;
        --preview-border: #cbd5e1;
      }
      
      .dark-theme {
        --bg-modal: #1e293b;
        --text-main: #f8fafc;
        --text-sub: #94a3b8;
        --border-color: #334155;
        --btn-secondary-bg: #334155;
        --btn-secondary-hover: #475569;
        --btn-secondary-text: #f8fafc;
        --preview-bg: #0f172a;
        --preview-border: #1e293b;
      }
      
      .sp-modal-container {
        position: relative;
        z-index: 10;
        width: 90%;
        max-width: 580px;
        transform: scale(0.95);
        animation: modalEntrance 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
      }
      
      @keyframes modalEntrance {
        to {
          transform: scale(1);
        }
      }
      
      .sp-modal {
        background: var(--bg-modal);
        color: var(--text-main);
        border: 1px solid var(--border-color);
        border-radius: 20px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        overflow: hidden;
        padding: 28px;
        transition: background-color 0.3s;
      }
      
      /* Loading State */
      .sp-loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 20px 0;
      }
      .sp-loader {
        width: 50px;
        height: 50px;
        border: 4px solid var(--border-color);
        border-top-color: #3b82f6;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-bottom: 24px;
      }
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
      .sp-loading-container h3 {
        margin: 0 0 8px 0;
        font-size: 20px;
        font-weight: 700;
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
      }
      .sp-loading-container p {
        margin: 0;
        color: var(--text-sub);
        font-size: 14px;
      }
      
      /* Header styles */
      .sp-modal-header {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 24px;
      }
      .sp-warning-icon, .sp-block-icon {
        font-size: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 54px;
        height: 54px;
        background: rgba(245, 158, 11, 0.15);
        border-radius: 12px;
      }
      .sp-block-icon {
        background: rgba(239, 68, 68, 0.15);
      }
      .sp-modal-header h3 {
        margin: 0 0 4px 0;
        font-size: 20px;
        font-weight: 700;
      }
      .sp-modal-header p {
        margin: 0;
        color: var(--text-sub);
        font-size: 13px;
      }
      
      /* Risk score badge */
      .sp-risk-badge {
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 12px;
      }
      .badge-none { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
      .badge-low { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
      .badge-medium { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
      .badge-high { background: rgba(249, 115, 22, 0.15); color: #f97316; }
      .badge-critical { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
      
      /* Body Content */
      .sp-reason-title {
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-sub);
        margin: 0 0 8px 0;
      }
      .sp-reason {
        font-size: 15px;
        margin: 0 0 20px 0;
        line-height: 1.5;
      }
      .sp-prompt-preview {
        background: var(--preview-bg);
        border: 1px solid var(--preview-border);
        border-radius: 10px;
        padding: 14px;
        max-height: 160px;
        overflow-y: auto;
        font-size: 14px;
        line-height: 1.6;
        white-space: pre-wrap;
        margin-bottom: 24px;
      }
      .sp-prompt-preview.highlight-mode {
        background: rgba(239, 68, 68, 0.02);
      }
      
      /* Highlight text within shadow dom */
      .sp-highlight {
        background-color: rgba(239, 68, 68, 0.25);
        border-bottom: 2px solid #ef4444;
        color: inherit;
        padding: 1px 3px;
        border-radius: 3px;
        font-weight: 500;
      }
      
      /* Footer Buttons */
      .sp-modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
      }
      .sp-btn {
        font-family: inherit;
        font-size: 14px;
        font-weight: 600;
        padding: 10px 20px;
        border-radius: 10px;
        cursor: pointer;
        border: none;
        transition: all 0.2s ease;
      }
      
      .btn-secondary {
        background: var(--btn-secondary-bg);
        color: var(--btn-secondary-text);
      }
      .btn-secondary:hover {
        background: var(--btn-secondary-hover);
      }
      
      .btn-primary {
        background: #3b82f6;
        color: #ffffff;
      }
      .btn-primary:hover {
        background: #2563eb;
      }
      
      .btn-danger {
        background: #ef4444;
        color: #ffffff;
      }
      .btn-danger:hover {
        background: #dc2626;
      }
    `;
  }

})();
