// WebBot Navigation Module
// Lazy-loads pages by parent_path from the backend API

console.log('Navigation Module initializing...');

// HTML escape helper (must be at top for global availability)
function esc(s) {
    if (!s) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/**
 * Auto-derive FileBot image path from page path.
 * Page path: /canadasite/en/section/subsection/...
 * Result:    /content/dam/en/section/subsection/...
 */
/**
 * Derive DAM image path from a WebBot page path.
 * e.g. /canadasite/en/contact → /canadasite/content/dam/en/contact
 */
function deriveImagePathFromPagePath(pagePath) {
    if (!pagePath) return '';
    // Insert /content/dam/ right after /canadasite/
    return pagePath.replace('/canadasite/', '/canadasite/content/dam/');
}

/**
 * Setup auto-image checkbox with listener for auto-fill.
 */
function setupAutoImageCheckbox(pagePath) {
    var chk = document.getElementById('prop-auto-image');
    if (!chk) return;
    // Remove previous listener to avoid duplicates
    var newChk = chk.cloneNode(true);
    chk.parentNode.replaceChild(newChk, chk);
    newChk.addEventListener('change', function() {
        if (newChk.checked && pagePath) {
            // Auto-fill filepath input from page path
            var derived = deriveImagePathFromPagePath(pagePath);
            setPropVal('prop-filepath', derived);
        }
        // When unchecked, leave filepath as-is (user may want to keep manual path)
    });
}

/**
 * Sync auto-image checkbox from saved auto_image_path metadata.
 * Checkbox is ON when auto_image_path was saved as true.
 * When checked, also auto-fill filepath if not already set.
 * @param {object} [pageData] - API response with metadata
 * @param {string} [pagePath] - current page path for derivation
 */
function syncAutoImageCheckbox(pageData, pagePath) {
    var chk = document.getElementById('prop-auto-image');
    if (!chk) return;
    var isChecked = !!(pageData && pageData.metadata && pageData.metadata.auto_image_path);
    chk.checked = isChecked;
    // When auto from ancestor, also fill filepath if empty
    if (isChecked && pagePath) {
        var existingFp = getPropVal('prop-filepath');
        if (!existingFp) {
            var derived = deriveImagePathFromPagePath(pagePath);
            setPropVal('prop-filepath', derived);
        }
    }
}

// ============================================================================
// 1. CONSTANTS
// ============================================================================
const API_BASE = '/api/v1/pages/';
const ROOT_PATH = '/canadasite';
const TAG_ROOT = '/canadasite/tags';
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
let btnCreate, btnEdit, btnPreview, btnMove, btnPublish, btnUnpublish, btnDelete, btnRefresh;

function initDom() {
    columnsContainer = $('#columns-container');
    loadingEl = $('#loading-columns');
    errorContainer = $('#error-container');
    pageStats = $('#page-stats');
    breadcrumbNav = $('#wb-bc .breadcrumb');
    // Home breadcrumb click → navigateHome
    var homeLink = document.getElementById('breadcrumb-home');
    if (homeLink) {
        homeLink.addEventListener('click', function(e) {
            e.preventDefault();
            navigateHome();
        });
    }
    btnCreate = $('#btn-top-create');
    btnEdit = $('#btn-top-edit');
    btnPreview = $('#btn-top-preview');
    btnMove = $('#btn-top-move');
    btnPublish = $('#btn-top-publish');
    btnUnpublish = $('#btn-top-unpublish');
    btnDelete = $('#btn-top-delete');
    btnRefresh = $('#btn-top-refresh');
    btnProperties = $('#btn-top-properties');
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
// Publish page — POST to backend, show toast + refresh status
// ============================================================================
async function performPublish(pageData) {
    var pagePath = pageData.path;
    var pageName = pageData.title || pageData.name;

    showToast('Publishing "' + pageName + '"...', 'info');

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

        // Update local data
        pageData.status = 'published';
        pageData.last_published = new Date().toISOString();

        showToast('Page ' + pagePath + ' is published', 'success');

        // Re-render to reflect status change
        renderColumns();
    } catch (err) {
        showToast('Failed to publish: ' + err.message, 'danger');
    }
}

// ============================================================================
async function performUnpublish(pageData) {
    var pagePath = pageData.path;
    var pageTitle = pageTitle ? pageTitle : pageData.name;

    if (!confirm('Unpublish "' + (pageTitle || pageData.name) + '"? This will remove the published page from the public site.')) {
        return;
    }

    showToast('Unpublishing "' + (pageTitle || pageData.name) + '"...', 'info');

    try {
        var resp = await fetch('/api/v1/pages/unpublish?path=' + encodeURIComponent(pagePath), {
            method: 'POST'
        });

        if (!resp.ok) {
            var errData = null;
            try { errData = await resp.json(); } catch(e) {}
            throw new Error(errData && errData.detail ? errData.detail : 'HTTP ' + resp.status);
        }

        var result = await resp.json();

        // Update local data
        pageData.status = 'draft';
        pageData.last_published = null;

        showToast('"' + (pageTitle || pageData.name) + '" unpublished!', 'success');

        // Re-render to reflect status change
        renderColumns();
    } catch (err) {
        showToast('Failed to unpublish: ' + err.message, 'danger');
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
    if (pages.length > 20) {
        list.className = 'pages-list wb-filter';
    }

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

        // Publish status icon
        var statusIcon = document.createElement('span');
        statusIcon.className = 'publish-status-icon';
        // Locked pages get red indicator regardless of publish status
        if (page.lock_status === 'locked') {
            statusIcon.textContent = page.status === 'published' ? '●' : '○';
            statusIcon.style.color = '#c62828';
            statusIcon.title = page.status === 'published' ? 'Published (Locked)' : 'Draft (Locked)';
        } else if (page.status === 'published') {
            statusIcon.textContent = '●';
            statusIcon.style.color = '#28a745';
            statusIcon.title = 'Published';
        } else {
            statusIcon.textContent = '○';
            statusIcon.style.color = '#aaa';
            statusIcon.title = 'Draft';
        }
        link.appendChild(statusIcon);

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
        list.appendChild(li);
    });

    // Empty state
    if (pages.length === 0) {
        var emptyLi = document.createElement('li');
        emptyLi.className = 'page-item empty';
        emptyLi.textContent = 'No child pages';
        list.appendChild(emptyLi);

        // If we have a parent path, add a "Go to parent" link
        if (parentPath) {
            var parentBtn = document.createElement('li');
            parentBtn.className = 'page-item go-parent';
            var parentLink = document.createElement('a');
            parentLink.href = '#';
            parentLink.className = 'page-link';
            parentLink.innerHTML = '← Go to parent page';
            parentLink.addEventListener('click', function(e) {
                e.preventDefault();
                var goIdx = columnIndex;
                if (goIdx < currentPath.length && goIdx >= 0) {
                    goToPath(goIdx);
                } else {
                    navigateHome();
                }
            });
            parentBtn.appendChild(parentLink);
            list.appendChild(parentBtn);
        }
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

    // Init WET-BOEW plugins on newly added elements
    if (typeof jQuery !== 'undefined') {
        jQuery('.wb-filter').trigger('wb-init.wb-filter');
    }
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
            columnsCache = [{
                title: pageTitle(page),
                pages: children,
                parentPath: page.path
            }];
        } else {
            // Levels 3+: multi-column
            // Column N holds path entry N+1 (col 0 = entry 1, col 1 = entry 2, etc.)
            var keepCount = columnIndex + 2;
            currentPath = currentPath.slice(0, keepCount);
            currentPath.push(page);

            columnsCache = columnsCache.slice(0, columnIndex + 1);
            if (columnsCache.length < MAX_COLUMNS) {
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
    lastActivePath = '/';
    initNavigation('/');
}

// ============================================================================
// 8. BREADCRUMB
// ============================================================================
function updateBreadcrumb() {
    var container = breadcrumbNav;  /* #wb-bc .breadcrumb (WET theme) */
    // Keep the home <li> from HTML template
    var homeLi = container.querySelector('#breadcrumb-home').parentElement;
    container.innerHTML = '';
    container.appendChild(homeLi);

    // Path items
    currentPath.forEach(function(page, idx) {
        var li = document.createElement('li');

        if (idx < currentPath.length - 1) {
            var link = document.createElement('a');
            link.href = '#';
            link.textContent = pageTitle(page);
            link.addEventListener('click', function(e) {
                e.preventDefault();
                goToPath(idx);
            });
            li.appendChild(link);
        } else {
            li.textContent = pageTitle(page);
        }

        container.appendChild(li);
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
        columnsCache = [{
            title: pageTitle(lastPage),
            pages: children,
            parentPath: lastPage.path
        }];
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
    var isPublished = hasSelection && selectedPageData && selectedPageData.status === 'published';
    var canMove = hasSelection && !isPublished;

    btnEdit.disabled = !hasSelection;
    btnPreview.disabled = !hasSelection;
    btnMove.disabled = !hasSelection || isPublished;
    btnPublish.disabled = !hasSelection;
    btnUnpublish.disabled = !isPublished;
    btnDelete.disabled = !hasSelection;
    btnProperties.disabled = !hasSelection;

    btnEdit.className = hasSelection ? 'btn btn-edit' : 'btn btn-edit disabled';
    btnPreview.className = hasSelection ? 'btn btn-info' : 'btn btn-info disabled';
    btnMove.className = canMove ? 'btn btn-move' : 'btn btn-move disabled';
    btnPublish.className = hasSelection ? 'btn btn-publish' : 'btn btn-publish disabled';
    btnUnpublish.className = isPublished ? 'btn btn-warning' : 'btn btn-warning disabled';
    btnDelete.className = hasSelection ? 'btn btn-delete' : 'btn btn-delete disabled';
    btnProperties.className = hasSelection ? 'btn btn-primary' : 'btn btn-primary disabled';

    // Tooltip messages for disabled state (#8)
    btnEdit.title = hasSelection ? 'Edit selected page' : 'Select a page to edit';
    btnPreview.title = hasSelection ? 'Preview page content' : 'Select a page to preview';
    btnMove.title = canMove ? 'Move selected page' : (isPublished ? 'Cannot move a published page' : 'Select a page to move');
    btnPublish.title = hasSelection ? 'Publish selected page' : 'Select a page to publish';
    btnUnpublish.title = isPublished ? 'Unpublish selected page' : (hasSelection ? 'Page is not published' : 'Select a published page to unpublish');
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
    var backdrop = document.querySelector('[data-modal-backdrop="' + el.id + '"]');
    if (backdrop) backdrop.remove();
    // Only remove modal-open if no other modal backdrops remain
    if (!document.querySelector('[data-modal-backdrop]')) {
        document.body.classList.remove('modal-open');
    }
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
    // Move modal elements
    // ============================================================================
    var moveModal = document.getElementById('moveModal');
    var movePageForm = document.getElementById('movePageForm');
    var movePageTitleInput = document.getElementById('movePageTitleInput');
    var movePageNameInput = document.getElementById('movePageNameInput');
    var movePageLang = document.getElementById('movePageLang');
    var movePageCurrentPath = document.getElementById('movePageCurrentPath');
    var moveNewParent = document.getElementById('moveNewParent');
    var movePathPreview = document.getElementById('movePathPreview');
    var movePageError = document.getElementById('movePageError');
    var movePageSuccess = document.getElementById('movePageSuccess');
    var movePageSaveBtn = document.getElementById('movePageSaveBtn');

    // Close button bindings for move modal
    if (moveModal) {
        moveModal.querySelectorAll('[data-dismiss="modal"]').forEach(function(btn) {
            btn.addEventListener('click', function() { hideModal(moveModal); });
        });
    }

    // ============================================================================
    // CREATE button (fix #1 - root node check, fix #9 - state retention)
    // ============================================================================
    btnCreate.addEventListener('click', function() {
        // If no page is selected, confirm before creating at root
        if (!selectedPageId && (!columnsCache.length || !columnsCache[columnsCache.length - 1].parentPath)) {
            showConfirmDialog(
                'No parent page selected. Create new page under <strong>Root</strong>?',
                'Yes, create at Root',
                'Cancel'
            ).then(function(confirmed) {
                if (confirmed) {
                    showCreatePageModal('/');
                }
            });
            return;
        }
        var parentPath = selectedPageData ? selectedPageData.path : (columnsCache.length > 0 ? columnsCache[columnsCache.length - 1].parentPath : ROOT_PATH);
        showCreatePageModal(parentPath);
    });

    // ============================================================================
    // EDIT button
    // ============================================================================
    btnEdit.addEventListener('click', function() {
        if (selectedPageData) {
            window.open('/static/editor.html?pageId=' + encodePath(selectedPageData.path), 'editor');
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
            showMoveModal(selectedPageData);
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
    // UNPUBLISH button
    // ============================================================================
    btnUnpublish.addEventListener('click', function() {
        if (selectedPageData) {
            performUnpublish(selectedPageData);
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

                // Auto-image checkbox: setup first (clone), then sync state
                setTimeout(function() {
                    setupAutoImageCheckbox(thePath);
                    syncAutoImageCheckbox(data, thePath);
                }, 0);

                // Version info
                loadVersionInfo(thePath);
                loadScheduleInfo(thePath);
                loadApprovalInfo(thePath);
                loadLockStatus(thePath);

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

                // Template dropdown
                var templateSel = document.getElementById('prop-template');
                if (templateSel) {
                    templateSel.value = data.publish_template || '';
                }

                // Render tag checkboxes — pass paths
                var tagPaths = (data.tags || []).map(function(t) {
                    return typeof t === 'string' ? t : (t.path || (TAG_ROOT + '/' + t.id));
                });
                renderTagCheckboxes(tagPaths);

                showModal(modal);
            })
            .catch(function(err) {
                console.error('Properties load error:', err);
                showToast('Failed to load properties: ' + err.message, 'danger');
            });
    }

    // Populate template dropdown
    function populateTemplateSelect() {
        populateOneTemplateSelect('prop-template');
        populateOneTemplateSelect('newPageTemplate');
    }

    function populateOneTemplateSelect(selectId) {
        var sel = document.getElementById(selectId);
        if (!sel) return;
        sel.disabled = true;

        // Fetch templates from the server — children of the templates folder, recursively
        var templateBase = '/canadasite/mustache-templates/page-template';
        var seen = new Set();

        function cleanLabel(text) {
            return text ? text.replace(/^Mustache Template:\s*/i, '') : text;
        }

        function addTemplateItem(path, label) {
            if (seen.has(path)) return;
            seen.add(path);
            var opt = document.createElement('option');
            opt.value = path;
            opt.textContent = cleanLabel(label);
            sel.appendChild(opt);
        }

        fetch('/api/v1/pages/by-path/' + encodeURI((templateBase.startsWith('/') ? templateBase.slice(1) : templateBase)) + '/children')
            .then(function(r) { if (r.ok) return r.json(); throw new Error('status ' + r.status); })
            .then(function(children) {
                sel.disabled = false;
                // Clear and rebuild
                sel.innerHTML = '';
                sel.appendChild(new Option('(Default page template)', '', false, true));
                // Add the base template itself
                addTemplateItem(templateBase, 'page-template');
                // Add children
                children.forEach(function(c) {
                    var label = c.title || c.path.split('/').pop() || c.id;
                    addTemplateItem(c.path, label);
                    // Fetch grandchildren too (e.g. HTML-template, Left-navigation-template)
                    fetch('/api/v1/pages/by-path/' + encodeURI((c.path.startsWith('/') ? c.path.slice(1) : c.path)) + '/children')
                        .then(function(r2) { if (r2.ok) return r2.json(); return []; })
                        .then(function(grandchildren) {
                            grandchildren.forEach(function(gc) {
                                var gLabel = (label + ' / ' + (gc.title || gc.path.split('/').pop() || gc.id));
                                addTemplateItem(gc.path, gLabel);
                            });
                        })
                        .catch(function() {});
                });
            })
            .catch(function(err) {
                sel.disabled = false;
                sel.innerHTML = '';
                sel.appendChild(new Option('(Default page template)', '', false, true));
                console.warn('Failed to load template list:', err);
            });
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

            var autoImageChk = document.getElementById('prop-auto-image');
            var payload = {
                title: getPropVal('prop-title') || undefined,
                status: document.getElementById('prop-status') ? document.getElementById('prop-status').value : undefined,
                file_path: filePath || undefined,
                metadata: { auto_image_path: !!(autoImageChk && autoImageChk.checked) },
                other_language_path: otherLang.trim(),
                hide_in_navigation: document.getElementById('prop-hide-nav') ? document.getElementById('prop-hide-nav').checked : undefined,
                publish_template: document.getElementById('prop-template') ? document.getElementById('prop-template').value || undefined : undefined
            };

            // Remove undefined values
            Object.keys(payload).forEach(function(k) {
                if (payload[k] === undefined) delete payload[k];
            });

            // Collect selected tag paths from hidden inputs and content type
            var selectedTags = [];
            [
                document.getElementById('selected-subject-tags'),
                document.getElementById('selected-audience-tags')
            ].forEach(function(h) {
                if (h && h.value) {
                    h.value.split(',').filter(function(p) { return p; }).forEach(function(p) {
                        if (selectedTags.indexOf(p) === -1) selectedTags.push(p);
                    });
                }
            });
            var ct = document.getElementById('prop-content-type');
            if (ct && ct.value) {
                if (selectedTags.indexOf(ct.value) === -1) selectedTags.push(ct.value);
            }

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
                // Also save tags via tags API
                return fetch('/api/v1/tags/page/' + encodeURIComponent(pagePath), {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({tag_paths: selectedTags})
                });
            })
            .then(function(r) {
                if (!r.ok) return r.json().then(function(e) { throw new Error('Tags save failed: ' + (e.detail || e.message)); });
                return r.json();
            })
            .then(function() {
                showToast('✅ Properties and tags saved!', 'success');
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

    // Bind close for tag tree modal
    var ttm = document.getElementById('tagTreeModal');
    if (ttm) {
        ttm.querySelectorAll('[data-dismiss="modal"]').forEach(function(btn) {
            btn.addEventListener('click', function() { hideModal(ttm); });
        });
    }

    // ============================================================================
    // MOVE PAGE MODAL
    // ============================================================================

    var moveModalPageData = null;

    function showMoveModal(pageData) {
        moveModalPageData = pageData;
        movePageTitleInput.value = pageData.title || '';
        var currentSlug = pageData.path ? pageData.path.split('/').filter(Boolean).pop() || '' : '';
        movePageNameInput.value = currentSlug;
        movePageLang.textContent = (pageData.language || 'en').toUpperCase();
        movePageCurrentPath.textContent = pageData.path;
        moveNewParent.value = '';
        movePathPreview.textContent = '(enter parent path to preview)';
        movePathPreview.style.color = '#888';
        movePageError.style.display = 'none';
        movePageSuccess.style.display = 'none';
        movePageSaveBtn.disabled = true;
        movePageSaveBtn.textContent = 'Move Page';
        updateMovePreview();
        showModal(moveModal);
        setTimeout(function() { moveNewParent.focus(); }, 300);
    }

    function updateMovePreview() {
        var parentPath = moveNewParent.value.trim();
        var slug = movePageNameInput.value.trim();
        if (parentPath && slug) {
            var newPath = parentPath.replace(/\/+$/, '') + '/' + slug;
            movePathPreview.textContent = newPath;
            movePathPreview.style.color = '#333';
            movePageSaveBtn.disabled = false;
        } else {
            movePathPreview.textContent = '(enter parent path to preview)';
            movePathPreview.style.color = '#888';
            movePageSaveBtn.disabled = true;
        }
    }

    // Live preview as user types parent path, name, or title
    if (moveNewParent) {
        moveNewParent.addEventListener('input', updateMovePreview);
    }
    if (movePageNameInput) {
        movePageNameInput.addEventListener('input', updateMovePreview);
    }

    // Move form submit
    if (movePageForm) {
        movePageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!moveModalPageData) return;
            performMove(moveModalPageData, moveNewParent.value.trim());
        });
    }

    function performMove(pageData, newParentPath) {
        movePageSaveBtn.disabled = true;
        movePageSaveBtn.textContent = 'Moving...';
        movePageError.style.display = 'none';
        movePageSuccess.style.display = 'none';

        var url = '/api/v1/pages/move';
        url += '?path=' + encodeURIComponent(pageData.path);
        url += '&new_parent_path=' + encodeURIComponent(newParentPath);
        url += '&new_name=' + encodeURIComponent(movePageNameInput.value.trim());
        url += '&new_title=' + encodeURIComponent(movePageTitleInput.value.trim());

        fetch(url, {
            method: 'POST',
            headers: { 'Accept': 'application/json' }
        })
        .then(function(resp) {
            if (!resp.ok) {
                return resp.json().then(function(err) {
                    throw new Error(err.detail || 'HTTP ' + resp.status);
                });
            }
            return resp.json();
        })
        .then(function(data) {
            movePageSuccess.textContent = '✅ Page moved successfully!';
            movePageSuccess.style.display = 'block';
            movePageSaveBtn.textContent = 'Move Page';
            movePageSaveBtn.disabled = true;
            showToast('Page moved: ' + data.old_path + ' → ' + data.new_path, 'success');
            // Refresh the navigation tree after a short delay
            setTimeout(function() {
                hideModal(moveModal);
                loadedPaths = {};
                columnsCache = [];
                currentPath = [];
                selectedPageId = null;
                selectedPageData = null;
                initNavigation();
            }, 1200);
        })
        .catch(function(err) {
            movePageError.textContent = '❌ ' + err.message;
            movePageError.style.display = 'block';
            movePageSaveBtn.disabled = false;
            movePageSaveBtn.textContent = 'Retry';
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

        // Get selected page template
        var selectedTemplate = document.getElementById('newPageTemplate');
        var pageTemplateValue = selectedTemplate ? selectedTemplate.value : '';

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
            // Helper function: create a page, or skip if already exists
            async function createOrSkip(lang, bodyData) {
                bodyData.skip_if_exists = true;
                var resp = await fetch('/api/v1/pages/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(bodyData)
                });
                if (resp.ok) {
                    var data = await resp.json();
                    return { created: true, path: data.path || bodyData.path, data: data };
                }
                var errData = null;
                try { errData = await resp.json(); } catch(e) {}
                var errMsg = (errData && errData.detail) || '';
                if (errMsg.indexOf('already exists') !== -1) {
                    return { created: false, skipped: true, path: bodyData.path };
                }
                throw new Error('Failed to create ' + lang + ' page: ' + errMsg);
            }

            var enResult = { created: false, path: pagePath };
            var frResult = { created: false, path: '' };

            // Build English page data
            var enPageData = {
                title: title,
                path: pagePath,
                parent_path: parentPath,
                language: 'en',
                status: 'draft',
                content: '',
                metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
                other_language_path: otherLanguagePath || undefined
            };
            if (pageTemplateValue) {
                enPageData.template = pageTemplateValue;
            }

            // 1. Create English page (or skip if exists)
            enResult = await createOrSkip('en', enPageData);

            var actualPagePath = enResult.path;

            // 2. Create French page too if FR fields present
            if (frTitle && frName && otherLangParent) {
                var frParentClean = otherLangParent.replace(/\/+$/, '');
                var frPagePath = frParentClean + '/' + frName;

                frResult = await createOrSkip('fr', {
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
                });
            }

            // 3. Show result message
            var msgs = [];
            if (enResult.created) msgs.push('✅ Created: "' + title + '" (EN)');
            else if (enResult.skipped) msgs.push('⚠️ Skipped (already exists): "' + title + '" (EN)');
            if (frResult.created) msgs.push('✅ Created: "' + frTitle + '" (FR)');
            else if (frResult.skipped) msgs.push('⚠️ Skipped (already exists): "' + frTitle + '" (FR)');
            if (frTitle && !frResult.created && !frResult.skipped) msgs.push('(French page was not created — check FR fields.)');
            showToast(msgs.join(' | '), 'success');

            // Refresh navigation
            loadedPaths = {};
            columnsCache = [];

            // Open English page editor in new tab (if EN was created)
            if (enResult.created || enResult.path) {
                var editorUrl = '/static/editor.html?pageId=' + encodeURIComponent(actualPagePath);
                window.open(editorUrl, 'editor');
            }

            // Close the Create dialog
            hideModal(createPageModal);

            // Refresh the navigation tree to show the new page
            refreshTree();

        } catch (err) {
            showToast('Failed to create page: ' + err.message, 'danger');
            createPageSaveBtn.disabled = false;
            createPageSaveBtn.textContent = 'Create & Edit';
        }
    });

    populateTemplateSelect();

    // Preload tags for Properties modal (disabled - now uses per-level loading)
    // loadAllTags();
}

// ============================================================================
// TAG MANAGEMENT
// ============================================================================

// Cache for all tags
var allTags = null;

// Load all tags from API
function loadAllTags() {
    fetch('/api/v1/tags?flat=true')
        .then(function(r) { return r.ok ? r.json() : []; })
        .then(function(data) {
            allTags = data;
        })
        .catch(function() {
            allTags = [];
        });
}

// Render tag checkboxes for the Properties modal
function renderTagCheckboxes(selectedTagPaths) {
    // Called when loading properties. Populates the display areas and hidden inputs.
    var selected = selectedTagPaths || [];

    // Group selected paths by type
    var subjectPaths = [];
    var audiencePaths = [];
    var contentTypePath = '';

    selected.forEach(function(p) {
        if (p.indexOf('/audience/') !== -1) audiencePaths.push(p);
        else if (p.indexOf('/content-types/') !== -1) contentTypePath = p;
        else subjectPaths.push(p); // includes /subjects/, /themes-and-topics/, /subject/
    });

    updateTagDisplay('prop-tags-subjects', 'selected-subject-tags', subjectPaths);
    updateTagDisplay('prop-tags-audience', 'selected-audience-tags', audiencePaths);

    // Load content types into the select
    populateContentTypeSelect(contentTypePath);
}

function updateTagDisplay(containerId, hiddenId, paths) {
    var container = document.getElementById(containerId);
    var hidden = document.getElementById(hiddenId);
    if (!container) return;
    if (hidden) hidden.value = paths.join(',');

    if (!paths || paths.length === 0) {
        container.innerHTML = '<span class="text-muted">(none selected)</span>';
        return;
    }

    var html = '';
    paths.forEach(function(p) {
        html += '<span class="tag-selection-item">' + esc(p) +
            ' <a href="#" class="remove-tag" onclick="removeSelectedTag(\'' + containerId + '\', \'' + hiddenId + '\', \'' + esc(p.replace(/'/g, "\\'")) + '\');return false;">&times;</a></span>';
    });
    container.innerHTML = html;
}

function removeSelectedTag(containerId, hiddenId, path) {
    var hidden = document.getElementById(hiddenId);
    if (!hidden) return;
    var paths = hidden.value ? hidden.value.split(',') : [];
    var idx = paths.indexOf(path);
    if (idx !== -1) paths.splice(idx, 1);
    updateTagDisplay(containerId, hiddenId, paths);
}

function populateContentTypeSelect(selectedPath) {
    var sel = document.getElementById('prop-content-type');
    if (!sel) return;

    // Clear existing options (keep the first empty one)
    sel.innerHTML = '<option value="">(none)</option>';

    fetch('/api/v1/tags?parent_path=' + encodeURIComponent(TAG_ROOT + '/content-types'))
        .then(function(r) { return r.ok ? r.json() : []; })
        .then(function(tags) {
            tags.forEach(function(t) {
                var tagPath = t.path || (TAG_ROOT + '/' + t.id);
                var opt = document.createElement('option');
                opt.value = tagPath;
                opt.textContent = (t.title_en || t.id) + ' / ' + (t.title_fr || '');
                if (tagPath === selectedPath) opt.selected = true;
                sel.appendChild(opt);
            });
        })
        .catch(function() {});
}

// ============================================================================
// TAG TREE MODAL (Lightbox)
// ============================================================================

var ttmType = '';      // 'subject' | 'audience'
var ttmMulti = true;   // multi- or single-select
var ttmPaths = [];     // currently selected paths
var ttmRootPath = '';  // TAG_ROOT + '/' + type
var ttmStack = [];     // breadcrumb stack: [{title, path}]
var ttmTags = [];      // current level's tags
var ttmCallback = null;// callback(selectedPaths)

function openTagTree(type, multi) {
    ttmType = type;
    ttmMulti = multi;
    ttmStack = [];
    ttmTags = [];

    // Load existing selections from hidden input
    var hiddenId = type === 'subject' ? 'selected-subject-tags' : 'selected-' + type + '-tags';
    var hidden = document.getElementById(hiddenId);
    ttmPaths = hidden && hidden.value ? hidden.value.split(',').filter(function(p) { return p; }) : [];

    var list = document.getElementById('ttm-tag-list');
    list.innerHTML = '<span class="text-muted">Loading...</span>';

    // Reset modal
    document.getElementById('ttm-filter').value = '';
    document.getElementById('ttm-selected-count').textContent = ttmPaths.length;
    document.getElementById('ttm-up-btn').style.display = 'none';
    document.getElementById('ttm-breadcrumb').textContent = '';

    var label = document.getElementById('tagTreeModalLabel');
    if (label) label.textContent = 'Select ' + type.charAt(0).toUpperCase() + type.slice(1) + ' Tags';

    // Set callback to update display on confirm
    ttmCallback = function(selectedPaths) {
        if (type === 'subject') {
            updateTagDisplay('prop-tags-subjects', 'selected-subject-tags', selectedPaths);
        } else {
            updateTagDisplay('prop-tags-audience', 'selected-audience-tags', selectedPaths);
        }
    };

    // Load root-level tags and filter by type. This shows namespace nodes
    // like 'subjects' and 'themes-and-topics' for type=subject.
    fetch('/api/v1/tags?parent_path=' + encodeURIComponent(TAG_ROOT))
        .then(function(r) { return r.ok ? r.json() : []; })
        .then(function(roots) {
            // Filter by type (subject or audience)
            ttmTags = roots.filter(function(t) { return t.type === type; });
            if (ttmTags.length === 0) {
                list.innerHTML = '<span class="text-muted">No ' + type + ' namespaces found.</span>';
                return;
            }

            var html = '';
            ttmTags.forEach(function(t) {
                var tagPath = t.path || (TAG_ROOT + '/' + t.id);
                var childCount = t.children_count || 0;
                var title = esc(t.title_en || t.id);
                var titleFr = t.title_fr ? ' / ' + esc(t.title_fr) : '';

                html += '<div class="ttm-item">' +
                    '<div class="ttm-label" style="font-weight:600;">' + title + '<span style="color:#888;font-size:11px;">' + titleFr + '</span></div>' +
                    '<span class="ttm-has-children" onclick="ttmDrill(\'' + esc(tagPath) + '\',\'' + esc(t.title_en || t.id) + '\');event.stopPropagation();">📂 ' + childCount + ' children</span>' +
                    '</div>';
            });
            list.innerHTML = html;
            showModal(document.getElementById('tagTreeModal'));
        })
        .catch(function() {
            list.innerHTML = '<span class="text-muted">Failed to load tags.</span>';
        });
}

function ttmLoadLevel(parentPath) {
    var list = document.getElementById('ttm-tag-list');
    list.innerHTML = '<span class="text-muted">Loading...</span>';

    // Update breadcrumb
    var bc = document.getElementById('ttm-breadcrumb');
    bc.innerHTML = ttmStack.map(function(s) {
        return '<span style="color:#888;">' + esc(s.title) + '</span>';
    }).join(' <span style="color:#ccc;">›</span> ');

    document.getElementById('ttm-up-btn').style.display = ttmStack.length > 1 ? 'inline-block' : 'none';

    fetch('/api/v1/tags?parent_path=' + encodeURIComponent(parentPath))
        .then(function(r) { return r.ok ? r.json() : []; })
        .then(function(tags) {
            ttmTags = tags;
            ttmRender();
        })
        .catch(function() {
            list.innerHTML = '<span class="text-muted">Failed to load tags.</span>';
        });
}

function ttmRender() {
    var list = document.getElementById('ttm-tag-list');
    var filter = (document.getElementById('ttm-filter').value || '').toLowerCase();

    var filtered = ttmTags;
    if (filter) {
        filtered = ttmTags.filter(function(t) {
            return (t.title_en || '').toLowerCase().indexOf(filter) !== -1 ||
                   (t.title_fr || '').toLowerCase().indexOf(filter) !== -1 ||
                   (t.path || '').toLowerCase().indexOf(filter) !== -1 ||
                   (t.id || '').toLowerCase().indexOf(filter) !== -1;
        });
    }

    if (filtered.length === 0) {
        list.innerHTML = '<span class="text-muted">No tags found' + (filter ? ' matching \'' + esc(filter) + '\'' : '') + '.</span>';
        return;
    }

    var html = '';
    filtered.forEach(function(t) {
        var tagPath = t.path || (TAG_ROOT + '/' + t.id);
        var title = esc(t.title_en || t.id);
        var titleFr = t.title_fr ? ' <span style="color:#888;font-size:11px;">/ ' + esc(t.title_fr) + '</span>' : '';
        var childCount = t.children_count || 0;
        var isSelected = ttmPaths.indexOf(tagPath) !== -1;

        if (ttmMulti) {
            html += '<div class="ttm-item' + (isSelected ? ' selected' : '') + '">' +
                '<input type="checkbox" class="ttm-check" value="' + esc(tagPath) + '" ' + (isSelected ? 'checked' : '') + ' onchange="ttmToggle(this.value)">' +
                '<div class="ttm-label" onclick="ttmToggleCheck(this)">' +
                    '<span class="ttm-title">' + title + titleFr + '</span>' +
                    '<span class="ttm-path">' + esc(tagPath) + '</span>' +
                '</div>' +
                (childCount > 0 ? '<span class="ttm-has-children" onclick="ttmDrill(\'' + esc(tagPath) + '\',\'' + esc(t.title_en || t.id) + '\');event.stopPropagation();">▶ ' + childCount + '</span>' : '') +
                '</div>';
        } else {
            html += '<div class="ttm-item' + (isSelected ? ' selected' : '') + '" onclick="ttmSelectSingle(\'' + esc(tagPath) + '\')">' +
                '<div class="ttm-label">' +
                    '<span class="ttm-title">' + title + titleFr + '</span>' +
                    '<span class="ttm-path">' + esc(tagPath) + '</span>' +
                '</div>' +
                (childCount > 0 ? '<span class="ttm-has-children" onclick="ttmDrill(\'' + esc(tagPath) + '\',\'' + esc(t.title_en || t.id) + '\');event.stopPropagation();">▶ ' + childCount + '</span>' : '') +
                '</div>';
        }
    });
    list.innerHTML = html;

    var count = document.getElementById('ttm-selected-count');
    if (count) count.textContent = ttmPaths.length;
}

function ttmToggle(path) {
    var idx = ttmPaths.indexOf(path);
    if (idx === -1) {
        ttmPaths.push(path);
    } else {
        ttmPaths.splice(idx, 1);
    }
    ttmRender();
}

function ttmToggleCheck(el) {
    var checkbox = el.parentNode.querySelector('.ttm-check');
    if (checkbox) {
        checkbox.checked = !checkbox.checked;
        ttmToggle(checkbox.value);
    }
}

function ttmSelectSingle(path) {
    ttmPaths = [path];
    ttmRender();
    // Auto-confirm for single select
    setTimeout(ttmConfirm, 300);
}

function ttmDrill(path, title) {
    ttmStack.push({title: title, path: path});
    ttmLoadLevel(path);
}

function ttmGoUp() {
    if (ttmStack.length <= 1) return;
    ttmStack.pop();
    var prevPath = ttmStack[ttmStack.length - 1].path;
    ttmLoadLevel(prevPath);
}

function ttmFilter() {
    ttmRender();
}

function ttmConfirm() {
    if (ttmCallback) {
        ttmCallback(ttmPaths.slice());
    }
    hideModal(document.getElementById('tagTreeModal'));
}

// ============================================================================
// TAG MANAGEMENT MODAL
// ============================================================================

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
            if (columnsCache.length < MAX_COLUMNS) {
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
async function initNavigation(initialPath) {
    showLoading();
    try {
        var pathToUse = initialPath || ROOT_PATH;
        var columnTitle = initialPath ? (initialPath === '/' ? 'Root' : initialPath.split('/').filter(Boolean).pop() || 'Root') : 'Canada.ca';
        var children = await fetchChildren(pathToUse);
        columnsCache = [{
            title: columnTitle,
            pages: children,
            parentPath: pathToUse
        }];
        selectedPageId = null;
        selectedPageData = null;
        // Breadcrumb: Home link already represents '/'.
        // Only add a crumb for sub-paths (e.g. /canadasite).
        currentPath = (pathToUse === '/') ? [] : [{
            path: pathToUse,
            title: columnTitle,
            id: pathToUse
        }];

        renderColumns();
        hideLoading();

        updateStats();
        console.log('Navigation initialized: ' + children.length + ' pages at ' + pathToUse);
    } catch (err) {
        console.error('Navigation init failed:', err);
        showError('Failed to load navigation: ' + err.message + '. Please try refreshing.');
    }
}

// ============================================================================
// 12. BOOT
// ============================================================================
function getUrlParam(name) {
    var params = new URLSearchParams(window.location.search);
    return params.get(name);
}

// ============================================================================
// Hash-based navigation: #/path → navigate to that path
// ============================================================================
function getHashPath() {
    var hash = window.location.hash;
    if (hash && hash.startsWith('#/')) return decodeURIComponent(hash.substring(1)); // '/canadasite/en'
    return null;
}

function navigateToHashPath(hashPath) {
    if (!hashPath || hashPath === '/') {
        navigateHome();
        return;
    }
    var parts = hashPath.split('/').filter(Boolean);
    if (parts.length === 0) {
        navigateHome();
        return;
    }
    // Navigate to the last segment as initial path
    // For deeper paths like /canadasite/en/contact, we go to /canadasite first
    // then the user can drill down naturally
    var initialPath = '/' + parts[0];
    if (parts.length > 1) {
        // Store the rest for lazy navigation after first column loads
        lastActivePath = hashPath;
    }
    initNavigation(initialPath);
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM ready - initializing navigation');
    initDom();
    initToast();
    setupButtons();

    // Priority: ?path= URL param > # hash > default
    var pathParam = getUrlParam('path');
    var hashPath = getHashPath();
    if (pathParam) {
        console.log('URL path param:', pathParam);
        initNavigation(pathParam);
    } else if (hashPath) {
        console.log('URL hash path:', hashPath);
        navigateToHashPath(hashPath);
    } else {
        initNavigation();
    }

    // Handle hash changes (user clicks breadcrumb or navigates)
    window.addEventListener('hashchange', function() {
        var newHash = getHashPath();
        if (newHash && newHash !== lastActivePath) {
            console.log('Hash changed:', newHash);
            navigateToHashPath(newHash);
        }
    });
});

// Version info loading for properties modal
var currentPagePathForVersion = null;

function loadVersionInfo(pagePath) {
    currentPagePathForVersion = pagePath;
    var verEl = document.getElementById('prop-current-version');
    var btnEl = document.getElementById('btn-view-version-history');
    var editorLink = document.getElementById('btn-open-editor');
    var rawBtn = document.getElementById('btn-raw-html');
    var compareBtn = document.getElementById('btn-compare');
    if (!verEl) return;

    // Set editor link href
    if (editorLink) {
        editorLink.href = '/static/editor.html?pageId=' + encodeURIComponent(pagePath);
        editorLink.disabled = false;
        editorLink.style.opacity = '1';
        editorLink.style.pointerEvents = 'auto';
    }

    // Show loading
    verEl.textContent = 'loading...';

    fetch('/api/v1/versions/page?path=' + encodeURIComponent(pagePath))
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
            if (data && data.version_count > 0) {
                var latest = data.versions[0];
                verEl.textContent = 'v' + latest.version + ' (' + latest.created_at.slice(0, 10) + ', ' + formatFileSize(latest.html_size) + ')';
                if (btnEl) btnEl.disabled = false;
                if (rawBtn) { rawBtn.disabled = false; rawBtn.style.opacity = '1'; rawBtn.style.pointerEvents = 'auto'; }
                if (compareBtn) { compareBtn.disabled = false; compareBtn.style.opacity = '1'; compareBtn.style.pointerEvents = 'auto'; }
            } else {
                verEl.textContent = 'No versions yet (publish first)';
                if (btnEl) btnEl.disabled = true;
                if (rawBtn) { rawBtn.disabled = true; rawBtn.style.opacity = '0.5'; rawBtn.style.pointerEvents = 'none'; }
                if (compareBtn) { compareBtn.disabled = true; compareBtn.style.opacity = '0.5'; compareBtn.style.pointerEvents = 'none'; }
            }
        })
        .catch(function() {
            verEl.textContent = '(unavailable)';
            if (btnEl) btnEl.disabled = true;
            if (rawBtn) { rawBtn.disabled = true; rawBtn.style.opacity = '0.5'; rawBtn.style.pointerEvents = 'none'; }
            if (compareBtn) { compareBtn.disabled = true; compareBtn.style.opacity = '0.5'; compareBtn.style.pointerEvents = 'none'; }
        });
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// Version history button handler (called from onclick in HTML)
function viewVersionHistory() {
    if (!currentPagePathForVersion) return;
    window.open('/static/version-manager.html?path=' + encodeURIComponent(currentPagePathForVersion), '_blank');
}

// Raw HTML viewer - opens latest version content in new tab
function viewRawHTML() {
    if (!currentPagePathForVersion) return;
    var path = currentPagePathForVersion;
    fetch('/api/v1/versions/page?path=' + encodeURIComponent(path))
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
            if (!data || !data.versions || data.versions.length === 0) {
                showWetAlert('No versions available');
                return;
            }
            var latest = data.versions[0];
            fetch('/api/v1/versions/page/version?path=' + encodeURIComponent(path) + '&version=' + latest.version)
                .then(function(r) { return r.json(); })
                .then(function(v) {
                    if (v.content) {
                        var win = window.open('', '_blank');
                        win.document.write('<!DOCTYPE html><html><head><title>Raw HTML v' + latest.version + '</title>');
                        win.document.write('<style>body{font-family:monospace;padding:20px;white-space:pre-wrap;word-break:break-word;background:#fff;color:#333;max-width:1200px;margin:0 auto;}</style>');
                        win.document.write('</head><body>');
                        win.document.write('<div style="background:#f0f4f8;padding:12px;border-radius:8px;margin-bottom:20px;font-family:sans-serif;font-size:14px;">');
                        win.document.write('<strong>📄 ' + escHtml(path) + '</strong> · v' + latest.version + ' · ' + (latest.created_at ? latest.created_at.slice(0,10) : '') );
                        win.document.write('<br><span style="color:#888;">Raw HTML content (' + formatFileSize((v.content || '').length) + ')</span>');
                        win.document.write('</div>');
                        win.document.write('<div style="border:1px solid #e0e0e0;border-radius:4px;padding:20px;">');
                        win.document.write(escHtml(v.content));
                        win.document.write('</div>');
                        win.document.write('</body></html>');
                        win.document.close();
                    }
                })
                .catch(function(e) { showWetAlert('Error: ' + e.message); });
        })
        .catch(function(e) { showWetAlert('Error: ' + e.message); });
}

// Open version manager compare mode
function openCompare() {
    if (!currentPagePathForVersion) return;
    window.open('/static/version-manager.html?path=' + encodeURIComponent(currentPagePathForVersion), '_blank');
}

function escHtml(s) {
    if (!s) return '';
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* ⏰ Scheduled Publish */
function loadScheduleInfo(pagePath) {
    if (!pagePath) return;
    fetch('/api/v1/pages/scheduled')
        .then(r => r.json())
        .then(list => {
            const match = list.find(p => p.path === pagePath);
            const statusEl = document.getElementById('prop-schedule-status');
            if (match && match.scheduled_publish) {
                const dt = match.scheduled_publish;
                // Convert ISO to local datetime-local format
                try {
                    const d = new Date(dt);
                    if (!isNaN(d.getTime())) {
                        const localStr = d.getFullYear() + '-' +
                            String(d.getMonth()+1).padStart(2,'0') + '-' +
                            String(d.getDate()).padStart(2,'0') + 'T' +
                            String(d.getHours()).padStart(2,'0') + ':' +
                            String(d.getMinutes()).padStart(2,'0');
                        document.getElementById('prop-schedule-dt').value = localStr;
                    }
                } catch(e) {}
                statusEl.textContent = '⏰ Scheduled: ' + dt;
            } else {
                document.getElementById('prop-schedule-dt').value = '';
                statusEl.textContent = '';
            }
        })
        .catch(() => {});
}

function setSchedule() {
    const path = currentPagePathForVersion;
    if (!path) return;
    const dtValue = document.getElementById('prop-schedule-dt').value;
    if (!dtValue) {
        showWetAlert('Please select a date and time');
        return;
    }
    // Convert local datetime to ISO format
    const localDate = new Date(dtValue);
    const isoStr = localDate.toISOString();
    
    fetch('/api/v1/pages/schedule?path=' + encodeURIComponent(path) +
          '&scheduled_publish=' + encodeURIComponent(isoStr), {
        method: 'PATCH'
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            document.getElementById('prop-schedule-status').textContent =
                '✅ Set for ' + isoStr;
        }
    })
    .catch(() => showWetAlert('Failed to set schedule'));
}

function cancelSchedule() {
    const path = currentPagePathForVersion;
    if (!path) return;
    fetch('/api/v1/pages/cancelschedule?path=' + encodeURIComponent(path), {
        method: 'PATCH'
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            document.getElementById('prop-schedule-dt').value = '';
            document.getElementById('prop-schedule-status').textContent = '❌ Cancelled';
        }
    })
    .catch(() => showWetAlert('Failed to cancel schedule'));
}

/* ✅ Approval */
function loadApprovalInfo(pagePath) {
    if (!pagePath) {
        document.getElementById('prop-approval-status').textContent = '—';
        document.getElementById('btn-approve').disabled = true;
        document.getElementById('btn-unapprove').disabled = true;
        return;
    }
    fetch('/api/v1/pages/approval-status?path=' + encodeURIComponent(pagePath))
        .then(r => r.json())
        .then(data => {
            const statusEl = document.getElementById('prop-approval-status');
            const btnApprove = document.getElementById('btn-approve');
            const btnUnapprove = document.getElementById('btn-unapprove');
            if (data.approved) {
                const by = data.approved_by ? ' by ' + data.approved_by : '';
                const at = data.approved_at ? ' at ' + data.approved_at : '';
                statusEl.textContent = '✅ Approved' + by + at;
                statusEl.style.color = '#2e7d32';
                btnApprove.disabled = true;
                btnUnapprove.disabled = false;
            } else {
                statusEl.textContent = '⏳ Not approved — publish blocked';
                statusEl.style.color = '#c62828';
                btnApprove.disabled = false;
                btnUnapprove.disabled = true;
            }
        })
        .catch(() => {
            document.getElementById('prop-approval-status').textContent = '⚠️ Could not load';
            document.getElementById('btn-approve').disabled = true;
            document.getElementById('btn-unapprove').disabled = true;
        });
}

function approvePage() {
    const path = currentPagePathForVersion;
    if (!path) return;
    if (!confirm('Approve this page for publish?')) return;
    fetch('/api/v1/pages/approve?path=' + encodeURIComponent(path) + '&approved_by=' + encodeURIComponent('current_user'), {
        method: 'POST'
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            loadApprovalInfo(path);
        }
    })
    .catch(() => showWetAlert('Failed to approve page'));
}

function unapprovePage() {
    const path = currentPagePathForVersion;
    if (!path) return;
    if (!confirm('Revoke approval for this page?')) return;
    fetch('/api/v1/pages/unapprove?path=' + encodeURIComponent(path), {
        method: 'POST'
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            loadApprovalInfo(path);
        }
    })
    .catch(() => showWetAlert('Failed to revoke approval'));
}

