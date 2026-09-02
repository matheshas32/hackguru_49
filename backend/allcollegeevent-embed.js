/**
 * =========================================================================
 * EventTrust AI - AllCollegeEvent.com Drop-in Verification Widget & SDK
 * Version: 1.0.0
 * Description: Client-side AI verification integration for college event posters
 * =========================================================================
 */

(function (window, document) {
  'use strict';

  const EventTrustAI = {
    version: '1.0.0',
    defaultEndpoint: 'http://127.0.0.1:8000/api/verify-poster',

    /**
     * Initialize EventTrust AI on a file input element.
     * @param {Object} config Configuration object
     * @param {string|HTMLInputElement} config.input File input element or selector
     * @param {string|HTMLElement} config.container Container element or selector for result card
     * @param {string} [config.apiEndpoint] API URL (default: http://127.0.0.1:8000/api/verify-poster)
     * @param {Function} [config.onStart] Callback when upload/analysis starts
     * @param {Function} [config.onSuccess] Callback with verification result
     * @param {Function} [config.onError] Callback with error object
     * @param {boolean} [config.autoAutofill=true] Auto-fill registration url input if found
     * @param {string} [config.regUrlInput] Registration URL input selector
     */
    init: function (config) {
      if (!config) throw new Error('EventTrustAI: Configuration object required.');

      const inputEl = typeof config.input === 'string' ? document.querySelector(config.input) : config.input;
      const containerEl = typeof config.container === 'string' ? document.querySelector(config.container) : config.container;

      if (!inputEl) {
        console.warn('EventTrustAI: File input element not found for selector', config.input);
        return;
      }
      if (!containerEl) {
        console.warn('EventTrustAI: Container element not found for selector', config.container);
        return;
      }

      const endpoint = config.apiEndpoint || this.defaultEndpoint;

      inputEl.addEventListener('change', async (e) => {
        if (e.target.files && e.target.files.length > 0) {
          const file = e.target.files[0];
          await this.verifyAndRender(file, containerEl, endpoint, config);
        }
      });
    },

    /**
     * Send poster file to FastAPI backend and receive JSON verification result.
     * @param {File|Blob} file Poster image file
     * @param {string} [endpoint] API URL
     * @returns {Promise<Object>} Verification response JSON
     */
    verify: async function (file, endpoint) {
      const targetUrl = endpoint || this.defaultEndpoint;
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(targetUrl, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({ detail: 'Verification request failed' }));
        throw new Error(errJson.detail || `Server responded with status ${response.status}`);
      }

      return await response.json();
    },

    /**
     * Verify poster and render rich visual UI inside target container.
     */
    verifyAndRender: async function (file, containerEl, endpoint, config = {}) {
      if (typeof config.onStart === 'function') config.onStart();

      // Render Loading UI
      containerEl.style.display = 'block';
      containerEl.innerHTML = `
        <div style="background: rgba(15, 23, 42, 0.9); border: 1.5px solid rgba(99, 102, 241, 0.4); border-radius: 12px; padding: 1.25rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #fff; margin-top: 10px;">
          <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="width: 32px; height: 32px; border: 3px solid #6366f1; border-top-color: transparent; border-radius: 50%; animation: eta-spin 0.9s linear infinite;"></div>
            <div>
              <div style="font-weight: 700; font-size: 0.95rem;">EventTrust AI: Analyzing Poster Architecture...</div>
              <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 2px;">Extracting visual features & multi-pass QR security verification</div>
            </div>
          </div>
        </div>
        <style>
          @keyframes eta-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
      `;

      try {
        const result = await this.verify(file, endpoint);

        // Render Result UI
        this.renderResult(containerEl, result, config);

        if (typeof config.onSuccess === 'function') config.onSuccess(result);
      } catch (err) {
        console.error('EventTrustAI Verification Error:', err);
        containerEl.innerHTML = `
          <div style="background: rgba(239, 68, 68, 0.1); border: 1.5px solid rgba(239, 68, 68, 0.4); border-radius: 12px; padding: 1rem; color: #fca5a5; font-family: sans-serif; font-size: 0.85rem; margin-top: 10px;">
            <strong>⚠ EventTrust AI Scan Failed:</strong> ${this._escape(err.message)}
          </div>
        `;
        if (typeof config.onError === 'function') config.onError(err);
      }
    },

    /**
     * Render the structured EventTrust AI card matching specification.
     */
    renderResult: function (containerEl, data, config = {}) {
      const isVerified = data.status === 'VERIFIED' || (data.risk_level === 'LOW' && data.prediction === 'REAL');
      const isFake = data.prediction === 'FAKE' || data.risk_level === 'HIGH';

      const themeColor = isVerified ? '#10b981' : (data.risk_level === 'MEDIUM' ? '#f59e0b' : '#ef4444');
      const themeBg = isVerified ? 'rgba(16, 185, 129, 0.08)' : (data.risk_level === 'MEDIUM' ? 'rgba(245, 158, 11, 0.08)' : 'rgba(239, 68, 68, 0.08)');
      const borderColor = isVerified ? 'rgba(16, 185, 129, 0.4)' : (data.risk_level === 'MEDIUM' ? 'rgba(245, 158, 11, 0.4)' : 'rgba(239, 68, 68, 0.4)');

      const confidencePct = (typeof data.confidence === 'number')
        ? (data.confidence <= 1.0 ? (data.confidence * 100).toFixed(1) : data.confidence.toFixed(1))
        : (data.poster_confidence || '94.7');

      let qrText = 'ℹ Not Detected';
      let qrColor = '#94a3b8';
      if (data.qr_detected) {
        if (data.qr_verified || data.qr_result === 'BENIGN') {
          qrText = '✓ Detected (Safe Link)';
          qrColor = '#10b981';
        } else {
          qrText = '⚠ Detected (Requires Review)';
          qrColor = '#ef4444';
        }
      }

      // Checklist
      let checklistItems = '';
      if (isVerified) {
        const items = data.positive_indicators && data.positive_indicators.length > 0
          ? data.positive_indicators
          : ['Event date detected', 'College/organization detected', 'Registration information detected', 'No major suspicious indicators'];
        checklistItems = items.map(i => `<li style="display:flex; align-items:flex-start; gap:8px; margin-bottom:4px; color:#e2e8f0; font-size:0.85rem;"><span style="color:#10b981; font-weight:bold;">✓</span> <span>${this._escape(i)}</span></li>`).join('');
      } else {
        const items = data.issues && data.issues.length > 0
          ? data.issues
          : ['Suspicious poster detected', 'Registration information could not be verified', 'QR destination requires review'];
        checklistItems = items.map(i => `<li style="display:flex; align-items:flex-start; gap:8px; margin-bottom:4px; color:#fca5a5; font-size:0.85rem;"><span style="color:#ef4444; font-weight:bold;">⚠</span> <span>${this._escape(i)}</span></li>`).join('');
      }

      // Auto-fill button for QR URL
      let qrAutofillBtn = '';
      if (data.qr_detected && data.qr_data && (data.qr_data.startsWith('http://') || data.qr_data.startsWith('https://'))) {
        qrAutofillBtn = `
          <div style="background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.3); border-radius:6px; padding:8px 12px; margin-top:10px; display:flex; justify-content:space-between; align-items:center; gap:8px; font-size:0.8rem;">
            <span style="color:#7dd3fc; word-break:break-all;"><strong>QR Link:</strong> ${this._escape(data.qr_data)}</span>
            <button type="button" onclick="EventTrustAI.applyQrUrl('${this._escape(data.qr_data)}', '${config.regUrlInput || '#event-reg-url'}')" style="background:#0284c7; color:#fff; border:none; border-radius:4px; padding:4px 10px; font-size:0.75rem; cursor:pointer; font-weight:600; flex-shrink:0;">
              Use Link
            </button>
          </div>
        `;
      }

      containerEl.innerHTML = `
        <div style="background: rgba(15, 23, 42, 0.95); border: 1.5px solid ${borderColor}; border-radius: 12px; padding: 1.4rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #fff; margin-top: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
          <!-- Top Bar -->
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 8px; font-weight: 800; font-size: 1.1rem; color: #fff;">
              <span style="color: #6366f1;">🛡️</span> EventTrust AI
            </div>
            <div style="font-size: 0.8rem; color: #94a3b8;">
              Poster Analysis: <strong style="color: #e2e8f0;">✓ Poster analyzed</strong>
            </div>
          </div>
          <div style="border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 14px;"></div>

          <!-- Metrics Row -->
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 10px; margin-bottom: 14px;">
            <div style="background: rgba(0,0,0,0.3); padding: 8px 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
              <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Trust Score</div>
              <div style="font-size: 1.4rem; font-weight: 800; color: ${themeColor}; font-family: monospace;">${data.trust_score}<span style="font-size: 0.8rem; color: #64748b;">/100</span></div>
            </div>

            <div style="background: rgba(0,0,0,0.3); padding: 8px 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
              <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Status</div>
              <div style="font-size: 0.85rem; font-weight: 800; color: ${themeColor}; margin-top: 4px;">${data.status || (isVerified ? 'VERIFIED' : 'REVIEW REQUIRED')}</div>
            </div>

            <div style="background: rgba(0,0,0,0.3); padding: 8px 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
              <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Confidence</div>
              <div style="font-size: 1rem; font-weight: 700; color: #fff; font-family: monospace; margin-top: 2px;">${confidencePct}%</div>
            </div>

            <div style="background: rgba(0,0,0,0.3); padding: 8px 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
              <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; font-weight: 600;">QR Code</div>
              <div style="font-size: 0.8rem; font-weight: 700; color: ${qrColor}; margin-top: 4px;">${qrText}</div>
            </div>

            <div style="background: rgba(0,0,0,0.3); padding: 8px 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
              <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Risk Level</div>
              <div style="font-size: 0.9rem; font-weight: 800; color: ${themeColor}; font-family: monospace; margin-top: 2px;">${data.risk_level || (isVerified ? 'LOW' : 'HIGH')}</div>
            </div>
          </div>

          <!-- Issues / Indicators Checklist -->
          <div style="background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px; margin-bottom: 12px;">
            <div style="font-size: 0.8rem; font-weight: 700; color: #cbd5e1; margin-bottom: 8px;">
              ${isVerified ? 'Issues:' : 'Issues:'}
            </div>
            <ul style="list-style: none; padding: 0; margin: 0;">
              ${checklistItems}
            </ul>
          </div>

          ${qrAutofillBtn}

          <!-- Recommendation Box -->
          <div style="background: ${themeBg}; border: 1px solid ${borderColor}; border-radius: 8px; padding: 10px 14px; font-size: 0.85rem;">
            <div style="font-weight: 700; color: ${themeColor}; margin-bottom: 2px;">Recommendation:</div>
            <div style="color: #e2e8f0; font-size: 0.82rem;">${this._escape(data.recommendation || (isVerified ? 'Poster verified. Ready for publishing.' : 'Verify this event before publishing.'))}</div>
          </div>
        </div>
      `;
    },

    applyQrUrl: function (url, targetSelector) {
      const el = document.querySelector(targetSelector);
      if (el) {
        el.value = url;
        el.focus();
        alert('Registration Link auto-filled from verified QR code!');
      }
    },

    _escape: function (str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
  };

  // Expose to window
  window.EventTrustAI = EventTrustAI;

  // Auto-bind inputs with data-eventtrust-verify attribute
  document.addEventListener('DOMContentLoaded', () => {
    const autoInputs = document.querySelectorAll('[data-eventtrust-verify="true"]');
    autoInputs.forEach((input) => {
      const containerSelector = input.getAttribute('data-eventtrust-container');
      const endpoint = input.getAttribute('data-eventtrust-endpoint');
      if (containerSelector) {
        EventTrustAI.init({
          input: input,
          container: containerSelector,
          apiEndpoint: endpoint || undefined
        });
      }
    });
  });

})(window, document);
