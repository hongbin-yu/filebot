/**
 * WetAlert — WET-compatible modal alert for Webbot
 * Replaces native alert()/confirm() with overlay modals.
 * Falls back to native functions if modal element is not present on the page.
 *
 * Usage:
 *   showWetAlert('Your message here');
 *   showWetAlert('Your message', 2000);  // auto-close after 2s
 *   showWetConfirm('Are you sure?', function(confirmed) { ... });
 */

(function() {
    'use strict';

    function getModal(id) {
        return document.getElementById(id);
    }

    function getMsgEl(id) {
        return document.getElementById(id);
    }

    /* Create a fixed-position wrapper so the modal-dialog renders properly
       even without the parent .modal container Bootstrap normally requires. */
    function showWetModal(modal) {
        if (!modal) return;

        // Build a self-contained overlay container
        var wrapper = document.createElement('div');
        wrapper.id = 'wet-overlay-' + modal.id;
        wrapper.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:9999;display:flex;align-items:center;justify-content:center;';

        // Backdrop
        var backdrop = document.createElement('div');
        backdrop.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.5);z-index:-1;';
        backdrop.addEventListener('click', function() { hideWetModal(modal); });
        wrapper.appendChild(backdrop);

        // Move modal into the wrapper
        modal.style.display = 'block';
        modal.style.position = 'relative';
        modal.style.zIndex = '1';
        modal.style.margin = '0 auto';
        modal.style.maxWidth = '500px';
        modal.style.width = '90%';
        modal.classList.remove('mfp-hide');

        // Insert wrapper right before modal, then move modal into it
        modal.parentNode.insertBefore(wrapper, modal);
        wrapper.appendChild(modal);

        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }

    function hideWetModal(modal) {
        if (!modal) return;
        modal.style.display = 'none';
        modal.classList.remove('in');

        // Remove the wrapper and put modal back
        var wrapper = document.getElementById('wet-overlay-' + modal.id);
        if (wrapper && wrapper.parentNode) {
            wrapper.parentNode.insertBefore(modal, wrapper);
            wrapper.remove();
        }

        document.body.style.overflow = '';
    }

    window.showWetAlert = function(message, duration) {
        var modal = getModal('wet-alert-modal');
        var msgEl = getMsgEl('wet-alert-message');
        if (modal && msgEl) {
            msgEl.textContent = message;
            // Remove any existing close buttons
            var existing = modal.querySelector('.wet-alert-close-btn');
            if (existing) existing.remove();
            var closeBtn = document.createElement('button');
            closeBtn.className = 'btn btn-primary wet-alert-close-btn';
            closeBtn.textContent = 'OK';
            closeBtn.addEventListener('click', function() { hideWetModal(modal); });
            var footer = modal.querySelector('.modal-footer');
            if (footer) footer.appendChild(closeBtn);
            showWetModal(modal);
            // Auto-close after duration (ms) if provided
            if (duration && duration > 0) {
                setTimeout(function() { hideWetModal(modal); }, duration);
            }
        } else {
            // Fallback
            alert(message);
        }
    };

    window.showWetConfirm = function(message, callback) {
        var modal = getModal('wet-confirm-modal');
        var msgEl = getMsgEl('wet-confirm-message');
        if (modal && msgEl) {
            msgEl.textContent = message;
            // Remove existing buttons
            modal.querySelectorAll('.wet-confirm-btn').forEach(function(b) { b.remove(); });
            var footer = modal.querySelector('.modal-footer');
            if (!footer) {
                footer = document.createElement('div');
                footer.className = 'modal-footer';
                modal.appendChild(footer);
            }
            var okBtn = document.createElement('button');
            okBtn.className = 'btn btn-primary wet-confirm-btn';
            okBtn.textContent = 'OK';
            okBtn.addEventListener('click', function() {
                hideWetModal(modal);
                if (callback) callback(true);
            });
            var cancelBtn = document.createElement('button');
            cancelBtn.className = 'btn btn-default wet-confirm-btn';
            cancelBtn.textContent = 'Cancel';
            cancelBtn.addEventListener('click', function() {
                hideWetModal(modal);
                if (callback) callback(false);
            });
            footer.appendChild(cancelBtn);
            footer.appendChild(okBtn);
            showWetModal(modal);
        } else {
            // Fallback
            callback && callback(confirm(message));
        }
    };
})();
