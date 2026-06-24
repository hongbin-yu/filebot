/**
 * wet-dialogs.js — Global WET-BOEW dialog functions
 *
 * Provides two Promise-based modal functions reusable across all WebBot apps:
 *   window.showWetAlert(message)  → resolves when user dismisses
 *   window.wetYesOrNo(message)    → resolves true / false
 *
 * Uses direct DOM creation (no HTML injection) for maximum reliability.
 * Dependencies: none (no jQuery, no WET, no Magnific Popup required)
 * ========================================================================= */

(function() {
    'use strict';

    // ── Shared cleanup: remove stale dialog elements ────────────────────────
    var STALE_IDS = [
        'wet-alert-modal', 'wet-confirm-modal',
        'wet-dialogs-backdrop', 'wet-dialogs-backdrop-alert'
    ];

    function cleanStale() {
        for (var i = 0; i < STALE_IDS.length; i++) {
            var el = document.getElementById(STALE_IDS[i]);
            if (el && el.parentNode) el.parentNode.removeChild(el);
        }
    }

    // ── showWetAlert ────────────────────────────────────────────────────────
    // Informational dialog with a single OK button.

    function showWetAlert(message) {
        return new Promise(function(resolve) {
            cleanStale();

            var modal = document.createElement('div');
            modal.id = 'wet-alert-modal';
            modal.style.cssText = 'display:block;position:fixed;z-index:99999;top:20%;left:50%;' +
                'transform:translateX(-50%);max-width:500px;background:#fff;border:1px solid #e3e3e3;' +
                'border-radius:6px;padding:24px;box-shadow:0 4px 16px rgba(0,0,0,0.25);' +
                'font-family:sans-serif;';

            var h2 = document.createElement('h2');
            h2.style.cssText = 'font-size:18px;font-weight:600;margin:0 0 12px 0;color:#333;';
            h2.textContent = 'Alert';
            modal.appendChild(h2);

            var p = document.createElement('p');
            p.style.cssText = 'white-space:pre-wrap;margin:0 0 20px 0;font-size:14px;color:#555;';
            p.textContent = message;
            modal.appendChild(p);

            var btnBox = document.createElement('div');
            btnBox.style.cssText = 'text-align:right;';
            var okBtn = document.createElement('button');
            okBtn.textContent = 'OK';
            okBtn.style.cssText = 'padding:8px 24px;background:#2572b4;color:#fff;border:none;' +
                'border-radius:4px;cursor:pointer;font-size:14px;font-weight:600;';
            okBtn.addEventListener('mouseenter', function() { okBtn.style.background = '#1d5f96'; });
            okBtn.addEventListener('mouseleave', function() { okBtn.style.background = '#2572b4'; });
            btnBox.appendChild(okBtn);
            modal.appendChild(btnBox);

            var backdrop = document.createElement('div');
            backdrop.id = 'wet-dialogs-backdrop-alert';
            backdrop.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;' +
                                     'background:rgba(0,0,0,0.35);z-index:99998';

            function dismiss() {
                if (modal.parentNode) modal.parentNode.removeChild(modal);
                if (backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
                resolve();
            }

            okBtn.addEventListener('click', dismiss, { once: true });
            backdrop.addEventListener('click', dismiss, { once: true });

            document.body.appendChild(backdrop);
            document.body.appendChild(modal);
            okBtn.focus();
        });
    }

    // ── wetYesOrNo ──────────────────────────────────────────────────────────
    // Confirmation dialog with Yes / No buttons. Returns Promise<boolean>.

    function wetYesOrNo(message, title) {
        title = title || 'Confirm';
        return new Promise(function(resolve) {
            cleanStale();

            var modal = document.createElement('div');
            modal.id = 'wet-confirm-modal';
            modal.style.cssText = 'display:block;position:fixed;z-index:99999;top:20%;left:50%;' +
                'transform:translateX(-50%);max-width:500px;background:#fff;border:1px solid #e3e3e3;' +
                'border-radius:6px;padding:24px;box-shadow:0 4px 16px rgba(0,0,0,0.25);' +
                'font-family:sans-serif;';

            var h2 = document.createElement('h2');
            h2.style.cssText = 'font-size:18px;font-weight:600;margin:0 0 12px 0;color:#333;';
            h2.textContent = title;
            modal.appendChild(h2);

            var p = document.createElement('p');
            p.style.cssText = 'white-space:pre-wrap;margin:0 0 20px 0;font-size:14px;color:#555;';
            p.textContent = message;
            modal.appendChild(p);

            var btnBox = document.createElement('div');
            btnBox.style.cssText = 'text-align:right;';

            var btnYes = document.createElement('button');
            btnYes.textContent = 'Yes';
            btnYes.style.cssText = 'padding:8px 24px;background:#2572b4;color:#fff;border:none;' +
                'border-radius:4px;cursor:pointer;font-size:14px;font-weight:600;margin-right:8px;';
            btnYes.addEventListener('mouseenter', function() { btnYes.style.background = '#1d5f96'; });
            btnYes.addEventListener('mouseleave', function() { btnYes.style.background = '#2572b4'; });

            var btnNo = document.createElement('button');
            btnNo.textContent = 'No';
            btnNo.style.cssText = 'padding:8px 24px;background:#f5f5f5;color:#333;border:1px solid #ccc;' +
                'border-radius:4px;cursor:pointer;font-size:14px;';
            btnNo.addEventListener('mouseenter', function() { btnNo.style.background = '#e0e0e0'; });
            btnNo.addEventListener('mouseleave', function() { btnNo.style.background = '#f5f5f5'; });

            btnBox.appendChild(btnYes);
            btnBox.appendChild(btnNo);
            modal.appendChild(btnBox);

            var backdrop = document.createElement('div');
            backdrop.id = 'wet-dialogs-backdrop';
            backdrop.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;' +
                                     'background:rgba(0,0,0,0.35);z-index:99998';

            function dismiss(result) {
                if (modal.parentNode) modal.parentNode.removeChild(modal);
                if (backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
                resolve(result);
            }

            btnYes.addEventListener('click', function() { dismiss(true); }, { once: true });
            btnNo.addEventListener('click', function() { dismiss(false); }, { once: true });
            backdrop.addEventListener('click', function() { dismiss(false); }, { once: true });

            document.body.appendChild(backdrop);
            document.body.appendChild(modal);
            btnYes.focus();
        });
    }

    // ── Export to window ────────────────────────────────────────────────────
    window.showWetAlert = showWetAlert;
    window.wetYesOrNo   = wetYesOrNo;

    // Legacy aliases
    window.wetAlert       = showWetAlert;
    window.showWetConfirm = wetYesOrNo;

    console.log('[wet-dialogs] v2 — direct DOM creation mode.');
})();
