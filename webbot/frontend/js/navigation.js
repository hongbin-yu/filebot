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

function customAlert(msg) {
    const modal = $('#alertModal');
    if (modal) {
        const body = modal.querySelector('.modal-body');
        if (body) body.textContent = msg;
        $('#alertModalOk').focus();
        jQuery("#alertModal").modal ? $(modal).modal('show') : alert(msg);
    } else {
        alert(msg);
    }
}

function pageTitle(page) {
    return page.title && page.title !== 'untitled' ? page.title : cleanPathTitle(page.path);
}

function cleanPathTitle(path) {
    if (!path) return 'Untitled';
    const parts = path.split('/').filter(Boolean);
    return parts[parts.length - 1] || path;
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
    
    const url = `${API_BASE}path?path=${encodePath(parentPath)}`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    
    const pages = await resp.json();
    // Strip content for performance
    const stripped = pages.map(p => {
        const { content, ...rest } = p;
        return rest;
    });
    // Sort by title
    stripped.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    
    loadedPaths[parentPath] = stripped;
    return stripped;
}

// ============================================================================
// 6. RENDERING
// ============================================================================
function renderColumn(columnIndex, title, pages, parentPath) {
    const column = document.createElement('div');
    column.className = 'navigation-column';
    column.dataset.columnIndex = columnIndex;
    
    // Header
    const header = document.createElement('div');
    header.className = 'column-header';
    const h3 = document.createElement('h3');
    h3.textContent = title || `Level ${columnIndex + 1}`;
    header.appendChild(h3);
    column.appendChild(header);
    
    // Pages list
    const list = document.createElement('ul');
    list.className = 'pages-list';
    
    pages.forEach(page => {
        const li = document.createElement('li');
        li.className = 'page-item';
        li.dataset.pageId = page.id;
        li.dataset.pagePath = page.path;
        
        if (parentPath) {
            li.dataset.parentPath = parentPath;
        }
        
        const link = document.createElement('a');
        link.href = '#';
        link.className = 'page-link';
        
        // Title
        const titleSpan = document.createElement('span');
        titleSpan.className = 'page-title';
        titleSpan.textContent = pageTitle(page);
        link.appendChild(titleSpan);
        
        // Path (small font below title)
        const pathSpan = document.createElement('span');
        pathSpan.className = 'page-path';
        pathSpan.textContent = page.path;
        link.appendChild(pathSpan);
        
        // Click handler
        link.addEventListener('click', (e) => {
            e.preventDefault();
            selectPage(page, columnIndex);
        });
        
        li.appendChild(link);
        column.appendChild(li);
    });
    
    // Empty state
    if (pages.length === 0) {
        const empty = document.createElement('li');
        empty.className = 'page-item empty';
        empty.textContent = 'No child pages';
        list.appendChild(empty);
    }
    
    column.appendChild(list);
    return column;
}

function renderColumns() {
    columnsContainer.innerHTML = '';
    
    columnsCache.forEach((colData, idx) => {
        const col = renderColumn(idx, colData.title, colData.pages, colData.parentPath);
        columnsContainer.appendChild(col);
    });
    
    updateBreadcrumb();
    updateButtons();
    updateStats();
    highlightSelectedPage();
}

function highlightSelectedPage() {
    columnsContainer.querySelectorAll('.page-item.selected').forEach(el => {
        el.classList.remove('selected');
    });
    if (selectedPageId) {
        const sel = columnsContainer.querySelector(`.page-item[data-page-id="${CSS.escape(selectedPageId)}"]`);
        if (sel) sel.classList.add('selected');
    }
}

