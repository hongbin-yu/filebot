/**
 * wet-dialogs.js — Global WET-BOEW dialog functions
 *
 * Provides two Promise-based modal functions reusable across all WebBot apps:
 *   window.showWetAlert(message)  → resolves when user dismisses
 *   window.wetYesOrNo(message)    → resolves true / false
 *
 * Auto-detects available UI in order:
 *   1. WET overlay (window.wb.doc)        — used in navigation pages
 *   2. WET lightbox (jQuery + Magnific)   — used in some navigation pages
 *   3. Bootstrap modal (#alertModal)       — fallback on some pages
 *   4. Native alert()/confirm()           — last resort
 *
 * Injects modal HTML into <body> if missing.
 *
 * Dependencies: jQuery (optional — used only for WET/Bootstrap paths)
 * ========================================================================= */

(function() {
    'use strict';

    // ── Modal HTML templates ────────────────────────────────────────────────
    // These match the structures used in static/navigation.html

    var ALERT_MODAL_HTML =
        '<section id="wet-alert-modal" class="modal-dialog modal-content overlay-def mfp-hide" ' +
        'aria-hidden="true" role="dialog">' +
        '<div class="modal-header"><h2 class="modal-title">Alert</h2></div>' +
        '<div class="modal-body"><p id="wet-alert-message" style="white-space:pre-wrap"></p></div>' +
        '</section>';

    var CONFIRM_MODAL_HTML =
        '<section id="wet-confirm-modal" class="modal-dialog modal-content overlay-def mfp-hide" ' +
        'aria-hidden="true" role="dialog">' +
        '<div class="modal-header"><h2 class="modal-title">Confirm</h2></div>' +
        '<div class="modal-body"><p id="wet-confirm-message" style="white-space:pre-wrap"></p></div>' +
        '<div class="modal-footer">' +
        '<button type="button" class="btn btn-primary" id="wet-confirm-yes">Yes</button>' +
        '<button type="button" class="btn btn-default" id="wet-confirm-no">No</button>' +
        '</div>' +
        '</section>';

    // ── DOM injection helpers ───────────────────────────────────────────────

    function ensureModalElements() {
        // Remove stale elements first to avoid WET-processed leftovers
        var oldAlert = document.getElementById('wet-alert-modal');
        if (oldAlert) oldAlert.parentNode.removeChild(oldAlert);
        var oldConfirm = document.getElementById('wet-confirm-modal');
        if (oldConfirm) oldConfirm.parentNode.removeChild(oldConfirm);

        document.body.insertAdjacentHTML('beforeend', ALERT_MODAL_HTML);
        document.body.insertAdjacentHTML('beforeend', CONFIRM_MODAL_HTML);
    }

    function getEl(id) {
        return document.getElementById(id);
    }

    // ── Detection helpers (kept for reference, not used by current simple-CSS mode) ──

    // ── showWetAlert ────────────────────────────────────────────────────────
    // Shows an informational alert. Returns a Promise that resolves when the
    // user dismisses it.

    function showWetAlert(message) {
        return new Promise(function(resolve) {
            ensureModalElements();

            var alertModal  = getEl('wet-alert-modal');
            var alertMsg    = getEl('wet-alert-message');

            if (!alertModal || !alertMsg) {
                console.warn('[wet-dialogs] Modal elements not found, using alert()');
                alert(message);
                resolve();
                return;
            }

            alertMsg.textContent = message;

            // ── Simple CSS show/hide (always, avoids WET overlay white-screen issue) ──
            alertModal.classList.remove('mfp-hide');
            alertModal.style.cssText = 'display:block;position:fixed;z-index:99999;top:20%;left:50%;' +
                'transform:translateX(-50%);max-width:500px;background:#fff;border:1px solid #ccc;' +
                'border-radius:4px;padding:20px;box-shadow:0 4px 12px rgba(0,0,0,0.3);';

            // Create OK button if missing
            var footer = alertModal.querySelector('.modal-footer');
            if (!footer) {
                footer = document.createElement('div');
                footer.className = 'modal-footer';
                footer.style.cssText = 'text-align:center;padding-top:15px;';
                alertModal.appendChild(footer);
            }
            var okBtn = getEl('wet-alert-ok');
            if (!okBtn) {
                okBtn = document.createElement('button');
                okBtn.id = 'wet-alert-ok';
                okBtn.className = 'wet-btn-fallback';
                okBtn.textContent = 'OK';
                okBtn.style.cssText = 'padding:8px 20px;background:#2572b4;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px;font-weight:600;';
                footer.appendChild(okBtn);
            }
            // Add backdrop
            var alertBackdrop = document.createElement('div');
            alertBackdrop.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;' +
                                         'background:rgba(0,0,0,0.3);z-index:99998';
            alertBackdrop.id = 'wet-dialogs-backdrop-alert';
            document.body.appendChild(alertBackdrop);

            okBtn.addEventListener('click', function dismissAlert() {
                alertModal.parentNode.removeChild(alertModal);
                var bdAlert = getEl('wet-dialogs-backdrop-alert');
                if (bdAlert) bdAlert.parentNode.removeChild(bdAlert);
                resolve();
            }, { once: true });
            okBtn.focus();
        });
    }

    // ── wetYesOrNo ──────────────────────────────────────────────────────────
    // Shows a Yes/No confirmation. Returns a Promise<boolean>.
    // Uses simple CSS show/hide (avoids WET overlay white-screen issue).

    function wetYesOrNo(message, title) {
        title = title || 'Confirm';
        return new Promise(function(resolve) {
            ensureModalElements();

            var confirmModal  = getEl('wet-confirm-modal');
            var confirmMsg    = getEl('wet-confirm-message');
            var btnYes        = getEl('wet-confirm-yes');
            var btnNo         = getEl('wet-confirm-no');

            if (!confirmModal || !confirmMsg || !btnYes || !btnNo) {
                console.warn('[wet-dialogs] Confirm modal elements missing, using native confirm()');
                resolve(confirm(message));
                return;
            }

            confirmMsg.textContent = message;
            var titleEl = confirmModal.querySelector('.modal-title');
            if (titleEl) titleEl.textContent = title;

            // ── Simple CSS show/hide (always, avoids WET overlay white-screen issue) ──
            confirmModal.classList.remove('mfp-hide');
            confirmModal.style.cssText = 'display:block;position:fixed;z-index:99999;top:20%;left:50%;' +
                'transform:translateX(-50%);max-width:500px;background:#fff;border:1px solid #ccc;' +
                'border-radius:4px;padding:20px;box-shadow:0 4px 12px rgba(0,0,0,0.3);';

            // Style buttons
            btnYes.style.cssText = 'padding:8px 20px;background:#2572b4;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px;font-weight:600;margin-right:8px;';
            btnNo.style.cssText = 'padding:8px 20px;background:#f5f5f5;color:#333;border:1px solid #ccc;border-radius:4px;cursor:pointer;font-size:14px;';

            // Ensure footer lays out buttons horizontally
            var footer = confirmModal.querySelector('.modal-footer');
            if (footer) {
                footer.style.cssText = 'text-align:center;padding-top:15px;';
            }

            // Overlay backdrop
            var backdrop = document.createElement('div');
            backdrop.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;' +
                                     'background:rgba(0,0,0,0.3);z-index:99998';
            backdrop.id = 'wet-dialogs-backdrop';
            document.body.appendChild(backdrop);

            btnYes.addEventListener('click', function dismissConfirm() {
                confirmModal.parentNode.removeChild(confirmModal);
                var bd = getEl('wet-dialogs-backdrop');
                if (bd) bd.parentNode.removeChild(bd);
                resolve(true);
            }, { once: true });

            btnNo.addEventListener('click', function dismissConfirm() {
                confirmModal.parentNode.removeChild(confirmModal);
                var bd = getEl('wet-dialogs-backdrop');
                if (bd) bd.parentNode.removeChild(bd);
                resolve(false);
            }, { once: true });

            return;
        });
    }

    // ── Export to window ────────────────────────────────────────────────────
    window.showWetAlert = showWetAlert;
    window.wetYesOrNo   = wetYesOrNo;

    // Legacy aliases
    window.wetAlert       = showWetAlert;   // shorthand for alert replacement
    window.showWetConfirm = wetYesOrNo;

    console.log('[wet-dialogs] Initialized — showWetAlert and wetYesOrNo are now global.');

})();
