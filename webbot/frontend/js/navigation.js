// WebBot Navigation Module
// Lazy-loads pages by parent_path from the backend API

console.log('Navigation Module initializing...');

// ============================================================================
// 1. CONSTANTS
// ============================================================================
const API_BASE = '/api/v1/pages/';
const ROOT_PATH = '/canadasite';
const MAX_COLUMNS = 10;

// ============================================================================
// 2. STATE
// ============================================================================
let selectedPageId = null;
let selectedPageData = null;
let currentPath = [];        // Array of {path, title, id} for breadcrumb trail
let loadedPaths = {};        // path -> {pages, status} cache
let columnsCache = [];       // Array of column data for rendering
let isLoading = false;
let lastActivePath = ROOT_PATH;  // Track last active context (#9)

// Expose for debugging
window._debugState = { selectedPageId, currentPath, loadedPaths };

// ============================================================================
// 3. DOM REFERENCES
// ============================================================================
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let columnsContainer, loadingEl, errorContainer, pageStats, breadcrumbNav;
let btnCreate, btnEdit, btnPreview, btnMove, btnPublish, btnDelete, btnRefresh;

function initDom() {
    columnsContainer = $('#columns-container');
    loadingEl = $('#loading-columns');
    errorContainer = $('#error-container');
    pageStats = $('#page-stats');
    breadcrumbNav = $('#breadcrumb-container');
    btnCreate = $('#btn-top-create');
    btnEdit = $('#btn-top-edit');
    btnPreview = $('#btn-top-preview');
    btnMove = $('#btn-top-move');
    btnPublish = $('#btn-top-publish');
    btnDelete = $('#btn-top-delete');
    btnRefresh = $('#btn-top-refresh');
    btnProperties = $('#btn-top-properties');
}

// ============================================================================
// 4. UTILITY
// ============================================================================
function showLoading() {
    if (loadingEl) loadingEl.style.display = 'block';
    if (columnsContainer) columnsContainer.style.display = 'none';
    if (errorContainer) errorContainer.style.display = 'none';
}

function hideLoading() {
    if (loadingEl) loadingEl.style.display = 'none';
    if (columnsContainer) columnsContainer.style.display = 'flex';
}

function showError(msg) {
    if (errorContainer) {
        errorContainer.textContent = msg;
        errorContainer.style.display = 'block';
    }
    if (loadingEl) loadingEl.style.display = 'none';
}

// ============================================================================
// 4b. TOAST NOTIFICATION SYSTEM (fix #5)
// ============================================================================
let toastContainer = null;

function initToast() {
    if (toastContainer) return;
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.style.cssText =
        'position:fixed;top:20px;right:20px;z-index:10000;' +
        'display:flex;flex-direction:column;gap:10px;pointer-events:none;';
    document.body.appendChild(toastContainer);
}