// ============================================================================
// 7. NAVIGATION
// ============================================================================
async function selectPage(page, columnIndex) {
    selectedPageId = page.id;
    selectedPageData = page;
    
    try {
        showLoading();
        const children = await fetchChildren(page.path);
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
            const keepCount = columnIndex + 2;
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
    initNavigation();
}

// ============================================================================
// 8. BREADCRUMB
// ============================================================================
function updateBreadcrumb() {
    const container = breadcrumbNav.querySelector('.aem-breadcrumb') || breadcrumbNav;
    container.innerHTML = '';
    
    // Home item
    const homeSpan = document.createElement('span');
    homeSpan.className = 'breadcrumb-item';
    const homeLink = document.createElement('a');
    homeLink.href = '#';
    homeLink.textContent = 'Canada site';
    homeLink.addEventListener('click', (e) => {
        e.preventDefault();
        navigateHome();
    });
    homeSpan.appendChild(homeLink);
    container.appendChild(homeSpan);
    
    // Path items
    currentPath.forEach((page, idx) => {
        const span = document.createElement('span');
        span.className = 'breadcrumb-item';
        
        if (idx < currentPath.length - 1) {
            const link = document.createElement('a');
            link.href = '#';
            link.textContent = pageTitle(page);
            link.addEventListener('click', (e) => {
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
    
    // Truncate path to this level
    currentPath = currentPath.slice(0, index + 1);
    
    // Rebuild columns from cached children
    const lastPage = currentPath[currentPath.length - 1];
    const children = loadedPaths[lastPage.path] || [];
    
    if (currentPath.length <= 2) {
        columnsCache = children.length > 0 ? [{
            title: pageTitle(lastPage),
            pages: children,
            parentPath: lastPage.path
        }] : [];
    } else {
        columnsCache = [];
        for (let i = 1; i < currentPath.length; i++) {
            const pp = currentPath[i];
            const ch = loadedPaths[pp.path] || [];
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
// 9. BUTTONS
// ============================================================================
function updateButtons() {
    const hasSelection = selectedPageId !== null;
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
}

// ============================================================================
// MODAL HELPERS (vanilla JS — Bootstrap modal plugin not available)
// ============================================================================
function showModal(el) {
    el.style.display = 'block';
    el.classList.add('in');
    document.body.classList.add('modal-open');
    // Add backdrop
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop fade in';
    backdrop.setAttribute('data-modal-backdrop', el.id);
    backdrop.addEventListener('click', () => hideModal(el));
    document.body.appendChild(backdrop);
}

function hideModal(el) {
    el.style.display = 'none';
    el.classList.remove('in');
    document.body.classList.remove('modal-open');
    const backdrop = document.querySelector(`[data-modal-backdrop="${el.id}"]`);
    if (backdrop) backdrop.remove();
}

function setupButtons() {
    btnCreate.addEventListener('click', () => {
        const parentPath = selectedPageData ? selectedPageData.path : ROOT_PATH;
        showCreatePageModal(parentPath);
    });
    
    btnEdit.addEventListener('click', () => {
        if (selectedPageData) {
            window.location.href = `/static/editor.html?pageId=${encodePath(selectedPageData.path)}`;
        }
    });
    
    btnPreview.addEventListener('click', () => {
        if (selectedPageData) {
            window.open(`/api/v1/pages/preview?path=${encodePath(selectedPageData.path)}`, '_blank');
        }
    });
    
    btnMove.addEventListener('click', () => {
        if (selectedPageData) {
            customAlert(`Move page: ${pageTitle(selectedPageData)}\nFeature under development.`);
        }
    });
    
    btnPublish.addEventListener('click', () => {
        if (selectedPageData) {
            customAlert(`Publish page: ${pageTitle(selectedPageData)}\nFeature under development.`);
        }
    });
    
    btnDelete.addEventListener('click', () => {
        if (selectedPageData) {
            customAlert(`Delete page: ${pageTitle(selectedPageData)}\nFeature under development.`);
        }
    });
    
    btnRefresh.addEventListener('click', () => {
        loadedPaths = {};
        columnsCache = [];
        currentPath = [];
        selectedPageId = null;
        selectedPageData = null;
        initNavigation();
    });

    // ============================================================================
    // 5b. CREATE PAGE MODAL
    // ============================================================================
    const createPageModal = document.getElementById('createPageModal');
    const createPageForm = document.getElementById('createPageForm');
    const newPageTitle = document.getElementById('newPageTitle');
    const newPageParent = document.getElementById('newPageParent');
    const createPageError = document.getElementById('createPageError');
    const createPageSuccess = document.getElementById('createPageSuccess');
    const createPageSaveBtn = document.getElementById('createPageSaveBtn');

    // Close button bindings (Bootstrap JS not available)
    createPageModal.querySelectorAll('[data-dismiss="modal"]').forEach(btn => {
        btn.addEventListener('click', () => hideModal(createPageModal));
    });

    function showCreatePageModal(parentPath) {
        newPageParent.value = parentPath;
        newPageTitle.value = '';
        createPageError.style.display = 'none';
        createPageSuccess.style.display = 'none';
        createPageSaveBtn.disabled = false;
        createPageSaveBtn.textContent = 'Create & Edit';
        showModal(createPageModal);
        setTimeout(() => newPageTitle.focus(), 300);
    }

    createPageForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const title = newPageTitle.value.trim();
        if (!title) {
            createPageError.textContent = 'Please enter a page title.';
            createPageError.style.display = 'block';
            return;
        }
        
        const parentPath = newPageParent.value;
        
        // Generate path from title
        const slug = title.toLowerCase()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-|-$/g, '');
        const pagePath = parentPath.endsWith('/') ? `${parentPath}${slug}` : `${parentPath}/${slug}`;
        
        createPageError.style.display = 'none';
        createPageSuccess.style.display = 'none';
        createPageSaveBtn.disabled = true;
        createPageSaveBtn.textContent = 'Creating...';
        
        try {
            const response = await fetch('/api/v1/pages/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: title,
                    path: pagePath,
                    parent_path: parentPath,
                    language: parentPath.includes('/fr') ? 'fr' : 'en',
                    status: 'draft',
                    content: '',
                    metadata: {}
                })
            });
            
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `HTTP ${response.status}`);
            }
            
            const newPage = await response.json();
            
            // Show success
            const actualPagePath = newPage.path || pagePath;
            createPageSuccess.innerHTML = `Page &quot;${title}&quot; created successfully!<br><small>Path: ${actualPagePath}</small>`;
            createPageSuccess.style.display = 'block';
            createPageSaveBtn.textContent = 'Opening editor...';
            
            // Refresh the tree
            loadedPaths = {};
            columnsCache = [];
            initNavigation();
            
            // Navigate to editor after brief delay
            setTimeout(() => {
                const editorUrl = `/static/editor.html?pageId=${encodeURIComponent(actualPagePath)}`;
                window.location.href = editorUrl;
            }, 800);
            
        } catch (err) {
            createPageError.textContent = `Failed to create page: ${err.message}`;
            createPageError.style.display = 'block';
            createPageSaveBtn.disabled = false;
            createPageSaveBtn.textContent = 'Create & Edit';
        }
    });
}

// ============================================================================
// 10. STATS
// ============================================================================
async function updateStats() {
    if (!pageStats) return;
    // Count loaded paths from cache (no extra API call needed)
    const loadedCount = Object.keys(loadedPaths).length;
    const totalVisible = Object.values(loadedPaths).reduce((sum, pages) => sum + pages.length, 0);
    
    // Also count total root pages
    const rootChildren = loadedPaths[ROOT_PATH];
    const rootCount = rootChildren ? rootChildren.length : '?';
    
    pageStats.innerHTML = `<strong>${rootCount}</strong> root pages · <strong>${totalVisible}</strong> pages loaded · <strong>${loadedCount}</strong> paths cached`;
}

// ============================================================================
// 11. INIT
// ============================================================================
async function initNavigation() {
    showLoading();
    try {
        const children = await fetchChildren(ROOT_PATH);
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
        console.log(`Navigation initialized: ${children.length} root pages`);
    } catch (err) {
        console.error('Navigation init failed:', err);
        showError(`Failed to load navigation: ${err.message}. Please try refreshing.`);
    }
}

// ============================================================================
// 12. BOOT
// ============================================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM ready - initializing navigation');
    initDom();
    setupButtons();
    initNavigation();
});

console.log('Navigation Module loaded.');
