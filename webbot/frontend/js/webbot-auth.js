/**
 * Webbot Auth — shared auth module for all management pages.
 * Uses the same localStorage keys as FileBot for seamless integration.
 * Include this in the <head> of any protected HTML page.
 *
 * Usage: <script src="/static/js/webbot-auth.js"></script>
 * On page load: checks localStorage for token, redirects to login page if missing.
 *
 * Visual design matches FileBot's login page for a unified experience.
 */

(function() {
    'use strict';

    // Use same keys as FileBot for cross-compatibility
    var STORAGE_KEY = 'access_token';
    var USER_KEY = 'user_info';
    var API_BASE = '/api/v1/auth';
    var LOGIN_PAGE = 'http://localhost:5174/login';

    // ── Helpers ──────────────────────────────────────────────────────

    function getToken() {
        try { return localStorage.getItem(STORAGE_KEY); } catch(e) { return null; }
    }

    function getUser() {
        try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); }
        catch(e) { return null; }
    }

    function clearAuth() {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem(USER_KEY);
        var ui = document.getElementById('webbot-user-info');
        var lb = document.getElementById('webbot-login-btn');
        var lo = document.getElementById('webbot-logout-btn');
        if (lb) lb.style.display = 'inline-block';
        if (lo) lo.style.display = 'none';
        if (ui) ui.style.display = 'none';
    }

    function saveAuth(token, user) {
        localStorage.setItem(STORAGE_KEY, token);
        localStorage.setItem(USER_KEY, JSON.stringify(user));
        updateUI();
    }

    function updateUI() {
        var user = getUser();
        var loginBtn = document.getElementById('webbot-login-btn');
        var logoutBtn = document.getElementById('webbot-logout-btn');
        var userInfo = document.getElementById('webbot-user-info');
        // Also support legacy IDs
        if (!loginBtn) loginBtn = document.getElementById('login-btn');
        if (!logoutBtn) logoutBtn = document.getElementById('logout-btn');
        if (!userInfo) userInfo = document.getElementById('user-info');
        if (!loginBtn) return;
        if (user) {
            loginBtn.style.display = 'none';
            if (logoutBtn) logoutBtn.style.display = 'inline-block';
            if (userInfo) {
                userInfo.style.display = 'inline';
                userInfo.textContent = '👤 ' + (user.full_name || user.username || user.email);
            }
        } else {
            loginBtn.style.display = 'inline-block';
            if (logoutBtn) logoutBtn.style.display = 'none';
            if (userInfo) userInfo.style.display = 'none';
        }
    }

    // ── Auth guard: redirect to login if no token ────────────────────

    (function checkAuth() {
        // Skip if we're already on the login page (avoid redirect loop)
        var path = window.location.pathname;
        var fullUrl = window.location.href;
        // Skip redirect if already on a login page
        if (path.indexOf('/login') >= 0 || path.indexOf(LOGIN_PAGE) >= 0 || fullUrl.indexOf(LOGIN_PAGE) >= 0) return;

        // Check for token in URL (cross-origin login callback)
        var urlParams = new URLSearchParams(window.location.search);
        var tokenParam = urlParams.get('token');
        var userParam = urlParams.get('user');
        if (tokenParam) {
            localStorage.setItem(STORAGE_KEY, tokenParam);
            if (userParam) {
                try { localStorage.setItem(USER_KEY, decodeURIComponent(userParam)); } catch(e) {}
            }
            // Clean URL: remove only token and user query params, preserve others
            var params = new URLSearchParams(window.location.search);
            params.delete('token');
            params.delete('user');
            var cleanSearch = params.toString();
            if (cleanSearch) cleanSearch = '?' + cleanSearch;
            var cleanUrl = window.location.origin + window.location.pathname + cleanSearch;
            window.history.replaceState({}, document.title, cleanUrl);
            // UI will update below
        }

        var token = getToken();
        if (!token) {
            // Use full URL so FileBot login can detect it as cross-origin redirect
            var currentUrl = window.location.href;
            var redirectTo = LOGIN_PAGE + '?redirect=' + encodeURIComponent(currentUrl);
            window.location.href = redirectTo;
            return;
        }
    })();

    // ── Login/logout button handlers ─────────────────────────────────

    function wireLoginBtn() {
        var loginBtn = document.getElementById('webbot-login-btn') || document.getElementById('login-btn');
        var logoutBtn = document.getElementById('webbot-logout-btn') || document.getElementById('logout-btn');

        if (loginBtn) {
            loginBtn.addEventListener('click', function() {
                var currentUrl = window.location.href;
                window.location.href = LOGIN_PAGE + '?redirect=' + encodeURIComponent(currentUrl);
            });
        }

        if (logoutBtn) {
            logoutBtn.addEventListener('click', function() {
                clearAuth();
                fetch(API_BASE + '/logout', { method: 'POST' }).catch(function(){});
                var currentUrl = window.location.href;
                window.location.href = LOGIN_PAGE + '?redirect=' + encodeURIComponent(currentUrl);
            });
        }
    }

    // ── Fetch interceptor: auto-add Bearer token ─────────────────────

    (function() {
        var __origFetch = window.fetch;
        window.fetch = function(url, opts) {
            opts = opts || {};
            var token = getToken();
            var urlStr = (typeof url === 'string') ? url : (url && url.url ? url.url : '');
            if (token && urlStr.indexOf('/api/v1/') === 0) {
                opts.headers = opts.headers || {};
                if (!opts.headers['Authorization'] && !opts.headers['authorization']) {
                    opts.headers['Authorization'] = 'Bearer ' + token;
                }
            }
            return __origFetch.call(window, url, opts).then(function(resp) {
                // Auto-detect 401 with valid token → token expired
                if (resp.status === 401 && getToken()) {
                    resp.clone().json().then(function(data) {
                        if (data && data.detail && (
                            data.detail.indexOf('无效') >= 0 ||
                            data.detail.indexOf('未激活') >= 0 ||
                            data.detail.indexOf('不存在') >= 0
                        )) {
                            clearAuth();
                            var currentPath = window.location.pathname + window.location.search;
                            window.location.href = LOGIN_PAGE + '?redirect=' + encodeURIComponent(currentPath);
                        }
                    }).catch(function(){});
                }
                return resp;
            });
        };
    })();

    // ── XHR interceptor ──────────────────────────────────────────────

    (function() {
        var __origOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(method, url) {
            this.__xhrUrl = (typeof url === 'string') ? url : String(url);
            return __origOpen.apply(this, arguments);
        };
        var __origSend = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.send = function(body) {
            var token = getToken();
            if (token && this.__xhrUrl && this.__xhrUrl.indexOf('/api/v1/') === 0) {
                this.setRequestHeader('Authorization', 'Bearer ' + token);
            }
            return __origSend.call(this, body);
        };
    })();

    // ── Init ─────────────────────────────────────────────────────────

    function init() {
        updateUI();
        wireLoginBtn();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose for other scripts
    window.WebbotAuth = {
        getToken: getToken,
        getUser: getUser,
        clearAuth: clearAuth,
        saveAuth: saveAuth,
        updateUI: updateUI,
        login: function(username, password) {
            return fetch(API_BASE + '/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'username=' + encodeURIComponent(username) + '&password=' + encodeURIComponent(password)
            }).then(function(resp) {
                return resp.json().then(function(data) {
                    if (!resp.ok) throw new Error(data.detail || '登录失败');
                    saveAuth(data.access_token, data.user);
                    return data;
                });
            });
        },
        logout: function() {
            clearAuth();
            fetch(API_BASE + '/logout', { method: 'POST' }).catch(function(){});
            var currentUrl = window.location.href;
            window.location.href = LOGIN_PAGE + '?redirect=' + encodeURIComponent(currentUrl);
        }
    };

    // Legacy global functions
    window.logout = window.WebbotAuth.logout;
})();