function showToast(message, type, duration) {
    if (!toastContainer) initToast();
    type = type || 'info';
    duration = duration || 4000;

    const toast = document.createElement('div');
    toast.className = 'toast-notification';

    // Color mapping
    const colorMap = {
        success: { bg: '#d4edda', border: '#c3e6cb', text: '#155724' },
        danger: { bg: '#f8d7da', border: '#f5c6cb', text: '#721c24' },
        error: { bg: '#f8d7da', border: '#f5c6cb', text: '#721c24' },
        warning: { bg: '#fff3cd', border: '#ffeeba', text: '#856404' },
        info: { bg: '#d1ecf1', border: '#bee5eb', text: '#0c5460' }
    };
    const colors = colorMap[type] || colorMap.info;

    toast.style.cssText =
        `background:${colors.bg};border:1px solid ${colors.border};` +
        `color:${colors.text};padding:12px 20px;border-radius:4px;` +
        'font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.15);' +
        'transition:all 0.3s ease;opacity:1;pointer-events:auto;' +
        'max-width:400px;word-break:break-word;';

    toast.textContent = message;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(50px)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ============================================================================
// 4c. CONFIRMATION DIALOG (fix #2) - custom overlay, no WET/Bootstrap dependencies
// ============================================================================
var _confirmDialogEl = null;
var _confirmBackdrop = null;

function initConfirmDialog() {
    if (_confirmDialogEl) return;

    // Backdrop
    _confirmBackdrop = document.createElement('div');
    _confirmBackdrop.style.cssText =
        'position:fixed;top:0;left:0;right:0;bottom:0;' +
        'background:rgba(0,0,0,0.5);z-index:9998;display:none;';
    document.body.appendChild(_confirmBackdrop);

    // Dialog
    _confirmDialogEl = document.createElement('div');
    _confirmDialogEl.style.cssText =
        'position:fixed;top:20%;left:50%;transform:translateX(-50%);' +
        'z-index:9999;background:#fff;border-radius:4px;' +
        'box-shadow:0 5px 20px rgba(0,0,0,0.3);' +
        'max-width:480px;width:90%;display:none;font-size:14px;';
    _confirmDialogEl.innerHTML =
        '<div style="padding:15px 20px;border-bottom:1px solid #e5e5e5;font-size:16px;font-weight:bold">' +
        '  Confirm' +
        '</div>' +
        '<div id="confirm-dialog-body" style="padding:20px;line-height:1.5;white-space:pre-wrap"></div>' +
        '<div style="padding:15px 20px;border-top:1px solid #e5e5e5;text-align:right">' +
        '  <button id="confirm-dialog-no" class="btn btn-default" style="margin-right:8px">Cancel</button>' +
        '  <button id="confirm-dialog-yes" class="btn btn-primary">Delete</button>' +
        '</div>';
    document.body.appendChild(_confirmDialogEl);
}

function showConfirmDialog(message, yesText, noText, asHtml) {
    return new Promise(function(resolve) {
        initConfirmDialog();

        var bodyEl = document.getElementById('confirm-dialog-body');
        if (asHtml) {
            bodyEl.innerHTML = message;
            bodyEl.style.whiteSpace = 'normal';
        } else {
            bodyEl.textContent = message;
            bodyEl.style.whiteSpace = 'pre-wrap';
        }
        document.getElementById('confirm-dialog-yes').textContent = yesText || 'Yes';
        document.getElementById('confirm-dialog-no').textContent = noText || 'No';

        _confirmDialogEl.style.display = 'block';
        _confirmBackdrop.style.display = 'block';

        function cleanup() {
            _confirmDialogEl.style.display = 'none';
            _confirmBackdrop.style.display = 'none';
            document.getElementById('confirm-dialog-yes').removeEventListener('click', onYes);
            document.getElementById('confirm-dialog-no').removeEventListener('click', onNo);
            _confirmBackdrop.removeEventListener('click', onBackdrop);
        }
        function onYes() { cleanup(); resolve(true); }
        function onNo() { cleanup(); resolve(false); }
        function onBackdrop() { cleanup(); resolve(false); }

        document.getElementById('confirm-dialog-yes').addEventListener('click', onYes);
        document.getElementById('confirm-dialog-no').addEventListener('click', onNo);
        _confirmBackdrop.addEventListener('click', onBackdrop);
    });
}

// ============================================================================
// 4d. SLUG GENERATION (fix #4 - Chinese-friendly)
// ============================================================================
function generateSlug(title) {
    if (!title) return 'untitled';
    // Keep Chinese characters, alphanumeric, and hyphens
    // Replace spaces/underscores with hyphens
    // Remove everything else (special chars)
    var slug = title.toLowerCase()
        .replace(/[\s_]+/g, '-')                  // spaces/underscores → hyphens
        .replace(/[^\w\u4e00-\u9fff-]+/g, '')     // keep A-Z, 0-9, _, 中文, hyphens
        .replace(/^-+|-+$/g, '');                  // trim leading/trailing hyphens
    return slug || 'untitled';
}

function cleanPathTitle(path) {
    if (!path) return 'Untitled';
    var parts = path.split('/').filter(Boolean);
    return parts[parts.length - 1] || path;
}

function pageTitle(page) {
    return page.title && page.title !== 'untitled' ? page.title : cleanPathTitle(page.path);
}

function encodePath(path) {
    return encodeURIComponent(path);
}

// ============================================================================
// 5. API
// ============================================================================
async function fetchChildren(parentPath) {
    if (loadedPaths[parentPath]) {
        return loadedPaths[parentPath];
    }

    var url = API_BASE + 'path?path=' + encodePath(parentPath);
    var resp = await fetch(url);
    if (!resp.ok) throw new Error('HTTP ' + resp.status + ': ' + resp.statusText);

    var pages = await resp.json();
    // Strip content for performance
    var stripped = pages.map(function(p) {
        var rest = Object.assign({}, p);
        delete rest.content;
        return rest;
    });
    // Sort by title
    stripped.sort(function(a, b) { return (a.title || '').localeCompare(b.title || ''); });

    loadedPaths[parentPath] = stripped;
    return stripped;
}

// ============================================================================
// 5b. DELETE PAGE (fix #2)
// ============================================================================
async function performDelete(pagePath, pageTitle) {
    // Get other language path from selected page data
    var otherLang = selectedPageData && selectedPageData.other_language_path;

    var message = 'Delete page "' + pageTitle + '"?<br>Path: ' + pagePath + '<br><br>This action cannot be undone. All child pages will also be deleted.';
    if (otherLang) {
        message += '<br><br><label style="font-weight:normal;cursor:pointer">' +
            '<input type="checkbox" id="delete-other-lang" checked style="margin-right:6px">' +
            'Delete other language page: <code>' + otherLang + '</code>' +
            '</label>';
    }

    var confirmed = await showConfirmDialog(message, 'Delete', 'Cancel', true);
    if (!confirmed) return;

    // Read checkbox state (if it exists)
    var delOther = true; // default
    var cb = document.getElementById('delete-other-lang');
    if (cb) {
        delOther = cb.checked;
    }

    try {
        var url = '/api/v1/pages/' + encodeURIComponent(pagePath);
        if (delOther && otherLang) {
            url += '?delete_other_language=true&other_language_path=' + encodeURIComponent(otherLang);
        }

        var resp = await fetch(url, {
            method: 'DELETE'
        });
        if (!resp.ok) {
            var errData = null;
            try { errData = await resp.json(); } catch(e) {}
            throw new Error(errData && errData.detail ? errData.detail : 'HTTP ' + resp.status);
        }

        var result = await resp.json();

        // Clear cache
        loadedPaths = {};
        columnsCache = [];

        var toastMsg = 'Page "' + pageTitle + '" deleted successfully';
        if (result.other_deleted) {
            toastMsg += ' (other language page also deleted)';
        }
        showToast(toastMsg, 'success');

        // Go back to parent if we have one
        if (currentPath.length > 1) {
            var parentIdx = currentPath.length - 2;
            currentPath = currentPath.slice(0, parentIdx + 1);
            selectedPageId = currentPath[parentIdx].id;
            selectedPageData = currentPath[parentIdx];
            initNavigationAt(currentPath);
        } else {
            selectedPageId = null;
            selectedPageData = null;
            currentPath = [];
            initNavigation();
        }
    } catch (err) {
        showToast('Failed to delete: ' + err.message, 'danger');
    }
}

// ============================================================================
// Publish page — POST to backend, open result in new tab
// ============================================================================
async function performPublish(pageData) {
    var pagePath = pageData.path;
    var pageTitle = pageTitle ? pageTitle : pageData.name;

    showToast('Publishing "' + (pageTitle || pageData.name) + '"...', 'info');

    try {
        var resp = await fetch('/api/v1/pages/publish?path=' + encodeURIComponent(pagePath), {
            method: 'POST'
        });

        if (!resp.ok) {
            var errData = null;
            try { errData = await resp.json(); } catch(e) {}
            throw new Error(errData && errData.detail ? errData.detail : 'HTTP ' + resp.status);
        }

        var result = await resp.json();

        showToast('"' + (pageTitle || pageData.name) + '" published successfully!', 'success');

        // Open published page in new tab
        const pageUrl = '/publish/' + pagePath.replace(/^\//, '') + '.html';
        window.open(pageUrl, '_blank');
    } catch (err) {
        showToast('Failed to publish: ' + err.message, 'danger');
    }
}

// ============================================================================
// 6. RENDERING
// ============================================================================
function renderColumn(columnIndex, title, pages, parentPath) {
    var column = document.createElement('div');
    column.className = 'navigation-column';
    column.dataset.columnIndex = columnIndex;

    // Header
    var header = document.createElement('div');
    header.className = 'column-header';
    var h3 = document.createElement('h3');
    h3.textContent = title || 'Level ' + (columnIndex + 1);
    header.appendChild(h3);
    column.appendChild(header);

    // Pages list
    var list = document.createElement('ul');
    list.className = 'pages-list';

    pages.forEach(function(page) {
        var li = document.createElement('li');
        li.className = 'page-item';
        li.dataset.pageId = page.id;
        li.dataset.pagePath = page.path;

        if (parentPath) {
            li.dataset.parentPath = parentPath;
        }

        var link = document.createElement('a');
        link.href = '#';
        link.className = 'page-link';

        // Title
        var titleSpan = document.createElement('span');
        titleSpan.className = 'page-title';
        titleSpan.textContent = pageTitle(page);
        link.appendChild(titleSpan);

        // Path (small font below title)
        var pathSpan = document.createElement('span');
        pathSpan.className = 'page-path';
        pathSpan.textContent = page.path;
        link.appendChild(pathSpan);

        // Click handler
        link.addEventListener('click', function(e) {
            e.preventDefault();
            selectPage(page, columnIndex);
        });

        li.appendChild(link);
        column.appendChild(li);
    });

    // Empty state
    if (pages.length === 0) {
        var empty = document.createElement('li');
        empty.className = 'page-item empty';
        empty.textContent = 'No child pages';
        list.appendChild(empty);
    }

    column.appendChild(list);
    return column;
}

function renderColumns() {
    columnsContainer.innerHTML = '';

    columnsCache.forEach(function(colData, idx) {
        var col = renderColumn(idx, colData.title, colData.pages, colData.parentPath);
        columnsContainer.appendChild(col);
    });

    updateBreadcrumb();
    updateButtons();
    updateStats();
    highlightSelectedPage();
}

function highlightSelectedPage() {
    columnsContainer.querySelectorAll('.page-item.selected').forEach(function(el) {
        el.classList.remove('selected');
    });
    if (selectedPageId) {
        var sel = columnsContainer.querySelector('.page-item[data-page-id="' + CSS.escape(selectedPageId) + '"]');
        if (sel) sel.classList.add('selected');
    }
}

// ============================================================================
// 7. NAVIGATION
// ============================================================================
async function selectPage(page, columnIndex) {
    selectedPageId = page.id;
    selectedPageData = page;
    lastActivePath = page.path; // track for state retention

    try {
        showLoading();
        var children = await fetchChildren(page.path);
        hideLoading();

        if (currentPath.length < 2) {
            // Levels 1-2: drill-down, single column replaces content
            currentPath.push(page);
            columnsCache = children.length > 0 ? [{
                title: pageTitle(page),
                pages: children,
                parentPath: page.path
            }] : [];
        } else {
            // Levels 3+: multi-column
            // Column N holds path entry N+1 (col 0 = entry 1, col 1 = entry 2, etc.)
            var keepCount = columnIndex + 2;
            currentPath = currentPath.slice(0, keepCount);
            currentPath.push(page);

            columnsCache = columnsCache.slice(0, columnIndex + 1);
            if (children.length > 0 && columnsCache.length < MAX_COLUMNS) {
                columnsCache.push({
                    title: pageTitle(page),
                    pages: children,
                    parentPath: page.path
                });
            }
        }
    } catch (err) {
        hideLoading();
        console.warn('Failed to load children:', err);
    }

    renderColumns();
}

function navigateHome() {
    selectedPageId = null;
    selectedPageData = null;
    currentPath = [];
    lastActivePath = ROOT_PATH;
    initNavigation();
}

// ============================================================================
// 8. BREADCRUMB
// ============================================================================
function updateBreadcrumb() {
    var container = breadcrumbNav.querySelector('.aem-breadcrumb') || breadcrumbNav;
    container.innerHTML = '';

    // Home item
    var homeSpan = document.createElement('span');
    homeSpan.className = 'breadcrumb-item';
    var homeLink = document.createElement('a');
    homeLink.href = '#';
    homeLink.textContent = 'Canada site';
    homeLink.addEventListener('click', function(e) {
        e.preventDefault();
        navigateHome();
    });
    homeSpan.appendChild(homeLink);
    container.appendChild(homeSpan);

    // Path items
    currentPath.forEach(function(page, idx) {
        var span = document.createElement('span');
        span.className = 'breadcrumb-item';

        if (idx < currentPath.length - 1) {
            var link = document.createElement('a');
            link.href = '#';
            link.textContent = pageTitle(page);
            link.addEventListener('click', function(e) {
                e.preventDefault();
                goToPath(idx);
            });
            span.appendChild(link);
        } else {
            span.textContent = pageTitle(page);
            span.className += ' active';
        }

        container.appendChild(span);
    });
}

function goToPath(index) {
    selectedPageId = currentPath[index].id;
    selectedPageData = currentPath[index];
    lastActivePath = currentPath[index].path;

    // Truncate path to this level
    currentPath = currentPath.slice(0, index + 1);

    // Rebuild columns from cached children
    var lastPage = currentPath[currentPath.length - 1];
    var children = loadedPaths[lastPage.path] || [];

    if (currentPath.length <= 2) {
        columnsCache = children.length > 0 ? [{
            title: pageTitle(lastPage),
            pages: children,
            parentPath: lastPage.path
        }] : [];
    } else {
        columnsCache = [];
        for (var i = 1; i < currentPath.length; i++) {
            var pp = currentPath[i];
            var ch = loadedPaths[pp.path] || [];
            columnsCache.push({
                title: pageTitle(pp),
                pages: ch,
                parentPath: pp.path
            });
        }
    }

    renderColumns();
}

// ============================================================================
// 9. BUTTONS (fix #8 - tooltips on disabled buttons)
// ============================================================================
function updateButtons() {
    var hasSelection = selectedPageId !== null;
    btnEdit.disabled = !hasSelection;
    btnPreview.disabled = !hasSelection;
    btnMove.disabled = !hasSelection;
    btnPublish.disabled = !hasSelection;
    btnDelete.disabled = !hasSelection;
    btnProperties.disabled = !hasSelection;

    btnEdit.className = hasSelection ? 'btn btn-edit' : 'btn btn-edit disabled';
    btnPreview.className = hasSelection ? 'btn btn-info' : 'btn btn-info disabled';
    btnMove.className = hasSelection ? 'btn btn-move' : 'btn btn-move disabled';
    btnPublish.className = hasSelection ? 'btn btn-publish' : 'btn btn-publish disabled';
    btnDelete.className = hasSelection ? 'btn btn-delete' : 'btn btn-delete disabled';
    btnProperties.className = hasSelection ? 'btn btn-primary' : 'btn btn-primary disabled';

    // Tooltip messages for disabled state (#8)
    btnEdit.title = hasSelection ? 'Edit selected page' : 'Select a page to edit';
    btnPreview.title = hasSelection ? 'Preview page content' : 'Select a page to preview';
    btnMove.title = hasSelection ? 'Move selected page' : 'Select a page to move';
    btnPublish.title = hasSelection ? 'Publish selected page' : 'Select a page to publish';
    btnDelete.title = hasSelection ? 'Delete selected page' : 'Select a page to delete';
    btnProperties.title = hasSelection ? 'View/edit page properties' : 'Select a page to view properties';
}

// ============================================================================
// MODAL HELPERS (vanilla JS — Bootstrap modal plugin not available)
// ============================================================================
function showModal(el) {
    el.style.display = 'block';
    el.classList.remove('mfp-hide'); // Handle WET overlay modals
    el.classList.add('in');
    document.body.classList.add('modal-open');
    // Add backdrop
    var backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop fade in';
    backdrop.setAttribute('data-modal-backdrop', el.id);
    backdrop.addEventListener('click', function() { hideModal(el); });
    document.body.appendChild(backdrop);
}

function hideModal(el) {
    el.style.display = 'none';
    el.classList.remove('in');
    document.body.classList.remove('modal-open');
    var backdrop = document.querySelector('[data-modal-backdrop="' + el.id + '"]');
    if (backdrop) backdrop.remove();
}

function setupButtons() {
    // ============================================================================
    // 5b. CREATE PAGE MODAL
    // ============================================================================
    var createPageModal = document.getElementById('createPageModal');
    var createPageForm = document.getElementById('createPageForm');
    var newPageTitle = document.getElementById('newPageTitle');
    var newPageName = document.getElementById('newPageName');
    var newPageFrTitle = document.getElementById('newPageFrTitle');
    var newPageFrName = document.getElementById('newPageFrName');
    var newPageParent = document.getElementById('newPageParent');
    var newPageOtherLangParent = document.getElementById('newPageOtherLangParent');
    var urlPreview = document.getElementById('urlPreview');
    var createPageError = document.getElementById('createPageError');
    var createPageSuccess = document.getElementById('createPageSuccess');
    var createPageSaveBtn = document.getElementById('createPageSaveBtn');

    // Close button bindings (Bootstrap JS not available)
    createPageModal.querySelectorAll('[data-dismiss="modal"]').forEach(function(btn) {
        btn.addEventListener('click', function() { hideModal(createPageModal); });
    });

    // ============================================================================
    // CREATE button (fix #1 - root node check, fix #9 - state retention)
    // ============================================================================
    btnCreate.addEventListener('click', function() {
        var parentPath = selectedPageData ? selectedPageData.path : ROOT_PATH;

        if (parentPath === ROOT_PATH) {
            showToast('Cannot create page directly under root. Select a sub-folder first.', 'warning');
            return;
        }

        showCreatePageModal(parentPath);
    });

    // ============================================================================
    // EDIT button
    // ============================================================================
    btnEdit.addEventListener('click', function() {
        if (selectedPageData) {
            window.open('/static/editor.html?pageId=' + encodePath(selectedPageData.path), '_blank');
        }
    });

    // ============================================================================
    // PREVIEW button
    // ============================================================================
    btnPreview.addEventListener('click', function() {
        if (selectedPageData) {
            window.open('/api/v1/pages/preview?path=' + encodePath(selectedPageData.path), '_blank');
        }
    });

    // ============================================================================
    // MOVE button
    // ============================================================================
    btnMove.addEventListener('click', function() {
        if (selectedPageData) {
            showToast('Move feature: under development.', 'warning');
        }
    });

    // ============================================================================
    // PUBLISH button
    // ============================================================================
    btnPublish.addEventListener('click', function() {
        if (selectedPageData) {
            performPublish(selectedPageData);
        }
    });

    // ============================================================================
    // DELETE button (fix #2)
    // ============================================================================
    btnDelete.addEventListener('click', function() {
        if (selectedPageData) {
            performDelete(selectedPageData.path, pageTitle(selectedPageData));
        }
    });

    // ============================================================================
    // REFRESH button
    // ============================================================================
    btnRefresh.addEventListener('click', function() {
        loadedPaths = {};
        columnsCache = [];
        currentPath = [];
        selectedPageId = null;
        selectedPageData = null;
        initNavigation();
    });

    // ============================================================================
    // PROPERTIES button
    // ============================================================================
    btnProperties.addEventListener('click', function() {
        if (!selectedPageData) return;
        loadAndShowProperties(selectedPageData);
    });

    // ============================================================================
    // PROPERTIES modal logic
    // ============================================================================
    function loadAndShowProperties(pageData) {
        var modal = document.getElementById('propertiesModal');
        if (!modal) { showToast('Properties modal not found', 'danger'); return; }

        // Determine the page ID to fetch
        var pageId = pageData.id || pageData.path;
        if (!pageId) { showToast('Cannot determine page ID', 'danger'); return; }

        showToast('Loading properties...', 'info');

        fetch('/api/v1/pages/' + encodeURIComponent(pageId) + '/properties')
            .then(function(r) {
                if (!r.ok) throw new Error('Failed: ' + r.status);
                return r.json();
            })
            .then(function(data) {
                // Page ID = last segment of path
                var thePath = data.path || pageData.path || '';
                var pageId = thePath.replace(/\/$/, '').split('/').pop() || data.id || '—';
                setPropVal('prop-id', pageId);
                setPropVal('prop-title', data.title);
                setPropVal('prop-language', data.language);
                setPropVal('prop-path', thePath);

                // Derive parent path: remove last segment from path
                var parentPath = data.parent_path;
                if (!parentPath && thePath) {
                    var parts = thePath.replace(/\/$/, '').split('/');
                    parts.pop();
                    parentPath = parts.join('/') || '';
                }
                setPropVal('prop-parent', parentPath || '—');
                setPropVal('prop-created-by', data.created_by || '—');
                setPropVal('prop-created-at', data.created_at || '—');
                setPropVal('prop-updated-at', data.updated_at || data.last_modified || '—');
                setPropVal('prop-published-at', data.published_at || data.last_published || '—');

                // Other language path: use value from DB first, fall back to alternate_fr_url
                var otherLangPath = data.other_language_path || '';
                if (!otherLangPath) {
                    var altUrl = data.metadata && data.metadata.alternate_fr_url;
                    if (altUrl) {
                        // e.g. 'https://www.canada.ca/fr/patrimoine-canadien.html' → '/fr/patrimoine-canadien'
                        otherLangPath = altUrl
                            .replace('https://www.canada.ca', '')
                            .replace(/\.html?$/i, '');
                    }
                }
                setPropVal('prop-other-lang', otherLangPath);

                // File path (from metadata)
                var filePath = data.file_path || (data.metadata && data.metadata.file_path) || '';
                setPropVal('prop-filepath', filePath);

                // Has children
                var childEl = document.getElementById('prop-has-children');
                if (childEl && data.has_children !== undefined) {
                    childEl.checked = !!data.has_children;
                }

                // Status dropdown
                var statusEl = document.getElementById('prop-status');
                if (statusEl && data.status) {
                    statusEl.value = data.status;
                }

                // Hide in Navigation
                var hideNavEl = document.getElementById('prop-hide-nav');
                if (hideNavEl && data.hide_in_navigation !== undefined) {
                    hideNavEl.checked = !!data.hide_in_navigation;
                }

                showModal(modal);
            })
            .catch(function(err) {
                console.error('Properties load error:', err);
                showToast('Failed to load properties: ' + err.message, 'danger');
            });
    }

    // Helper: set input value
    function setPropVal(id, val) {
        var el = document.getElementById(id);
        if (el) el.value = (val != null) ? val : '—';
    }

    // Helper: get input value
    function getPropVal(id) {
        var el = document.getElementById(id);
        return el ? el.value.trim() : '';
    }

    // Save properties handler
    var propSaveBtn = document.getElementById('prop-save-btn');
    if (propSaveBtn) {
        propSaveBtn.addEventListener('click', function() {
            var modal = document.getElementById('propertiesModal');
            // Use full path for API, not the display ID (last segment)
            var pagePath = getPropVal('prop-path');
            if (!pagePath) { showToast('No page path', 'danger'); return; }

            var filePath = getPropVal('prop-filepath');
            var otherLang = getPropVal('prop-other-lang');

            // Other language path is mandatory
            if (!otherLang || !otherLang.trim()) {
                showToast('Other Language Path is required!', 'danger');
                document.getElementById('prop-other-lang').focus();
                return;
            }

            var payload = {
                title: getPropVal('prop-title') || undefined,
                status: document.getElementById('prop-status') ? document.getElementById('prop-status').value : undefined,
                file_path: filePath || undefined,
                other_language_path: otherLang.trim(),
                hide_in_navigation: document.getElementById('prop-hide-nav') ? document.getElementById('prop-hide-nav').checked : undefined
            };

            // Remove undefined values
            Object.keys(payload).forEach(function(k) {
                if (payload[k] === undefined) delete payload[k];
            });

            fetch('/api/v1/pages/' + encodeURIComponent(pagePath), {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(function(r) {
                if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail || e.message || r.status); });
                return r.json();
            })
            .then(function() {
                showToast('✅ Properties saved!', 'success');
                hideModal(modal);
                // Refresh current view without jumping to root
                loadedPaths = {};
                var restorePath = currentPath.slice(); // copy
                if (restorePath.length > 0) {
                    initNavigationAt(restorePath);
                } else {
                    initNavigation();
                }
            })
            .catch(function(err) {
                showToast('Failed to save: ' + err.message, 'danger');
            });
        });
    }

    // Bind close for properties modal
    var propModal = document.getElementById('propertiesModal');
    if (propModal) {
        propModal.querySelectorAll('[data-dismiss="modal"]').forEach(function(btn) {
            btn.addEventListener('click', function() { hideModal(propModal); });
        });
    }

    // ============================================================================
    // CREATE MODAL helpers
    // ============================================================================
    function showCreatePageModal(parentPath) {
        newPageParent.value = parentPath;
        newPageTitle.value = '';
        newPageName.value = '';
        newPageFrTitle.value = '';
        newPageFrName.value = '';
        newPageOtherLangParent.value = '';
        createPageError.style.display = 'none';
        createPageSuccess.style.display = 'none';
        createPageSaveBtn.disabled = false;
        createPageSaveBtn.textContent = 'Create & Edit';
        var parentInfoText = document.getElementById('parentInfoText');
        if (parentInfoText) parentInfoText.textContent = '';
        if (parentPath) {
            fetch('/api/v1/pages/by-path?path=' + encodeURIComponent(parentPath))
                .then(function(resp) {
                    if (!resp.ok) throw new Error('HTTP ' + resp.status);
                    return resp.json();
                })
                .then(function(data) {
                    if (data) {
                        if (data.title && parentInfoText) {
                            parentInfoText.textContent = '📄 ' + data.title;
                        }
                        if (data.other_language_path && newPageOtherLangParent) {
                            newPageOtherLangParent.value = data.other_language_path;
                        }
                        updateCreatePreviews();
                    }
                })
                .catch(function(err) {
                    // Silent fail
                });
        }
        updateCreatePreviews();
        showModal(createPageModal);
        setTimeout(function() { newPageTitle.focus(); }, 300);
    }

    // ============================================================================
    // Update path previews for Create modal
    // ============================================================================
    var createEnPathPreview = document.getElementById('createEnPathPreview');
    var createFrPathPreview = document.getElementById('createFrPathPreview');
    function updateCreatePreviews() {
        var parentPath = newPageParent ? newPageParent.value : '';
        var nameVal = newPageName ? newPageName.value.trim() : '';
        var frParentVal = newPageOtherLangParent ? newPageOtherLangParent.value.trim() : '';
        var frNameVal = newPageFrName ? newPageFrName.value.trim() : '';
        // English path preview
        if (createEnPathPreview) {
            if (nameVal && parentPath) {
                createEnPathPreview.textContent = parentPath.replace(/\/+$/, '') + '/' + nameVal;
            } else {
                createEnPathPreview.textContent = '';
            }
        }
        // French path preview
        if (createFrPathPreview) {
            if (frNameVal && frParentVal) {
                createFrPathPreview.textContent = frParentVal.replace(/\/+$/, '') + '/' + frNameVal;
            } else {
                createFrPathPreview.textContent = '';
            }
        }
    }

    // ============================================================================
    // URL live preview + name auto-generation (fix #3)
    // ============================================================================
    if (urlPreview) {
        // Auto-generate EN name from title (only if user hasn't manually edited the name field)
        var nameManuallyEdited = false;
        newPageTitle.addEventListener('input', function() {
            var title = this.value.trim();
            var parentPath = newPageParent.value;
            var slug = generateSlug(title);
            if (!nameManuallyEdited && newPageName) {
                newPageName.value = slug;
            }
            var usedSlug = newPageName ? (newPageName.value.trim() || slug) : slug;
            var fullPath = parentPath ? parentPath + '/' + usedSlug : '/' + usedSlug;
            urlPreview.textContent = usedSlug ? fullPath : (parentPath ? parentPath + '/' : '/');
            if (typeof updateCreatePreviews === 'function') updateCreatePreviews();
        });
        if (newPageName) {
            newPageName.addEventListener('input', function() {
                nameManuallyEdited = true;
                var slug = this.value.trim();
                var parentPath = newPageParent.value;
                var fullPath = parentPath ? parentPath + '/' + slug : '/' + slug;
                urlPreview.textContent = slug ? fullPath : (parentPath ? parentPath + '/' : '/');
                if (typeof updateCreatePreviews === 'function') updateCreatePreviews();
            });
            newPageName.addEventListener('blur', function() {
                if (!this.value.trim()) {
                    nameManuallyEdited = false;
                }
            });
        }
    } else {
        // No old urlPreview element — register bare event listeners that call updateCreatePreviews
        newPageTitle.addEventListener('input', function() {
            var title = this.value.trim();
            var slug = generateSlug(title);
            if (typeof nameManuallyEdited === 'undefined' || !nameManuallyEdited) {
                if (newPageName) newPageName.value = slug;
            }
            if (typeof updateCreatePreviews === 'function') updateCreatePreviews();
        });
        if (newPageName) {
            newPageName.addEventListener('input', function() {
                nameManuallyEdited = true;
                if (typeof updateCreatePreviews === 'function') updateCreatePreviews();
            });
            newPageName.addEventListener('blur', function() {
                if (!this.value.trim()) nameManuallyEdited = false;
            });
        }
    }

    // Always register FR name auto-generation and Other Language Parent Path preview updates
    if (newPageFrTitle && newPageFrName) {
        var frNameManuallyEdited = false;
        newPageFrTitle.addEventListener('input', function() {
            var frTitle = this.value.trim();
            var frSlug = generateSlug(frTitle);
            if (!frNameManuallyEdited) {
                newPageFrName.value = frSlug;
            }
            if (typeof updateCreatePreviews === 'function') updateCreatePreviews();
        });
        newPageFrName.addEventListener('input', function() {
            frNameManuallyEdited = true;
            if (typeof updateCreatePreviews === 'function') updateCreatePreviews();
        });
        newPageFrName.addEventListener('blur', function() {
            if (!this.value.trim()) {
                frNameManuallyEdited = false;
            }
        });
    }
    if (newPageOtherLangParent) {
        newPageOtherLangParent.addEventListener('input', function() {
            if (typeof updateCreatePreviews === 'function') updateCreatePreviews();
        });
    }

    // ============================================================================
    // TRANSLATE button handler
    // ============================================================================
    var btnTranslate = document.getElementById('btnTranslateFr');
    if (btnTranslate) {
        btnTranslate.addEventListener('click', async function() {
            var enTitle = newPageTitle.value.trim();
            if (!enTitle) {
                showToast('Please enter an English title first.', 'warning');
                newPageTitle.focus();
                return;
            }
            btnTranslate.disabled = true;
            btnTranslate.textContent = '...';
            try {
                var resp = await fetch('/api/v1/pages/translate?text=' + encodeURIComponent(enTitle));
                if (!resp.ok) {
                    var errData = null;
                    try { errData = await resp.json(); } catch(e) {}
                    throw new Error(errData && errData.detail ? errData.detail : 'HTTP ' + resp.status);
                }
                var data = await resp.json();
                if (newPageFrTitle) {
                    newPageFrTitle.value = data.translated;
                    // Auto-trigger input event to generate FR name
                    var evt = new Event('input', { bubbles: true });
                    newPageFrTitle.dispatchEvent(evt);
                }
                showToast('✅ Translated: "' + data.translated + '"', 'success');
            } catch (err) {
                showToast('Translation failed: ' + err.message, 'danger');
            } finally {
                btnTranslate.disabled = false;
                btnTranslate.textContent = '⟳ Translate';
            }
        });
    }

    // ============================================================================
    // CREATE FORM SUBMIT (fix #7 - remove 800ms delay, fix #5 - toast, fix #9)
    // ============================================================================
    createPageForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        var title = newPageTitle.value.trim();
        if (!title) {
            createPageError.textContent = 'Please enter a page title.';
            createPageError.style.display = 'block';
            return;
        }

        var parentPath = newPageParent.value;

        // Extra safety: check root path again (fix #1)
        if (parentPath === ROOT_PATH) {
            hideModal(createPageModal);
            showToast('Cannot create page directly under root. Select a sub-folder first.', 'warning');
            return;
        }

        // Generate path from title using Chinese-friendly slug (fix #4)
        // Use user-editable name field if non-empty, otherwise fallback to auto-generated
        var slug;
        if (newPageName && newPageName.value.trim()) {
            slug = generateSlug(newPageName.value.trim());
        } else {
            slug = generateSlug(title);
        }
        var pagePath = parentPath.endsWith('/') ? parentPath + slug : parentPath + '/' + slug;

        // Collect French fields
        var frTitle = newPageFrTitle ? newPageFrTitle.value.trim() : '';
        var frName = newPageFrName ? newPageFrName.value.trim() : '';
        var otherLangParent = newPageOtherLangParent ? newPageOtherLangParent.value.trim() : '';

        // Build metadata with FR fields
        var metadata = {};
        if (frTitle) metadata.fr_title = frTitle;
        if (frName) metadata.fr_name = frName;
        if (otherLangParent) metadata.fr_parent_path = otherLangParent;

        // Build other_language_path from FR fields
        var otherLanguagePath = '';
        if (frName && otherLangParent) {
            var frParentClean = otherLangParent.replace(/\/+$/, '');
            otherLanguagePath = frParentClean + '/' + frName;
        }

        createPageError.style.display = 'none';
        createPageSuccess.style.display = 'none';
        createPageSaveBtn.disabled = true;
        createPageSaveBtn.textContent = 'Creating...';

        try {
            // 1. Create English page
            var response = await fetch('/api/v1/pages/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: title,
                    path: pagePath,
                    parent_path: parentPath,
                    language: 'en',
                    status: 'draft',
                    content: '',
                    metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
                    other_language_path: otherLanguagePath || undefined
                })
            });

            if (!response.ok) {
                var errData = null;
                try { errData = await response.json(); } catch(e) {}
                throw new Error(errData && errData.detail ? errData.detail : 'HTTP ' + response.status);
            }

            var newPage = await response.json();
            var actualPagePath = newPage.path || pagePath;
            var frCreated = false;

            // 2. Create French page too if FR fields present
            if (frTitle && frName && otherLangParent) {
                var frParentClean = otherLangParent.replace(/\/+$/, '');
                var frPagePath = frParentClean + '/' + frName;

                try {
                    var frResp = await fetch('/api/v1/pages/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            title: frTitle,
                            path: frPagePath,
                            parent_path: otherLangParent,
                            language: 'fr',
                            status: 'draft',
                            content: '',
                            metadata: {
                                en_title: title,
                                en_name: slug,
                                en_parent_path: parentPath
                            },
                            other_language_path: actualPagePath
                        })
                    });
                    frCreated = frResp.ok;
                } catch(e) {
                    // French page creation failed silently
                }
            }

            // Show toast
            var msg = '✅ Page "' + title + '" created!';
            if (frCreated) {
                msg += ' French page "' + frTitle + '" also created.';
            } else if (frTitle) {
                msg += ' (French page was not created — check FR fields.)';
            }
            showToast(msg, 'success');

            // Refresh navigation
            loadedPaths = {};
            columnsCache = [];

            // Open English page editor in new tab
            var editorUrl = '/static/editor.html?pageId=' + encodeURIComponent(actualPagePath);
            window.open(editorUrl, '_blank');

        } catch (err) {
            showToast('Failed to create page: ' + err.message, 'danger');
            createPageSaveBtn.disabled = false;
            createPageSaveBtn.textContent = 'Create & Edit';
        }
    });
}

