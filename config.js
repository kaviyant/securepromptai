/**
 * SecurePrompt AI - Configuration File
 * Contains list of supported websites, DOM selectors for input boxes and send buttons,
 * and default API endpoints.
 */

const CONFIG = {
  // Backend Configuration
  DEFAULT_BACKEND_URL: 'http://localhost:8000',
  SCAN_ENDPOINT: '/api/scan',
  DEFAULT_BYPASS_TIMEOUT_MS: 5000,
  
  // Storage Keys
  STORAGE_KEYS: {
    SETTINGS: 'secure_prompt_settings',
    HISTORY: 'secure_prompt_history'
  },

  // Action responses from the backend
  ACTIONS: {
    ALLOW: 'ALLOW',
    WARN: 'WARN',
    BLOCK: 'BLOCK'
  },

  // Default Settings
  DEFAULT_SETTINGS: {
    backendUrl: 'http://localhost:8000',
    isEnabled: true,
    enableNotifications: true,
    enableDocumentVerification: true,
    restrictedFiles: ['confidential_report.pdf', 'financials_2026.xlsx', 'secret_keys.docx'],
    sensitivityThreshold: 50, // default sensitivity threshold
    interceptionMode: 'MANUAL', // 'MANUAL' (Edit manually), 'AUTO_REVIEW' (Autofill & review), 'AUTO_SEND' (Silent auto-send)
    sites: {
      chatgpt: true,
      gemini: true,
      claude: true,
      copilot: true,
      grok: true,
      perplexity: true,
      deepseek: true,
      openrouter: true
    }
  },

  // Target AI websites selectors and details
  SITES: {
    chatgpt: {
      name: 'ChatGPT',
      domains: ['chatgpt.com', 'chat.openai.com'],
      // Input text area selector
      inputSelectors: [
        '#prompt-textarea',
        'textarea[placeholder*="ChatGPT"]',
        'textarea'
      ],
      // Submit button selector
      submitSelectors: [
        'button[data-testid="send-button"]',
        'button[data-testid="composer-unreachable-submit-button"]',
        'button[aria-label="Send prompt"]',
        'button:has(svg)'
      ]
    },
    gemini: {
      name: 'Gemini',
      domains: ['gemini.google.com'],
      // Gemini uses a contenteditable div inside rich-textarea component
      inputSelectors: [
        'div.textarea[role="textbox"]',
        'div[contenteditable="true"]',
        'rich-textarea div[contenteditable="true"]',
        'textarea'
      ],
      submitSelectors: [
        'button.send-button',
        'button[aria-label="Send message"]',
        '.send-button-container button',
        'button:has(mat-icon)'
      ]
    },
    claude: {
      name: 'Claude',
      domains: ['claude.ai'],
      inputSelectors: [
        'div[contenteditable="true"].ProseMirror',
        'div[contenteditable="true"]',
        'textarea'
      ],
      submitSelectors: [
        'button[aria-label="Send Message"]',
        'button[aria-label="Send message"]',
        'button:has(svg)'
      ]
    },
    copilot: {
      name: 'Copilot',
      domains: ['copilot.microsoft.com', 'bing.com'],
      inputSelectors: [
        'textarea#searchbox',
        'textarea[placeholder*="Copilot"]',
        'textarea'
      ],
      submitSelectors: [
        'button[aria-label="Submit"]',
        'button[aria-label="Send"]',
        'button.submit',
        'button[type="submit"]'
      ]
    },
    grok: {
      name: 'Grok',
      domains: ['grok.com'],
      inputSelectors: [
        'textarea',
        'div[contenteditable="true"]'
      ],
      submitSelectors: [
        'button[aria-label="Send"]',
        'button[aria-label="Grok loop"]',
        'button:has(svg)'
      ]
    },
    perplexity: {
      name: 'Perplexity',
      domains: ['perplexity.ai', 'www.perplexity.ai'],
      inputSelectors: [
        'textarea[placeholder*="Ask"]',
        'textarea',
        'div[contenteditable="true"]'
      ],
      submitSelectors: [
        'button[aria-label="Submit"]',
        'button:has(svg[data-icon="arrow-right"])',
        'button:has(svg[data-icon="arrow-up"])',
        'button.bg-super'
      ]
    },
    deepseek: {
      name: 'DeepSeek',
      domains: ['chat.deepseek.com'],
      inputSelectors: [
        'textarea#chat-input',
        'textarea'
      ],
      submitSelectors: [
        'div#chat-input-send-button',
        'button[aria-label="Send"]',
        '.chat-input-send-button',
        'button:has(svg)'
      ]
    },
    openrouter: {
      name: 'OpenRouter',
      domains: ['openrouter.ai'],
      inputSelectors: [
        'textarea',
        'div[contenteditable="true"]'
      ],
      submitSelectors: [
        'button[type="submit"]',
        'button[aria-label="Send message"]',
        'button:has(svg)'
      ]
    }
  }
};

// Export to global scope or module exports
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONFIG;
} else {
  globalThis.CONFIG = CONFIG;
}
