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

function showConfirmDialog(message, yesText, noText) {
    return new Promise(function(resolve) {
        initConfirmDialog();

        document.getElementById('confirm-dialog-body').textContent = message;
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
    var confirmed = await showConfirmDialog(
        'Delete page "' + pageTitle + '"?\nPath: ' + pagePath + '\n\nThis action cannot be undone.\nAll child pages will also be deleted.',
        'Delete',
        'Cancel'
    );
    if (!confirmed) return;

    try {
        var resp = await fetch('/api/v1/pages/' + encodeURIComponent(pagePath), {
            method: 'DELETE'
        });
        if (!resp.ok) {
            var errData = null;
            try { errData = await resp.json(); } catch(e) {}
            throw new Error(errData && errData.detail ? errData.detail : 'HTTP ' + resp.status);
        }

        // Clear cache
        loadedPaths = {};
        columnsCache = [];

        showToast('Page "' + pageTitle + '" deleted successfully', 'success');

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

    btnEdit.className = hasSelection ? 'btn btn-edit' : 'btn btn-edit disabled';
    btnPreview.className = hasSelection ? 'btn btn-info' : 'btn btn-info disabled';
    btnMove.className = hasSelection ? 'btn btn-move' : 'btn btn-move disabled';
    btnPublish.className = hasSelection ? 'btn btn-publish' : 'btn btn-publish disabled';
    btnDelete.className = hasSelection ? 'btn btn-delete' : 'btn btn-delete disabled';

    // Tooltip messages for disabled state (#8)
    btnEdit.title = hasSelection ? 'Edit selected page' : 'Select a page to edit';
    btnPreview.title = hasSelection ? 'Preview page content' : 'Select a page to preview';
    btnMove.title = hasSelection ? 'Move selected page' : 'Select a page to move';
    btnPublish.title = hasSelection ? 'Publish selected page' : 'Select a page to publish';
    btnDelete.title = hasSelection ? 'Delete selected page' : 'Select a page to delete';
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
    var newPageParent = document.getElementById('newPageParent');
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
            showToast('Publish feature: under development.', 'warning');
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
    // CREATE MODAL helpers
    // ============================================================================
    function showCreatePageModal(parentPath) {
        newPageParent.value = parentPath;
        newPageTitle.value = '';
        createPageError.style.display = 'none';
        createPageSuccess.style.display = 'none';
        createPageSaveBtn.disabled = false;
        createPageSaveBtn.textContent = 'Create & Edit';
        // Update URL preview (fix #3)
        if (urlPreview) urlPreview.textContent = parentPath + '/';
        showModal(createPageModal);
        setTimeout(function() { newPageTitle.focus(); }, 300);
    }

    // ============================================================================
    // URL live preview (fix #3)
    // ============================================================================
    if (urlPreview) {
        newPageTitle.addEventListener('input', function() {
            var title = this.value.trim();
            var parentPath = newPageParent.value;
            var slug = generateSlug(title);
            var fullPath = parentPath ? parentPath + '/' + slug : '/' + slug;
            urlPreview.textContent = slug ? fullPath : (parentPath ? parentPath + '/' : '/');
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
        var slug = generateSlug(title);
        var pagePath = parentPath.endsWith('/') ? parentPath + slug : parentPath + '/' + slug;

        createPageError.style.display = 'none';
        createPageSuccess.style.display = 'none';
        createPageSaveBtn.disabled = true;
        createPageSaveBtn.textContent = 'Creating...';

        try {
            var response = await fetch('/api/v1/pages/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: title,
                    path: pagePath,
                    parent_path: parentPath,
                    language: parentPath.indexOf('/fr') !== -1 ? 'fr' : 'en',
                    status: 'draft',
                    content: '',
                    metadata: {}
                })
            });

            if (!response.ok) {
                var errData = null;
                try { errData = await response.json(); } catch(e) {}
                throw new Error(errData && errData.detail ? errData.detail : 'HTTP ' + response.status);
            }

            var newPage = await response.json();
            var actualPagePath = newPage.path || pagePath;

            // Show toast instead of modal message (fix #5)
            showToast('Page "' + title + '" created!', 'success');

            // Refresh navigation with state retention (fix #9)
            loadedPaths = {};
            columnsCache = [];

            // Navigate to editor immediately (fix #7 - no 800ms delay)
            var editorUrl = '/static/editor.html?pageId=' + encodeURIComponent(actualPagePath);
            window.location.href = editorUrl;

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