// ============================================================================
// 8b. NAVIGATION WITH STATE RETENTION (fix #9)
// ============================================================================
async function initNavigationAt(pathToRestore) {
    showLoading();
    try {
        if (!pathToRestore || pathToRestore.length === 0) {
            // No path to restore — just init normally
            var children = await fetchChildren(ROOT_PATH);
            columnsCache = [{
                title: 'Canada.ca',
                pages: children,
                parentPath: ROOT_PATH
            }];
            selectedPageId = null;
            selectedPageData = null;
            currentPath = [];
            renderColumns();
            hideLoading();
            updateStats();
            return;
        }

        // Reset state
        loadedPaths = {};
        selectedPageId = pathToRestore[pathToRestore.length - 1].id;
        selectedPageData = pathToRestore[pathToRestore.length - 1];
        currentPath = [];
        columnsCache = [];

        // Walk through each level to load children
        for (var i = 0; i < pathToRestore.length; i++) {
            var entry = pathToRestore[i];
            currentPath.push(entry);

            var children = await fetchChildren(entry.path);

            // Build column for this level's children (except last level = selected page)
            if (children.length > 0 && columnsCache.length < MAX_COLUMNS) {
                columnsCache.push({
                    title: pageTitle(entry),
                    pages: children,
                    parentPath: entry.path
                });
            }
        }

        renderColumns();
        hideLoading();
        updateStats();
        console.log('Navigation restored to: ' + selectedPageData.path);
    } catch (err) {
        console.error('Navigation restore failed:', err);
        showError('Failed to restore navigation: ' + err.message + '. Please try refreshing.');
    }
}

