// Tag Tree Lightbox - Shared component for editor and navigation pages
// ============================================================================
// HTML escape helper
function esc(s) {
    if (!s) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

const TAG_ROOT = '/canadasite/tags';

// ============================================================================
// MODAL HELPERS (vanilla JS)
// ============================================================================
function showModal(el) {
    el.style.display = 'block';
    el.classList.remove('mfp-hide');
    el.classList.add('in');
    document.body.classList.add('modal-open');
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
    if (!document.querySelector('[data-modal-backdrop]')) {
        document.body.classList.remove('modal-open');
    }
}

// ============================================================================
// TAG DISPLAY
// ============================================================================
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

// ============================================================================
// TAG TREE MODAL (Lightbox)
// ============================================================================

var ttmType = '';
var ttmMulti = true;
var ttmPaths = [];
var ttmRootPath = '';
var ttmStack = [];
var ttmTags = [];
var ttmCallback = null;

function openTagTree(type, multi) {
    ttmType = type;
    ttmMulti = multi;
    ttmStack = [];
    ttmTags = [];

    // Load existing selections from hidden input
    var hiddenId = 'selected-' + type + '-tags';
    var hidden = document.getElementById(hiddenId);
    ttmPaths = hidden && hidden.value ? hidden.value.split(',').filter(function(p) { return p; }) : [];

    var list = document.getElementById('ttm-tag-list');
    list.innerHTML = '<span class="text-muted">Loading...</span>';

    document.getElementById('ttm-filter').value = '';
    document.getElementById('ttm-selected-count').textContent = ttmPaths.length;
    document.getElementById('ttm-up-btn').style.display = 'none';
    document.getElementById('ttm-breadcrumb').textContent = '';

    var label = document.getElementById('tagTreeModalLabel');
    var typeLabel = type.charAt(0).toUpperCase() + type.slice(1);
    if (label) label.textContent = 'Select ' + typeLabel + ' Tags';

    // Set callback
    ttmCallback = function(selectedPaths) {
        var dispId = 'tags-display-' + type;
        updateTagDisplay(dispId, 'selected-' + type + '-tags', selectedPaths);
    };

    fetch('/api/v1/tags?parent_path=' + encodeURIComponent(TAG_ROOT))
        .then(function(r) { return r.ok ? r.json() : []; })
        .then(function(roots) {
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
