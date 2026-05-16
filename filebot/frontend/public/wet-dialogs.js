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
        var needed = false;
        if (!document.getElementById('wet-alert-modal')) {
            document.body.insertAdjacentHTML('beforeend', ALERT_MODAL_HTML);
            needed = true;
        }
        if (!document.getElementById('wet-confirm-modal')) {
            document.body.insertAdjacentHTML('beforeend', CONFIRM_MODAL_HTML);
            needed = true;
        }
        return needed;
    }

    function getEl(id) {
        return document.getElementById(id);
    }

    // ── Detection helpers ───────────────────────────────────────────────────

    var hasWbDoc = function() {
        return typeof window.wb !== 'undefined' &&
               window.wb !== null &&
               typeof window.wb.doc !== 'undefined' &&
               typeof window.wb.doc.trigger === 'function';
    };

    var hasJQuery = function() {
        return typeof window.$ !== 'undefined' &&
               typeof window.$.fn !== 'undefined';
    };

    var hasBootstrapModal = function() {
        return typeof window.$ !== 'undefined' &&
               typeof window.$.fn !== 'undefined' &&
               typeof window.$.fn.modal === 'function';
    };

    var hasBootstrapAlertEl = function() {
        return document.getElementById('alertModal') !== null;
    };

    // ── showWetAlert ────────────────────────────────────────────────────────
    // Shows an informational alert. Returns a Promise that resolves when the
    // user dismisses it.

    function showWetAlert(message) {
        return new Promise(function(resolve) {
            ensureModalElements();

            var alertModal  = getEl('wet-alert-modal');
            var alertMsg    = getEl('wet-alert-message');

            if (!alertModal || !alertMsg) {
                // Shouldn't happen since we injected, but be safe
                console.warn('[wet-dialogs] Modal elements not found, using alert()');
                alert(message);
                resolve();
                return;
            }

            alertMsg.textContent = message;

            // ── Strategy 1: WET overlay (wb.doc) ──
            if (hasWbDoc()) {
                try {
                    // Need a close handler that doesn't persist
                    function onOverlayClosed(e) {
                        if (e && e.namespace !== undefined) return;
                        // Resolve after a tick so WET finishes cleanup
                        setTimeout(resolve, 50);
                    }

                    // Listen for overlay close
                    $(alertModal).on('closed.wb-overlay', function() {
                        setTimeout(resolve, 50);
                    });

                    window.wb.doc.trigger('open.wb-overlay', { id: 'wet-alert-modal' });
                    return; // resolve will be called on close
                } catch (e) {
                    console.warn('[wet-dialogs] WET overlay open failed:', e);
                    // Fall through
                }
            }

            // ── Strategy 2: WET lightbox (Magnific Popup) ──
            if (hasJQuery()) {
                try {
                    $(alertModal).on('close.mfp', function() {
                        setTimeout(resolve, 50);
                    });

                    $(document).trigger('open.wb-lbx', [[{
                        src: '#wet-alert-modal',
                        type: 'inline'
                    }], false, ['Alert']]);

                    // Timeout fallback: if no close event within 30s, resolve anyway
                    setTimeout(function() {
                        $(alertModal).off('close.mfp');
                        resolve();
                    }, 30000);

                    return;
                } catch (e) {
                    console.warn('[wet-dialogs] Lightbox open failed:', e);
                }
            }

            // ── Strategy 3: Bootstrap modal ──
            if (hasBootstrapModal() && hasBootstrapAlertEl()) {
                try {
                    var $bsModal = $('#alertModal');
                    $bsModal.find('.modal-body').text(message);
                    $bsModal.find('.modal-title').text('Alert');
                    $bsModal.one('hidden.bs.modal', function() {
                        resolve();
                    });
                    $bsModal.modal('show');

                    // Timeout fallback
                    setTimeout(function() {
                        resolve();
                    }, 30000);

                    return;
                } catch (e) {
                    console.warn('[wet-dialogs] Bootstrap modal failed:', e);
                }
            }

            // ── Strategy 4: Simple show/hide ──
            if (alertModal.style.display !== 'none' &&
                alertModal.classList.contains('mfp-hide')) {
                // Not shown yet, show it manually
                alertModal.classList.remove('mfp-hide');
                alertModal.style.display = 'block';
                alertModal.style.zIndex = '99999';
                alertModal.style.position = 'fixed';
                alertModal.style.top = '20%';
                alertModal.style.left = '50%';
                alertModal.style.transform = 'translateX(-50%)';
                alertModal.style.maxWidth = '500px';
                alertModal.style.background = '#fff';
                alertModal.style.border = '1px solid #ccc';
                alertModal.style.borderRadius = '4px';
                alertModal.style.padding = '20px';
                alertModal.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';

                // Create OK button if missing
                var footer = alertModal.querySelector('.modal-footer');
                if (!footer) {
                    footer = document.createElement('div');
                    footer.className = 'modal-footer';
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

                okBtn.addEventListener('click', function() {
                    alertModal.style.display = 'none';
                    alertModal.classList.add('mfp-hide');
                    var bdAlert = getEl('wet-dialogs-backdrop-alert');
                    if (bdAlert) bdAlert.remove();
                    resolve();
                }, { once: true });
                okBtn.focus();
                return;
            }

            // ── Strategy 5: Native alert fallback ──
            console.warn('[wet-dialogs] No dialog system found, using native alert()');
            alert(message);
            resolve();
        });
    }

    // ── wetYesOrNo ──────────────────────────────────────────────────────────
    // Shows a Yes/No confirmation. Returns a Promise<boolean>.

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

            // ── Strategy 1: WET overlay (wb.doc) ──
            if (hasWbDoc()) {
                try {
                    btnYes.addEventListener('click', function yesHandler() {
                        window.wb.doc.trigger('close.wb-overlay', { id: 'wet-confirm-modal' });
                        setTimeout(function() { resolve(true); }, 50);
                    }, { once: true });

                    btnNo.addEventListener('click', function noHandler() {
                        window.wb.doc.trigger('close.wb-overlay', { id: 'wet-confirm-modal' });
                        setTimeout(function() { resolve(false); }, 50);
                    }, { once: true });

                    window.wb.doc.trigger('open.wb-overlay', { id: 'wet-confirm-modal' });
                    return;
                } catch (e) {
                    console.warn('[wet-dialogs] WET overlay confirm failed:', e);
                }
            }

            // ── Strategy 2: WET modal (wb.doc trigger) ──
            if (hasWbDoc()) {
                try {
                    btnYes.addEventListener('click', function yesHandler() {
                        window.wb.doc.trigger('close.wb-modal', { id: 'wet-confirm-modal' });
                        setTimeout(function() { resolve(true); }, 50);
                    }, { once: true });

                    btnNo.addEventListener('click', function noHandler() {
                        window.wb.doc.trigger('close.wb-modal', { id: 'wet-confirm-modal' });
                        setTimeout(function() { resolve(false); }, 50);
                    }, { once: true });

                    window.wb.doc.trigger('open.wb-modal', { id: 'wet-confirm-modal' });
                    return;
                } catch (e) {
                    console.warn('[wet-dialogs] WET modal confirm failed:', e);
                }
            }

            // ── Strategy 3: Simple show/hide with local event handling ──
            confirmModal.classList.remove('mfp-hide');
            confirmModal.style.display = 'block';
            confirmModal.style.zIndex = '99999';
            confirmModal.style.position = 'fixed';
            confirmModal.style.top = '20%';
            confirmModal.style.left = '50%';
            confirmModal.style.transform = 'translateX(-50%)';
            confirmModal.style.maxWidth = '500px';
            confirmModal.style.background = '#fff';
            confirmModal.style.border = '1px solid #ccc';
            confirmModal.style.borderRadius = '4px';
            confirmModal.style.padding = '20px';
            confirmModal.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';

            // Style buttons for fallback (no WET CSS)
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

            function cleanup() {
                confirmModal.style.display = 'none';
                confirmModal.classList.add('mfp-hide');
                var bd = getEl('wet-dialogs-backdrop');
                if (bd) bd.remove();
            }

            btnYes.addEventListener('click', function() {
                cleanup();
                resolve(true);
            }, { once: true });

            btnNo.addEventListener('click', function() {
                cleanup();
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