// ============================================================================
// Lock / Unlock page management
// ============================================================================
function loadLockStatus(pagePath) {
    var statusEl = document.getElementById('prop-lock-status');
    var btnLock = document.getElementById('btn-lock');
    var btnUnlock = document.getElementById('btn-unlock');
    
    if (!pagePath) {
        if (statusEl) statusEl.textContent = '—';
        if (btnLock) btnLock.disabled = true;
        if (btnUnlock) btnUnlock.disabled = true;
        return;
    }

    // Store for use by lock/unlock buttons
    currentPagePathForVersion = pagePath;

    fetch('/api/v1/pages/lock-status?path=' + encodeURIComponent(pagePath))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.locked) {
                var by = data.locked_by ? ' by ' + data.locked_by : '';
                var at = data.locked_at ? ' since ' + data.locked_at.slice(0, 16) : '';
                if (statusEl) {
                    statusEl.textContent = '🔒 Locked' + by + at;
                    statusEl.style.color = '#c62828';
                }
                if (btnLock) btnLock.disabled = true;
                if (btnUnlock) btnUnlock.disabled = false;
            } else {
                if (statusEl) {
                    statusEl.textContent = '🔓 Unlocked';
                    statusEl.style.color = '#2e7d32';
                }
                if (btnLock) btnLock.disabled = false;
                if (btnUnlock) btnUnlock.disabled = true;
            }
        })
        .catch(function() {
            if (statusEl) statusEl.textContent = '⚠️ Could not load';
            if (btnLock) btnLock.disabled = true;
            if (btnUnlock) btnUnlock.disabled = true;
        });
}