// ============================================================================
// 10. STATS
// ============================================================================
async function updateStats() {
    if (!pageStats) return;
    var loadedCount = Object.keys(loadedPaths).length;
    var totalVisible = Object.values(loadedPaths).reduce(function(sum, pages) { return sum + pages.length; }, 0);

    var rootChildren = loadedPaths[ROOT_PATH];
    var rootCount = rootChildren ? rootChildren.length : '?';

    pageStats.innerHTML = '<strong>' + rootCount + '</strong> root pages · <strong>' + totalVisible + '</strong> pages loaded · <strong>' + loadedCount + '</strong> paths cached';
}

// ============================================================================
// 11. INIT
// ============================================================================
async function initNavigation() {
    showLoading();
    try {
        var children = await fetchChildren(ROOT_PATH);
        columnsCache = [{
            title: 'Canada.ca',
            pages: children,
            parentPath: ROOT_PATH
        }];
        selectedPageId = null;
        selectedPageData = null;
        currentPath = [];

        renderColumns();
        hideLoading();

        updateStats();
        console.log('Navigation initialized: ' + children.length + ' root pages');
    } catch (err) {
        console.error('Navigation init failed:', err);
        showError('Failed to load navigation: ' + err.message + '. Please try refreshing.');
    }
}

// ============================================================================
// 12. BOOT
// ============================================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM ready - initializing navigation');
    initDom();
    initToast();
    setupButtons();
    initNavigation();
});

console.log('Navigation Module loaded.');