function lockPage() {
    var path = currentPagePathForVersion;
    if (!path) return;
    showConfirmDialog(
        'Lock this page to prevent editing and publishing?',
        'Lock', 'Cancel'
    ).then(function(confirmed) {
        if (!confirmed) return;
        var token = localStorage.getItem('access_token');
        var headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = 'Bearer ' + token;
        fetch('/api/v1/pages/lock?path=' + encodeURIComponent(path) + '&locked_by=admin', {
            method: 'POST',
            headers: headers
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                loadLockStatus(path);
                showWetAlert('Page locked successfully. Editing and publishing are now blocked.');
            }
        })
        .catch(function() { showWetAlert('Failed to lock page'); });
    });
}

function unlockPage() {
    var path = currentPagePathForVersion;
    if (!path) return;
    showConfirmDialog(
        'Unlock this page to allow editing and publishing?',
        'Unlock', 'Cancel'
    ).then(function(confirmed) {
        if (!confirmed) return;
        var token = localStorage.getItem('access_token');
        var headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = 'Bearer ' + token;
        fetch('/api/v1/pages/unlock?path=' + encodeURIComponent(path), {
            method: 'POST',
            headers: headers
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                loadLockStatus(path);
                showWetAlert('Page unlocked. Editing and publishing are now allowed.');
            }
        })
        .catch(function() { showWetAlert('Failed to unlock page'); });
    });
}

// ============================================================================
// Global compatibility: window.loadRootPages() for external callers
// ============================================================================
window.loadRootPages = async function loadRootPages() {
    console.log('loadRootPages called — navigating to root /');
    return initNavigation('/');
};

console.log('Navigation Module loaded.');
