
        // API configuration
        const API_BASE = '/api/v1/pages';
        let currentPageId = null;
        let currentPageData = null;
        window.allPages = [];

        // Breadcrumb titles to skip (root-level home pages)
        var SKIP_BREADCRUMB_TITLES = ['canadasite', 'home', 'accueil'];

        // DOM elements
        const pageTreeEl = document.getElementById('page-tree');
        const editorFormEl = document.getElementById('editor-form');
        const noPageSelectedEl = document.getElementById('no-page-selected');
        const loadingContentEl = document.getElementById('loading-content');
        const errorAreaEl = document.getElementById('error-area');
        const successMessageEl = document.getElementById('success-message');
        const editorActionsEl = document.getElementById('editor-actions');

        // Form elements
        // const editorTitleEl = document.getElementById('editor-title'); // Removed from UI
        const editorContentEl = document.getElementById('editor-content');
        // const editorLanguageEl = document.getElementById('editor-language'); // Removed from UI
        // const editorStatusEl = document.getElementById('editor-status'); // Removed from UI
        const previewPageBtn = document.getElementById('preview-page');
        const topPreviewBtn = document.getElementById('btn-top-preview');
        const savePageBtn = document.getElementById('save-page');
        const publishPageBtn = document.getElementById('publish-page');
        const cancelEditBtn = document.getElementById('cancel-edit');
        // File manager buttons removed per user request - dummy variables to prevent reference errors
        const fileManagerBtn = null;
        const fileManagerHeaderBtn = null;
        // FileBot sidebar - toggle button and close button (initialized in DOMContentLoaded)
        const filebotToggleBtn = null;
        const filebotSidebar = null;
        const filebotSidebarClose = null;

        // WYSIWYG Editor elements
        let tinyMceEditor = null;
        let isNewPage = false;
        let newPageParentPath = null;
        const wysiwygContainer = document.getElementById('wysiwyg-editor-container');
        const htmlSourceContainer = document.getElementById('html-source-container');
        const editorModeBtns = document.querySelectorAll('.editor-mode-btn');

        // Display elements
        const pageTitleDisplayEl = document.querySelector('#page-title-display');
        const pageIdDisplayEl = document.querySelector('#page-id-display');
        const pageLanguageDisplayEl = document.querySelector('#page-language-display');
        const pageStatusDisplayEl = document.querySelector('#page-status-display');
        const filePathDisplayEl = document.querySelector('#file-path-display');
        const lastModifiedDisplayEl = document.querySelector('#page-lastmodified-display');
        const pagePublishedDisplayEl = document.querySelector('#page-published-display');
        const savePageTopBtn = document.getElementById('save-page-top');
        const breadcrumbEl = document.getElementById('breadcrumb');

        // Load all pages for path resolution
        function loadAllPages() {
            console.log('Loading all pages for path resolution...');
            fetch('/api/v1/pages/?limit=1000')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(pages => {
                    console.log('All pages loaded for path resolution:', pages.length, 'pages');
                    window.allPages = pages;
                    console.log('allPages array populated with', window.allPages.length, 'pages');

                    // If we have a page to load, try loading it now that we have all pages
                    const urlParams = new URLSearchParams(window.location.search);
                    const pageIdFromUrl = urlParams.get('pageId');
                    const pathFromUrl = urlParams.get('path');
                    const pageToLoad = pathFromUrl || pageIdFromUrl;

                    if (pageToLoad && window.hasPageBeenLoaded !== true) {
                        console.log('Re-loading page with all pages available:', pageToLoad);
                        window.hasPageBeenLoaded = true;
                        // Give a small delay for any other initialization
                        setTimeout(() => {
                            loadPage(pageToLoad);
                        }, 100);
                    }
                })
                .catch(error => {
                    console.error('Error loading all pages:', error);
                    console.log('Path resolution will use available data');
                });
        }

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            console.log('WebBot Editor initialized');
            // Initialize components sidebar on page load
            loadComponents();
            // Load pages for sidebar - only if no page is being loaded from URL
            // (loadPage will call loadPagesForSidebar with page path if needed)
            // Load all pages for path resolution (for breadcrumb navigation)
            loadAllPages();
            // Add CSS styles for component menus
            addTemplateEditStyles();

            // Initialize menus for existing components
            setTimeout(() => {
                initializeComponentMenus();
            }, 500); // Wait a bit for TinyMCE to fully initialize

            // Get page ID or path from URL if present
            // Function to extract page path from URL pathname
            function getPagePathFromUrl() {
                const pathname = window.location.pathname;
                console.log('URL pathname:', pathname);

                // Check for /static/editor.html/{path} pattern
                const staticEditorPrefix = '/static/editor.html/';
                if (pathname.startsWith(staticEditorPrefix)) {
                    const pagePath = pathname.substring(staticEditorPrefix.length);
                    console.log('Extracted from /static/editor.html/:', pagePath);
                    return pagePath ? '/' + pagePath : null;
                }

                // Check for /editor.html/{path} pattern (without static)
                const editorPrefix = '/editor.html/';
                if (pathname.startsWith(editorPrefix)) {
                    const pagePath = pathname.substring(editorPrefix.length);
                    console.log('Extracted from /editor.html/:', pagePath);
                    return pagePath ? '/' + pagePath : null;
                }

                return null;
            }

            const urlParams = new URLSearchParams(window.location.search);
            const pageIdFromUrl = urlParams.get('pageId');
            const pathFromUrl = urlParams.get('path');
            const pathFromUrlPath = getPagePathFromUrl();
            console.log('URL params - pageIdFromUrl:', pageIdFromUrl, 'pathFromUrl:', pathFromUrl, 'pathFromUrlPath:', pathFromUrlPath);

            // Determine what to load: URL path takes highest precedence, then query params
            let pageToLoad = null;
            if (pathFromUrlPath) {
                pageToLoad = pathFromUrlPath;
                console.log('Using path from URL pathname:', pathFromUrlPath);
                // Update URL to use pageId query parameter for consistency
                const url = new URL(window.location);
                url.searchParams.set('pageId', pathFromUrlPath);
                window.history.replaceState({}, '', url);
                console.log('Updated URL to use pageId parameter');
            } else if (pathFromUrl) {
                pageToLoad = pathFromUrl;
                console.log('Using path parameter:', pathFromUrl);
                // Optionally update URL to use pageId parameter for consistency
                const url = new URL(window.location);
                url.searchParams.set('pageId', pathFromUrl);
                url.searchParams.delete('path');
                window.history.replaceState({}, '', url);
                console.log('Updated URL to use pageId parameter');
            } else if (pageIdFromUrl) {
                pageToLoad = pageIdFromUrl;
                console.log('Using pageId parameter:', pageIdFromUrl);
            }

            // Check for parent_path parameter (create new page mode)
            const parentPathFromUrl = urlParams.get('parent_path');

            // If we have something to load, do it
            if (pageToLoad) {
                console.log('Will load page:', pageToLoad);
                window.hasPageBeenLoaded = true;
                setTimeout(() => {
                    loadPage(pageToLoad);
                }, 500);
            } else if (parentPathFromUrl) {
                console.log('Creating new page with parent_path:', parentPathFromUrl);
                window.hasPageBeenLoaded = true;
                // Initialize immediately - no need to wait for TinyMCE
                initializeNewPage(decodeURIComponent(parentPathFromUrl));
            } else {
                console.log('No page to load from URL');
                // Show initial message in pages sidebar
                loadPagesForSidebar();
            }

            // Event listeners
            previewPageBtn.addEventListener('click', previewPage);
            if (topPreviewBtn) topPreviewBtn.addEventListener('click', previewPage);
            savePageBtn.addEventListener('click', savePage);
            if (savePageTopBtn) {
                savePageTopBtn.addEventListener('click', savePage);
            }
            publishPageBtn.addEventListener('click', publishPage);
            cancelEditBtn.addEventListener('click', cancelEdit);
            // File manager buttons removed per user request - event listeners removed

            // Home link - removed click override to allow natural navigation to navigation.html

            // FileBot toggle button - controls left sidebar
            const resourceToggleBtn = document.getElementById('filebot-toggle-btn');
            const resourceSidebar = document.getElementById('resource-sidebar');
            const resourceSidebarClose = document.getElementById('resource-sidebar-close');

            // Set initial state based on sidebar visibility
            if (resourceToggleBtn && resourceSidebar) {
                if (!resourceSidebar.classList.contains('hidden')) {
                    resourceToggleBtn.classList.add('active');
                }

                resourceToggleBtn.addEventListener('click', function() {
                    resourceSidebar.classList.toggle('hidden');
                    resourceToggleBtn.classList.toggle('active');
                    console.log('Resource sidebar toggled');
                });
            }

            if (resourceSidebarClose) {
                resourceSidebarClose.addEventListener('click', function() {
                    resourceSidebar.classList.add('hidden');
                    resourceToggleBtn.classList.remove('active');
                    console.log('Resource sidebar closed via close button');
                });
            }

            // AI toggle button - controls right panel
            const aiToggleBtn = document.getElementById('ai-toggle-btn');
            const aiPanel = document.getElementById('ai-assistant-panel');

            if (aiToggleBtn && aiPanel) {
                aiToggleBtn.addEventListener('click', function() {
                    aiPanel.classList.toggle('hidden');
                    aiToggleBtn.classList.toggle('active');
                    console.log('AI assistant panel toggled');

                    // Focus on input when panel opens
                    if (!aiPanel.classList.contains('hidden')) {
                        setTimeout(() => {
                            const input = document.getElementById('ai-chat-input');
                            if (input) input.focus();
                        }, 300);
                    }
                });
            }

            // Sidebar File Upload Area
            const sidebarFileInput = document.getElementById('sidebar-file-input');
            const sidebarBrowseBtn = document.getElementById('sidebar-browse-files-btn');
            const sidebarUploadArea = document.getElementById('sidebar-file-upload-area');

            // Function to open file manager modal (reused from previous logic) - COMMENTED OUT: FileManager no longer used
            function openFileManagerModal() { /* Commented out */ return;
                console.log('openFileManagerModal called');

                // Ensure file manager modal exists in DOM
                ensureFileManagerModalExists();

                // Open file manager modal
                const fileManagerModal = document.getElementById('file-manager-modal');
                if (fileManagerModal) {
                    console.log('File manager modal found, opening with simple display');
                    console.log('Modal style before:', fileManagerModal.style.display);

                    // Remove any hiding classes that might still exist
                    fileManagerModal.classList.remove('mfp-hide');
                    fileManagerModal.classList.remove('wb-lbx-inline');

                    // Show the modal - styling is already defined in HTML
                    fileManagerModal.style.display = 'block';

                    // Ensure modal is visible and properly positioned
                    fileManagerModal.style.position = 'fixed';
                    fileManagerModal.style.top = '50%';
                    fileManagerModal.style.left = '50%';
                    fileManagerModal.style.transform = 'translate(-50%, -50%)';
                    fileManagerModal.style.width = '900px';
                    fileManagerModal.style.maxWidth = '90vw';
                    fileManagerModal.style.maxHeight = '90vh';
                    fileManagerModal.style.overflow = 'auto';
                    fileManagerModal.style.backgroundColor = 'white';
                    fileManagerModal.style.border = '1px solid #ccc';
                    fileManagerModal.style.borderRadius = '8px';
                    fileManagerModal.style.boxShadow = '0 4px 20px rgba(0,0,0,0.2)';
                    fileManagerModal.style.zIndex = '9999';

                    console.log('Modal style after:', fileManagerModal.style.display);
                    console.log('Modal computed style:', window.getComputedStyle(fileManagerModal).display);

                    // Load files when modal opens (方案C:智能延迟加载)
                    // Wait a moment for modal DOM to be fully ready
                    setTimeout(() => {
                        if (typeof loadFiles === 'function') {
                            console.log('Loading files for FileBot manager...');
                            // Check if file list container exists
                            const fileListBody = document.getElementById('file-list-body');
                            if (fileListBody) {
                                console.log('File list container found, loading files...');
                                loadFiles();
                            } else {
                                console.warn('file-list-body not found, retrying in 100ms...');
                                setTimeout(() => {
                                    if (typeof loadFiles === 'function') {
                                        console.log('Retry loading files...');
                                        loadFiles();
                                    }
                                }, 100);
                            }
                        } else {
                            console.warn('loadFiles function not defined');
                        }
                    }, 50);

                    // Add close button handler if not already added
                    const closeBtn = fileManagerModal.querySelector('.overlay-close, .close');
                    if (closeBtn && !closeBtn.hasAttribute('data-filebot-close-handler')) {
                        console.log('Adding close button handler');
                        closeBtn.setAttribute('data-filebot-close-handler', 'true');
                        closeBtn.addEventListener('click', function() {
                            console.log('Close button clicked');
                            fileManagerModal.style.display = 'none';
                        });
                    }

                    // Add click outside to close
                    if (!fileManagerModal.hasAttribute('data-filebot-overlay-handler')) {
                        fileManagerModal.setAttribute('data-filebot-overlay-handler', 'true');
                        fileManagerModal.addEventListener('click', function(e) {
                            if (e.target === fileManagerModal) {
                                console.log('Click outside modal, closing');
                                fileManagerModal.style.display = 'none';
                            }
                        });
                    }

                    // Force a reflow and check visibility
                    setTimeout(() => {
                        const rect = fileManagerModal.getBoundingClientRect();
                        console.log('Modal bounding rect:', rect);
                        if (rect.width === 0 || rect.height === 0) {
                            console.warn('Modal appears to have zero dimensions');
                        } else {
                            console.log('Modal visible with dimensions:', rect.width, 'x', rect.height);
                        }
                    }, 100);

                    console.log('File manager modal opened successfully');
                } else {
                    console.warn('File manager modal not found even after ensuring');
                    alert('File manager is not available. Please check if FileBot is running.');
                }
            }

            // Sidebar file upload event handlers
            if (sidebarBrowseBtn && sidebarFileInput) {
                sidebarBrowseBtn.addEventListener('click', function() {
                    sidebarFileInput.click();
                });
            }

            // File input change event for sidebar
            if (sidebarFileInput) {
                sidebarFileInput.addEventListener('change', function(e) {
                    if (e.target.files.length > 0) {
                        uploadFiles(e.target.files);
                    }
                });
            }

            // Drag and drop upload for sidebar
            if (sidebarUploadArea) {
                sidebarUploadArea.addEventListener('dragover', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    sidebarUploadArea.style.borderColor = '#31708f';
                    sidebarUploadArea.style.backgroundColor = '#f5f5f5';
                });

                sidebarUploadArea.addEventListener('dragleave', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    sidebarUploadArea.style.borderColor = '#4CAF50';
                    sidebarUploadArea.style.backgroundColor = '#f8fff8';
                });

                sidebarUploadArea.addEventListener('drop', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    sidebarUploadArea.style.borderColor = '#4CAF50';
                    sidebarUploadArea.style.backgroundColor = '#f8fff8';

                    if (e.dataTransfer.files.length > 0) {
                        uploadFiles(e.dataTransfer.files);
                    }
                });

                sidebarUploadArea.addEventListener('click', function() {
                    sidebarFileInput.click();
                });
            }


            // Load sidebar sections (Images, Components, etc.) via Mustache
            initializeSidebarSections();

            // Initialize TinyMCE WYSIWYG Editor
            initializeTinyMCE();

            // Initialize File Manager - DISABLED per user request to remove duplicate functionality
            //insertFileManagerHTML(); // Keep disabled to avoid duplicate functionality, using lazy loading instead

            // Lazy initialize file manager on demand - will be loaded when first clicked
            // For now, we'll initialize it on page load to ensure it's available
            // ensureFileManagerModalExists(); // Commented out: FileManager no longer used per user request

            // Add event listeners for editor mode switching
            editorModeBtns.forEach(btn => {
                btn.addEventListener('click', function() {
                    const mode = this.getAttribute('data-mode');
                    switchEditorMode(mode);
                });
            });

            // Initialize language switcher
            initLanguageSwitcher();

            // Quick Edit buttons wiring
            var quickEditComponent = document.getElementById('quick-edit-component');
            var quickEditHTML = document.getElementById('quick-edit-html');
            if (quickEditComponent) {
                quickEditComponent.addEventListener('click', function() {
                    showCurrentElementWYSIWYGEdit();
                });
            }
            if (quickEditHTML) {
                quickEditHTML.addEventListener('click', function() {
                    showCurrentElementHTMLEdit('code');
                });
            }
        });

        /**
         * Initialize sidebar sections (Images, Components, etc.)
         * Loads mustache templates and data for each .wb-filter[data-filebot-url]
         */
        async function initializeSidebarSections() {
            const sections = document.querySelectorAll('.wb-filter[data-filebot-url]');
            if (!sections.length) return;

            const templateCache = {};

            // Map: template URL pattern -> (apiUrl, dataMapper)
            // dataMapper receives API response and returns { dataKey: itemsArray }
            const sectionHandlers = {
                'images.html': {
                    apiUrl: '/api/v1/files/',
                    dataKey: 'images',
                    mapData: function(items) {
                        return items.map(function(f) {
                            return {
                                id: f.id,
                                title: f.name || f.title || 'Untitled',
                                thumbnail_url: f.thumbnail_url || '',
                                file_size: f.size || '',
                                mime_type: f.type || f.mime_type || '',
                                url: f.url || ''
                            };
                        });
                    }
                },
                'components.html': {
                    apiUrl: '/api/v1/components/templates',
                    dataKey: 'components',
                    mapData: function(items) {
                        return items.map(function(c) {
                            return {
                                id: c.id,
                                name: c.display_name || c.name || 'Unknown',
                                description: c.description || '',
                                category: c.category || 'basic',
                                icon: c.icon || '',
                                is_custom: c.category === 'custom' || false,
                                has_preview: true
                            };
                        });
                    }
                },
                'document-list.html': {
                    apiUrl: '/api/v1/files/',
                    dataKey: 'documents',
                    mapData: function(items) {
                        return items.map(function(f) {
                            var type = (f.type || f.mime_type || '').toLowerCase();
                            return {
                                id: f.id,
                                title: f.name || f.title || 'Untitled',
                                original_filename: f.name || '',
                                file_size: f.size || '',
                                mime_type: type,
                                is_pdf: type.indexOf('pdf') >= 0,
                                is_word: type.indexOf('word') >= 0 || type.indexOf('doc') >= 0,
                                is_excel: type.indexOf('excel') >= 0 || type.indexOf('sheet') >= 0,
                                is_powerpoint: type.indexOf('powerpoint') >= 0 || type.indexOf('presentation') >= 0,
                                document_number: f.id ? f.id.substring(0, 8) : ''
                            };
                        });
                    }
                },
                'templates.html': {
                    apiUrl: '/api/v1/pages/?limit=50',
                    dataKey: 'templates',
                    mapData: function(items) {
                        return items.map(function(p) {
                            return {
                                id: p.id || p.path || '',
                                title: p.title || p.name || 'Untitled',
                                type: p.template_type || (p.parent_path === '/' ? 'Content Page' : 'Sub Page'),
                                description: p.description || '',
                                author: p.author || '',
                                created_date: p.created_at ? new Date(p.created_at).toLocaleDateString() : '',
                                is_official: false,
                                is_custom: true,
                                can_edit: true
                            };
                        });
                    }
                }
            };

            // Fetch raw template text from static
            async function getTemplate(url) {
                if (templateCache[url]) return templateCache[url];
                // Convert /mustache/en/mustache-templates/name.html -> /static/mustache-templates/en/name.html
                // The /mustache/ route goes through renderer; get raw template from static
                // Pattern: /mustache/{lang}/mustache-templates/{name}.html
                var parts = url.split('/');
                var lang = parts[2];   // 'en'
                var name = parts[4];   // 'images.html'
                var staticPath = '/static/mustache-templates/' + lang + '/' + name;
                try {
                    var resp = await fetch(staticPath);
                    if (!resp.ok) throw new Error('HTTP ' + resp.status);
                    var text = await resp.text();
                    templateCache[url] = text;
                    return text;
                } catch (e) {
                    console.warn('Failed to load template from', staticPath, e);
                    return null;
                }
            }

            // Process each section
            for (var i = 0; i < sections.length; i++) {
                var el = sections[i];
                var templateUrl = el.getAttribute('data-filebot-url');
                if (!templateUrl) continue;

                // Determine handler based on filename in URL
                var filename = templateUrl.split('/').pop();
                var handler = sectionHandlers[filename];
                if (!handler) {
                    console.warn('No data handler for template:', filename);
                    continue;
                }

                // Fetch template + data in parallel
                var templatePromise = getTemplate(templateUrl);
                var dataPromise = fetch(handler.apiUrl).then(function(r) {
                    if (!r.ok) throw new Error('API ' + r.status);
                    return r.json();
                }).catch(function(e) {
                    console.warn('Failed to fetch data from', handler.apiUrl, e);
                    return null;
                });

                var results = await Promise.all([templatePromise, dataPromise]);
                var templateText = results[0];
                var apiResult = results[1];

                if (!templateText) {
                    el.innerHTML = '<em style="color: #d32f2f;">Template loading failed</em>';
                    continue;
                }

                // Extract items from API response
                var items = [];
                if (apiResult) {
                    if (Array.isArray(apiResult)) {
                        items = apiResult;
                    } else if (apiResult.files) {
                        items = apiResult.files;
                    } else if (apiResult.pages) {
                        items = apiResult.pages;
                    } else if (apiResult.data) {
                        items = apiResult.data;
                    } else if (apiResult[handler.dataKey]) {
                        items = apiResult[handler.dataKey];
                    } else {
                        // Try to find any array property
                        for (var key in apiResult) {
                            if (Array.isArray(apiResult[key])) {
                                items = apiResult[key];
                                break;
                            }
                        }
                    }
                }

                // Map data to match template expectations
                var mapped = handler.mapData(items);

                // Build render context: { images: [...], components: [...], etc. }
                var context = {};
                context[handler.dataKey] = mapped;

                // Render with Mustache
                try {
                    if (typeof Mustache !== 'undefined' && Mustache.render) {
                        var rendered = Mustache.render(templateText, context);
                        el.innerHTML = rendered;
                        console.log('Rendered', filename, '-', mapped.length, 'items');
                    } else {
                        el.innerHTML = '<em>Mustache.js not loaded</em>';
                    }
                } catch (renderError) {
                    console.error('Mustache render error:', renderError);
                    el.innerHTML = '<em style="color: #d32f2f;">Render error</em>';
                }
            }
        }

        // Initialize Quill WYSIWYG Editor
        function initializeTinyMCE() {
            console.log('Initializing TinyMCE editor...');

            // Configure TinyMCE
            tinymce.init({
                selector: '#wysiwyg-editor-container',
                height: 1500,
                menubar: 'file edit view insert format tools table help',
                base_url: '/gcweb/external/tinymce/tinymce/js/tinymce/',
                plugins: [
                    'advlist', 'autolink', 'lists', 'link', 'image', 'charmap', 'preview',
                    'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
                    'insertdatetime', 'media', 'table', 'help', 'wordcount',
                    'pagebreak'
                ],
                toolbar: 'undo redo | styleselect | bold italic underline | ' +
                         'alignleft aligncenter alignright alignjustify | ' +
                         'bullist numlist outdent indent | link image media table | ' +
                         'blockquote pagebreak | charmap preview searchreplace visualblocks | ' +
                         'code fullscreen help | insertButton insertTable insertAlert insertBreadcrumb insertSidebar insertFooter insertSearch insertIntroduction insertIntroFullImage insertIntroHalfImage insertMostRequested insertFeatureLink insertGovernmentInitiatives insertFeatures insertServicesInfo3col insertServicesInfo2col insertServicesInfoList insertFeatureLinkDark insertFeatureLinkLight insertFeatureLinkGray | insertByPath | deleteComponent | aiAssistant',
                content_style: 'body { font-family:Helvetica,Arial,sans-serif; font-size:14px }',
                // Load Canada.ca CSS for editor content (makes editing look like preview)
                content_css: [
                    '/etc/designs/canada/wet-boew/css/theme.min.css'
                ],
                // Allow all HTML elements for Canada.ca pages
                extended_valid_elements: '*[*]',
                // Disable cleanup of HTML
                cleanup: false,
                valid_elements: '*[*]',
                // Allow full HTML
                allow_html_in_named_anchor: true,
                // Image editing options
                image_advtab: true,
                image_dimensions: true,
                image_title: true,
                image_caption: true,
                object_resizing: 'img',
                // Preserve root-relative URLs (e.g. /en/contact.html) as-is
                relative_urls: false,
                remove_script_host: true,
                convert_urls: false,
                // Prevent link plugin from converting relative paths
                link_default_protocol: 'https',
                link_assume_external_targets: false,
                // Custom preview template to match WebBot preview
                preview_template: '<!DOCTYPE html><html><head><title>Preview</title><base target="_blank"></head><body style="background: #f8f9fa; padding: 20px;"><div style="max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); padding: 20px;">{content}</div></body></html>',
                // Setup callback when editor is initialized
                setup: function(editor) {
                    tinyMceEditor = editor;
                    window.tinyMceEditor = editor;  // Make available globally for component-params.js

                    // Add component insertion buttons
                    editor.ui.registry.addButton('insertButton', {
                        icon: 'plus',
                        tooltip: 'Insert Button',
                        onAction: function() {
                            insertComponent('button');
                        }
                    });


                    editor.ui.registry.addButton('insertByPath', {
                        text: '📄 Insert by Path',
                        tooltip: 'Fetch a page by path and insert its content at cursor',
                        onAction: function() {
                            const path = prompt('Enter page path to insert\n(e.g. /en/contact or contact):');
                            if (path && path.trim()) {
                                insertPath(path.trim());
                            }
                        }
                    });

                    editor.ui.registry.addButton('insertTable', {
                        icon: 'table',
                        tooltip: 'Insert Table',
                        onAction: function() {
                            insertComponent('table');
                        }
                    });

                    editor.ui.registry.addButton('insertAlert', {
                        icon: 'warning',
                        tooltip: 'Insert Alert Box',
                        onAction: function() {
                            insertComponent('alert');
                        }
                    });

                    editor.ui.registry.addButton('insertBreadcrumb', {
                        icon: 'arrow-right',
                        tooltip: 'Insert Breadcrumb',
                        onAction: function() {
                            insertComponent('breadcrumb');
                        }
                    });

                    editor.ui.registry.addButton('insertSidebar', {
                        icon: 'menu',
                        tooltip: 'Insert Sidebar Navigation',
                        onAction: function() {
                            insertComponent('sidebar');
                        }
                    });

                    editor.ui.registry.addButton('insertFooter', {
                        icon: 'page-break',
                        tooltip: 'Insert Footer Section',
                        onAction: function() {
                            insertComponent('footer');
                        }
                    });

                    editor.ui.registry.addButton('insertSearch', {
                        icon: 'search',
                        tooltip: 'Insert Search Box',
                        onAction: function() {
                            insertComponent('search');
                        }
                    });

                    editor.ui.registry.addButton('insertIntroduction', {
                        icon: 'newspaper-o',
                        tooltip: 'Insert Introduction Block',
                        onAction: function() {
                            insertComponent('introduction');
                        }
                    });

                    editor.ui.registry.addButton('insertIntroFullImage', {
                        icon: 'picture-o',
                        tooltip: 'Insert Introduction with Full Image',
                        onAction: function() {
                            insertComponent('introduction-full-image');
                        }
                    });

                    editor.ui.registry.addButton('insertIntroHalfImage', {
                        icon: 'columns',
                        tooltip: 'Insert Introduction with Half Image',
                        onAction: function() {
                            insertComponent('introduction-half-image');
                        }
                    });

                    editor.ui.registry.addButton('insertMostRequested', {
                        icon: 'list-ol',
                        tooltip: 'Insert Most Requested Links',
                        onAction: function() {
                            insertComponent('most-requested');
                        }
                    });

                    editor.ui.registry.addButton('insertFeatureLink', {
                        icon: 'link',
                        tooltip: 'Insert Feature Link with Description',
                        onAction: function() {
                            insertComponent('feature-link');
                        }
                    });

                    editor.ui.registry.addButton('insertGovernmentInitiatives', {
                        icon: 'flag',
                        tooltip: 'Insert Government Initiatives',
                        onAction: function() {
                            insertComponent('government-initiatives');
                        }
                    });

                    editor.ui.registry.addButton('insertFeatures', {
                        icon: 'gallery',
                        tooltip: 'Insert Features Section',
                        onAction: function() {
                            insertComponent('features');
                        }
                    });

                    editor.ui.registry.addButton('insertServicesInfo3col', {
                        icon: 'grid',
                        tooltip: 'Insert Services & Info (3 Columns)',
                        onAction: function() {
                            insertComponent('services-info-3col');
                        }
                    });

                    editor.ui.registry.addButton('insertServicesInfo2col', {
                        icon: 'grid-2',
                        tooltip: 'Insert Services & Info (2 Columns)',
                        onAction: function() {
                            insertComponent('services-info-2col');
                        }
                    });

                    editor.ui.registry.addButton('insertServicesInfoList', {
                        icon: 'list',
                        tooltip: 'Insert Services & Info (List)',
                        onAction: function() {
                            insertComponent('services-info-list');
                        }
                    });

                    editor.ui.registry.addButton('insertFeatureLinkDark', {
                        icon: 'tint',
                        tooltip: 'Insert Feature Link (Dark Background)',
                        onAction: function() {
                            insertComponent('feature-link-dark');
                        }
                    });

                    editor.ui.registry.addButton('insertFeatureLinkLight', {
                        icon: 'tint',
                        tooltip: 'Insert Feature Link (Light Background)',
                        onAction: function() {
                            insertComponent('feature-link-light');
                        }
                    });

                    editor.ui.registry.addButton('insertFeatureLinkGray', {
                        icon: 'tint',
                        tooltip: 'Insert Feature Link (Gray Background)',
                        onAction: function() {
                            insertComponent('feature-link-gray');
                        }
                    });

                    editor.ui.registry.addButton('deleteComponent', {
                        icon: 'trash',
                        tooltip: 'Delete Component',
                        onAction: function() {
                            deleteComponent();
                        }
                    });

                    // Components button
                    editor.ui.registry.addButton('insertComponents', {
                        text: '🧩', // Use emoji for better visibility
                        tooltip: 'Insert Component - Browse and insert Canada.ca components',
                        onAction: function() {
                            console.log('Insert Components button clicked');
                            showComponentsModal();
                        }
                    });

                    // AI Assistant button
                    editor.ui.registry.addButton('aiAssistant', {
                        icon: 'user',
                        tooltip: 'AI Assistant (Beta)',
                        onAction: function() {
                            toggleAIAssistant();
                        }
                    });

                    // Override TinyMCE preview command to use our previewPage function
                    editor.addCommand('mcePreview', function() {
                        console.log('TinyMCE preview command overridden, calling previewPage()');
                        previewPage();
                    });

                    // Also override 'preview' command (some versions use this)
                    editor.addCommand('preview', function() {
                        console.log('TinyMCE preview command (preview) overridden, calling previewPage()');
                        previewPage();
                    });

                    // Sync content changes to textarea
                    editor.on('change', function() {
                        const htmlContent = editor.getContent();
                        // Only update textarea if we're in WYSIWYG mode
                        if (wysiwygContainer.classList.contains('active')) {
                            editorContentEl.value = htmlContent;
                        }
                    });

                    // Also sync when textarea content changes (for HTML mode)
                    editorContentEl.addEventListener('input', function() {
                        // Only update TinyMCE if we're in HTML mode
                        if (htmlSourceContainer.classList.contains('active')) {
                            editor.setContent(this.value);
                        }
                    });
                }
            });

            console.log('TinyMCE editor initialized');
        }

        // Switch between WYSIWYG and HTML source modes
        function switchEditorMode(mode) {
            console.log(`Switching to ${mode} mode`);

            // Update active button state
            editorModeBtns.forEach(btn => {
                if (btn.getAttribute('data-mode') === mode) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });

            // Show/hide appropriate containers
            if (mode === 'wysiwyg') {
                wysiwygContainer.classList.add('active');
                htmlSourceContainer.classList.remove('active');

                // Sync content from textarea to TinyMCE
                const htmlContent = editorContentEl.value;
                if (tinyMceEditor) {
                    tinyMceEditor.setContent(htmlContent);
                    // Focus the editor
                    setTimeout(() => {
                        tinyMceEditor.focus();
                    }, 100);
                }
            } else {
                wysiwygContainer.classList.remove('active');
                htmlSourceContainer.classList.add('active');

                // Sync content from TinyMCE to textarea
                if (tinyMceEditor) {
                    const htmlContent = tinyMceEditor.getContent();
                    editorContentEl.value = htmlContent;
                }

                // Focus the textarea
                setTimeout(() => {
                    editorContentEl.focus();
                }, 100);
            }
        }

        // Initialize editor for creating a new (unsaved) page
        function initializeNewPage(parentPath) {
            console.log('initializeNewPage called with parentPath:', parentPath);
            isNewPage = true;
            newPageParentPath = parentPath;

            // Extract the language from the parent path (first segment after /)
            const pathParts = parentPath.split('/').filter(Boolean);
            const language = (pathParts.length > 0 && ['en', 'fr'].includes(pathParts[0])) ? pathParts[0] : 'en';

            // Create a placeholder new page data object
            const newPage = {
                id: 'new-page-' + Date.now(),
                title: 'New Page',
                path: parentPath + '/new-page',
                parent_path: parentPath,
                language: language,
                status: 'draft',
                content: '',
                metadata: {}
            };

            currentPageId = newPage.id;
            currentPageData = newPage;
            window.currentPageData = newPage;

            // Update breadcrumb (wrap in try-catch since new page doesn't exist yet)
            try {
                updateBreadcrumb(newPage);
            } catch (e) {
                console.log('Breadcrumb update skipped for new page:', e.message);
            }

            // Update display
            pageTitleDisplayEl.textContent = 'New Page';
            pageIdDisplayEl.textContent = ' | New Page (unsaved)';
            pageLanguageDisplayEl.textContent = ' | Language: ' + language.toUpperCase();
            pageStatusDisplayEl.textContent = ' | Status: DRAFT';
            filePathDisplayEl.textContent = '';
            lastModifiedDisplayEl.textContent = '';
            pagePublishedDisplayEl.textContent = '';

            // Populate editor with empty content
            editorContentEl.value = '';

            // Also populate TinyMCE if initialized
            if (tinyMceEditor) {
                tinyMceEditor.setContent('');
            }

            // Show editor and actions, hide other states
            hideLoading();
            editorFormEl.style.display = 'block';
            editorActionsEl.style.display = 'block';
            if (savePageTopBtn) savePageTopBtn.style.display = '';
            noPageSelectedEl.style.display = 'none';
            errorAreaEl.style.display = 'none';
            successMessageEl.style.display = 'none';

            // Update URL without reloading
            const url = new URL(window.location);
            url.searchParams.set('pageId', currentPageId);
            window.history.replaceState({}, '', url);

            console.log('New page initialized with parent_path:', parentPath);
        }

        // Load all pages for the tree


        // Build page tree from flat list
        function buildPageTree() {
            // Group pages by parent_path
            const pagesByParent = {};
            window.allPages.forEach(page => {
                const parentId = page.parent_path || 'root';
                if (!pagesByParent[parentId]) {
                    pagesByParent[parentId] = [];
                }
                pagesByParent[parentId].push(page);
            });

            // Build tree for root pages
            let html = '';
            const rootPages = pagesByParent['root'] || pagesByParent[null] || [];

            if (rootPages.length === 0) {
                html = '<div class="loading">No pages found.</div>';
            } else {
                // Sort root pages by title
                if (Array.isArray(rootPages)) {
                    rootPages.sort((a, b) => a.title.localeCompare(b.title));
                }

                // Create categories for each root page with children
                rootPages.forEach(rootPage => {
                    const children = pagesByParent[rootPage.id] || [];
                    const hasChildren = children.length > 0;

                    html += `
                    <div class="tree-category">
                        <div class="tree-category-header ${hasChildren ? '' : 'no-children'}">
                            <span class="page-title" data-page-id="${rootPage.id}">${rootPage.title}</span>
                            ${hasChildren ? '<span class="toggle-icon">▼</span>' : ''}
                        </div>
                        ${hasChildren ? `
                        <div class="tree-category-items">
                            ${children.map(child => `
                                <div class="page-item" data-page-id="${child.id}">
                                    ${child.title}
                                </div>
                            `).join('')}
                        </div>
                        ` : ''}
                    </div>
                    `;
                });
            }

            pageTreeEl.innerHTML = html;

            // Add event listeners
            document.querySelectorAll('.page-item').forEach(item => {
                item.addEventListener('click', function() {
                    const pageId = this.getAttribute('data-page-id');
                    loadPage(pageId);
                });
            });

            // Add event listeners for category headers
            document.querySelectorAll('.tree-category-header').forEach(header => {
                const toggleIcon = header.querySelector('.toggle-icon');
                if (toggleIcon) {
                    header.addEventListener('click', function() {
                        const items = this.nextElementSibling;
                        if (items && items.classList.contains('tree-category-items')) {
                            items.classList.toggle('collapsed');
                            this.classList.toggle('collapsed');
                        }
                    });
                } else {
                    // No children, make header clickable
                    header.addEventListener('click', function() {
                        const pageId = this.querySelector('.page-title').getAttribute('data-page-id');
                        loadPage(pageId);
                    });
                    header.style.cursor = 'pointer';
                }
            });

            // Make root page titles clickable
            document.querySelectorAll('.page-title').forEach(titleEl => {
                titleEl.style.cursor = 'pointer';
                titleEl.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const pageId = this.getAttribute('data-page-id');
                    loadPage(pageId);
                });
            });
        }

        // Get effective file_path for a page, with inheritance from parent pages
        async function getEffectiveFilePath(pageId, maxDepth = 10) {
            console.log('getEffectiveFilePath called for page:', pageId, 'maxDepth:', maxDepth);

            if (maxDepth <= 0) {
                console.warn('Maximum recursion depth reached for file_path inheritance');
                return { file_path: null, source: 'root (max depth reached)' };
            }

            try {
                // Special handling for language roots (en/fr)
                // They exist as pages but only accessible via /by-path endpoint, not by ID
                if (pageId === 'en' || pageId === 'fr') {
                    console.log('Language root detected, fetching via /by-path endpoint:', pageId);
                    // Use path endpoint for language roots
                    const apiUrl = `${API_BASE}/by-path?path=/${pageId}`;
                    const response = await fetch(apiUrl);
                    if (!response.ok) {
                        // If still not found, treat as empty page
                        console.log('Language root not found via /by-path, treating as empty:', pageId);
                        return {
                            file_path: null,
                            source: 'language root (not found)'
                        };
                    }
                    const page = await response.json();

                    // Check if this language root page has file_path
                    if (page.metadata && page.metadata.file_path) {
                        console.log('Found file_path in language root:', page.metadata.file_path);
                        return {
                            file_path: page.metadata.file_path,
                            source: `language root (/${pageId})`
                        };
                    } else {
                        console.log('Language root has no file_path:', pageId);
                        return {
                            file_path: null,
                            source: `language root (no file_path)`
                        };
                    }
                }

                // Fetch the page
                let apiUrl;
                if (pageId.includes('/')) {
                    apiUrl = `${API_BASE}/by-path?path=${encodeURIComponent(pageId)}`;
                } else {
                    apiUrl = `${API_BASE}/${encodeURIComponent(pageId)}`;
                }

                const response = await fetch(apiUrl);
                let page;
                if (!response.ok) {
                    if (response.status === 404) {
                        // Page not found, treat as empty page (e.g., language root)
                        console.log('Page not found (404), treating as empty page:', pageId);
                        page = { metadata: {} };
                    } else {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                } else {
                    page = await response.json();
                }

                // Check if this page has file_path
                if (page.metadata && page.metadata.file_path) {
                    console.log('Found file_path in current page:', page.metadata.file_path);
                    return {
                        file_path: page.metadata.file_path,
                        source: 'current page'
                    };
                }

                // No file_path in current page, check if it has a parent
                if (page.parent_path) {
                    console.log('No file_path in current page, checking parent:', page.parent_path);

                    const parentResult = await getEffectiveFilePath(page.parent_path, maxDepth - 1);

                    if (parentResult.file_path) {
                        // Update source to indicate inheritance
                        return {
                            file_path: parentResult.file_path,
                            source: `inherited from parent (${parentResult.source})`
                        };
                    } else {
                        return {
                            file_path: null,
                            source: `no file_path found in ${maxDepth - 1} parent levels`
                        };
                    }
                } else {
                    // No parent, this is a root page
                    console.log('No file_path and no parent_path, this is a root page');
                    return {
                        file_path: null,
                        source: 'root page (no parent)'
                    };
                }
            } catch (error) {
                console.error('Error getting effective file_path:', error);
                return {
                    file_path: null,
                    source: `error: ${error.message}`
                };
            }
        }

        // Same as getEffectiveFilePath but accepts an already-fetched page object (avoids duplicate API call)
        async function getEffectiveFilePathFromPage(page, maxDepth = 10) {
            if (maxDepth <= 0) {
                return { file_path: null, source: 'root (max depth reached)' };
            }
            try {
                // Check if this page has file_path
                if (page.metadata && page.metadata.file_path) {
                    return { file_path: page.metadata.file_path, source: 'current page' };
                }
                // No file_path, recurse up to parent
                if (page.parent_path) {
                    const parentResult = await getEffectiveFilePath(page.parent_path, maxDepth - 1);
                    if (parentResult.file_path) {
                        return { file_path: parentResult.file_path, source: 'inherited from parent (' + parentResult.source + ')' };
                    }
                    return { file_path: null, source: 'no file_path found in ' + (maxDepth - 1) + ' parent levels' };
                }
                return { file_path: null, source: 'root page (no parent)' };
            } catch (error) {
                return { file_path: null, source: 'error: ' + error.message };
            }
        }

        // Update FileBot target folder display
        function updateFileBotTargetFolder(filePathInfo) {
            const folderPathEl = document.getElementById('filebot-target-folder-path');
            const folderSourceEl = document.getElementById('folder-source-text');
            console.log('updateFileBotTargetFolder called with:', filePathInfo);
            console.log('Elements found:', !!folderPathEl, !!folderSourceEl);

            if (!folderPathEl || !folderSourceEl) {
                console.debug('FileBot target folder elements not found (not present in this HTML revision)');
                return;
            }

            if (filePathInfo.file_path) {
                // Show the effective file_path
                folderPathEl.textContent = filePathInfo.file_path;
                folderPathEl.style.color = '#2e7d32';
                folderPathEl.style.fontWeight = 'normal';

                // Show the source (inheritance info)
                folderSourceEl.textContent = `Source: ${filePathInfo.source}`;

                // Update icon based on source
                const folderSourceContainer = document.getElementById('filebot-folder-source');
                if (folderSourceContainer) {
                    const icon = folderSourceContainer.querySelector('.folder-source-icon');
                    if (icon) {
                        if (filePathInfo.source.includes('inherited')) {
                            icon.textContent = '↰';
                            icon.style.color = '#ff9800';
                        } else {
                            icon.textContent = '↳';
                            icon.style.color = '#9e9e9e';
                        }
                    }
                }

                // Store current folder path for uploads
                window.currentFileBotFolder = filePathInfo.file_path;

                // Load recent documents from this target folder
                loadRecentDocumentsFromTargetFolder(filePathInfo.file_path);
            } else {
                // No file_path found
                let displayText = 'No target folder configured';
                if (filePathInfo.source && filePathInfo.source.includes('language root')) {
                    displayText = 'Language root (no file_path)';
                }
                folderPathEl.innerHTML = `<em style="color: #757575;">${displayText}</em>`;
                folderSourceEl.textContent = `Inheritance: ${filePathInfo.source}`;

                // Clear current folder and load documents from root
                window.currentFileBotFolder = null;
                loadRecentDocumentsFromTargetFolder(null);
            }
        }



        // Helper function to get folder ID from folder path
        async function getFolderIdFromPath(folderPath) {
            if (!folderPath) return null;

            try {
                console.log(`Looking up folder ID for path: ${folderPath}`);

                // 尝试直接通过路径获取文件夹信息
                // 使用新的文件夹路径端点
                const response = await fetch(`${URL_CONFIG.filebot.folders}/by-path/${encodeURIComponent(folderPath)}`, {
                    headers: {
                        'Authorization': `Bearer ${FILEBOT_JWT_TOKEN}`
                    }
                });

                if (response.ok) {
                    const folder = await response.json();
                    console.log(`Found folder ID ${folder.id} for path: ${folderPath}`);
                    return folder.id;
                } else if (response.status === 404) {
                    // 文件夹不存在,但我们不在这里创建它
                    // 创建文件夹应该在FileBot端处理(当通过路径上传文档时)
                    console.warn(`Folder not found for path: ${folderPath}`);
                    return null;
                } else {
                    console.warn(`Failed to fetch folder: HTTP ${response.status}`);
                    return null;
                }
            } catch (error) {
                console.error('Error fetching folder:', error);
                return null;
            }
        }

        // Helper function to check if file type is an image
        function isImageFile(fileType, fileName) {
            const type = (fileType || '').toLowerCase();
            const name = (fileName || '').toLowerCase();
            const imageTypes = ['image', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'];
            const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'];

            // Check file type
            for (const imgType of imageTypes) {
                if (type.includes(imgType)) return true;
            }

            // Check file extension
            for (const ext of imageExtensions) {
                if (name.endsWith(ext)) return true;
            }

            return false;
        }

        // Helper function to extract public URL from document metadata
        function getPublicUrlFromDocument(doc) {
            console.log('getPublicUrlFromDocument called with doc:', doc ? {
                id: doc.id,
                hasDocumentMetadata: !!doc.document_metadata,
                publish_status: doc.publish_status,
                hasStoredFilename: !!doc.stored_filename,
                hostname: window.location.hostname
            } : null);

            // First try to get URL from document_metadata
            if (doc && doc.document_metadata) {
                try {
                    const metadata = typeof doc.document_metadata === 'string'
                        ? JSON.parse(doc.document_metadata)
                        : doc.document_metadata;

                    const url = metadata.url || metadata.original_url;
                    console.log('Extracted URL from metadata:', url);
                    if (url) {
                        // If URL is already a full URL (http/https), return it directly
                        // This could be a CDN URL or external service URL
                        if (url.startsWith('http://') || url.startsWith('https://')) {
                            console.log('Returning full URL from metadata:', url);
                            return url;
                        } else {
                            // URL is a path (e.g., "/1c7dd921-...")
                            let path = url.startsWith('/') ? url : '/' + url;

                            // Always use WebBot proxy path /content/dam/ for better security
                            // This hides FileBot backend and provides unified access control
                            console.log('Using WebBot proxy path:', `/content/dam${path}`);
                            return `/content/dam${path}`;  // Proxy through WebBot for security
                        }
                    }
                } catch (error) {
                    console.warn('Failed to extract public URL from document metadata:', error);
                }
            }

            // Fallback: if document is published but has no metadata URL, try stored_filename
            if (doc && doc.publish_status === 'PUBLISHED' && !doc.document_metadata && doc.stored_filename) {
                console.log('Document is published but has no metadata URL, using stored_filename:', doc.stored_filename);

                // Always use WebBot proxy path for better security
                return `/content/dam/${doc.stored_filename}`;
            }

            // Fallback 2: if no stored_filename but document is published, try using ID
            if (doc && doc.publish_status === 'PUBLISHED' && doc.id) {
                console.log('Document is published but has no stored_filename, trying ID:', doc.id);

                // Always use WebBot proxy path for better security
                return `/content/dam/${doc.id}`;
            }

            console.log('No public URL available for document');
            return null;
        }

        // Helper function to get image thumbnail URL from document
        function getImageThumbnailUrl(doc) {
            if (!doc) return null;

            // First try to get public URL from document metadata
            const publicUrl = getPublicUrlFromDocument(doc);
            if (publicUrl) {
                console.log('getImageThumbnailUrl: Using public URL from getPublicUrlFromDocument:', publicUrl);
                return publicUrl;
            }

            // Fallback: construct /content/dam/ URL using stored_filename or id
            // Always use WebBot proxy path for unified access control
            if (doc.stored_filename) {
                const proxyUrl = `/content/dam/${doc.stored_filename}`;
                console.log('getImageThumbnailUrl: Using proxy URL with stored_filename:', proxyUrl);
                return proxyUrl;
            }

            // Last resort: use ID with /content/dam/ proxy
            if (doc.id) {
                const proxyUrl = `/content/dam/${doc.id}`;
                console.log('getImageThumbnailUrl: Using proxy URL with document ID:', proxyUrl);
                return proxyUrl;
            }

            console.warn('getImageThumbnailUrl: No URL available for document');
            return null;
        }

        // Load recent documents from target folder in FileBot sidepanel
        async function loadRecentDocumentsFromTargetFolder(folderPath) {
            console.log('Loading recent documents for folder:', folderPath || 'root');

            const sidebarEl = document.getElementById('filebot-documents-sidebar');
            if (!sidebarEl) {
                console.warn('FileBot documents sidebar element not found');
                return;
            }

            // Show loading
            sidebarEl.innerHTML = '<li class="filebot-document-item-sidebar"><em>Loading documents...</em></li>';

            let apiUrl = ''; // Declare outside try block for error logging

            try {
                // 直接使用文件夹路径,不尝试获取folderId
                // FileBot API应该支持folder_path参数

                // Build API URL using environment-aware base
                apiUrl = URL_CONFIG.filebot.documents;
                const params = new URLSearchParams();

                if (folderPath) {
                    // 直接使用folder_path参数
                    params.append('folder_path', folderPath);
                    console.log(`Filtering documents by folder_path: ${folderPath}`);
                }

                if (params.toString()) {
                    apiUrl += '?' + params.toString();
                }

                const response = await fetch(apiUrl, {
                    headers: {
                        'Authorization': `Bearer ${FILEBOT_JWT_TOKEN}`
                    }
                });

                if (!response.ok) {
                    // 如果API不支持folder_path参数,尝试备用方法
                    if (folderPath && response.status === 400) {
                        console.warn(`folder_path参数可能不被支持,尝试备用方法`);
                        // 这里可以尝试获取folderId,但我们应该优先修复API而不是这里
                        throw new Error(`FileBot API不支持folder_path参数`);
                    }
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                let documentsData = await response.json();

                // Ensure documents is an array
                let documents = [];
                if (Array.isArray(documentsData)) {
                    documents = documentsData;
                } else if (documentsData && documentsData.documents) {
                    // Handle case where API returns {documents: [...]}
                    documents = Array.isArray(documentsData.documents) ? documentsData.documents : [];
                } else if (documentsData && documentsData.items) {
                    // Handle case where API returns {items: [...]}
                    documents = Array.isArray(documentsData.items) ? documentsData.items : [];
                } else if (documentsData && typeof documentsData === 'object') {
                    // Single document object
                    documents = [documentsData];
                }

                console.log(`Loaded ${documents.length || 0} documents for folder: ${folderPath || 'root'}`);

                // 注意:不再需要客户端过滤,因为API应该已经正确过滤

                // Update sidebar with documents
                if (!documents || documents.length === 0) {
                    sidebarEl.innerHTML = '<li class="filebot-document-item-sidebar"><em>No documents in this folder</em></li>';
                    return;
                }

                // Sort by created_at (newest first) and take up to 10
                const recentDocs = Array.isArray(documents) ? documents
                    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
                    .slice(0, 10) : [];

                let html = '';
                const docDataArray = []; // Store docData for each document
                recentDocs.forEach((doc, index) => {
                    // Use title first, then original_filename, then fallback
                    const docName = doc.title || doc.original_filename || doc.name || doc.filename || 'Unnamed document';
                    const docType = doc.file_type || 'file';
                    const docDate = doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '';
                    const isImage = isImageFile(docType, doc.original_filename || docName);

                    // Prepare document data for dataset
                    const docData = {
                        id: doc.id,
                        original_filename: doc.original_filename || '',
                        mime_type: doc.mime_type || '',
                        file_type: doc.file_type || 'file',
                        document_metadata: doc.document_metadata || null,
                        title: doc.title || '',
                        stored_filename: doc.stored_filename || ''
                    };
                    docDataArray[index] = docData;

                    // Generate icon HTML based on file type
                    let iconHtml = '';
                    if (isImage) {
                        // For images, create img tag with thumbnail URL
                        const thumbnailUrl = getImageThumbnailUrl(doc);
                        iconHtml = `<img src="${thumbnailUrl}" alt="${escapeHtml(docName)}" class="filebot-thumbnail responvise" style="border-radius: 3px; object-fit: cover;">`;
                    } else {
                        // For non-images, use emoji icon
                        const docIcon = getFileIconEmoji(docType);
                        iconHtml = `<span class="filebot-document-icon-emoji">${docIcon}</span>`;
                    }

                    html += `
                    <li class="filebot-document-item-sidebar"
                         data-document-id="${doc.id}"
                         data-doc-index="${index}"
                         data-is-image="${isImage}">
                        <div class="filebot-document-icon">${iconHtml}</div>
                        <div class="filebot-document-details">
                            <div class="filebot-document-name">${escapeHtml(docName)}</div>
                            <div class="filebot-document-meta">
                                <span class="filebot-document-type">${docType}</span>
                                ${docDate ? `<span class="filebot-document-date">${docDate}</span>` : ''}
                            </div>
                        </div>
                        <button class="filebot-document-insert" title="Insert into editor">+</button>
                    </li>`;
                });

                sidebarEl.innerHTML = html;

                // Set documentData on each element (bypass HTML escaping issues)
                sidebarEl.querySelectorAll('.filebot-document-item-sidebar').forEach((item, index) => {
                    if (docDataArray[index]) {
                        item.dataset.documentData = JSON.stringify(docDataArray[index]);
                    }
                });

                // Add click events for insert buttons and icons
                sidebarEl.querySelectorAll('.filebot-document-insert, .filebot-document-icon').forEach(element => {
                    element.addEventListener('click', function(e) {
                        // Stop propagation to prevent multiple triggers if icon contains button
                        e.stopPropagation();

                        const documentItem = this.closest('.filebot-document-item-sidebar');
                        const documentId = documentItem.dataset.documentId;
                        const documentName = documentItem.querySelector('.filebot-document-name').textContent;
                        const documentType = documentItem.querySelector('.filebot-document-type').textContent;

                        // Parse stored document data
                        let originalDocument = null;
                        try {
                            if (documentItem.dataset.documentData) {
                                originalDocument = JSON.parse(documentItem.dataset.documentData);
                                console.log('Loaded originalDocument from sidebar data:', originalDocument);
                            }
                        } catch (e) {
                            console.warn('Failed to parse documentData:', e);
                        }

                        // Construct download URL
                        const downloadUrl = URL_CONFIG.filebot.documentDownload(documentId);

                        // If we have original_filename from originalDocument, use it for documentName
                        const finalDocumentName = originalDocument?.original_filename || documentName;
                        const finalDocumentType = originalDocument?.mime_type || documentType;

                        console.log('Inserting from sidebar (clicked:', this.className, '):', {
                            documentId,
                            finalDocumentName,
                            finalDocumentType,
                            hasOriginalDocument: !!originalDocument
                        });

                        insertFileBotDocument(documentId, finalDocumentName, finalDocumentType, downloadUrl, originalDocument);
                    });
                });

            } catch (error) {
                console.error('Error loading recent documents:', error);
                console.error('Error details - folderPath:', folderPath, 'apiUrl:', apiUrl);
                // Show more detailed error for debugging
                const errorMessage = error.message || 'Unknown error';
                const safeMessage = escapeHtml(errorMessage.length > 100 ? errorMessage.substring(0, 100) + '...' : errorMessage);
                sidebarEl.innerHTML = `<div class="filebot-document-item-sidebar"><em style="color: #d32f2f;">Error loading documents: ${safeMessage}</em></div>`;
            }
        }

        // Helper function to escape HTML
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Helper function to get emoji icon for file type (for sidebar)
        function getFileIconEmoji(fileType) {
            const type = (fileType || '').toLowerCase();
            if (type.includes('pdf')) return '📕';
            if (type.includes('doc') || type.includes('word')) return '📄';
            if (type.includes('excel') || type.includes('sheet')) return '📊';
            if (type.includes('image')) return '🖼️';
            if (type.includes('video')) return '🎬';
            if (type.includes('audio')) return '🎵';
            return '📄';
        }

        // Language switcher functions
        function detectCurrentLanguage() {
            // Try to get language from current page data (most reliable)
            if (currentPageData && currentPageData.language) {
                return currentPageData.language.toLowerCase();
            }

            // Try to extract from currentPageId (path)
            if (currentPageId) {
                const path = currentPageId.startsWith('/') ? currentPageId : `/${currentPageId}`;

                // Method 1: Look for language code pattern in the path
                // Language codes are typically 2-3 letters (en, fr, es, etc.)
                const langMatch = path.match(/\/([a-z]{2,3})\//i);
                if (langMatch && langMatch[1]) {
                    return langMatch[1].toLowerCase();
                }

                // Method 2: Check individual path parts
                const parts = path.split('/').filter(p => p.trim() !== '');
                for (const part of parts) {
                    if (/^[a-z]{2,3}$/i.test(part)) {
                        return part.toLowerCase();
                    }
                }
            }

            // Default to English
            return 'en';
        }

        function getAvailableLanguages() {
            const languages = new Set(['en', 'fr']); // Default languages

            // Try to get languages from allPages
            if (window.allPages && window.allPages.length > 0) {
                window.allPages.forEach(page => {
                    if (page.language) {
                        languages.add(page.language.toLowerCase());
                    }
                });
            }

            // Also check root pages (pages with parent_path null or empty)
            if (window.allPages && window.allPages.length > 0) {
                window.allPages.forEach(page => {
                    if (!page.parent_path || page.parent_path === '') {
                        // Try to extract language from path
                        const path = page.path || '';
                        const parts = path.split('/').filter(p => p.trim() !== '');
                        if (parts.length === 1 && /^[a-z]{2,3}$/.test(parts[0].toLowerCase())) {
                            languages.add(parts[0].toLowerCase());
                        }
                    }
                });
            }

            return Array.from(languages).sort();
        }

        function populateLanguageSwitcher() {
            const languageSwitcher = document.getElementById('language-switcher');
            const languageLink = document.getElementById('language-link');

            if (!languageSwitcher || !languageLink) {
                console.warn('Language switcher elements not found');
                return;
            }

            // Only show if we have a current page with other_language_path
            if (!currentPageData || !currentPageData.other_language_path) {
                languageSwitcher.style.display = 'none';
                return;
            }

            const otherPath = currentPageData.other_language_path;
            const currentLang = (currentPageData.language || 'en').toLowerCase();

            // Determine correct editor URL base
            let baseUrl = '/editor.html';
            if (window.location.pathname.includes('/static/editor.html')) {
                baseUrl = '/static/editor.html';
            }

            languageLink.href = baseUrl + '?path=' + encodeURIComponent(otherPath);
            languageLink.textContent = currentLang === 'en' ? 'Français' : 'English';
            languageSwitcher.style.display = 'inline-block';
        }

        function switchToLanguage(lang) {
            if (!currentPageId || !lang) return;
            console.warn('switchToLanguage is deprecated, using language link instead');
        }

        // Initialize language switcher (now handled by populateLanguageSwitcher)
        function initLanguageSwitcher() {
            // No-op: language switcher driven by populateLanguageSwitcher() on page load
        }

        // Load a specific page
        async function loadPage(pageId) {
            console.log('loadPage called with:', pageId, 'type:', typeof pageId);
            currentPageId = pageId;

            // Show loading, hide other content
            showLoading();

            try {
                let apiUrl;
                if (pageId.includes('/')) {
                    // It's a path, use the by-path endpoint
                    apiUrl = `${API_BASE}/by-path?path=${encodeURIComponent(pageId)}`;
                    console.log('Using path API endpoint:', apiUrl);
                } else {
                    // It's a page ID
                    apiUrl = `${API_BASE}/${encodeURIComponent(pageId)}`;
                    console.log('Using pageId API endpoint:', apiUrl);
                }
                console.log('Fetching API...');
                const response = await fetch(apiUrl);
                console.log('API response status:', response.status, response.statusText);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                const page = await response.json();
                console.log('API response data received, page id:', page?.id, 'title:', page?.title);
                console.log('Page object keys:', Object.keys(page || {}));
                console.log('Page content type:', typeof page?.content, 'length:', page?.content?.length);
                if (!page) {
                    throw new Error('Page object is null or undefined from API');
                }

                // Store page data
                currentPageData = page;
                window.currentPageData = page;

                // Update breadcrumb
                await updateBreadcrumb(page);

                // Update pages sidebar based on current page path
                // Only show pages when a third-level (department) page is selected
                const pagePath = page.path || page.id;
                loadPagesForSidebar(pagePath);

                // Update display
                pageTitleDisplayEl.textContent = page.title || 'Untitled';
                pageLanguageDisplayEl.textContent = ` | Language: ${page.language ? page.language.toUpperCase() : 'EN'}`;
                pageStatusDisplayEl.textContent = ` | Status: ${page.status || 'draft'}`;
                lastModifiedDisplayEl.textContent = formatLastModified(page.last_modified);
                pagePublishedDisplayEl.textContent = formatPublishedAt(page.last_published);

                // Update language switcher
                populateLanguageSwitcher();
                // Update translate button visibility
                if (window.updateTranslateBtn) window.updateTranslateBtn();

                // Extract language links and metadata from page content head section
                if (page.content && typeof page.content === 'string') {
                    metadataManager.extractAndStore(page.content);
                }

                // Get file_path from URL parameter
                const urlParams = new URLSearchParams(window.location.search);
                const filePathFromUrl = urlParams.get('file_path');

                // Update path display (priority: URL parameter > page.path > page id)
                if (filePathFromUrl) {
                    pageIdDisplayEl.textContent = ` | Path: ${filePathFromUrl}`;
                } else if (page.path) {
                    pageIdDisplayEl.textContent = ` | Path: ${page.path}`;
                } else {
                    pageIdDisplayEl.textContent = ` | ID: ${page.id}`;
                }
                filePathDisplayEl.textContent = '';
                filePathDisplayEl.style.color = '';
                filePathDisplayEl.style.fontWeight = '';
                filePathDisplayEl.title = '';
                lastModifiedDisplayEl.textContent = formatLastModified(page.last_modified);
                pagePublishedDisplayEl.textContent = formatPublishedAt(page.last_published);

                // Update FileBot target folder display
                try {
                    // Determine effective file_path for FileBot
                    let effectiveFilePathInfo;

                    // Priority 1: URL parameter (explicit override)
                    if (filePathFromUrl) {
                        effectiveFilePathInfo = {
                            file_path: filePathFromUrl,
                            source: 'URL parameter (explicit override)'
                        };
                        console.log('Using file_path from URL parameter for FileBot:', filePathFromUrl);
                    }
                    // Priority 2: Inherited file_path from page hierarchy
                    else {
                        effectiveFilePathInfo = await getEffectiveFilePathFromPage(page);
                        console.log('Using inherited file_path for FileBot:', effectiveFilePathInfo);
                    }

                    // Update the FileBot sidebar display
                    updateFileBotTargetFolder(effectiveFilePathInfo);

                    // Store the effective file_path for upload operations
                    window.currentFileBotFolder = effectiveFilePathInfo.file_path;

                } catch (error) {
                    console.error('Error updating FileBot target folder:', error);
                    // Fallback display
                    updateFileBotTargetFolder({
                        file_path: null,
                        source: `error: ${error.message}`
                    });
                }

                // Clean the page content to remove header/footer before editing
                console.log('Calling cleanContent with content length:', page.content?.length);
                const cleanedContent = cleanContent(page.content || '', pageId);
                console.log('cleanContent returned, length:', cleanedContent?.length);

                // Populate form with cleaned content
                // editorTitleEl.value = page.title || ''; // Title field removed from UI
                editorContentEl.value = cleanedContent;
                // editorLanguageEl.value = page.language || 'en'; // Language field removed from UI
                // editorStatusEl.value = page.status || 'draft'; // Status field removed from UI

                // Also populate TinyMCE editor if initialized
                if (tinyMceEditor) {
                    try {
                        tinyMceEditor.setContent(cleanedContent);
                    } catch (e) {
                        console.warn('TinyMCE setContent failed (non-fatal):', e);
                    }
                }

                // Update page content in currentPageData to cleaned version
                page.content = cleanedContent;

                // Show editor and actions, hide other states
                hideLoading();
                editorFormEl.style.display = 'block';
                editorActionsEl.style.display = 'block';
                if (savePageTopBtn) savePageTopBtn.style.display = '';
                noPageSelectedEl.style.display = 'none';
                errorAreaEl.style.display = 'none';
                successMessageEl.style.display = 'none';

                // Update URL without reloading
                const url = new URL(window.location);
                url.searchParams.set('pageId', pageId);
                window.history.replaceState({}, '', url);

                console.log(`Loaded page: ${page.title}`);

                // Check if autoPreview is requested
                if (urlParams.get('autoPreview') === 'true') {
                    // Remove autoPreview from URL to avoid repeated triggers
                    const url = new URL(window.location);
                    url.searchParams.delete('autoPreview');
                    window.history.replaceState({}, '', url);

                    // Trigger preview after a short delay to ensure UI is ready
                    setTimeout(() => {
                        previewPage();
                    }, 500);
                }
            } catch (error) {
                console.error('Error loading page:', error);
                console.error('Error stack:', error.stack);
                console.error('Error occurred in loadPage with pageId:', pageId);
                showError(`Failed to load page: ${error.message}`);
            }
        }

        // Generate editor URL for a page path
        function getEditorUrl(pagePath) {
            // Remove .html or .HTML extension for consistency with API
            const cleanPath = removeHtmlExtension(pagePath);
            return `editor.html?pageId=${encodeURIComponent(cleanPath)}`;
        }

        // Update breadcrumb navigation
        async function updateBreadcrumb(page) {
            console.log('updateBreadcrumb called for page:', page.id, 'title:', page.title);

            // Show loading state in breadcrumb
            breadcrumbEl.innerHTML = `
                <div class="breadcrumb-item">
                    <a href="navigation.html?path=${encodeURIComponent(page.path)}" id="home-link">Canadasite</a>
                </div>
                <div class="breadcrumb-item">Loading breadcrumb...</div>
            `;

            try {
                // Build breadcrumb path by traversing up the hierarchy
                const breadcrumbPath = await buildBreadcrumbPath(page);

                // Debug: log breadcrumb path details
                console.log('breadcrumbPath length:', breadcrumbPath.length);
                breadcrumbPath.forEach((p, idx) => {
                    console.log(`  [${idx}] id: ${p.id}, path: "${p.path}", language: ${p.language}, title: "${p.title}"`);
                });

                // Render breadcrumb
                let breadcrumbHtml = `
                    <div class="breadcrumb-item">
                        <a href="navigation.html?path=${encodeURIComponent(page.path)}" id="home-link">Canadasite</a>
                    </div>
                `;

                // Add intermediate pages (except the current page which will be added as active)
                // Skip the first breadcrumbPath item if it's a root-level page (avoids "Canadasite > canadasite" or "Canadasite > Home" duplicates)
                for (let i = 0; i < breadcrumbPath.length - 1; i++) {
                    if (i === 0 && breadcrumbPath[0].title && SKIP_BREADCRUMB_TITLES.includes(breadcrumbPath[0].title.toLowerCase())) {
                        continue;
                    }
                    const ancestor = breadcrumbPath[i];
                    // Pass only the path up to this ancestor (slice 0 to i+1)
                    const ancestorPath = buildFullPath(ancestor, breadcrumbPath.slice(0, i + 1));
                    const editorUrl = getEditorUrl(ancestorPath);
                    const ancestorTitle = cleanTitle(ancestor.title) || ancestor.id;
                    breadcrumbHtml += `
                        <div class="breadcrumb-item">
                            <a href="${editorUrl}" class="breadcrumb-link" data-page-path="${removeHtmlExtension(ancestorPath)}">${ancestorTitle}</a>
                        </div>
                    `;
                }

                // Add current page as active (last in array)
                if (breadcrumbPath.length > 0) {
                    const currentPage = breadcrumbPath[breadcrumbPath.length - 1];
                    const currentPagePath = buildFullPath(currentPage, breadcrumbPath);
                    breadcrumbHtml += `
                        <div class="breadcrumb-item active">${cleanTitle(currentPage.title) || currentPage.id}</div>
                    `;
                } else {
                    // Fallback if no breadcrumb path (shouldn't happen)
                    breadcrumbHtml += `
                        <div class="breadcrumb-item active">${cleanTitle(page.title) || page.id}</div>
                    `;
                }

                breadcrumbEl.innerHTML = breadcrumbHtml;

                // No event listener - home-link now naturally navigates to navigation.html

                // Add click events for breadcrumb links
                document.querySelectorAll('.breadcrumb-link').forEach(link => {
                    link.addEventListener('click', function(e) {
                        e.preventDefault();
                        // Get path from data-page-path attribute (contains the actual page path)
                        let pagePath = this.getAttribute('data-page-path');
                        if (pagePath) {
                            loadPage(pagePath);
                        }
                    });
                });

                console.log('Breadcrumb updated with', breadcrumbPath.length, 'levels');
            } catch (error) {
                console.error('Error building breadcrumb:', error);
                // Fallback to simple breadcrumb
                breadcrumbEl.innerHTML = `
                    <div class="breadcrumb-item">
                        <a href="navigation.html?path=${encodeURIComponent(page.path)}" id="home-link">Canadasite</a>
                    </div>
                    <div class="breadcrumb-item active">${cleanTitle(page.title) || page.id}</div>
                `;

                // No event listener needed - home-link navigates naturally to navigation.html
            }
        }

        // Build breadcrumb path by traversing up the page hierarchy
        async function buildBreadcrumbPath(startPage) {
            // Use the parents endpoint for a single API call
            if (startPage && startPage.path) {
                try {
                    const resp = await fetch(`${API_BASE}/parents?path=${encodeURIComponent(startPage.path)}`);
                    if (resp.ok) {
                        const data = await resp.json();
                        const parents = data.parents || [];
                        const page = data.page;
                        if (page) {
                            const path = [...parents, page];
                            console.log('Built breadcrumb path via /parents endpoint:', path.length, 'pages:', path.map(p => p.id));
                            return path;
                        }
                    }
                } catch (e) {
                    console.warn('Parents endpoint failed, falling back to manual traversal:', e);
                }
            }

            // Fallback: manual traversal
            const path = [startPage];
            let currentPage = startPage;
            while (currentPage && currentPage.parent_path) {
                try {
                    let parentPage = null;
                    if (currentPage.path) {
                        const currentPath = currentPage.path;
                        const lastSlashIndex = currentPath.lastIndexOf('/');
                        if (lastSlashIndex > 0) {
                            const parentPath = currentPath.substring(0, lastSlashIndex) || '/';
                            const parentResponse = await fetch(`${API_BASE}/by-path?path=${encodeURIComponent(parentPath)}`);
                            if (parentResponse.ok) {
                                parentPage = await parentResponse.json();
                            }
                        }
                    }
                    if (!parentPage) {
                        console.warn(`Unable to fetch parent page ${currentPage.parent_path}, stopping breadcrumb`);
                        break;
                    }
                    if (parentPage.hide_in_navigation !== true) {
                        path.unshift(parentPage);
                    }
                    currentPage = parentPage;
                } catch (error) {
                    console.error(`Error fetching parent ${currentPage.parent_path}:`, error);
                    break;
                }
            }
            console.log('Built breadcrumb path (fallback) with', path.length, 'pages');
            return path;
        }

        // Get hierarchical path for a page (like getPathToPage in navigation.html)
        function getPathToPage(pageObject) {
            console.log('getPathToPage called with page object:', pageObject?.id);
            if (!pageObject || !pageObject.id) {
                console.error('Invalid page object provided to getPathToPage');
                return [pageObject?.id || 'unknown'];
            }

            // Check if allPages is available
            if (!window.allPages || window.allPages.length === 0) {
                console.log('  getPathToPage: allPages not available, returning page ID only');
                return [pageObject.id];
            }

            const path = [];
            let currentPage = pageObject;

            while (currentPage && currentPage.id) {
                // Add current page ID to path
                path.unshift(currentPage.id);
                console.log(`  getPathToPage: Added ${currentPage.id} to path. Full path:`, path);

                // If this page has no parent, we've reached the root
                if (!currentPage.parent_path) {
                    console.log('  getPathToPage: Reached root page (no parent_path)');
                    break;
                }

                // Find the parent page in allPages array
                const parentCandidates = window.allPages.filter(p => p.id === currentPage.parent_path);
                console.log(`  getPathToPage: Looking for parent page id=${currentPage.parent_path}: ${parentCandidates.length} candidates`);

                if (parentCandidates.length === 0) {
                    console.log(`  getPathToPage: Parent page ${currentPage.parent_path} not found, stopping`);
                    break;
                }

                // Take the first parent candidate
                const parentPage = parentCandidates[0];

                // Move up to parent
                currentPage = parentPage;
            }

            console.log('getPathToPage returning path array:', path);
            return path;
        }

        // Build full path for a page given its breadcrumb path
        function buildFullPath(page, breadcrumbPath) {
            console.log('buildFullPath called for page:', page.id, 'page.path:', page.path, 'page.language:', page.language, 'breadcrumbPath length:', breadcrumbPath?.length);

            // Debug: log breadcrumbPath details
            if (breadcrumbPath && breadcrumbPath.length > 0) {
                console.log('  breadcrumbPath details:');
                breadcrumbPath.forEach((p, idx) => {
                    console.log(`    [${idx}] id: ${p.id}, path: "${p.path}", language: ${p.language}, title: "${p.title}"`);
                });
            }

            // Priority 1: Use page.path if available
            if (page.path && page.path.trim() !== '') {
                let path = page.path;
                // Ensure path starts with /
                if (!path.startsWith('/')) {
                    path = '/' + path;
                }
                // Ensure .html extension is lowercase (if present)
                if (path.endsWith('.HTML')) {
                    path = path.replace(/\.HTML$/, '.html');
                }
                console.log('  -> Priority 1: Using page.path:', path);
                return path;
            }

            // Priority 2: Use getPathToPage to build hierarchical path from allPages
            // This ensures each page gets its own correct hierarchical path
            if (page.language && window.allPages && window.allPages.length > 0) {
                // Get hierarchical path for this specific page
                const hierarchicalPath = getPathToPage(page);
                console.log('  -> getPathToPage returned:', hierarchicalPath);

                if (hierarchicalPath && hierarchicalPath.length > 0) {
                    let pathParts = [];

                    // Add language as prefix if not already first element
                    if (hierarchicalPath[0] !== page.language) {
                        pathParts.push(page.language);
                    }

                    // Add all path elements
                    pathParts = pathParts.concat(hierarchicalPath);

                    // Construct full path
                    const basePath = '/' + pathParts.join('/');

                    // Add .html extension if not already present (lowercase)
                    let finalPath = basePath;
                    if (!basePath.toLowerCase().endsWith('.html')) {
                        finalPath = basePath + '.html';
                    }

                    // Ensure extension is lowercase
                    if (finalPath.endsWith('.HTML')) {
                        finalPath = finalPath.replace(/\.HTML$/, '.html');
                    }

                    console.log('  -> Priority 2: Built hierarchical path using getPathToPage:', finalPath, 'from parts:', pathParts);
                    return finalPath;
                }
            } else if (page.language) {
                console.log('  -> Priority 2: Skipped - allPages not available or empty');
            }

            // Priority 3: Use page.language and page.id if available (fallback)
            if (page.language) {
                const path = `/${page.language}/${page.id}.html`;
                console.log('  -> Priority 3: Using simple language+id path:', path);
                return path;
            }

            // Priority 4: Fallback to hierarchical path based on breadcrumb
            // Find the index of this page in the breadcrumb path
            const pageIndex = breadcrumbPath?.findIndex(p => p.id === page.id) ?? -1;
            if (pageIndex === -1 || !breadcrumbPath || breadcrumbPath.length === 0) {
                const path = `/${page.id}.html`; // Fallback with .html extension (lowercase)
                console.log('  -> Priority 4: Fallback to page.id path:', path);
                return path;
            }

            // Build path from root to this page
            const pathParts = [];
            for (let i = 0; i <= pageIndex; i++) {
                pathParts.push(breadcrumbPath[i].id);
            }

            // Construct full path with .html extension
            const basePath = '/' + pathParts.join('/');

            // Special handling for root path
            if (basePath === '/') {
                console.log('  -> Priority 4: Root path, returning /index.html');
                return '/index.html';
            }

            // Add .html extension if not already present (lowercase)
            let finalPath = basePath;
            if (!basePath.toLowerCase().endsWith('.html')) {
                finalPath = basePath + '.html';
            }

            // Ensure extension is lowercase
            if (finalPath.endsWith('.HTML')) {
                finalPath = finalPath.replace(/\.HTML$/, '.html');
            }

            console.log('  -> Priority 4: Hierarchical path:', finalPath);
            return finalPath;
        }

        // Remove .HTML extension from a path for API calls
        function removeHtmlExtension(path) {
            if (!path) return path;
            // Remove .HTML or .html extension
            return path.replace(/\.HTML$/i, '');
        }

        // Generate breadcrumb HTML for preview pages
        async function generateBreadcrumbHTML(page) {
            console.log('generateBreadcrumbHTML called for page:', page.id, 'title:', page.title);

            try {
                // Build breadcrumb path
                const breadcrumbPath = await buildBreadcrumbPath(page);

                if (breadcrumbPath.length === 0) {
                    return ''; // Return empty if no breadcrumb
                }

                // Generate breadcrumb HTML
                let breadcrumbHtml = '';

                // Add Canadasite root link
                breadcrumbHtml += `<li><a href="navigation.html?path=${encodeURIComponent(page.path)}">Canadasite</a></li>`;

                // Add intermediate pages (except the current page)
                // Skip the first breadcrumbPath item if it's a root-level page
                for (let i = 0; i < breadcrumbPath.length - 1; i++) {
                    if (i === 0 && breadcrumbPath[0].title && SKIP_BREADCRUMB_TITLES.includes(breadcrumbPath[0].title.toLowerCase())) {
                        continue;
                    }
                    const ancestor = breadcrumbPath[i];
                    // Pass only the path up to this ancestor (slice 0 to i+1)
                    const ancestorPath = buildFullPath(ancestor, breadcrumbPath.slice(0, i + 1));
                    const ancestorTitle = cleanTitle(ancestor.title) || ancestor.id;
                    breadcrumbHtml += `<li><a href="${ancestorPath}">${escapeHtml(ancestorTitle)}</a></li>`;
                }

                // Add current page as active (last in array)
                const currentPage = breadcrumbPath[breadcrumbPath.length - 1];
                const currentPagePath = buildFullPath(currentPage, breadcrumbPath);
                const cleanedTitle = cleanTitle(currentPage.title) || currentPage.id;
                const currentPageTitle = escapeHtml(cleanedTitle);

                // Skip adding current page if it's a root-level page
                if (!SKIP_BREADCRUMB_TITLES.includes(cleanedTitle.toLowerCase())) {
                    breadcrumbHtml += `<li class="active">${currentPageTitle}</li>`;
                }

                // Wrap in nav element (Canada.ca breadcrumb structure)
                const fullBreadcrumbHtml = `
<nav role="navigation" id="wb-bc" property="breadcrumb">
    <h2 class="wb-inv">You are here:</h2>
    <div class="container">
        <div class="row">
            <ol class="breadcrumb">
                ${breadcrumbHtml}
            </ol>
        </div>
    </div>
</nav>`;

                console.log('Generated breadcrumb HTML with', breadcrumbPath.length, 'levels');
                return fullBreadcrumbHtml;

            } catch (error) {
                console.error('Error generating breadcrumb HTML:', error);
                return ''; // Return empty on error
            }
        }

        // Helper function to escape HTML special characters
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Helper function to clean title by removing " - Canada.ca" suffix
        function cleanTitle(title) {
            if (!title) return title;
            // Remove trailing " - Canada.ca" or " - canada.ca" (case insensitive)
            return title.replace(/\s*-\s*Canada\.ca\s*$/i, '');
        }

        // Extract language links and metadata from HTML head section
        function extractHeadMetadata(htmlContent) {
            console.log('extractHeadMetadata called, content length:', htmlContent?.length);
            if (!htmlContent || typeof htmlContent !== 'string') {
                console.log('extractHeadMetadata: invalid content');
                return {
                    alternateLanguages: [],
                    metadata: {}
                };
            }

            try {
                const parser = new DOMParser();
                const doc = parser.parseFromString(htmlContent, 'text/html');
                const head = doc.head;

                if (!head) {
                    console.log('extractHeadMetadata: no head element found');
                    return {
                        alternateLanguages: [],
                        metadata: {}
                    };
                }

                // Extract alternate language links
                const alternateLanguages = [];
                const languageLinks = head.querySelectorAll('link[rel="alternate"][hreflang]');

                languageLinks.forEach(link => {
                    const hreflang = link.getAttribute('hreflang');
                    const href = link.getAttribute('href');
                    const title = link.getAttribute('title') || '';

                    if (hreflang && href) {
                        alternateLanguages.push({
                            hreflang: hreflang.toLowerCase(),
                            href: href,
                            title: title
                        });
                        console.log('Found alternate language link:', { hreflang, href, title });
                    }
                });

                // Extract other important metadata
                const metadata = {};

                // Extract description
                const descriptionMeta = head.querySelector('meta[name="description"]');
                if (descriptionMeta) {
                    metadata.description = descriptionMeta.getAttribute('content') || '';
                }

                // Extract keywords
                const keywordsMeta = head.querySelector('meta[name="keywords"]');
                if (keywordsMeta) {
                    metadata.keywords = keywordsMeta.getAttribute('content') || '';
                }

                // Extract subjects
                const subjectsMeta = head.querySelector('meta[name="subjects"]');
                if (subjectsMeta) {
                    metadata.subjects = subjectsMeta.getAttribute('content') || '';
                }

                // Extract audience
                const audienceMeta = head.querySelector('meta[name="audience"]');
                if (audienceMeta) {
                    metadata.audience = audienceMeta.getAttribute('content') || '';
                }

                // Extract custom tags
                const customMeta = head.querySelector('meta[name="custom-tags"]');
                if (customMeta) {
                    metadata.custom = customMeta.getAttribute('content') || '';
                }

                // Extract author
                const authorMeta = head.querySelector('meta[name="author"]');
                if (authorMeta) {
                    metadata.author = authorMeta.getAttribute('content') || '';
                }

                // Extract viewport
                const viewportMeta = head.querySelector('meta[name="viewport"]');
                if (viewportMeta) {
                    metadata.viewport = viewportMeta.getAttribute('content') || '';
                }

                // Extract robots
                const robotsMeta = head.querySelector('meta[name="robots"]');
                if (robotsMeta) {
                    metadata.robots = robotsMeta.getAttribute('content') || '';
                }

                // Extract OG (Open Graph) metadata
                const ogTags = head.querySelectorAll('meta[property^="og:"]');
                if (ogTags.length > 0) {
                    metadata.openGraph = {};
                    ogTags.forEach(tag => {
                        const property = tag.getAttribute('property');
                        const content = tag.getAttribute('content') || '';
                        if (property) {
                            const key = property.replace('og:', '');
                            metadata.openGraph[key] = content;
                        }
                    });
                }

                // Extract Twitter Card metadata
                const twitterTags = head.querySelectorAll('meta[name^="twitter:"]');
                if (twitterTags.length > 0) {
                    metadata.twitterCard = {};
                    twitterTags.forEach(tag => {
                        const name = tag.getAttribute('name');
                        const content = tag.getAttribute('content') || '';
                        if (name) {
                            const key = name.replace('twitter:', '');
                            metadata.twitterCard[key] = content;
                        }
                    });
                }

                // Extract canonical URL
                const canonicalLink = head.querySelector('link[rel="canonical"]');
                if (canonicalLink) {
                    metadata.canonicalUrl = canonicalLink.getAttribute('href') || '';
                }

                // Extract language from HTML lang attribute
                const htmlElement = doc.documentElement;
                if (htmlElement) {
                    const htmlLang = htmlElement.getAttribute('lang');
                    if (htmlLang) {
                        metadata.htmlLang = htmlLang;
                    }
                }

                console.log('extractHeadMetadata results:', { alternateLanguages, metadata });
                return {
                    alternateLanguages,
                    metadata
                };

            } catch (error) {
                console.error('Error extracting head metadata:', error);
                return {
                    alternateLanguages: [],
                    metadata: {}
                };
            }
        }

        // Inject head metadata back into HTML content
        function injectHeadMetadata(htmlContent, metadata) {
            console.log('injectHeadMetadata called, content length:', htmlContent?.length, 'metadata:', metadata);
            if (!htmlContent || typeof htmlContent !== 'string') {
                console.log('injectHeadMetadata: invalid content');
                return htmlContent;
            }

            if (!metadata || typeof metadata !== 'object') {
                console.log('injectHeadMetadata: invalid metadata, returning original content');
                return htmlContent;
            }

            try {
                const parser = new DOMParser();
                const doc = parser.parseFromString(htmlContent, 'text/html');

                // Ensure head element exists
                let head = doc.head;
                if (!head) {
                    // Create head element if it doesn't exist
                    head = doc.createElement('head');
                    const htmlElement = doc.documentElement || doc.getElementsByTagName('html')[0];
                    if (htmlElement) {
                        htmlElement.insertBefore(head, htmlElement.firstChild);
                    } else {
                        // Create a minimal HTML structure
                        const newHtml = doc.createElement('html');
                        head = doc.createElement('head');
                        const body = doc.createElement('body');
                        newHtml.appendChild(head);
                        newHtml.appendChild(body);
                        doc.appendChild(newHtml);
                    }
                }

                // Clear existing metadata tags (but keep other head elements like style, script, etc.)
                // We'll only remove specific meta tags that we manage
                const metaTagsToRemove = [
                    'description', 'keywords', 'subjects', 'author', 'viewport', 'robots',
                    'audience', 'custom-tags'
                ];

                metaTagsToRemove.forEach(name => {
                    const existing = head.querySelector(`meta[name="${name}"]`);
                    if (existing) {
                        existing.remove();
                    }
                });

                // Remove Open Graph and Twitter Card tags
                const ogTags = head.querySelectorAll('meta[property^="og:"]');
                ogTags.forEach(tag => tag.remove());

                const twitterTags = head.querySelectorAll('meta[name^="twitter:"]');
                twitterTags.forEach(tag => tag.remove());

                // Remove alternate language links and canonical
                const altLinks = head.querySelectorAll('link[rel="alternate"][hreflang]');
                altLinks.forEach(link => link.remove());

                const canonicalLink = head.querySelector('link[rel="canonical"]');
                if (canonicalLink) {
                    canonicalLink.remove();
                }

                // Inject new metadata

                // Description
                if (metadata.description && metadata.description.trim()) {
                    const meta = doc.createElement('meta');
                    meta.setAttribute('name', 'description');
                    meta.setAttribute('content', metadata.description.trim());
                    head.appendChild(meta);
                }

                // Keywords
                if (metadata.keywords && metadata.keywords.trim()) {
                    const meta = doc.createElement('meta');
                    meta.setAttribute('name', 'keywords');
                    meta.setAttribute('content', metadata.keywords.trim());
                    head.appendChild(meta);
                }

                // Subjects
                if (metadata.subjects && metadata.subjects.trim()) {
                    const meta = doc.createElement('meta');
                    meta.setAttribute('name', 'subjects');
                    meta.setAttribute('content', metadata.subjects.trim());
                    head.appendChild(meta);
                }

                // Audience
                if (metadata.audience && metadata.audience.trim()) {
                    const meta = doc.createElement('meta');
                    meta.setAttribute('name', 'audience');
                    meta.setAttribute('content', metadata.audience.trim());
                    head.appendChild(meta);
                }

                // Custom tags
                if (metadata.custom && metadata.custom.trim()) {
                    const meta = doc.createElement('meta');
                    meta.setAttribute('name', 'custom-tags');
                    meta.setAttribute('content', metadata.custom.trim());
                    head.appendChild(meta);
                }

                // Author
                if (metadata.author && metadata.author.trim()) {
                    const meta = doc.createElement('meta');
                    meta.setAttribute('name', 'author');
                    meta.setAttribute('content', metadata.author.trim());
                    head.appendChild(meta);
                }

                // Viewport (with default if not provided)
                const viewportContent = metadata.viewport && metadata.viewport.trim()
                    ? metadata.viewport.trim()
                    : 'width=device-width, initial-scale=1.0';
                const viewportMeta = doc.createElement('meta');
                viewportMeta.setAttribute('name', 'viewport');
                viewportMeta.setAttribute('content', viewportContent);
                head.appendChild(viewportMeta);

                // Robots (optional)
                if (metadata.robots && metadata.robots.trim()) {
                    const meta = doc.createElement('meta');
                    meta.setAttribute('name', 'robots');
                    meta.setAttribute('content', metadata.robots.trim());
                    head.appendChild(meta);
                }

                // Open Graph metadata
                if (metadata.openGraph && typeof metadata.openGraph === 'object') {
                    Object.entries(metadata.openGraph).forEach(([key, value]) => {
                        if (value && typeof value === 'string' && value.trim()) {
                            const meta = doc.createElement('meta');
                            meta.setAttribute('property', `og:${key}`);
                            meta.setAttribute('content', value.trim());
                            head.appendChild(meta);
                        }
                    });
                }

                // Twitter Card metadata
                if (metadata.twitterCard && typeof metadata.twitterCard === 'object') {
                    Object.entries(metadata.twitterCard).forEach(([key, value]) => {
                        if (value && typeof value === 'string' && value.trim()) {
                            const meta = doc.createElement('meta');
                            meta.setAttribute('name', `twitter:${key}`);
                            meta.setAttribute('content', value.trim());
                            head.appendChild(meta);
                        }
                    });
                }

                // Alternate language links
                if (metadata.alternateLanguages && Array.isArray(metadata.alternateLanguages)) {
                    metadata.alternateLanguages.forEach(lang => {
                        if (lang.hreflang && lang.href && lang.hreflang.trim() && lang.href.trim()) {
                            const link = doc.createElement('link');
                            link.setAttribute('rel', 'alternate');
                            link.setAttribute('hreflang', lang.hreflang.trim().toLowerCase());
                            link.setAttribute('href', lang.href.trim());
                            if (lang.title && lang.title.trim()) {
                                link.setAttribute('title', lang.title.trim());
                            }
                            head.appendChild(link);
                        }
                    });
                }

                // Canonical URL
                if (metadata.canonicalUrl && metadata.canonicalUrl.trim()) {
                    const link = doc.createElement('link');
                    link.setAttribute('rel', 'canonical');
                    link.setAttribute('href', metadata.canonicalUrl.trim());
                    head.appendChild(link);
                }

                // HTML lang attribute
                if (metadata.htmlLang && metadata.htmlLang.trim()) {
                    const htmlElement = doc.documentElement;
                    if (htmlElement) {
                        htmlElement.setAttribute('lang', metadata.htmlLang.trim());
                    }
                }

                // Serialize back to HTML string
                const serializer = new XMLSerializer();
                let result = serializer.serializeToString(doc);

                // Clean up any DOMParser artifacts (like xmlns attributes)
                result = result.replace(/xmlns=".*?"/g, '');

                console.log('injectHeadMetadata completed, result length:', result.length);
                return result;

            } catch (error) {
                console.error('Error injecting head metadata:', error);
                return htmlContent; // Return original content on error
            }
        }

        // Metadata Manager - Unified system for managing HTML head metadata
        const metadataManager = {
            // Extract metadata from HTML content
            extract: function(htmlContent) {
                console.log('metadataManager.extract called');
                return extractHeadMetadata(htmlContent);
            },

            // Inject metadata into HTML content
            inject: function(htmlContent, metadata) {
                console.log('metadataManager.inject called');
                return injectHeadMetadata(htmlContent, metadata);
            },

            // Extract and merge metadata from page content into currentPageData
            extractAndStore: function(pageContent) {
                console.log('metadataManager.extractAndStore called');
                if (!pageContent || typeof pageContent !== 'string') {
                    console.log('No content to extract metadata from');
                    return;
                }

                if (!currentPageData) {
                    console.error('currentPageData not available');
                    return;
                }

                const headMetadata = extractHeadMetadata(pageContent);
                console.log('Extracted head metadata:', headMetadata);

                // Initialize metadata object if it doesn't exist
                if (!currentPageData.metadata) {
                    currentPageData.metadata = {};
                }

                // Merge extracted metadata with existing metadata
                currentPageData.metadata = {
                    ...currentPageData.metadata,
                    ...headMetadata.metadata,
                    alternateLanguages: headMetadata.alternateLanguages
                };

                console.log('Updated currentPageData.metadata:', currentPageData.metadata);
                return currentPageData.metadata;
            },

            // Get metadata for display or editing
            getMetadata: function() {
                if (!currentPageData || !currentPageData.metadata) {
                    return {
                        description: '',
                        keywords: '',
                        author: '',
                        viewport: 'width=device-width, initial-scale=1.0',
                        robots: '',
                        alternateLanguages: [],
                        canonicalUrl: '',
                        htmlLang: currentPageData?.language || 'en'
                    };
                }
                return currentPageData.metadata;
            },

            // Update specific metadata field
            updateField: function(field, value) {
                if (!currentPageData) {
                    console.error('currentPageData not available');
                    return false;
                }

                if (!currentPageData.metadata) {
                    currentPageData.metadata = {};
                }

                currentPageData.metadata[field] = value;
                console.log(`Updated metadata field ${field} to:`, value);
                return true;
            },

            /* === FUTURE: Multi-language support ===
            updateAlternateLanguages: function(languages) {
                ...
            },
            addAlternateLanguage: function(hreflang, href, title = '') {
                ...
            },
            removeAlternateLanguage: function(hreflang) {
                ...
            },
            */

            // Generate default metadata for a new page
            generateDefaultMetadata: function(pageTitle = '', pageLanguage = 'en') {
                return {
                    description: pageTitle ? `${pageTitle} - Canada.ca` : '',
                    keywords: 'Canada, government, services, information',
                    author: 'Government of Canada',
                    viewport: 'width=device-width, initial-scale=1.0',
                    robots: 'index, follow',
                    alternateLanguages: [],
                    canonicalUrl: '',
                    htmlLang: pageLanguage,
                    openGraph: {
                        title: pageTitle || '',
                        type: 'website',
                        url: '',
                        description: pageTitle ? `${pageTitle} - Canada.ca` : '',
                        image: ''
                    },
                    twitterCard: {
                        card: 'summary',
                        title: pageTitle || '',
                        description: pageTitle ? `${pageTitle} - Canada.ca` : '',
                        image: ''
                    }
                };
            },

            // Validate metadata (basic validation)
            validate: function(metadata) {
                const errors = [];

                if (metadata.description && metadata.description.length > 160) {
                    errors.push('Description should be 160 characters or less for SEO');
                }

                if (metadata.keywords && metadata.keywords.split(',').length > 10) {
                    errors.push('Too many keywords (max 10 recommended)');
                }

                if (metadata.alternateLanguages) {
                    metadata.alternateLanguages.forEach((lang, index) => {
                        if (!lang.hreflang || !lang.href) {
                            errors.push(`Alternate language ${index} missing hreflang or href`);
                        }
                        if (lang.hreflang && !/^[a-z]{2}(-[A-Z]{2})?$/.test(lang.hreflang)) {
                            errors.push(`Invalid hreflang format: ${lang.hreflang}. Should be like 'en' or 'fr-CA'`);
                        }
                    });
                }

                return {
                    isValid: errors.length === 0,
                    errors: errors
                };
            },

            // Export metadata as HTML string (just the head section)
            exportAsHtml: function(metadata) {
                if (!metadata) {
                    return '';
                }

                const headLines = [];

                // Basic meta tags
                if (metadata.description) {
                    headLines.push(`<meta name="description" content="${this.escapeHtml(metadata.description)}">`);
                }

                if (metadata.keywords) {
                    headLines.push(`<meta name="keywords" content="${this.escapeHtml(metadata.keywords)}">`);
                }

                if (metadata.author) {
                    headLines.push(`<meta name="author" content="${this.escapeHtml(metadata.author)}">`);
                }

                // Viewport (always included)
                const viewport = metadata.viewport || 'width=device-width, initial-scale=1.0';
                headLines.push(`<meta name="viewport" content="${this.escapeHtml(viewport)}">`);

                if (metadata.robots) {
                    headLines.push(`<meta name="robots" content="${this.escapeHtml(metadata.robots)}">`);
                }

                // Alternate languages
                if (metadata.alternateLanguages && Array.isArray(metadata.alternateLanguages)) {
                    metadata.alternateLanguages.forEach(lang => {
                        let tag = `<link rel="alternate" hreflang="${this.escapeHtml(lang.hreflang)}" href="${this.escapeHtml(lang.href)}"`;
                        if (lang.title) {
                            tag += ` title="${this.escapeHtml(lang.title)}"`;
                        }
                        tag += '>';
                        headLines.push(tag);
                    });
                }

                // Canonical URL
                if (metadata.canonicalUrl) {
                    headLines.push(`<link rel="canonical" href="${this.escapeHtml(metadata.canonicalUrl)}">`);
                }

                // Open Graph
                if (metadata.openGraph) {
                    Object.entries(metadata.openGraph).forEach(([key, value]) => {
                        if (value) {
                            headLines.push(`<meta property="og:${key}" content="${this.escapeHtml(value)}">`);
                        }
                    });
                }

                // Twitter Card
                if (metadata.twitterCard) {
                    Object.entries(metadata.twitterCard).forEach(([key, value]) => {
                        if (value) {
                            headLines.push(`<meta name="twitter:${key}" content="${this.escapeHtml(value)}">`);
                        }
                    });
                }

                return headLines.join('\n    ');
            },

            // Helper: Escape HTML special characters
            escapeHtml: function(text) {
                if (typeof text !== 'string') {
                    return text;
                }
                const map = {
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#039;'
                };
                return text.replace(/[&<>"']/g, function(m) { return map[m]; });
            }
        };

        // Clean content by removing Canada.ca header/footer and date section, keeping only main content
        function cleanContent(content, pageId) {
            console.log('cleanContent called for page:', pageId, 'content type:', typeof content, 'content length:', content?.length);
            console.log('content first 500 chars:', content?.substring?.(0, 500));
            if (!content || typeof content !== 'string') {
                console.log('cleanContent: invalid content, returning:', content);
                return content;
            }

            let cleaned = content;

            // Try to extract main content if it's HTML
            if (content.includes('<') && content.includes('>')) {
                // It's HTML content
                // Create a temporary DOM parser
                const parser = new DOMParser();
                try {
                    const doc = parser.parseFromString(content, 'text/html');

                    // Remove Canada.ca header and footer elements before extracting main
                    const headerFooterSelectors = [
                        '#wb-bnr', '#wb-sm', '#wb-info', '#wb-srch', '#wb-lng',
                        '#wb-sec', '#wb-dtmd', '#wb-glb-mn', '#wb-srch-frm',
                        '.pagedetails', '.brand', '.subsite', '.gc-footer',
                        '.gc-subway', '.gc-main-nav', '.gc-top-nav',
                        'footer', 'header', '.footer', '.header',
                        '#gcwu-sig', '#gcwu-sig-in', '#gcwu-tc', '#gcwu-date-mod',
                        // Additional header/footer selectors
                        '[role="banner"]', '[role="contentinfo"]',
                        '.gcweb-menu', '.gc-web-menu', '.gc-web-header', '.gc-web-footer',
                        '#gcweb-nav', '#gcweb-header', '#gcweb-footer',
                        '.site-header', '.site-footer', '.global-header', '.global-footer',
                        '.header-main', '.footer-main', '#header', '#footer',
                        '.nav-main', '.navigation', '.main-nav', '.primary-nav'
                    ];

                    headerFooterSelectors.forEach(selector => {
                        const elements = doc.querySelectorAll(selector);
                        elements.forEach(el => {
                            el.remove();
                        });
                    });

                    // Try to find main content area - prioritize Canada.ca main element
                    // NOTE: keep only specific selectors; avoid generic ones (like .container, #wb-cont)
                    // that match non-main sections (e.g., banner containers) and cause content loss on save
                    const mainSelectors = [
                        'main[property="mainContentOfPage"]',
                        'main',
                        '.mwstext.section',           // Canada.ca content area
                        '.row.profile',               // Canada.ca profile/content container
                        '#main-content',
                        '.container.main'
                    ];

                    let mainElement = null;
                    let matchedSelector = '';
                    for (const selector of mainSelectors) {
                        mainElement = doc.querySelector(selector);
                        if (mainElement) {
                            matchedSelector = selector;
                            break;
                        }
                    }

                    // If found main element, use its innerHTML
                    if (mainElement) {
                        console.log('cleanContent: found main element via selector ' + matchedSelector + ', innerHTML length:', mainElement.innerHTML.length);
                        // Remove only external script elements (with src attribute) to avoid cross-origin issues
                        const scripts = mainElement.querySelectorAll('script[src]');
                        scripts.forEach(script => {
                            const src = script.src || '';
                            // Only remove external scripts, keep inline scripts
                            if (src && !src.startsWith('data:') && !src.startsWith('blob:')) {
                                script.remove();
                                console.log('cleanContent: removed external script element, src:', src);
                            }
                        });
                        // Also remove external stylesheet links that might trigger cross-origin requests
                        const stylesheets = mainElement.querySelectorAll('link[rel="stylesheet"]');
                        stylesheets.forEach(link => {
                            const href = link.href || '';
                            // Remove external CDN links but keep local stylesheets
                            if (href.includes('googleapis.com') || href.includes('fontawesome.com') || href.includes('adobe.com') || href.includes('cloudflare.com')) {
                                link.remove();
                                console.log('cleanContent: removed external stylesheet link:', href);
                            }
                        });
                        cleaned = mainElement.innerHTML;
                    } else {
                        console.log('cleanContent: no main element found, falling back to body');
                        // Fallback: use body content but keep the header/footer removal
                        const body = doc.body;
                        if (body) {
                            console.log('cleanContent: body found, innerHTML length:', body.innerHTML.length);
                            // Remove only external script elements from body
                            const scripts = body.querySelectorAll('script[src]');
                            scripts.forEach(script => {
                                const src = script.src || '';
                                if (src && !src.startsWith('data:') && !src.startsWith('blob:')) {
                                    script.remove();
                                    console.log('cleanContent: removed external script element from body, src:', src);
                                }
                            });
                            // Also remove external stylesheet links from body
                            const stylesheets = body.querySelectorAll('link[rel="stylesheet"]');
                            stylesheets.forEach(link => {
                                const href = link.href || '';
                                if (href.includes('googleapis.com') || href.includes('fontawesome.com') || href.includes('adobe.com') || href.includes('cloudflare.com')) {
                                    link.remove();
                                    console.log('cleanContent: removed external stylesheet link from body:', href);
                                }
                            });
                            cleaned = body.innerHTML;
                        } else {
                            console.log('cleanContent: no body found');
                        }
                    }

                    // Additional cleanup: remove any remaining date/modified sections
                    const dateSelectors = [
                        '.pagedetails',
                        '.wb-inv',
                        '.wb-tphp',
                        '.date-modified',
                        '.modified',
                        '[class*="date"]',
                        '[id*="date"]'
                    ];

                    dateSelectors.forEach(selector => {
                        const elements = doc.querySelectorAll(selector);
                        elements.forEach(el => {
                            const text = el.textContent || '';
                            if (text.includes('Date modified') || text.includes('Page details') ||
                                text.includes('Modified') || text.match(/\d{4}-\d{2}-\d{2}/)) {
                                el.remove();
                            }
                        });
                    });

                } catch (e) {
                    console.warn('HTML parsing failed, falling back to text cleaning:', e);
                }
            }

            // For plain text content or fallback, use pattern matching
            if (!cleaned.includes('<') || cleaned === content) {
                // Remove "Page details YYYY-MM-DD" footer
                cleaned = cleaned.replace(/Page details \d{4}-\d{2}-\d{2}$/i, '').trim();

                // Remove common Canada.ca footer patterns
                const footerPatterns = [
                    /Date modified:.*$/im,
                    /Government of Canada.*$/im,
                    /©.*$/im,
                    /All rights reserved.*$/im,
                    /Report a problem.*$/im,
                    /Contact us.*$/im,
                    /Terms and conditions.*$/im,
                    /Privacy.*$/im,
                    /Canada\.ca.*$/im
                ];

                footerPatterns.forEach(pattern => {
                    cleaned = cleaned.replace(pattern, '').trim();
                });

                // Remove duplicate title at beginning
                const lines = cleaned.split('\n');
                if (lines.length > 1) {
                    const firstLine = lines[0].trim();
                    if (firstLine.length < 100 && cleaned.indexOf(firstLine, firstLine.length) !== -1) {
                        lines.shift();
                        cleaned = lines.join('\n').trim();
                    }
                }
            }

            // Fallback: if cleaned content is too short but original content is substantial, return original
            if (cleaned.length < 100 && content.length > 500) {
                console.warn('cleanContent: cleaned content too short, returning original content. Cleaned:', cleaned.length, 'Original:', content.length);
                // Return original content but with basic footer removal
                const basicCleaned = content.replace(/Page details \d{4}-\d{2}-\d{2}$/i, '').trim();
                return basicCleaned;
            }

            console.log('cleanContent: returning cleaned content, length:', cleaned.length, 'first 200 chars:', cleaned.substring(0, 200).replace(/\n/g, ' '));
            // Return cleaned content only (no WebBot header/footer)
            return cleaned;
        }

        // Create a full WebBot page with custom header and footer
        function createWebBotPage(title, content, headerContent = '', footerContent = '') {
            console.log('createWebBotPage: creating wrapped page, title:', title);
            console.log('Header content provided:', headerContent ? 'yes, length: ' + headerContent.length : 'no');
            console.log('Footer content provided:', footerContent ? 'yes, length: ' + footerContent.length : 'no');

            // Use provided header and footer, or fallback to WebBot custom styling
            let headerHtml = '';
            let footerHtml = '';

            if (headerContent && headerContent.trim().length > 0) {
                // Use fetched header content
                headerHtml = headerContent;
                console.log('Using fetched header content');
            } else {
                // Fallback to WebBot custom header
                headerHtml = `
                <!-- WebBot Custom Header -->
                <header class="webbot-header" style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px 0;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                ">
                    <div class="container" style="max-width: 1200px; margin: 0 auto; padding: 0 20px;">
                        <div class="header-content" style="display: flex; justify-content: space-between; align-items: center;">
                            <div class="logo" style="font-size: 24px; font-weight: bold;">
                                🥕 WebBot
                            </div>
                            <div class="header-info" style="font-size: 14px; opacity: 0.9;">
                                <span class="page-id" style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px;">
                                    ${currentPageId || 'untitled'}
                                </span>
                            </div>
                        </div>
                        <div class="page-title" style="margin-top: 15px; font-size: 28px; font-weight: 300;">
                            ${title}
                        </div>
                    </div>
                </header>
            `;
            }

            if (footerContent && footerContent.trim().length > 0) {
                // Use fetched footer content
                footerHtml = footerContent;
                console.log('Using fetched footer content');
            } else {
                // Fallback to WebBot custom footer
                footerHtml = `
                <!-- WebBot Custom Footer -->
                <footer class="webbot-footer" style="
                    background: #f8f9fa;
                    color: #666;
                    padding: 30px 0;
                    margin-top: 40px;
                    border-top: 1px solid #eaeaea;
                ">
                    <div class="container" style="max-width: 1200px; margin: 0 auto; padding: 0 20px;">
                        <div class="footer-content" style="display: flex; justify-content: space-between; align-items: center;">
                            <div class="footer-left" style="font-size: 14px;">
                                <strong>WebBot Content Management System</strong><br>
                                AI-enhanced website content management
                            </div>
                            <div class="footer-right" style="text-align: right; font-size: 12px; color: #999;">
                                <div>Generated: ${new Date().toLocaleString()}</div>
                                <div>Powered by FileBot &amp; Canada.ca GCWeb</div>
                            </div>
                        </div>
                    </div>
                </footer>
            `;
            }

            // Return full page with header and footer
            return `
                ${headerHtml}
				<main property="mainContentOfPage" resource="#wb-main" typeof="WebPageElement" class="container">
                    ${content}
                </main>
                ${footerHtml}
            `;
        }

        // Synchronize content between TinyMCE editor and textarea based on active mode
        function syncEditorContent() {
            if (!tinyMceEditor) {
                console.log('syncEditorContent: TinyMCE editor not available');
                return;
            }

            // Determine which direction to sync based on active mode
            if (wysiwygContainer.classList.contains('active')) {
                // WYSIWYG mode is active: sync TinyMCE → textarea
                const tinyMceContent = tinyMceEditor.getContent();
                editorContentEl.value = tinyMceContent;
                console.log('syncEditorContent: WYSIWYG mode, TinyMCE → textarea, length:', tinyMceContent.length);
            } else {
                // HTML source mode is active: sync textarea → TinyMCE
                const textareaContent = editorContentEl.value;
                tinyMceEditor.setContent(textareaContent);
                console.log('syncEditorContent: HTML mode, textarea → TinyMCE, length:', textareaContent.length);
            }
        }

        // Get current editor content based on active mode
        function getCurrentContent() {
            // Check if WYSIWYG mode is active
            if (wysiwygContainer.classList.contains('active') && tinyMceEditor) {
                return tinyMceEditor.getContent();
            } else {
                // HTML source mode is active or TinyMCE not initialized
                return editorContentEl.value;
            }
        }

        // Preview page content using the backend template renderer
        async function previewPage() {
            if (!currentPageId || !currentPageData) {
                showError('No page selected to preview.');
                return;
            }

            // Synchronize editor content before preview
            syncEditorContent();

            // Get current content from editor
            const content = getCurrentContent();
            console.log('previewPage: content length from getCurrentContent:', content?.length);

            if (!content) {
                console.log('previewPage: content is empty, showing error');
                showError('No content to preview.');
                return;
            }

            console.log('Previewing page:', currentPageId);
            showLoading(true);

            try {
                // Call backend preview endpoint which uses the page-template
                const response = await fetch(`/api/v1/pages/preview?path=${encodeURIComponent(currentPageId)}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: content })
                });

                if (!response.ok) {
                    const errText = await response.text();
                    console.error('Preview API error:', response.status, errText);
                    showError(`Preview failed (${response.status}). Falling back to local rendering.`);
                    // Fallback to local preview
                    previewPageLocal();
                    return;
                }

                const renderedHtml = await response.text();

                // Wrap in preview container with actions
                const previewHtml = `
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>Preview: ${currentPageData.title || 'Untitled Page'}</title>
                        <link rel="stylesheet" href="/etc/designs/canada/wet-boew/css/theme.min.css">
                        <style>
                            .preview-actions {
                                position: fixed;
                                bottom: 0;
                                left: 0;
                                right: 0;
                                padding: 12px 20px;
                                background: #f8f9fa;
                                border-top: 2px solid #ddd;
                                text-align: center;
                                z-index: 9999;
                                box-shadow: 0 -2px 8px rgba(0,0,0,0.1);
                            }
                            .preview-actions .btn {
                                padding: 8px 20px;
                                border: none;
                                border-radius: 4px;
                                cursor: pointer;
                                font-size: 14px;
                                margin: 0 5px;
                            }
                            .btn-primary { background: #007bff; color: white; }
                            body { padding-bottom: 60px; }
                        </style>
                    </head>
                    <body>
                        ${renderedHtml}
                        <div class="preview-actions">
                            <button class="btn btn-primary" onclick="window.print()">Print Preview</button>
                            <button class="btn" onclick="window.close()">Close Preview</button>
                        </div>
                        <script src="/etc/designs/canada/wet-boew/js/jquery/2.2.4/jquery.min.js"><\/script>
                        <script src="/etc/designs/canada/wet-boew/js/wet-boew.min.js" defer><\/script>
                        <script src="/etc/designs/canada/wet-boew/js/theme.min.js" defer><\/script>
                    </body>
                    </html>
                `;

                const previewWindow = window.open('', '_blank');
                if (!previewWindow) {
                    showError('Preview window was blocked by browser. Please allow popups for this site.');
                    return;
                }
                previewWindow.document.write(previewHtml);
                previewWindow.document.close();
                previewWindow.focus();

            } catch (error) {
                console.error('previewPage error:', error);
                showError('Preview failed. Falling back to local rendering.');
                previewPageLocal();
            } finally {
                hideLoading();
                if (currentPageData) {
                    editorFormEl.style.display = 'block';
                    editorActionsEl.style.display = 'block';
                    if (savePageTopBtn) savePageTopBtn.style.display = '';
                    noPageSelectedEl.style.display = 'none';
                }
            }
        }

        // Fallback: local preview without template (original logic kept for robustness)
        async function previewPageLocal() {
            if (!currentPageId || !currentPageData) return;

            let content = getCurrentContent();
            const title = currentPageData?.title || 'Untitled Page';

            if (!content) {
                showError('No content to preview.');
                return;
            }

            // Clean the content
            const cleanedContent = cleanContent(content, currentPageId);
            let finalContent = cleanedContent;
            const cleanedLength = finalContent ? finalContent.trim().length : 0;
            const originalLength = content ? content.trim().length : 0;
            const minLength = Math.min(500, originalLength * 0.3);

            if (!finalContent || cleanedLength < minLength) {
                finalContent = content;
                const basicCleaned = content.replace(/Page details \d{4}-\d{2}-\d{2}$/i, '').trim();
                if (basicCleaned.length > cleanedLength && basicCleaned.length >= minLength) {
                    finalContent = basicCleaned;
                }
            }

            // Try to get header and footer
            let headerContent = '';
            let footerContent = '';
            try {
                const language = currentPageData?.language || 'en';
                const rootPath = `/${language}`;

                const headerResponse = await fetch(`/api/v1/pages/by-path?path=${encodeURIComponent(rootPath + '/header')}`);
                if (headerResponse.ok) {
                    const headerData = await headerResponse.json();
                    headerContent = headerData.content || '';
                }

                // Use new getfooter API that returns institution + language level
                const pathForFooter = currentPageData?.path || rootPath;
                const lang = currentPageData?.language || 'en';
                // Use server-side mustache rendering: loads template config & datasource in one call
                try {
                    const dsUrl = `/api/v1/getfooter?path=${encodeURIComponent(pathForFooter)}`;
                    const mustacheResp = await fetch(`/mustache/${lang}/mustache-templates/getfooter?datasource=${encodeURIComponent(dsUrl)}`);
                    if (mustacheResp.ok) {
                        footerContent = await mustacheResp.text();
                    }
                } catch (e) {
                    console.error('Error rendering footer via mustache:', e);
                }
                // Fallback: direct call if mustache rendering failed
                if (!footerContent) {
                    try {
                        const fallbackResp = await fetch(`/api/v1/getfooter?path=${encodeURIComponent(pathForFooter)}`);
                        if (fallbackResp.ok) {
                            const fd = await fallbackResp.json();
                            var _inst = (fd.institution_level?.content || '');
                            var _lang = (fd.language_level?.content || '');
                            var _m1 = _inst.match(/<footer[^>]*>[\s\S]*?<\/footer>/i);
                            if (_m1) _inst = _m1[0];
                            var _m2 = _lang.match(/<footer[^>]*>[\s\S]*?<\/footer>/i);
                            if (_m2) _lang = _m2[0];
                            footerContent = _inst + _lang;
                        }
                    } catch (e2) {
                        console.error('Fallback footer fetch failed:', e2);
                    }
                }
            } catch (error) {
                console.error('Error fetching header/footer:', error);
            }

            // Generate breadcrumb
            if (headerContent && currentPageData) {
                try {
                    const breadcrumbHtml = await generateBreadcrumbHTML(currentPageData);
                    if (breadcrumbHtml) {
                        headerContent = headerContent.replace(/{breadcrumb}/g, breadcrumbHtml);
                        headerContent = headerContent.replace(/{ breadcrumb }/g, breadcrumbHtml);
                    }
                } catch (e) {
                    console.error('Error generating breadcrumb:', e);
                }
            }

            // Create preview HTML using createWebBotPage
            const previewHtml = `
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Preview: ${title}</title>
                    <link rel="stylesheet" href="/etc/designs/canada/wet-boew/css/theme.min.css">
                    <style>
                        body { padding: 20px; background: #f8f9fa; }
                        .preview-container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); padding: 20px; }
                        .preview-actions { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 6px; border: 1px solid #ddd; text-align: center; }
                        .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; margin: 0 5px; }
                        .btn-primary { background: #007bff; color: white; }
                    </style>
                </head>
                <body>
                    <div class="preview-container">
                        ${createWebBotPage(title, finalContent, headerContent, footerContent)}
                        <div class="preview-actions">
                            <button class="btn btn-primary" onclick="window.print()">Print Preview</button>
                            <button class="btn" onclick="window.close()">Close Preview</button>
                        </div>
                    </div>
                    <script src="/etc/designs/canada/wet-boew/js/jquery/2.2.4/jquery.min.js"><\/script>
                    <script src="/etc/designs/canada/wet-boew/js/wet-boew.min.js" defer><\/script>
                    <script src="/etc/designs/canada/wet-boew/js/theme.min.js" defer><\/script>
                </body>
                </html>
            `;

            const previewWindow = window.open('', '_blank');
            if (!previewWindow) {
                showError('Preview window was blocked by browser. Please allow popups for this site.');
                return;
            }
            previewWindow.document.write(previewHtml);
            previewWindow.document.close();
            previewWindow.focus();
        }

        // Create a new page via POST
        async function createNewPage() {
            console.log('createNewPage called, parentPath:', newPageParentPath);

            // Show saving indicator
            const originalText = savePageBtn.textContent;
            savePageBtn.disabled = true;
            savePageBtn.innerHTML = '<span class="glyphicon glyphicon-refresh spinning" aria-hidden="true"></span> Creating...';

            try {
                // Get editor content
                let content;
                if (tinyMceEditor) {
                    content = tinyMceEditor.getContent();
                } else {
                    content = editorContentEl.value;
                }

                // Process images in content
                console.log('Processing images in content before creating page...');
                let processedContent;
                try {
                    processedContent = await processImagesInHtmlContent(content);
                } catch (imageError) {
                    console.error('Error processing images:', imageError);
                    showError('Warning: Failed to process some images. Saving with original URLs.');
                    processedContent = content;
                }

                // Extract language from parent path
                const pathParts = newPageParentPath.split('/').filter(Boolean);
                const language = (pathParts.length > 0 && ['en', 'fr'].includes(pathParts[0])) ? pathParts[0] : 'en';

                // Build the title (use first heading text or default)
                const titleMatch = processedContent.match(/<h1[^>]*>([^<]+)<\/h1>/i) ||
                                   processedContent.match(/<h2[^>]*>([^<]+)<\/h2>/i);
                const title = titleMatch ? titleMatch[1].trim() : 'Untitled Page';

                // Build the request body
                const pageData = {
                    title: title,
                    content: processedContent,
                    language: language,
                    status: 'draft',
                    parent_path: newPageParentPath
                };

                console.log('Sending POST request to create page with data:', {
                    ...pageData,
                    content: '(content length: ' + processedContent.length + ' chars)'
                });

                const response = await fetch(API_BASE + '/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(pageData)
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => null);
                    throw new Error(
                        (errorData && errorData.detail)
                            ? errorData.detail
                            : 'HTTP ' + response.status + ': ' + response.statusText
                    );
                }

                const createdPage = await response.json();
                console.log('Page created successfully:', createdPage.id, createdPage.path);

                // Update state to reflect saved page
                isNewPage = false;
                currentPageId = createdPage.path || createdPage.id;
                currentPageData = createdPage;
                window.currentPageData = createdPage;
                
                // Update display
                pageTitleDisplayEl.textContent = createdPage.title || title;
                pageIdDisplayEl.textContent = ' | Path: ' + (createdPage.metadata?.file_path || createdPage.id || '');
                pageLanguageDisplayEl.textContent = ' | Language: ' + (createdPage.language || language).toUpperCase();
                pageStatusDisplayEl.textContent = ' | Status: ' + (createdPage.status || 'draft');
                if (createdPage.metadata && createdPage.metadata.file_path) {
                    filePathDisplayEl.textContent = ' | File Path: ' + createdPage.metadata.file_path;
                    filePathDisplayEl.style.color = '#007bff';
                    filePathDisplayEl.style.fontWeight = 'normal';
                } else {
                    filePathDisplayEl.textContent = '';
                }
                lastModifiedDisplayEl.textContent = formatLastModified(createdPage.last_modified);
                pagePublishedDisplayEl.textContent = formatPublishedAt(createdPage.last_published);

                // Update URL
                const url = new URL(window.location);
                url.searchParams.set('pageId', (createdPage.path || createdPage.id));
                window.history.replaceState({}, '', url);

                // Update breadcrumb
                try {
                    await updateBreadcrumb(createdPage);
                } catch (e) {
                    console.log('Breadcrumb update error:', e.message);
                }

                // Reload pages sidebar (use timeout to let state settle)
                setTimeout(() => {
                    loadPagesForSidebar(createdPage.path || createdPage.id);
                }, 100);

                // Show success message
                successMessageEl.textContent = 'Page created successfully!';
                successMessageEl.style.display = 'block';
                errorAreaEl.style.display = 'none';

                console.log('New page created successfully');
            } catch (error) {
                console.error('Error creating page:', error);
                showError('Failed to create page: ' + error.message);
            } finally {
                // Restore button
                savePageBtn.disabled = false;
                savePageBtn.innerHTML = originalText;

                // Hide success message after 5 seconds
                setTimeout(() => {
                    successMessageEl.style.display = 'none';
                }, 5000);
            }
        }

        // Save page changes
        async function savePage() {
            if (!currentPageId || !currentPageData) {
                showError('No page selected to save.');
                return;
            }

            // If this is a new page, create it via POST instead of PUT
            if (isNewPage) {
                await createNewPage();
                return;
            }

            // Show saving indicator
            const originalText = savePageBtn.textContent;
            savePageBtn.disabled = true;
            savePageBtn.innerHTML = '<span class="glyphicon glyphicon-refresh spinning" aria-hidden="true"></span> Saving...';

            try {
                // 获取编辑器内容(如果使用TinyMCE则从TinyMCE获取)
                let content;
                if (tinyMceEditor) {
                    content = tinyMceEditor.getContent();
                    console.log('Getting content from TinyMCE editor');
                    // Fix any '../' paths that TinyMCE may have added to href attributes
                    content = content.replace(/(href=["'])(?:\.\.\/)+/gi, '$1/');
                } else {
                    content = editorContentEl.value;
                    console.log('Getting content from textarea');
                }

                // 处理内容中的图片(上传blob/localhost图片到FileBot)
                console.log('Processing images in content before saving...');
                let processedContent;
                try {
                    processedContent = await processImagesInHtmlContent(content);
                    console.log('Image processing completed');
                } catch (imageError) {
                    console.error('Error processing images:', imageError);
                    // 图片处理失败,但继续保存原始内容
                    showError(`Warning: Failed to process some images: ${imageError.message}. Saving with original image URLs.`);
                    processedContent = content;
                }

                // Inject metadata into content if available
                let finalContent = processedContent;
                if (currentPageData && currentPageData.metadata) {
                    console.log('Injecting metadata into content before saving...');
                    try {
                        finalContent = metadataManager.inject(processedContent, currentPageData.metadata);
                        console.log('Metadata injection completed, final content length:', finalContent.length);
                    } catch (metadataError) {
                        console.error('Error injecting metadata:', metadataError);
                        // Continue with original content if metadata injection fails
                        showError(`Warning: Failed to inject metadata: ${metadataError.message}. Saving without metadata.`);
                    }
                } else {
                    console.log('No metadata found to inject, using processed content as-is');
                }

                const updatedData = {
                    title: currentPageData?.title || 'Untitled Page',
                    content: finalContent,
                    description: currentPageData?.description || '',
                    keywords: currentPageData?.keywords || '',
                    other_language_path: currentPageData?.other_language_path || null,
                    language: currentPageData?.language || 'en',
                    status: currentPageData?.status || 'draft',
                    hide_in_navigation: currentPageData?.hide_in_navigation ?? false,
                    navigation_title: currentPageData?.navigation_title || null,
                    metadata: currentPageData?.metadata || undefined
                };

                // Validate required fields
                if (!updatedData.title) {
                    throw new Error('Page title is required');
                }

                // Determine the correct API URL for saving using path format
                // When page is loaded by path (e.g., /en/template-container/wet-carousel),
                // currentPageId is the full path and should be used directly
                // Otherwise, build path from parent_path or parent_path
                let apiUrl;

                if (currentPageId && currentPageId.includes('/')) {
                    // currentPageId is already a full path (e.g., /en/template-container/wet-carousel)
                    apiUrl = `${API_BASE}${currentPageId}`;
                    console.log('Using currentPageId as full path for API:', apiUrl);
                } else {
                    // currentPageId is just a page ID, need to build full path
                    let pageIdToUse = currentPageId;
                    if (currentPageData && currentPageData.id) {
                        pageIdToUse = currentPageData.id;
                        console.log('Using page ID from currentPageData:', pageIdToUse, 'original currentPageId:', currentPageId);
                    }

                    // Try to get parent path from parent_path first, then fallback to parent_path
                    let parentPath = currentPageData?.parent_path;
                    if (!parentPath && currentPageData?.parent_path) {
                        // Convert parent_path to parent_path format
                        // Note: This assumes parent_path corresponds to a page at root level
                        // For nested parents, this may need adjustment
                        parentPath = `/${currentPageData.parent_path}`;
                    }

                    if (parentPath) {
                        // Ensure parentPath starts with slash and has no trailing slash
                        const normalizedParent = parentPath.startsWith('/') ? parentPath : `/${parentPath}`;
                        const cleanParent = normalizedParent.replace(/\/$/, '');
                        apiUrl = `${API_BASE}${cleanParent}/${encodeURIComponent(pageIdToUse)}`;
                        console.log('Built path from parent:', apiUrl, 'parentPath:', parentPath);
                    } else {
                        // Root page (no parent)
                        apiUrl = `${API_BASE}/${encodeURIComponent(pageIdToUse)}`;
                        console.log('Root page path:', apiUrl);
                    }
                }

                const response = await fetch(apiUrl, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(updatedData)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                // Update last modified and current page data
                const now = new Date();
                updatedData.last_modified = now.toISOString();
                currentPageData = { ...currentPageData, ...updatedData };
                window.currentPageData = currentPageData;

                // Show success message
                successMessageEl.textContent = 'Page saved successfully!';
                successMessageEl.style.display = 'block';
                errorAreaEl.style.display = 'none';

                // Update display
                pageTitleDisplayEl.textContent = updatedData.title;
                pageLanguageDisplayEl.textContent = ` | Language: ${updatedData.language.toUpperCase()}`;
                pageStatusDisplayEl.textContent = ` | Status: ${updatedData.status}`;
                lastModifiedDisplayEl.textContent = formatLastModified(updatedData.last_modified);
                pagePublishedDisplayEl.textContent = formatPublishedAt(currentPageData.last_published);
                if (currentPageData.metadata && currentPageData.metadata.file_path) {
                    filePathDisplayEl.textContent = ` | File Path: ${currentPageData.metadata.file_path}`;
                    filePathDisplayEl.style.color = '#007bff';
                    filePathDisplayEl.style.fontWeight = 'normal';
                } else {
                    filePathDisplayEl.textContent = '';
                }
                lastModifiedDisplayEl.textContent = formatLastModified(currentPageData.last_modified);
                pagePublishedDisplayEl.textContent = formatPublishedAt(currentPageData.last_published);


                console.log('Page saved successfully');
            } catch (error) {
                console.error('Error saving page:', error);
                showError(`Failed to save page: ${error.message}`);
            } finally {
                // Restore button
                savePageBtn.disabled = false;
                savePageBtn.innerHTML = originalText;

                // Hide success message after 3 seconds
                setTimeout(() => {
                    successMessageEl.style.display = 'none';
                }, 3000);

            }
        }

        async function publishPage() {
            if (!currentPageId || !currentPageData) {
                showError('No page selected to publish.');
                return;
            }

            // First save current content
            const content = getCurrentContent();
            if (!content || !content.trim()) {
                showError('Page has no content to publish.');
                return;
            }

            // Save before publishing
            await savePage();

            const path = currentPageData.path || currentPageId;
            const originalText = publishPageBtn.textContent;
            publishPageBtn.disabled = true;
            publishPageBtn.innerHTML = '<span class="glyphicon glyphicon-refresh spinning" aria-hidden="true"></span> Publishing...';

            try {
                const response = await fetch('/api/v1/pages/publish?path=' + encodeURIComponent(path), {
                    method: 'POST'
                });

                if (!response.ok) {
                    const errData = await response.json().catch(() => ({}));
                    throw new Error(errData.detail || 'Publish failed (HTTP ' + response.status + ')');
                }

                const result = await response.json();

                // Update local page data with publish status
                currentPageData.status = 'published';
                currentPageData.last_published = result.published_at;
                currentPageData.last_modified = result.published_at;
                // Refresh display
                pageStatusDisplayEl.textContent = ' | Status: published';
                lastModifiedDisplayEl.textContent = formatLastModified(result.last_modified || result.published_at);
                pagePublishedDisplayEl.textContent = formatPublishedAt(result.published_at);

                showSuccess('Page published successfully!');
                console.log('Published page:', result);

                // Open the published page in a new tab
                // Page is saved to FileBot publish directory, served at /publish/
                // Strip site prefix (canadasite/site/www) since FileBot strips it during publish
                const publishPath = path.replace(/^\/(canadasite|site|www)\/?/, '/');
                const pageUrl = '/publish/' + publishPath.replace(/^\//, '') + '.html';
                window.open(pageUrl, '_blank');

            } catch (error) {
                showError('Publish failed: ' + error.message);
                console.error('Publish error:', error);
            } finally {
                publishPageBtn.disabled = false;
                publishPageBtn.innerHTML = originalText;
            }
        }

        // Cancel editing
        function cancelEdit() {
            if (currentPageData) {
                // Reset form to original values
                // editorTitleEl.value = currentPageData.title || ''; // Title field removed from UI
                editorContentEl.value = currentPageData.content || '';
                // editorLanguageEl.value = currentPageData.language || 'en'; // Language field removed from UI
                // editorStatusEl.value = currentPageData.status || 'draft'; // Status field removed from UI

                // Also reset TinyMCE editor if initialized
                if (tinyMceEditor) {
                    tinyMceEditor.setContent(currentPageData.content || '');
                }

                successMessageEl.style.display = 'none';
                errorAreaEl.style.display = 'none';

                console.log('Edit cancelled');
            }
        }

        // Clear editor (go back to no page selected)
        function clearEditor() {
            currentPageId = null;
            currentPageData = null;
            window.currentPageData = null;
            
            editorFormEl.style.display = 'none';
            editorActionsEl.style.display = 'none';
            if (savePageTopBtn) savePageTopBtn.style.display = 'none';
            noPageSelectedEl.style.display = 'block';
            errorAreaEl.style.display = 'none';
            successMessageEl.style.display = 'none';

            pageTitleDisplayEl.textContent = 'No page selected';
            pageIdDisplayEl.textContent = '';
            pageLanguageDisplayEl.textContent = '';
            pageStatusDisplayEl.textContent = '';
            filePathDisplayEl.textContent = '';
            lastModifiedDisplayEl.textContent = '';
            pagePublishedDisplayEl.textContent = '';

            // Clear URL parameter
            const url = new URL(window.location);
            url.searchParams.delete('pageId');
            window.history.replaceState({}, '', url);

            // Clear active items in tree
            document.querySelectorAll('.page-item, .tree-category-header').forEach(el => {
                el.classList.remove('active');
            });

            console.log('Editor cleared');
        }

        // Helper functions
        function showLoading() {
            loadingContentEl.style.display = 'block';
            editorFormEl.style.display = 'none';
            errorAreaEl.style.display = 'none';
            successMessageEl.style.display = 'none';
        }

        function hideLoading() {
            loadingContentEl.style.display = 'none';
        }

        function formatLastModified(lastModified) {
            if (!lastModified) return '';
            try {
                const d = new Date(lastModified);
                if (isNaN(d.getTime())) return '';
                const year = d.getFullYear();
                const month = String(d.getMonth() + 1).padStart(2, '0');
                const day = String(d.getDate()).padStart(2, '0');
                const hours = String(d.getHours()).padStart(2, '0');
                const minutes = String(d.getMinutes()).padStart(2, '0');
                return ` | Last modified: ${year}-${month}-${day} ${hours}:${minutes}`;
            } catch (e) {
                return '';
            }
        }

        function formatPublishedAt(publishedAt) {
            if (!publishedAt) return '';
            try {
                const d = new Date(publishedAt);
                if (isNaN(d.getTime())) return '';
                const year = d.getFullYear();
                const month = String(d.getMonth() + 1).padStart(2, '0');
                const day = String(d.getDate()).padStart(2, '0');
                const hours = String(d.getHours()).padStart(2, '0');
                const minutes = String(d.getMinutes()).padStart(2, '0');
                return ` | Published: ${year}-${month}-${day} ${hours}:${minutes}`;
            } catch (e) {
                return '';
            }
        }

        function showError(message) {
            errorAreaEl.textContent = message;
            errorAreaEl.style.display = 'block';
            successMessageEl.style.display = 'none';
            hideLoading();
        }

        // Simple Component Selector Functions
        let allComponents = [];
        let componentChildrenMap = {};  // parent_path → [child pages]
        let currentCategory = 'all';
        let currentSearch = '';

        function loadComponents() {
            console.log('Loading components...');

            // 主数据源: 从 /canadasite/en/components/ 子页面获取组件列表
            fetch('/api/v1/pages/by-path/canadasite/en/components/children')
                .then(response => {
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    return response.json();
                })
                .then(childPages => {
                    console.log(`Loaded ${childPages.length} component pages from /canadasite/en/components/`);

                    // 将子页面转换为组件对象
                    allComponents = childPages.map(page => ({
                        id: page.id || page.path,
                        name: page.title || page.path.split('/').pop(),
                        description: (page.metadata && page.metadata._description) || page.description || '',
                        category: 'components',
                        source: 'page',
                        path: page.path || '',
                        url: '',
                        pageData: page
                    }));

                    // 使用 backend prefix 参数拉取 components 路径下所有页面
                    fetch('/api/v1/pages/?prefix=/canadasite/en/components/&limit=5000')
                        .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
                        .then(function(allCompPages) {
                            // Build children map: group by parent_path
                            componentChildrenMap = {};
                            allCompPages.forEach(function(p) {
                                if (p && p.parent_path) {
                                    if (!componentChildrenMap[p.parent_path]) {
                                        componentChildrenMap[p.parent_path] = [];
                                    }
                                    componentChildrenMap[p.parent_path].push(p);
                                }
                            });
                            console.log('Component children map built:', Object.keys(componentChildrenMap).length, 'groups');

                            // Also fetch template pages (metadata marked)
                            return fetch('/api/v1/pages/?limit=100')
                                .then(function(r) { if (!r.ok) return []; return r.json(); })
                                .then(function(allPages) {
                                    var extraPages = allPages.filter(function(p) {
                                        return p.metadata && (p.metadata.is_template === true || p.metadata.component_template === true);
                                    });
                                    return extraPages;
                                });
                        })
                        .then(function(extraPages) {
                            // Supplement template pages to allComponents
                            if (extraPages && extraPages.length > 0) {
                                var existingPaths = new Set(allComponents.map(function(c) { return c.path; }));
                                extraPages.forEach(function(page) {
                                    if (!existingPaths.has(page.path)) {
                                        var cat = (page.metadata && page.metadata.category) || 'gcweb';
                                        allComponents.push({
                                            id: page.id || page.path,
                                            name: page.title || page.path.split('/').pop(),
                                            description: page.description || '',
                                            category: cat,
                                            source: 'template',
                                            path: page.path || '',
                                            url: '',
                                            pageData: page
                                        });
                                        existingPaths.add(page.path);
                                    }
                                });
                            }
                            finishLoad();
                        })
                        .catch(function(err) {
                            console.error('Error building component children map:', err);
                            componentChildrenMap = {};
                            finishLoad();
                        });

                    // 补充加载JSON定义的组件(确保wet-*组件不丢失)
                    function finishLoad() {
                        updateComponentCategories();
                        filterComponents();
                        renderSidebarComponents();
                        supplementFromStaticJSON();
                    }
                })
                .catch(error => {
                    console.error('Error loading component children:', error);
                    // 回退到全部页面API
                    fetchPageAPI();
                });

            // 回退: 使用全部页面API
            function fetchPageAPI() {
                console.log('Falling back to /api/v1/pages/?limit=5000...');
                fetch('/api/v1/pages/?limit=5000')
                    .then(response => {
                        if (!response.ok) throw new Error(`HTTP ${response.status}`);
                        return response.json();
                    })
                    .then(pages => {
                        const componentPages = pages.filter(page => {
                            if (page.metadata && page.metadata.is_template === true) return true;
                            if (page.metadata && page.metadata.component_template === true) return true;
                            if (page.parent_path === '/canadasite/en/components') return true;
                            if (page.id && page.id.startsWith('template-')) return true;
                            if (page.parent_path === '/en/template-container' ||
                                (page.path && page.path.startsWith('/en/template-container/'))) return true;
                            return false;
                        });
                        allComponents = componentPages.map(page => ({
                            id: page.id || page.path,
                            name: page.title || 'Unnamed',
                            description: page.description || '',
                            category: (page.metadata && page.metadata.category) || 'basic',
                            source: 'page',
                            path: page.path || '',
                            url: '',
                            pageData: page
                        }));
                        updateComponentCategories();
                        filterComponents();
                        renderSidebarComponents();
                        supplementFromStaticJSON();
                    })
                    .catch(err => {
                        console.error('Page API failed:', err);
                        fallbackToComponentsAPI();
                    });
            }

            // 回退函数:使用原来的组件API
            function fallbackToComponentsAPI() {
                console.log('Loading components from API /api/v1/components/templates...');
                fetch('/api/v1/components/templates')
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! Status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log('Components loaded from API:', data);
                        if (Array.isArray(data) && data.length > 0) {
                            allComponents = data.map(component => ({
                                id: component.name || component.id,
                                name: component.display_name || component.name,
                                description: component.description || '',
                                category: component.category || 'basic',
                                source: component.source || 'database',
                                path: component.path || '',
                                url: component.url || ''
                            }));
                            console.log(`Loaded ${allComponents.length} components from API`);
                            updateComponentCategories();
                            filterComponents();
                            renderSidebarComponents();
                            supplementFromStaticJSON();
                        } else {
                            console.error('No templates found in API response');
                            fallbackToStaticJSON();
                        }
                    })
                    .catch(error => {
                        console.error('Error loading components from API:', error);
                        fallbackToStaticJSON();
                    });
            }

            // 最终回退:使用静态JSON文件
            function fallbackToStaticJSON() {
                console.log('Falling back to static component-templates.json...');
                fetch('/static/component-templates.json')
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! Status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log('Components loaded from fallback JSON:', data);
                        if (data.templates) {
                            allComponents = Object.entries(data.templates).map(([key, component]) => ({
                                id: key,
                                name: component.name || key,
                                description: component.description || '',
                                category: component.category || 'basic',
                                source: component.source || 'database',
                                path: component.path || '',
                                url: component.url || ''
                            }));
                            console.log(`Loaded ${allComponents.length} components from fallback`);
                            updateComponentCategories();
                            filterComponents();
                            renderSidebarComponents();
                        } else {
                            console.error('No templates found in fallback JSON');
                            allComponents = [];
                            renderSidebarComponents();
                        }
                    })
                    .catch(fallbackError => {
                        console.error('Error loading components from fallback:', fallbackError);
                        allComponents = [];
                        renderSidebarComponents();
                    });
            }

            // 回退函数:使用原来的组件API
            function fallbackToComponentsAPI() {
                console.log('Loading components from API /api/v1/components/templates...');
                fetch('/api/v1/components/templates')
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! Status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log('Components loaded from API:', data);
                        if (Array.isArray(data) && data.length > 0) {
                            // API返回的是组件对象数组,每个对象有id、name、display_name等字段
                            allComponents = data.map(component => ({
                                id: component.name || component.id,
                                name: component.display_name || component.name,
                                description: component.description || '',
                                category: component.category || 'basic',
                                source: component.source || 'database',
                                path: component.path || '',
                                url: component.url || ''
                            }));
                            console.log(`Loaded ${allComponents.length} components from API`);
                            updateComponentCategories();
                            filterComponents();
                            renderSidebarComponents();
                            supplementFromStaticJSON();
                        } else {
                            console.error('No templates found in API response');
                            fallbackToStaticJSON();
                        }
                    })
                    .catch(error => {
                        console.error('Error loading components from API:', error);
                        fallbackToStaticJSON();
                    });
            }

            // 最终回退:使用静态JSON文件
            function fallbackToStaticJSON() {
                console.log('Falling back to static component-templates.json...');
                fetch('/static/component-templates.json')
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! Status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log('Components loaded from fallback JSON:', data);
                        if (data.templates) {
                            allComponents = Object.entries(data.templates).map(([key, component]) => ({
                                id: key,
                                name: component.name || key,
                                description: component.description || '',
                                category: component.category || 'basic',
                                source: component.source || 'database',
                                path: component.path || '',
                                url: component.url || ''
                            }));
                            console.log(`Loaded ${allComponents.length} components from fallback`);
                            updateComponentCategories();
                            filterComponents();
                            renderSidebarComponents();
                        } else {
                            console.error('No templates found in fallback JSON');
                            allComponents = [];
                            renderSidebarComponents();
                        }
                    })
                    .catch(fallbackError => {
                        console.error('Error loading components from fallback:', fallbackError);
                        allComponents = [];
                        renderSidebarComponents();
                    });
            }

            // 补充加载:从component-templates.json合并组件(按id去重)
            function supplementFromStaticJSON() {
                console.log('Supplementing components from static JSON...');
                fetch('/static/component-templates.json')
                    .then(response => {
                        if (!response.ok) throw new Error(`HTTP ${response.status}`);
                        return response.json();
                    })
                    .then(data => {
                        let extraComponents = [];
                        if (data.templates) {
                            extraComponents = Object.entries(data.templates).map(([key, component]) => ({
                                id: key,
                                name: component.name || key,
                                description: component.description || '',
                                category: component.category || 'basic',
                                source: 'static',
                                path: component.path || '',
                                url: component.url || ''
                            }));
                        } else if (Array.isArray(data)) {
                            extraComponents = data.map(c => ({
                                id: c.id || c.name,
                                name: c.name || c.display_name || c.id,
                                description: c.description || '',
                                category: c.category || 'basic',
                                source: 'static',
                                path: c.path || '',
                                url: c.url || ''
                            }));
                        }
                        // 合并去重
                        const existingIds = new Set(allComponents.map(c => c.id));
                        const newCount = extraComponents.filter(c => !existingIds.has(c.id)).length;
                        extraComponents.forEach(c => {
                            if (!existingIds.has(c.id)) {
                                allComponents.push(c);
                                existingIds.add(c.id);
                            }
                        });
                        if (newCount > 0) {
                            console.log(`Supplemented ${newCount} components from static JSON`);
                            updateComponentCategories();
                            filterComponents();
                            renderSidebarComponents();
                        }
                    })
                    .catch(err => console.warn('Could not supplement from static JSON:', err));
            }
        }

        function renderSidebarComponents() {
            const sidebarEl = document.getElementById('filebot-components-sidebar');
            if (!sidebarEl) {
                console.warn('Sidebar components element not found');
                return;
            }

            if (!allComponents || allComponents.length === 0) {
                sidebarEl.innerHTML = '<li class="filebot-component-item">No components loaded</li>';
                return;
            }

            // Clear loading message
            sidebarEl.innerHTML = '';

            // Add help message about parameter dialogs
            const helpLi = document.createElement('li');
            helpLi.className = 'filebot-component-help';
            helpLi.style.padding = '8px 12px';
            helpLi.style.fontSize = '11px';
            helpLi.style.color = '#666';
            helpLi.style.borderBottom = '1px solid #eee';
            helpLi.style.fontStyle = 'italic';
            helpLi.innerHTML = '📁 = click to expand | Click component to insert';
            sidebarEl.appendChild(helpLi);

            // Group components by category for better organization
            const componentsByCategory = {};
            allComponents.forEach(component => {
                const category = component.category || 'basic';
                if (!componentsByCategory[category]) {
                    componentsByCategory[category] = [];
                }
                componentsByCategory[category].push(component);
            });

            // Keep track of which parents we've already rendered children for
            const renderedParentPaths = new Set();

            // Render categories and components
            Object.keys(componentsByCategory).sort().forEach(category => {
                const components = componentsByCategory[category];

                // Add category header
                const categoryLi = document.createElement('li');
                categoryLi.className = 'filebot-component-category';
                categoryLi.innerHTML = `<strong>${category.charAt(0).toUpperCase() + category.slice(1)}</strong>`;
                sidebarEl.appendChild(categoryLi);

                // Add components in this category
                components.forEach(component => {
                    const parentPath = component.path.replace(/\/+$/, '');
                    const children = componentChildrenMap[parentPath];
                    const hasChildren = children && children.length > 0;

                    if (hasChildren) {
                        // Skip if we already rendered this parent's children
                        if (renderedParentPaths.has(parentPath)) return;
                        renderedParentPaths.add(parentPath);
                    }

                    const li = document.createElement('li');
                    li.className = 'filebot-component-item' + (hasChildren ? ' component-parent' : '');
                    li.dataset.componentId = component.id;

                    // Check if this component requires parameter dialog
                    const needsDialog = window.componentsWithDialog &&
                                      window.componentsWithDialog.includes(component.id);

                    // Build title with explanation
                    let titleText = component.description || component.name;
                    if (hasChildren) {
                        titleText += ' (click to expand/collapse variants)';
                    } else if (needsDialog) {
                        titleText += ' (needs config params)';
                    } else {
                        titleText += ' (direct insert)';
                    }
                    li.title = titleText;

                    // Create content with optional gear icon and expand arrow
                    const contentSpan = document.createElement('span');
                    contentSpan.style.display = 'flex';
                    contentSpan.style.justifyContent = 'space-between';
                    contentSpan.style.alignItems = 'center';
                    contentSpan.style.width = '100%';

                    const nameSpan = document.createElement('span');
                    if (hasChildren) {
                        // Parent: show ▶ / 📁 icon, not insertable directly
                        nameSpan.innerHTML = `<span class="component-arrow">▶</span> 📁 ${component.name}`;
                    } else {
                        nameSpan.textContent = component.name;
                    }

                    const iconSpan = document.createElement('span');
                    if (needsDialog && !hasChildren) {
                        iconSpan.textContent = '⚙️';
                        iconSpan.title = 'Click to configure parameters';
                        iconSpan.style.marginLeft = '8px';
                        iconSpan.style.fontSize = '12px';
                        iconSpan.style.opacity = '0.7';
                    }

                    contentSpan.appendChild(nameSpan);
                    contentSpan.appendChild(iconSpan);
                    li.appendChild(contentSpan);

                    // Click behavior: expand/collapse for parents, insert for children/leaf
                    if (hasChildren) {
                        // Parent: create a nested list for children
                        const childUl = document.createElement('ul');
                        childUl.className = 'component-children';
                        childUl.style.display = 'none';  // collapsed by default
                        childUl.style.paddingLeft = '16px';
                        childUl.style.listStyle = 'none';
                        childUl.style.margin = '0';

                        children.forEach(child => {
                            const childLi = document.createElement('li');
                            // Use child's actual path - display its title or last segment
                            const childName = child.title || child.path.split('/').pop();
                            childLi.className = 'filebot-component-item component-child';
                            childLi.textContent = childName;
                            childLi.title = (child.description || childName) + ' (click to insert)';
                            childLi.style.paddingLeft = '8px';
                            childLi.style.fontSize = '12px';
                            childLi.style.cursor = 'pointer';
                            childLi.style.borderLeft = '2px solid #ddd';
                            childLi.style.margin = '2px 0';

                            childLi.addEventListener('click', (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                insertPath(child.path);
                            });

                            childUl.appendChild(childLi);
                        });

                        li.appendChild(childUl);

                        // Toggle expand/collapse on click
                        let expanded = false;
                        li.addEventListener('click', (e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            expanded = !expanded;
                            childUl.style.display = expanded ? 'block' : 'none';
                            const arrow = li.querySelector('.component-arrow');
                            if (arrow) {
                                arrow.textContent = expanded ? '▼' : '▶';
                            }
                        });
                    } else {
                        // Leaf component: insert on click
                        li.addEventListener('click', (e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            if (component.path) {
                                insertPath(component.path);
                            } else {
                                insertComponent(component.id);
                            }
                        });
                    }

                    sidebarEl.appendChild(li);
                });
            });

            console.log(`Rendered ${allComponents.length} components in sidebar with grouping`);
        }

        function updateComponentCategories() {
            const categoriesEl = document.getElementById('components-categories');
            if (!categoriesEl) return;

            // Get unique categories
            const categories = ['all'];
            allComponents.forEach(component => {
                if (component.category && !categories.includes(component.category)) {
                    categories.push(component.category);
                }
            });

            // Clear existing categories (keeping "All Components")
            const allItem = categoriesEl.querySelector('[data-category="all"]');
            categoriesEl.innerHTML = '';
            if (allItem) {
                categoriesEl.appendChild(allItem);
            }

            // Add category items
            categories.forEach(category => {
                if (category === 'all') return; // Already added
                const li = document.createElement('li');
                li.textContent = category.charAt(0).toUpperCase() + category.slice(1);
                li.setAttribute('data-category', category);
                li.addEventListener('click', () => {
                    document.querySelectorAll('#components-categories li').forEach(item => {
                        item.classList.remove('active');
                    });
                    li.classList.add('active');
                    currentCategory = category;
                    filterComponents();
                });
                categoriesEl.appendChild(li);
            });
        }

        function filterComponents() {
            const componentsListEl = document.getElementById('components-list');
            if (!componentsListEl) return;

            let filteredComponents = [...allComponents];

            // Filter by category
            if (currentCategory !== 'all') {
                filteredComponents = filteredComponents.filter(component =>
                    component.category === currentCategory
                );
            }

            // Filter by search
            if (currentSearch.trim() !== '') {
                const searchTerm = currentSearch.toLowerCase();
                filteredComponents = filteredComponents.filter(component =>
                    component.name.toLowerCase().includes(searchTerm) ||
                    component.description.toLowerCase().includes(searchTerm) ||
                    component.category.toLowerCase().includes(searchTerm)
                );
            }

            // Clear list
            componentsListEl.innerHTML = '';

            // Add components
            if (filteredComponents.length === 0) {
                componentsListEl.innerHTML = '<div class="no-components">No components found</div>';
                return;
            }

            filteredComponents.forEach(component => {
                const card = document.createElement('div');
                card.className = 'component-card';
                card.setAttribute('data-component-id', component.id);

                // Determine icon based on category
                let icon = '🧩';
                if (component.category === 'navigation') icon = '🧭';
                else if (component.category === 'form') icon = '📝';
                else if (component.category === 'content') icon = '📄';
                else if (component.category === 'social') icon = '🤝';
                else if (component.category === 'government') icon = '🏛️';
                else if (component.category === 'basic') icon = '🔧';

                card.innerHTML = `
                    <div class="component-icon">${icon}</div>
                    <div class="component-name">${component.name}</div>
                    <div class="component-description">${component.description || 'No description'}</div>
                    <div class="component-category">${component.category}</div>
                `;

                card.addEventListener('click', () => {
                    insertComponent(component.id);
                    hideComponentsModal();
                });

                componentsListEl.appendChild(card);
            });
        }

        function showComponentsModal() {
            const modal = document.getElementById('components-modal');
            if (!modal) return;

            modal.classList.add('show');
            loadComponents();

            // Focus search input
            setTimeout(() => {
                const searchInput = document.getElementById('components-search-input');
                if (searchInput) searchInput.focus();
            }, 100);
        }

        function hideComponentsModal() {
            const modal = document.getElementById('components-modal');
            if (modal) {
                modal.classList.remove('show');
            }
            // Reset search
            const searchInput = document.getElementById('components-search-input');
            if (searchInput) {
                searchInput.value = '';
                currentSearch = '';
            }
        }

        function checkMustacheLoaded() {
            const isLoaded = !!window.Mustache;
            console.log('Mustache.js loaded:', isLoaded);
            if (isLoaded) {
                console.log('Mustache.js version:', Mustache?.version || 'unknown');
                console.log('Mustache.render function:', typeof Mustache?.render);
            } else {
                console.warn('❌ Mustache.js not loaded!');
                console.warn('Checking CDN status...');

                // Try to load Mustache.js manually as fallback
                const loadMustacheManually = function() {
                    console.log('Attempting to load Mustache.js manually...');
                    const script = document.createElement('script');
                    script.src = 'https://unpkg.com/mustache@3.2.1/mustache.min.js';
                    script.onload = () => {
                        console.log('✅ Mustache.js manually loaded successfully!');
                        console.log('Mustache.js version:', Mustache?.version || 'unknown');
                        // Update any disabled buttons
                        const templateBtn = document.getElementById('template-button');
                        if (templateBtn && templateBtn.disabled) {
                            templateBtn.disabled = false;
                            templateBtn.title = 'Insert Mustache template';
                            templateBtn.innerHTML = '🎨 Template';
                            console.log('✅ Template button enabled');
                        }
                    };
                    script.onerror = () => {
                        console.error('❌ Failed to load Mustache.js from unpkg');
                    };
                    document.head.appendChild(script);
                };

                // Offer manual load option
                console.log('To manually load Mustache.js, run in console:');
                console.log('const s=document.createElement("script");s.src="https://unpkg.com/mustache@3.2.1/mustache.min.js";document.head.appendChild(s);');

                // Auto-attempt after 3 seconds if still not loaded
                setTimeout(() => {
                    if (!window.Mustache) {
                        loadMustacheManually();
                    }
                }, 3000);
            }
            return isLoaded;
        }

        // Add template button to editor UI
        function addTemplateButtonToUI() {
            console.log('addTemplateButtonToUI called');

            // Check Mustache.js status
            const mustacheLoaded = checkMustacheLoaded();

            // Check if button already exists
            const existingBtn = document.getElementById('template-button');
            if (existingBtn) {
                console.log('✅ Template button already exists');
                // Update button state based on Mustache.js loading
                if (!mustacheLoaded) {
                    existingBtn.disabled = true;
                    existingBtn.title = 'Mustache.js not loaded - Click for details';
                    existingBtn.innerHTML = '🎨❌ Template';
                    existingBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        alert('Mustache.js template engine not loaded. Check console for details.');
                        checkMustacheLoaded();
                    });
                }
                return true;
            }

            // Find the component insertion button area
            const insertComponentBtn = document.getElementById('insert-component-btn');
            if (!insertComponentBtn) {
                console.log('❌ Insert component button not found');
                console.log('Available elements with ID insert-component-btn:', document.querySelectorAll('#insert-component-btn').length);
                return false;
            }

            console.log('✅ Found component button:', insertComponentBtn);
            console.log('Component button parent:', insertComponentBtn.parentNode);
            console.log('Component button next sibling:', insertComponentBtn.nextSibling);

            // Create template button
            const templateBtn = document.createElement('button');
            templateBtn.id = 'template-button';
            templateBtn.className = 'tox-btn tox-btn--secondary tox-btn--icon';
            templateBtn.style.marginLeft = '8px';

            // Set button state based on Mustache.js loading
            if (mustacheLoaded) {
                templateBtn.innerHTML = '🎨 Template';
                templateBtn.title = 'Insert Mustache template';
                templateBtn.addEventListener('click', function(e) {
                    if (typeof showTemplateSelector === 'function') {
                        showTemplateSelector();
                    } else {
                        console.error('showTemplateSelector not defined');
                        alert('Template selector function not available. Please refresh the page.');
                    }
                });
            } else {
                templateBtn.innerHTML = '🎨❌ Template';
                templateBtn.title = 'Mustache.js not loaded - Click for details';
                templateBtn.disabled = true;
                templateBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    alert('Mustache.js template engine not loaded. Check console for details.');
                    checkMustacheLoaded();
                });
                console.warn('⚠️ Template button created but disabled - Mustache.js not loaded');
            }

            // Add button after insert component button
            // If nextSibling is null, insertBefore will add at the end (which is fine)
            try {
                insertComponentBtn.parentNode.insertBefore(templateBtn, insertComponentBtn.nextSibling);
                console.log('✅ Template button successfully inserted');
                console.log('Template button position:', templateBtn.parentNode === insertComponentBtn.parentNode ? 'Same parent' : 'Different parent');
                console.log('Template button inserted after component button:', templateBtn.previousSibling === insertComponentBtn ? 'Yes' : 'No');
            } catch (error) {
                console.error('❌ Failed to insert template button:', error);
                // Fallback: append to the same parent
                insertComponentBtn.parentNode.appendChild(templateBtn);
                console.log('✅ Template button added via fallback');
            }

            console.log('✅ Template button added to UI');
            return true;
        }

        // Function to show template selector modal
        function showTemplateSelector() {
            console.log('showTemplateSelector called - checking registry availability');

            // Use ONLY window.templateRegistry to avoid scope issues
            let registry = window.templateRegistry;

            // If window.templateRegistry doesn't exist, check if we can find it elsewhere
            if (typeof registry === 'undefined') {
                console.log('window.templateRegistry not found, checking other sources...');

                // Try to find templateRegistry in global scope (non-window)
                try {
                    // Use eval in try-catch to check if variable exists without throwing
                    if (typeof templateRegistry !== 'undefined') {
                        registry = templateRegistry;
                        console.log('Found templateRegistry in global scope');
                    }
                } catch (e) {
                    console.log('templateRegistry not accessible:', e.message);
                }
            }

            // If still undefined, create a fallback registry
            if (typeof registry === 'undefined') {
                console.warn('templateRegistry not found in any scope, creating fallback');
                registry = {
                    'canada-ca-header': {
                        name: 'Canada.ca Header (Fallback)',
                        template: '<header><h1>Canada.ca Header Fallback</h1></header>',
                        variables: {}
                    },
                    'canada-ca-footer': {
                        name: 'Canada.ca Footer (Fallback)',
                        template: '<footer><p>Canada.ca Footer Fallback</p></footer>',
                        variables: {}
                    }
                };
                // Also set it globally for future use
                window.templateRegistry = registry;
                console.log('Fallback registry created with', Object.keys(registry).length, 'templates');
            } else {
                console.log('Registry found with', Object.keys(registry).length, 'templates');
            }

            // Create modal HTML
            const modalHtml = `
                <div id="template-selector-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; display: flex; align-items: center; justify-content: center;">
                    <div style="background: white; border-radius: 8px; width: 90%; max-width: 800px; max-height: 80vh; overflow-y: auto; padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <h2 style="margin: 0;">🎨 Mustache Templates</h2>
                            <button id="close-template-modal" style="background: none; border: none; font-size: 24px; cursor: pointer;">×</button>
                        </div>

                        <p>Select a Canada.ca template to insert into the editor:</p>

                        <div id="template-list" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; margin-top: 20px;">
                            <!-- Templates will be inserted here -->
                        </div>

                        <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd;">
                            <h3>Custom Template</h3>
                            <textarea id="custom-template" placeholder="Enter your Mustache template here..." style="width: 100%; height: 150px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 10px;"></textarea>
                            <textarea id="custom-data" placeholder='Enter JSON data (optional) e.g., {"title": "My Title"}' style="width: 100%; height: 100px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 10px;"></textarea>
                            <button id="insert-custom-template" style="background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">Insert Custom Template</button>
                        </div>
                    </div>
                </div>
            `;

            // Add modal to page
            const modalContainer = document.createElement('div');
            modalContainer.innerHTML = modalHtml;
            document.body.appendChild(modalContainer);

            // Populate template list
            const templateList = document.getElementById('template-list');
            for (const [id, template] of Object.entries(registry)) {
                const templateCard = document.createElement('div');
                templateCard.style.border = '1px solid #ddd';
                templateCard.style.borderRadius = '6px';
                templateCard.style.padding = '15px';
                templateCard.style.cursor = 'pointer';
                templateCard.style.transition = 'all 0.2s';
                templateCard.innerHTML = `
                    <h4 style="margin: 0 0 10px 0;">${template.name}</h4>
                    <p style="margin: 0; color: #666; font-size: 14px;">ID: <code>${id}</code></p>
                    <p style="margin: 10px 0 0 0; color: #888; font-size: 13px;">${Object.keys(template.variables).length} variables available</p>
                `;

                templateCard.addEventListener('mouseenter', () => {
                    templateCard.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
                });
                templateCard.addEventListener('mouseleave', () => {
                    templateCard.style.boxShadow = 'none';
                });

                templateCard.addEventListener('click', () => {
                    insertMustacheTemplate(id);
                    closeTemplateModal();
                });

                templateList.appendChild(templateCard);
            }

            // Close modal function
            function closeTemplateModal() {
                document.body.removeChild(modalContainer);
            }

            // Event listeners
            document.getElementById('close-template-modal').addEventListener('click', closeTemplateModal);

            // Close on outside click
            modalContainer.addEventListener('click', (e) => {
                if (e.target === modalContainer) {
                    closeTemplateModal();
                }
            });

            // Custom template insertion
            document.getElementById('insert-custom-template').addEventListener('click', () => {
                const customTemplate = document.getElementById('custom-template').value;
                const customDataText = document.getElementById('custom-data').value;

                if (!customTemplate.trim()) {
                    alert('Please enter a template');
                    return;
                }

                let data = {};
                if (customDataText.trim()) {
                    try {
                        data = JSON.parse(customDataText);
                    } catch (e) {
                        alert('Invalid JSON data: ' + e.message);
                        return;
                    }
                }

                try {
                    const rendered = Mustache.render(customTemplate, data);
                    if (window.tinymce && window.tinymce.activeEditor) {
                        window.tinymce.activeEditor.insertContent(rendered);
                        closeTemplateModal();
                    } else {
                        alert('Editor not available');
                    }
                } catch (error) {
                    alert('Error rendering template: ' + error.message);
                }
            });
        }

        // Expose function globally
        window.showTemplateSelector = showTemplateSelector;

        function initializeComponentsModal() {
            // Initialize retry counter if not exists
            if (typeof initializeComponentsModal.retryCount === 'undefined') {
                initializeComponentsModal.retryCount = 0;
            }

            // Check max retries (10 attempts = ~5 seconds)
            if (initializeComponentsModal.retryCount >= 10) {
                console.error('❌ Failed to initialize components modal after 10 retries');
                console.error('Possible causes:');
                console.error('1. TinyMCE not loaded properly');
                console.error('2. Toolbar selectors outdated');
                console.error('3. Editor container ID changed');
                console.error('Please check browser console for details');
                return;
            }

            console.log('initializeComponentsModal called (attempt ' + (initializeComponentsModal.retryCount + 1) + '/10)');

            // Check if TinyMCE editor is loaded
            if (!window.tinymce) {
                console.log('❌ TinyMCE not loaded yet, waiting...');
                initializeComponentsModal.retryCount++;
                setTimeout(initializeComponentsModal, 500);
                return;
            }

            // Check if editor instance exists
            const editor = tinymce.get('wysiwyg-editor-container');
            if (!editor) {
                console.log('❌ TinyMCE editor instance not ready, waiting...');
                initializeComponentsModal.retryCount++;
                setTimeout(initializeComponentsModal, 500);
                return;
            }

            console.log('✅ TinyMCE editor instance found:', editor);

            // Try multiple toolbar selectors
            const selectors = [
                '.tox-toolbar__primary',
                '.tox-editor-header',
                '.tox-toolbar',
                '#wysiwyg-editor-container + .tox-tinymce .tox-toolbar__primary',
                '#wysiwyg-editor-container ~ .tox-tinymce .tox-toolbar__primary'
            ];

            let toolbar = null;
            for (const selector of selectors) {
                toolbar = document.querySelector(selector);
                if (toolbar) {
                    console.log(`✅ Found toolbar with selector: ${selector}`);
                    break;
                }
            }

            // Last resort: find any TinyMCE toolbar
            if (!toolbar) {
                const allToolbars = document.querySelectorAll('.tox-toolbar__primary, .tox-toolbar');
                if (allToolbars.length > 0) {
                    toolbar = allToolbars[0];
                    console.log('✅ Found toolbar via general search:', toolbar);
                }
            }

            // Create components button
            const componentsButton = document.createElement('button');
            componentsButton.className = 'tox-btn tox-btn--secondary tox-btn--icon';
            componentsButton.innerHTML = '🧩 Components';
            componentsButton.style.marginLeft = '8px';
            componentsButton.title = 'Insert Component';
            componentsButton.id = 'insert-component-btn';
            componentsButton.addEventListener('click', showComponentsModal);

            if (toolbar) {
                console.log('Adding components button to toolbar');
                toolbar.appendChild(componentsButton);
                console.log('✅ Components button added with ID:', componentsButton.id);
                console.log('✅ Components button parent:', componentsButton.parentNode);

                // Wait a bit for DOM to settle, then add template button
                setTimeout(() => {
                    console.log('Now attempting to add template button...');
                    if (typeof addTemplateButtonToUI === 'function') {
                        addTemplateButtonToUI();
                    } else {
                        console.error('❌ addTemplateButtonToUI is not defined yet, retrying...');
                        // Try again after a short delay
                        setTimeout(() => {
                            if (typeof addTemplateButtonToUI === 'function') {
                                addTemplateButtonToUI();
                            } else {
                                console.error('❌ addTemplateButtonToUI still not defined after retry');
                            }
                        }, 500);
                    }
                }, 100);
            } else {
                console.log('❌ No toolbar found, trying alternative placement');

                // Try to find the AI Assistant button container
                const aiButton = document.querySelector('[aria-label="AI Assistant (Beta)"]');
                if (aiButton && aiButton.parentNode) {
                    console.log('✅ Found AI Assistant button, inserting near it');
                    aiButton.parentNode.insertBefore(componentsButton, aiButton);
                    console.log('✅ Components button added near AI Assistant');

                    setTimeout(() => {
                        console.log('Now attempting to add template button...');
                        if (typeof addTemplateButtonToUI === 'function') {
                            addTemplateButtonToUI();
                        } else {
                            console.error('❌ addTemplateButtonToUI is not defined yet, retrying...');
                            // Try again after a short delay
                            setTimeout(() => {
                                if (typeof addTemplateButtonToUI === 'function') {
                                    addTemplateButtonToUI();
                                } else {
                                    console.error('❌ addTemplateButtonToUI still not defined after retry');
                                }
                            }, 500);
                        }
                    }, 100);
                } else {
                    console.log('❌ Could not find suitable placement, will retry in 500ms');
                    initializeComponentsModal.retryCount++;
                    setTimeout(initializeComponentsModal, 500);
                }
            }

            // Setup modal close button
            const closeButton = document.getElementById('components-modal-close');
            if (closeButton) {
                closeButton.addEventListener('click', hideComponentsModal);
            }

            // Setup search input
            const searchInput = document.getElementById('components-search-input');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    currentSearch = e.target.value;
                    filterComponents();
                });
            }

            // Close modal when clicking outside
            const modal = document.getElementById('components-modal');
            if (modal) {
                modal.addEventListener('click', (e) => {
                    if (e.target === modal) {
                        hideComponentsModal();
                    }
                });
            }

            // Handle escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && modal && modal.classList.contains('show')) {
                    hideComponentsModal();
                }
            });
        }

        // Initialize components modal when TinyMCE is ready
        function initializeComponentsWhenReady() {
            // Initialize retry counter if not exists
            if (typeof initializeComponentsWhenReady.retryCount === 'undefined') {
                initializeComponentsWhenReady.retryCount = 0;
            }

            // Check max retries (15 attempts = ~7.5 seconds)
            if (initializeComponentsWhenReady.retryCount >= 15) {
                console.error('❌ TinyMCE not available after 15 retries, attempting modal initialization anyway');
                console.error('This may indicate TinyMCE failed to load or encountered an error');
                // Continue to modal initialization for last attempt
                setTimeout(initializeComponentsModal, 500);
                return;
            }

            console.log('initializeComponentsWhenReady called (attempt ' + (initializeComponentsWhenReady.retryCount + 1) + '/15)');

            if (typeof tinymce !== 'undefined' && tinymce.activeEditor) {
                console.log('✅ TinyMCE ready, proceeding to modal initialization');
                setTimeout(initializeComponentsModal, 500);
            } else {
                console.log('❌ TinyMCE not ready yet, waiting...');
                initializeComponentsWhenReady.retryCount++;
                setTimeout(initializeComponentsWhenReady, 500);
            }
        }

        // Start initialization
        setTimeout(initializeComponentsWhenReady, 1000);

        // Get component HTML by type
        function getComponentHTML(componentType) {
            let componentHtml = '';

            switch(componentType) {
                case 'button':
                    componentHtml = '<button type="button" class="btn btn-primary webbot-component">Button</button>';
                    break;
                case 'button-success':
                    componentHtml = '<button type="button" class="btn btn-success webbot-component">Success</button>';
                    break;
                case 'button-info':
                    componentHtml = '<button type="button" class="btn btn-info webbot-component">Info</button>';
                    break;
                case 'button-warning':
                    componentHtml = '<button type="button" class="btn btn-warning webbot-component">Warning</button>';
                    break;
                case 'button-danger':
                    componentHtml = '<button type="button" class="btn btn-danger webbot-component">Danger</button>';
                    break;
                case 'table':
                    componentHtml = '<table class="table table-striped webbot-component">\n' +
                                    '  <thead>\n' +
                                    '    <tr>\n' +
                                    '      <th scope="col">#</th>\n' +
                                    '      <th scope="col">Header 1</th>\n' +
                                    '      <th scope="col">Header 2</th>\n' +
                                    '    </tr>\n' +
                                    '  </thead>\n' +
                                    '  <tbody>\n' +
                                    '    <tr>\n' +
                                    '      <th scope="row">1</th>\n' +
                                    '      <td>Data 1</td>\n' +
                                    '      <td>Data 2</td>\n' +
                                    '    </tr>\n' +
                                    '  </tbody>\n' +
                                    '</table>';
                    break;
                                    '</section>';
                    break;
                case 'alert-success':
                    componentHtml = '<section class="alert alert-success webbot-component">\n' +
                                    '  <h3>Success alert</h3>\n' +
                                    '  <p>Alert details.</p>\n' +
                                    '</section>';
                    break;
                case 'alert-info':
                    componentHtml = '<section class="alert alert-info webbot-component">\n' +
                                    '  <h3>Info alert</h3>\n' +
                                    '  <p>Alert details.</p>\n' +
                                    '</section>';
                    break;
                case 'alert-danger-link':
                    componentHtml = '<section class="alert alert-danger webbot-component">\n' +
                                    '  <h3>(Info Title)</h3>\n' +
                                    '  <p> Danger content goes here <a href="#" class="alert-link">link text</a>.</p>\n' +
                                    '</section>';
                    break;
                case 'alert-warning-link':
                    componentHtml = '<section class="alert alert-warning webbot-component">\n' +
                                    '  <h3>(Warning Title)</h3>\n' +
                                    '  <p> Warning content goes here <a href="#" class="alert-link">link text</a>.</p>\n' +
                                    '</section>';
                    break;
                case 'alert-success-link':
                    componentHtml = '<section class="alert alert-success webbot-component">\n' +
                                    '  <h3>(Success Title)</h3>\n' +
                                    '  <p> Success content goes here <a href="#" class="alert-link">link text</a>.</p>\n' +
                                    '</section>';
                    break;
                case 'alert-info-link':
                    componentHtml = '<section class="alert alert-info webbot-component">\n' +
                                    '  <h3>(Info Title)</h3>\n' +
                                    '  <p> Info content goes here <a href="#" class="alert-link">link text</a>.</p>\n' +
                                    '</section>';
                    break;
                case 'breadcrumb':
                    componentHtml = '<nav class="wb-breadcrumb webbot-component" role="navigation" aria-label="Breadcrumb">\n' +
                                    '  <h2 class="wb-inv">You are here:</h2>\n' +
                                    '  <ul class="breadcrumb">\n' +
                                    '    <li><a href="https://www.canada.ca/en.html">canada.ca</a></li>\n' +
                                    '    <li><a href="#">[Section]</a></li>\n' +
                                    '    <li><a href="#">[Subsection]</a></li>\n' +
                                    '    <li>[Current page]</li>\n' +
                                    '  </ul>\n' +
                                    '</nav>';
                    break;
                case 'sidebar':
                    componentHtml = '<nav class="wb-sec col-md-3 col-md-pull-9" role="navigation" id="wb-sec" typeof="SiteNavigationElement">\n' +
                                    '  <h2 class="wb-inv">Section menu</h2>\n' +
                                    '  <ul class="list-group menu list-unstyled">\n' +
                                    '    <li><h3 class="wb-navcurr"><a href="#">[Section 1]</a></h3>\n' +
                                    '      <ul class="list-group menu list-unstyled">\n' +
                                    '        <li><a href="#">[Page 1.1]</a></li>\n' +
                                    '        <li><a href="#">[Page 1.2]</a></li>\n' +
                                    '      </ul>\n' +
                                    '    </li>\n' +
                                    '    <li><h3><a href="#">[Section 2]</a></h3>\n' +
                                    '      <ul class="list-group menu list-unstyled">\n' +
                                    '        <li><a href="#">[Page 2.1]</a></li>\n' +
                                    '        <li><a href="#">[Page 2.2]</a></li>\n' +
                                    '      </ul>\n' +
                                    '    </li>\n' +
                                    '  </ul>\n' +
                                    '</nav>';
                    break;
                case 'footer':
                    componentHtml = '<footer id="wb-info">\n' +
                                    '  <div class="landscape">\n' +
                                    '    <nav class="container wb-navcurr">\n' +
                                    '      <h2 class="wb-inv">About government</h2>\n' +
                                    '      <ul class="list-unstyled colcount-sm-2 colcount-md-3">\n' +
                                    '        <li><a href="https://www.canada.ca/en/contact.html">Contact us</a></li>\n' +
                                    '        <li><a href="https://www.canada.ca/en/government/dept.html">Departments and agencies</a></li>\n' +
                                    '        <li><a href="https://www.canada.ca/en/government/publicservice.html">Public service and military</a></li>\n' +
                                    '        <li><a href="https://www.canada.ca/en/news.html">News</a></li>\n' +
                                    '        <li><a href="https://www.canada.ca/en/government/system/laws.html">Treaties, laws and regulations</a></li>\n' +
                                    '        <li><a href="https://www.canada.ca/en/transparency/reporting.html">Government-wide reporting</a></li>\n' +
                                    '        <li><a href="http://pm.gc.ca/eng">Prime Minister</a></li>\n' +
                                    '        <li><a href="https://www.canada.ca/en/government/system.html">How government works</a></li>\n' +
                                    '        <li><a href="http://open.canada.ca/en">Open government</a></li>\n' +
                                    '      </ul>\n' +
                                    '    </nav>\n' +
                                    '  </div>\n' +
                                    '  <div class="brand">\n' +
                                    '    <div class="container">\n' +
                                    '      <div class="row">\n' +
                                    '        <div class="col-xs-6 visible-sm visible-xs tofpg">\n' +
                                    '          <a href="#wb-cont">Top of Page <span class="glyphicon glyphicon-chevron-up"></span></a>\n' +
                                    '        </div>\n' +
                                    '        <div class="col-xs-6 col-md-12 text-right">\n' +
                                    '          <object type="image/svg+xml" tabindex="-1" role="img" data="/dist/GCWeb/assets/wmms-blk.svg" aria-label="Symbol of the Government of Canada"></object>\n' +
                                    '        </div>\n' +
                                    '      </div>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</footer>';
                    break;
                case 'search':
                    componentHtml = '<section id="wb-srch" class="col-md-8 col-md-offset-2 text-right visible-md visible-lg">\n' +
                                    '  <h2>Search</h2>\n' +
                                    '  <form action="https://recherche-search.gc.ca/rGs/s_r?#wb-land" method="get" role="search" class="form-inline">\n' +
                                    '    <div class="form-group">\n' +
                                    '      <label for="wb-srch-q" class="wb-inv">Search Canada.ca</label>\n' +
                                    '      <input id="wb-srch-q" list="wb-srch-q-ac" class="wb-srch-q form-control" name="q" type="search" value="" size="27" maxlength="150" placeholder="Search Canada.ca">\n' +
                                    '      <datalist id="wb-srch-q-ac"></datalist>\n' +
                                    '    </div>\n' +
                                    '    <div class="form-group submit">\n' +
                                    '      <button type="submit" id="wb-srch-sub" class="btn btn-primary btn-small" name="wb-srch-sub"><span class="glyphicon glyphicon-search"></span><span class="wb-inv">Search</span></button>\n' +
                                    '    </div>\n' +
                                    '  </form>\n' +
                                    '</section>';
                    break;
                case 'introduction':
                    componentHtml = '<section class="gc-intro webbot-component">\n' +
                                    '  <h1 class="wb-inv">Page title</h1>\n' +
                                    '  <div class="row">\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <p>Introduction text goes here.</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <p>More details or supplementary information.</p>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'introduction-full-image':
                    componentHtml = '<section class="gc-intro webbot-component gc-intro-full-image" style="background-image: url(/dist/GCWeb/assets/intro-bg.jpg);">\n' +
                                    '  <h1 class="wb-inv">Page title</h1>\n' +
                                    '  <div class="row">\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <p>Introduction text goes here.</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <p>More details or supplementary information.</p>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'introduction-half-image':
                    componentHtml = '<section class="gc-intro webbot-component gc-intro-half-image" style="background-image: url(/dist/GCWeb/assets/intro-bg.jpg);">\n' +
                                    '  <h1 class="wb-inv">Page title</h1>\n' +
                                    '  <div class="row">\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <p>Introduction text goes here.</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <p>More details or supplementary information.</p>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'services-and-information':
                    componentHtml = '<section class="gc-srvinfo webbot-component">\n' +
                                    '  <h2>Services and information</h2>\n' +
                                    '  <div class="row">\n' +
                                    '    <div class="col-md-4">\n' +
                                    '      <h3><a href="#">Service 1</a></h3>\n' +
                                    '      <p>Description of service 1.</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-4">\n' +
                                    '      <h3><a href="#">Service 2</a></h3>\n' +
                                    '      <p>Description of service 2.</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-4">\n' +
                                    '      <h3><a href="#">Service 3</a></h3>\n' +
                                    '      <p>Description of service 3.</p>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'services-and-information-2-columns':
                    componentHtml = '<section class="gc-srvinfo webbot-component">\n' +
                                    '  <h2>Services and information</h2>\n' +
                                    '  <div class="row">\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <h3><a href="#">Service 1</a></h3>\n' +
                                    '      <p>Description of service 1.</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <h3><a href="#">Service 2</a></h3>\n' +
                                    '      <p>Description of service 2.</p>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'services-and-information-list':
                    componentHtml = '<section class="gc-srvinfo webbot-component">\n' +
                                    '  <h2>Services and information</h2>\n' +
                                    '  <ul class="colcount-md-2">\n' +
                                    '    <li><a href="#">Service 1</a></li>\n' +
                                    '    <li><a href="#">Service 2</a></li>\n' +
                                    '    <li><a href="#">Service 3</a></li>\n' +
                                    '    <li><a href="#">Service 4</a></li>\n' +
                                    '    <li><a href="#">Service 5</a></li>\n' +
                                    '    <li><a href="#">Service 6</a></li>\n' +
                                    '  </ul>\n' +
                                    '</section>';
                    break;
                case 'feature-link':
                    componentHtml = '<section class="gc-featured-link webbot-component">\n' +
                                    '  <div class="container">\n' +
                                    '    <h2 class="wb-inv">Spotlight on</h2>\n' +
                                    '    <p><a class="stretched-link" href="#">[Promotion title]</a></p>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'feature-link-dark':
                    componentHtml = '<section class="gc-featured-link webbot-component" data-bg-color="#26374A">\n' +
                                    '  <div class="container">\n' +
                                    '    <h2 class="wb-inv">Spotlight on</h2>\n' +
                                    '    <p><a class="stretched-link" href="#">[Promotion title]</a></p>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'feature-link-light':
                    componentHtml = '<section class="gc-featured-link webbot-component" data-bg-color="#F5F5F5">\n' +
                                    '  <div class="container">\n' +
                                    '    <h2 class="wb-inv">Spotlight on</h2>\n' +
                                    '    <p><a class="stretched-link" href="#">[Promotion title]</a></p>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'feature-link-gray':
                    componentHtml = '<section class="gc-featured-link webbot-component" data-bg-color="#8F8F8F">\n' +
                                    '  <div class="container">\n' +
                                    '    <h2 class="wb-inv">Spotlight on</h2>\n' +
                                    '    <p><a class="stretched-link" href="#">[Promotion title]</a></p>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'government-initiatives':
                    componentHtml = '<section class="gc-initiatives webbot-component">\n' +
                                    '  <h2>Government initiatives</h2>\n' +
                                    '  <div class="row">\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <h3><a href="#" class="stretched-link">Initiative 1</a></h3>\n' +
                                    '      <p>Description of initiative 1.</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <h3><a href="#" class="stretched-link">Initiative 2</a></h3>\n' +
                                    '      <p>Description of initiative 2.</p>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'features':
                    componentHtml = '<section class="gc-features webbot-component">\n' +
                                    '  <h2>Features</h2>\n' +
                                    '  <div class="row">\n' +
                                    '    <div class="col-md-4">\n' +
                                    '      <h3><a href="#">Feature 1</a></h3>\n' +
                                    '      <p>Description of feature 1.</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-4">\n' +
                                    '      <h3><a href="#">Feature 2</a></h3>\n' +
                                    '      <p>Description of feature 2.</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-4">\n' +
                                    '      <h3><a href="#">Feature 3</a></h3>\n' +
                                    '      <p>Description of feature 3.</p>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'most-requested-links':
                    componentHtml = '<section class="gc-most-requested webbot-component">\n' +
                                    '  <h2>Most requested</h2>\n' +
                                    '  <ul class="colcount-md-2">\n' +
                                    '    <li><a href="#">Link 1</a></li>\n' +
                                    '    <li><a href="#">Link 2</a></li>\n' +
                                    '    <li><a href="#">Link 3</a></li>\n' +
                                    '    <li><a href="#">Link 4</a></li>\n' +
                                    '    <li><a href="#">Link 5</a></li>\n' +
                                    '    <li><a href="#">Link 6</a></li>\n' +
                                    '  </ul>\n' +
                                    '</section>';
                    break;
                case 'social-media':
                case 'follow-us':
                    componentHtml = '<section class="gc-followus webbot-component">\n' +
                                    '  <h2>On social media</h2>\n' +
                                    '  <ul>\n' +
                                    '    <li>\n' +
                                    '      <a href="#facebook" class="facebook"><span class="wb-inv">Facebook: </span>FacebookPageName</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="x-social"><span class="wb-inv">X: </span>@XAccount</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="youtube"><span class="wb-inv">YouTube: </span>YouTubeName</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="instagram"><span class="wb-inv">Instagram: </span>InstagramName</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="linkedin"><span class="wb-inv">LinkedIn: </span>LinkedInName</a>\n' +
                                    '    </li>\n' +
                                    '  </ul>\n' +
                                    '</section>\n' +
                                    '<section id="facebook" class="modal-dialog modal-content overlay-def mfp-hide">\n' +
                                    '  <header class="modal-header">\n' +
                                    '    <h2 class="modal-title" id="lbx-title">Facebook</h2>\n' +
                                    '  </header>\n' +
                                    '  <div class="modal-body">\n' +
                                    '    <ul class="list-unstyled lst-spcd">\n' +
                                    '      <li>\n' +
                                    '        <a href="#" rel="external">[First Facebook account title]</a>\n' +
                                    '      </li>\n' +
                                    '      <li>\n' +
                                    '        <a href="#" rel="external">[Second Facebook account title]</a>\n' +
                                    '      </li>\n' +
                                    '    </ul>\n' +
                                    '  </div>\n' +
                                    '  <div class="modal-footer">\n' +
                                    '    <button type="button" class="btn btn-sm btn-primary pull-left popup-modal-dismiss">Close<span class="wb-inv">Close overlay</span></button>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'follow-us-horizontal':
                case 'social-media-horizontal':
                    componentHtml = '<section class="gc-followus gc-followus-horizontal webbot-component">\n' +
                                    '  <h2 class="wb-inv">On social media</h2>\n' +
                                    '  <ul>\n' +
                                    '    <li>\n' +
                                    '      <a href="#facebook" class="facebook"><span class="wb-inv">Facebook: </span>FacebookPageName</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="x-social"><span class="wb-inv">X: </span>@XAccount</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="youtube"><span class="wb-inv">YouTube: </span>YouTubeName</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="instagram"><span class="wb-inv">Instagram: </span>InstagramName</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="linkedin"><span class="wb-inv">LinkedIn: </span>LinkedInName</a>\n' +
                                    '    </li>\n' +
                                    '  </ul>\n' +
                                    '</section>\n' +
                                    '<section id="facebook" class="modal-dialog modal-content overlay-def mfp-hide">\n' +
                                    '  <header class="modal-header">\n' +
                                    '    <h2 class="modal-title" id="lbx-title">Facebook</h2>\n' +
                                    '  </header>\n' +
                                    '  <div class="modal-body">\n' +
                                    '    <ul class="list-unstyled lst-spcd">\n' +
                                    '      <li>\n' +
                                    '        <a href="#" rel="external">[First Facebook account title]</a>\n' +
                                    '      </li>\n' +
                                    '      <li>\n' +
                                    '        <a href="#" rel="external">[Second Facebook account title]</a>\n' +
                                    '      </li>\n' +
                                    '    </ul>\n' +
                                    '</section>';
                    break;
                case 'calendar':
                case 'events':
                    componentHtml = '<section class="gc-calendar webbot-component">\n' +
                                    '  <h2>Calendar of events</h2>\n' +
                                    '  <div class="row">\n' +
                                    '    <div class="col-md-4">\n' +
                                    '      <div class="well">\n' +
                                    '        <h3>Event 1</h3>\n' +
                                    '        <p><strong>Date:</strong> January 15, 2026</p>\n' +
                                    '        <p><strong>Location:</strong> Online</p>\n' +
                                    '        <p>Description of event 1.</p>\n' +
                                    '        <a href="#" class="btn btn-primary">Register</a>\n' +
                                    '      </div>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-4">\n' +
                                    '      <div class="well">\n' +
                                    '        <h3>Event 2</h3>\n' +
                                    '        <p><strong>Date:</strong> February 20, 2026</p>\n' +
                                    '        <p><strong>Location:</strong> Ottawa, ON</p>\n' +
                                    '        <p>Description of event 2.</p>\n' +
                                    '        <a href="#" class="btn btn-primary">Register</a>\n' +
                                    '      </div>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-4">\n' +
                                    '      <div class="well">\n' +
                                    '        <h3>Event 3</h3>\n' +
                                    '        <p><strong>Date:</strong> March 10, 2026</p>\n' +
                                    '        <p><strong>Location:</strong> Online</p>\n' +
                                    '        <p>Description of event 3.</p>\n' +
                                    '        <a href="#" class="btn btn-primary">Register</a>\n' +
                                    '      </div>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'theme-page-jobs':
                    componentHtml = '<section class="gc-theme-jobs webbot-component">\n' +
                                    '  <h1>Jobs and the workplace</h1>\n' +
                                    '  <div class="row">\n' +
                                    '    <div class="col-md-8">\n' +
                                    '      <h2>Find a job</h2>\n' +
                                    '      <p>Looking for employment? Explore job opportunities and resources.</p>\n' +
                                    '      <ul>\n' +
                                    '        <li><a href="#">Job Bank</a></li>\n' +
                                    '        <li><a href="#">Job search tools</a></li>\n' +
                                    '        <li><a href="#">Career planning</a></li>\n' +
                                    '      </ul>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-4">\n' +
                                    '      <h2>Most requested</h2>\n' +
                                    '      <ul>\n' +
                                    '        <li><a href="#">EI benefits</a></li>\n' +
                                    '        <li><a href="#">Work permits</a></li>\n' +
                                    '        <li><a href="#">Labour standards</a></li>\n' +
                                    '      </ul>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'topic-template':
                    componentHtml = '<section class="gc-topic-template webbot-component">\n' +
                                    '  <h1>Topic Title</h1>\n' +
                                    '  <div class="row">\n' +
                                    '    <div class="col-md-8">\n' +
                                    '      <p>Topic description goes here.</p>\n' +
                                    '      <h2>Most requested</h2>\n' +
                                    '      <ul class="colcount-md-2">\n' +
                                    '        <li><a href="#">Link 1</a></li>\n' +
                                    '        <li><a href="#">Link 2</a></li>\n' +
                                    '        <li><a href="#">Link 3</a></li>\n' +
                                    '        <li><a href="#">Link 4</a></li>\n' +
                                    '        <li><a href="#">Link 5</a></li>\n' +
                                    '        <li><a href="#">Link 6</a></li>\n' +
                                    '      </ul>\n' +
                                    '      <h2>Services and information</h2>\n' +
                                    '      <div class="row">\n' +
                                    '        <div class="col-md-6">\n' +
                                    '          <h3><a href="#">Service 1</a></h3>\n' +
                                    '          <p>Description of service 1.</p>\n' +
                                    '        </div>\n' +
                                    '        <div class="col-md-6">\n' +
                                    '          <h3><a href="#">Service 2</a></h3>\n' +
                                    '          <p>Description of service 2.</p>\n' +
                                    '        </div>\n' +
                                    '      </div>\n' +
                                    '      <h2>Featured content</h2>\n' +
                                    '      <div class="row">\n' +
                                    '        <div class="col-md-6">\n' +
                                    '          <div class="well">\n' +
                                    '            <h3>Feature 1</h3>\n' +
                                    '            <p>Description of feature 1.</p>\n' +
                                    '            <a href="#" class="btn btn-primary">Learn more</a>\n' +
                                    '          </div>\n' +
                                    '        </div>\n' +
                                    '        <div class="col-md-6">\n' +
                                    '          <div class="well">\n' +
                                    '            <h3>Feature 2</h3>\n' +
                                    '            <p>Description of feature 2.</p>\n' +
                                    '            <a href="#" class="btn btn-primary">Learn more</a>\n' +
                                    '          </div>\n' +
                                    '        </div>\n' +
                                    '      </div>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-4">\n' +
                                    '      <h2>On social media</h2>\n' +
                                    '      <section class="gc-followus">\n' +
                                    '        <ul>\n' +
                                    '          <li>\n' +
                                    '            <a href="#facebook" class="facebook"><span class="wb-inv">Facebook: </span>FacebookPageName</a>\n' +
                                    '          </li>\n' +
                                    '          <li>\n' +
                                    '            <a href="#" rel="external" class="x-social"><span class="wb-inv">X: </span>@XAccount</a>\n' +
                                    '          </li>\n' +
                                    '          <li>\n' +
                                    '            <a href="#" rel="external" class="youtube"><span class="wb-inv">YouTube: </span>YouTubeName</a>\n' +
                                    '          </li>\n' +
                                    '          <li>\n' +
                                    '            <a href="#" rel="external" class="instagram"><span class="wb-inv">Instagram: </span>InstagramName</a>\n' +
                                    '          </li>\n' +
                                    '          <li>\n' +
                                    '            <a href="#" rel="external" class="linkedin"><span class="wb-inv">LinkedIn: </span>LinkedInName</a>\n' +
                                    '          </li>\n' +
                                    '        </ul>\n' +
                                    '</section>';
                    break;
                default:
                    componentHtml = `<div class="webbot-component">${componentType} component</div>`;
            }

            return componentHtml;
        }

        // Insert component at cursor position
        /**
         * Canada.ca component templates - parameterized.
         * Colorable components (button, alert) use a shared color mapper
         * instead of creating one variant per color.
         */
        const CANADA_CSS_PREFIXES = {
            'button': 'btn',
            'alert': 'alert',
            'label': 'label',
            'badge': 'label',
            'background': 'bg',
            'text': 'text'
        };

        const CANADA_COLOR_MAP_TEMPLATE = {
            'danger': 'danger',
            'success': 'success',
            'info': 'info',
            'warning': 'warning',
            'primary': 'primary',
            'red': 'danger',
            'green': 'success',
            'blue': 'info',
            'yellow': 'warning'
        };

        /**
         * Build HTML for a colorable component by type + color.
         * Keeps templates DRY - no more 5 button variants, 8 alert variants, etc.
         */
        function makeButtonHtml(color, label) {
            const cls = CANADA_CSS_PREFIXES['button'] + '-' + (CANADA_COLOR_MAP_TEMPLATE[color] || 'primary');
            return '<button type="button" class="btn ' + cls + ' webbot-component">' + (label || 'Button') + '</button>';
        }

        function makeAlertHtml(color, withLink) {
            const cls = 'alert-' + (CANADA_COLOR_MAP_TEMPLATE[color] || 'info');
            const title = color === 'danger' ? 'Danger alert' :
                          color === 'warning' ? 'Warning alert' :
                          color === 'success' ? 'Success alert' : 'Info alert';
            if (withLink) {
                return '<section class="alert ' + cls + ' webbot-component">\n' +
                       '  <h3>(' + title + ')</h3>\n' +
                       '  <p> Content goes here <a href="#" class="alert-link">link text</a>.</p>\n' +
                       '</section>';
            }
            return '<div class="alert ' + cls + ' webbot-component">\n' +
                   '  <h3>' + title + '</h3>\n' +
                   '  <p>This is an alert box.</p>\n' +
                   '</div>';
        }

        async function insertComponent(componentType, options) {
            if (!tinyMceEditor) {
                console.error('TinyMCE editor not initialized');
                return false;
            }

            let componentHtml;

            // Map old compound names (button-danger, alert-success-link)
            // to simple type + options
            var match;
            var parsedType = componentType;
            var parsedColor = (options && options.color) || null;
            var parsedLink = (options && options.link) || false;

            // Parse 'type-color' compound format (e.g. 'button-danger')
            match = componentType.match(/^(button|alert)-(danger|success|info|warning)$/);
            if (match) {
                parsedType = match[1];
                parsedColor = match[2];
            }

            // Parse 'type-color-link' format (e.g. 'alert-success-link')
            match = componentType.match(/^(alert)-(danger|success|info|warning)-link$/);
            if (match) {
                parsedType = match[1];
                parsedColor = match[2];
                parsedLink = true;
            }

            // Handle new format: button(color: danger)
            match = componentType.match(/^(button|alert)\(color:\s*(\w+)\)$/);
            if (match) {
                parsedType = match[1];
                parsedColor = match[2];
            }

            // Helper: extract inner <footer> from full HTML doc (DB stores with <html><body> wrapper)
            function _cleanFooterHtml(raw) {
                var m = raw.match(/<footer[^>]*>[\s\S]*?<\/footer>/i);
                if (m) return m[0];
                var b = raw.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
                if (b) return b[1].trim();
                return raw;
            }

            // Special async handling for footer: fetch real Canada.ca footer via mustache API
            if (parsedType === 'footer') {
                try {
                    const currentPagePath = window.currentPageData?.path || '/' + (window.currentPageData?.language || 'en');
                    const lang = window.currentPageData?.language || 'en';
                    const dsUrl = '/api/v1/getfooter?path=' + encodeURIComponent(currentPagePath);
                    const mustacheResp = await fetch('/mustache/' + lang + '/mustache-templates/getfooter?datasource=' + encodeURIComponent(dsUrl));
                    if (mustacheResp.ok) {
                        var footerHtml = await mustacheResp.text();
                        tinyMceEditor.insertContent(_cleanFooterHtml(footerHtml));
                        return true;
                    }
                } catch (e) {
                    console.error('Footer fetch via mustache failed:', e);
                }
                // Fallback: try direct API
                try {
                    const currentPagePath = window.currentPageData?.path || '/' + (window.currentPageData?.language || 'en');
                    const fallbackResp = await fetch('/api/v1/getfooter?path=' + encodeURIComponent(currentPagePath));
                    if (fallbackResp.ok) {
                        const fd = await fallbackResp.json();
                        var footerHtml = _cleanFooterHtml(fd.institution_level?.content || '') + _cleanFooterHtml(fd.language_level?.content || '');
                        if (footerHtml.trim()) {
                            tinyMceEditor.insertContent(footerHtml);
                            return true;
                        }
                    }
                } catch (e2) {
                    console.error('Footer fallback fetch failed:', e2);
                }
                // If async methods failed, fall through to hardcoded fallback
                console.warn('Footer API fetch failed, using hardcoded fallback');
            }

            switch(parsedType) {
                case 'button':
                    componentHtml = makeButtonHtml(parsedColor || 'primary');
                    break;
                case 'alert':
                    componentHtml = makeAlertHtml(parsedColor || 'info', parsedLink);
                    break;
                case 'table':
                    componentHtml = '<table class="table table-striped webbot-component">\n' +
                                    '  <thead>\n' +
                                    '    <tr>\n' +
                                    '      <th scope="col">#</th>\n' +
                                    '      <th scope="col">Header 1</th>\n' +
                                    '      <th scope="col">Header 2</th>\n' +
                                    '    </tr>\n' +
                                    '  </thead>\n' +
                                    '  <tbody>\n' +
                                    '    <tr>\n' +
                                    '      <th scope="row">1</th>\n' +
                                    '      <td>Data 1</td>\n' +
                                    '      <td>Data 2</td>\n' +
                                    '    </tr>\n' +
                                    '  </tbody>\n' +
                                    '</table>';
                    break;
                    componentHtml = '<nav class="wb-breadcrumb webbot-component" role="navigation" aria-label="Breadcrumb">\n' +
                                    '  <h2 class="wb-inv">You are here:</h2>\n' +
                                    '  <ul class="breadcrumb">\n' +
                                    '    <li><a href="https://www.canada.ca/en.html">canada.ca</a></li>\n' +
                                    '    <li><a href="#">Section</a></li>\n' +
                                    '    <li>Current page</li>\n' +
                                    '  </ul>\n' +
                                    '</nav>';
                    break;
                case 'sidebar':
                    componentHtml = '<nav class="wb-sec col-md-3 col-md-pull-9 webbot-component" role="navigation" aria-labelledby="wb-sec-h">\n' +
                                    '  <h2 id="wb-sec-h">Section Menu</h2>\n' +
                                    '  <ul class="list-group menu list-unstyled">\n' +
                                    '    <li><a href="#">Menu Item 1</a></li>\n' +
                                    '    <li><a href="#">Menu Item 2</a></li>\n' +
                                    '    <li><a href="#">Menu Item 3</a></li>\n' +
                                    '  </ul>\n' +
                                    '</nav>';
                    break;
                case 'footer':
                    componentHtml = '<footer class="pagedetails container webbot-component">\n' +
                                    '  <h2 class="wb-inv">Page details</h2>\n' +
                                    '  <div class="row">\n' +
                                    '    <div class="col-sm-8 col-md-9 col-lg-9">\n' +
                                    '      <p>Date modified: 2026-04-02</p>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</footer>';
                    break;
                case 'search':
                    componentHtml = '<form action="https://www.canada.ca/en/sr/srb.html" method="get" role="search" class="form-inline webbot-component">\n' +
                                    '  <div class="input-group">\n' +
                                    '    <label for="search" class="wb-inv">Search Canada.ca</label>\n' +
                                    '    <input id="search" name="q" type="search" size="34" maxlength="170" class="form-control" placeholder="Search Canada.ca">\n' +
                                    '    <div class="input-group-btn">\n' +
                                    '      <button type="submit" class="btn btn-primary">\n' +
                                    '        <span class="glyphicon glyphicon-search"></span>\n' +
                                    '        <span class="wb-inv">Search</span>\n' +
                                    '      </button>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</form>';
                    break;
                case 'introduction':
                    componentHtml = '<div class="webbot-component">\n' +
                                    '  <h1 property="name" id="wb-cont">Introduction block</h1>\n' +
                                    '  <p>The introduction block pattern introduces the content of a landing page.</p>\n' +
                                    '  <p><a class="btn btn-call-to-action" href="#">Super task button</a></p>\n' +
                                    '</div>';
                    break;
                case 'introduction-full-image':
                    componentHtml = '<div class="bg-center bg-cover webbot-component" data-bgimg-srcset="https://wet-boew.github.io/vocab/wb/utilities#no-image 991w, https://dummyimage.com/1200x726/667eea/764ba2.png 992w">\n' +
                                    '  <div class="container">\n' +
                                    '    <div class="row">\n' +
                                    '      <div class="col-md-7">\n' +
                                    '        <h1 property="name" id="wb-cont">Introduction block with full-width image</h1>\n' +
                                    '        <p>The introduction block pattern introduces the content of a landing page.</p>\n' +
                                    '        <p><a class="btn btn-call-to-action" href="#">Supertask button</a></p>\n' +
                                    '      </div>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</div>';
                    break;
                case 'introduction-half-image':
                    componentHtml = '<div class="row webbot-component">\n' +
                                    '  <div class="col-md-6">\n' +
                                    '    <h1 property="name" id="wb-cont">Introduction block with half-width image</h1>\n' +
                                    '    <p>The introduction block pattern introduces the content of a landing page.</p>\n' +
                                    '    <p><a class="btn btn-call-to-action" href="#">Supertask button</a></p>\n' +
                                    '  </div>\n' +
                                    '  <div class="col-md-6 hidden-sm hidden-xs">\n' +
                                    '    <img src="https://dummyimage.com/520x200/667eea/764ba2.png" alt="" class="img-responsive pull-right mrgn-tp-lg">\n' +
                                    '  </div>\n' +
                                    '</div>';
                    break;
                case 'most-requested':
                    componentHtml = '<section class="gc-most-requested webbot-component">\n' +
                                    '  <div class="container">\n' +
                                    '    <h2>Most requested</h2>\n' +
                                    '    <ul>\n' +
                                    '      <li><a href="#">[Top task hyperlink 1]</a></li>\n' +
                                    '      <li><a href="#">[Top task hyperlink 2]</a></li>\n' +
                                    '      <li><a href="#">[Top task hyperlink 3]</a></li>\n' +
                                    '      <li><a href="#">[Top task hyperlink 4]</a></li>\n' +
                                    '      <li><a href="#">[Top task hyperlink 5]</a></li>\n' +
                                    '      <li><a href="#">[Top task hyperlink 6]</a></li>\n' +
                                    '    </ul>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'feature-link':
                    componentHtml = '<section class="gc-featured-link webbot-component">\n' +
                                    '  <div class="container">\n' +
                                    '    <h2 class="wb-inv">Spotlight on</h2>\n' +
                                    '    <p><a class="stretched-link" href="#">[Promotion title]</a></p>\n' +
                                    '    <p>Long description [Optional]</p>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'government-initiatives':
                    // 政府倡议组件:两列布局,拉伸链接,标题"Government initiatives"
                    componentHtml = '<section class="gc-features webbot-component">\n' +
                                    '  <h2>Government initiatives</h2>\n' +
                                    '  <div class="row wb-eqht-grd">\n' +
                                    '    <div class="col-sm-6">\n' +
                                    '      <div class="well well-sm eqht-trgt">\n' +
                                    '        <img src="https://dummyimage.com/520x200/667eea/764ba2.png" alt="Government initiative image">\n' +
                                    '        <h3><a class="stretched-link" href="#">[Feature hyperlink text]</a></h3>\n' +
                                    '        <p>Brief description of the feature being promoted.</p>\n' +
                                    '      </div>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-sm-6">\n' +
                                    '      <div class="well well-sm eqht-trgt">\n' +
                                    '        <img src="https://dummyimage.com/520x200/667eea/764ba2.png" alt="Government initiative image">\n' +
                                    '        <h3><a class="stretched-link" href="#">[Feature hyperlink text]</a></h3>\n' +
                                    '        <p>Brief description of the feature being promoted.</p>\n' +
                                    '      </div>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'features':
                    // 标准Features组件:三列布局,通用标题"Features"
                    componentHtml = '<section class="gc-features webbot-component">\n' +
                                    '  <h2>Features</h2>\n' +
                                    '  <div class="row wb-eqht-grd">\n' +
                                    '    <div class="col-lg-4 col-sm-6">\n' +
                                    '      <div class="well well-sm eqht-trgt">\n' +
                                    '        <img src="https://dummyimage.com/360x203/667eea/764ba2.png" alt="Feature image">\n' +
                                    '        <h3><a href="#">[Feature hyperlink text]</a></h3>\n' +
                                    '        <p>Brief description of the feature being promoted.</p>\n' +
                                    '      </div>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-lg-4 col-sm-6">\n' +
                                    '      <div class="well well-sm eqht-trgt">\n' +
                                    '        <img src="https://dummyimage.com/360x203/667eea/764ba2.png" alt="Feature image">\n' +
                                    '        <h3><a href="#">[Feature hyperlink text]</a></h3>\n' +
                                    '        <p>Brief description of the feature being promoted.</p>\n' +
                                    '      </div>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-lg-4 col-sm-6">\n' +
                                    '      <div class="well well-sm eqht-trgt">\n' +
                                    '        <img src="https://dummyimage.com/360x203/667eea/764ba2.png" alt="Feature image">\n' +
                                    '        <h3><a href="#">[Feature hyperlink text]</a></h3>\n' +
                                    '        <p>Brief description of the feature being promoted.</p>\n' +
                                    '      </div>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'services-info-3col':
                    componentHtml = '<section class="gc-srvinfo webbot-component">\n' +
                                    '  <h2>Services and information</h2>\n' +
                                    '  <div class="wb-eqht row">\n' +
                                    '    <div class="col-md-6 col-lg-4">\n' +
                                    '      <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-6 col-lg-4">\n' +
                                    '      <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-6 col-lg-4">\n' +
                                    '      <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-6 col-lg-4">\n' +
                                    '      <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-6 col-lg-4">\n' +
                                    '      <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-6 col-lg-4">\n' +
                                    '      <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'services-info-2col':
                    componentHtml = '<section class="gc-srvinfo webbot-component">\n' +
                                    '  <h2>Services and information</h2>\n' +
                                    '  <div class="wb-eqht row">\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '    </div>\n' +
                                    '    <div class="col-md-6">\n' +
                                    '      <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'services-info-list':
                    componentHtml = '<section class="gc-srvinfo webbot-component">\n' +
                                    '  <h2>Services and information</h2>\n' +
                                    '  <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '  <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '  <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '  <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '  <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '  <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '</section>';
                    break;
                case 'feature-link-dark':
                    componentHtml = '<section class="gc-featured-link webbot-component" data-bg-color="#005B61">\n' +
                                    '  <div class="container">\n' +
                                    '    <h2 class="wb-inv">Spotlight on</h2>\n' +
                                    '    <p><a class="stretched-link" href="#">[Promotion title]</a></p>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'feature-link-light':
                    componentHtml = '<section class="gc-featured-link webbot-component" data-bg-color="#99dade">\n' +
                                    '  <div class="container">\n' +
                                    '    <h2 class="wb-inv">Spotlight on</h2>\n' +
                                    '    <p><a class="stretched-link" href="#">[Promotion title]</a></p>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'feature-link-gray':
                    componentHtml = '<section class="gc-featured-link webbot-component" data-bg-color="#8F8F8F">\n' +
                                    '  <div class="container">\n' +
                                    '    <h2 class="wb-inv">Spotlight on</h2>\n' +
                                    '    <p><a class="stretched-link" href="#">[Promotion title]</a></p>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'follow-us':
                    componentHtml = '<section class="gc-followus webbot-component">\n' +
                                    '  <h2>On social media</h2>\n' +
                                    '  <ul>\n' +
                                    '    <li>\n' +
                                    '      <a href="#facebook" class="facebook"><span class="wb-inv">Facebook: </span>FacebookPageName</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="x-social"><span class="wb-inv">X: </span>@XAccount</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="youtube"><span class="wb-inv">YouTube: </span>YouTubeName</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="instagram"><span class="wb-inv">Instagram: </span>InstagramName</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="linkedin"><span class="wb-inv">LinkedIn: </span>LinkedInName</a>\n' +
                                    '    </li>\n' +
                                    '  </ul>\n' +
                                    '</section>\n' +
                                    '<section id="facebook" class="modal-dialog modal-content overlay-def mfp-hide">\n' +
                                    '  <header class="modal-header">\n' +
                                    '    <h2 class="modal-title" id="lbx-title">Facebook</h2>\n' +
                                    '  </header>\n' +
                                    '  <div class="modal-body">\n' +
                                    '    <ul class="list-unstyled lst-spcd">\n' +
                                    '      <li>\n' +
                                    '        <a href="#" rel="external">[First Facebook account title]</a>\n' +
                                    '      </li>\n' +
                                    '      <li>\n' +
                                    '        <a href="#" rel="external">[Second Facebook account title]</a>\n' +
                                    '      </li>\n' +
                                    '    </ul>\n' +
                                    '  </div>\n' +
                                    '  <div class="modal-footer">\n' +
                                    '    <button type="button" class="btn btn-sm btn-primary pull-left popup-modal-dismiss">Close<span class="wb-inv">Close overlay</span></button>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'follow-us-horizontal':
                    componentHtml = '<section class="gc-followus webbot-component">\n' +
                                    '  <h2>On social media</h2>\n' +
                                    '  <ul class="list-inline">\n' +
                                    '    <li>\n' +
                                    '      <a href="#facebook" class="facebook"><span class="wb-inv">Facebook: </span>FacebookPageName</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="x-social"><span class="wb-inv">X: </span>@XAccount</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="youtube"><span class="wb-inv">YouTube: </span>YouTubeName</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="instagram"><span class="wb-inv">Instagram: </span>InstagramName</a>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <a href="#" rel="external" class="linkedin"><span class="wb-inv">LinkedIn: </span>LinkedInName</a>\n' +
                                    '    </li>\n' +
                                    '  </ul>\n' +
                                    '</section>\n' +
                                    '<section id="facebook" class="modal-dialog modal-content overlay-def mfp-hide">\n' +
                                    '  <header class="modal-header">\n' +
                                    '    <h2 class="modal-title" id="lbx-title">Facebook</h2>\n' +
                                    '  </header>\n' +
                                    '  <div class="modal-body">\n' +
                                    '    <ul class="list-unstyled lst-spcd">\n' +
                                    '      <li>\n' +
                                    '        <a href="#" rel="external">[First Facebook account title]</a>\n' +
                                    '      </li>\n' +
                                    '      <li>\n' +
                                    '        <a href="#" rel="external">[Second Facebook account title]</a>\n' +
                                    '      </li>\n' +
                                    '    </ul>\n' +
                                    '  </div>\n' +
                                    '  <div class="modal-footer">\n' +
                                    '    <button type="button" class="btn btn-sm btn-primary pull-left popup-modal-dismiss">Close<span class="wb-inv">Close overlay</span></button>\n' +
                                    '  </div>\n' +
                                    '</section>';
                    break;
                case 'calendar-events':
                    componentHtml = '<div id="calendar1"></div>\n\n' +
                                    '<div class="wb-calevt webbot-component" data-calevt-src="calendar1">\n' +
                                    '  <ul>\n' +
                                    '    <li>\n' +
                                    '      <section>\n' +
                                    '        <h4><a href="https://www.canada.ca" rel="external">Single-Day Event</a></h4>\n' +
                                    '        <p><time datetime="2013-03-11">March 11th, 2013</time></p>\n' +
                                    '        <p>Event Description</p>\n' +
                                    '      </section>\n' +
                                    '    </li>\n' +
                                    '    <li>\n' +
                                    '      <section>\n' +
                                    '        <h4><a href="https://www.canada.ca" rel="external">Multi-Day Event</a></h4>\n' +
                                    '        <p><time datetime="2013-03-12">March 12th, 2013</time> to <time datetime="2013-03-14">March 14th, 2013</time></p>\n' +
                                    '        <p>Another event description with longer text to show how the calendar component displays multiple events.</p>\n' +
                                    '      </section>\n' +
                                    '    </li>\n' +
                                    '  </ul>\n' +
                                    '</div>';
                    break;
                case 'theme-page-jobs':
                    componentHtml = '<div id="gridContainer" class="webbot-component">\n' +
                                    '  <nav id="theme-nav">\n' +
                                    '    <div class="container">\n' +
                                    '      <h2 class="wb-inv">Themes menu</h2>\n' +
                                    '      <a class="wb-sl" href="#wb-cont">Skip to main content</a>\n' +
                                    '      <button id="menu-btn" class="btn btn-primary"><span class="wb-inv">Toggle </span>Menu<span class="glyphicon glyphicon-chevron-down"></span></button>\n' +
                                    '      <ul class="list-unstyled">\n' +
                                    '        <li><a href="theme-en.html">Jobs</a></li>\n' +
                                    '        <li><a href="#">National security and defence</a></li>\n' +
                                    '      </ul>\n' +
                                    '    </div>\n' +
                                    '  </nav>\n' +
                                    '  <section>\n' +
                                    '    <div class="container">\n' +
                                    '      <h1 id="wb-cont">Jobs</h1>\n' +
                                    '    </div>\n' +
                                    '    <section class="gc-most-requested">\n' +
                                    '      <div class="container">\n' +
                                    '        <h2>Most requested</h2>\n' +
                                    '        <ul>\n' +
                                    '          <li><a href="#">View your records of employment</a></li>\n' +
                                    '        </ul>\n' +
                                    '      </div>\n' +
                                    '    </section>\n' +
                                    '    <div class="container">\n' +
                                    '      <section class="gc-srvinfo">\n' +
                                    '        <h2 class="wb-inv">Services and information</h2>\n' +
                                    '        <div class="wb-eqht-grd row">\n' +
                                    '          <div class="col-md-6">\n' +
                                    '            <h3><a href="#">Find a job</a></h3>\n' +
                                    '            <p>Search for jobs in Canada, apply or extend a work permit, get a Social Insurance Number (SIN), a criminal record check or security clearance</p>\n' +
                                    '          </div>\n' +
                                    '          <div class="col-md-6">\n' +
                                    '            <h3><a href="#">Funding for jobs and training</a></h3>\n' +
                                    '            <p>Find funding programs, grants and contributions that help support jobs, training, and social development</p>\n' +
                                    '          </div>\n' +
                                    '        </div>\n' +
                                    '      </section>\n' +
                                    '    </div>\n' +
                                    '  </section>\n' +
                                    '</div>';
                    break;
                case 'topic-template':
                    componentHtml = '<div id="topic-template" class="webbot-component">\n' +
                                    '  <div class="container">\n' +
                                    '    <div class="row">\n' +
                                    '      <div class="col-md-6"><h1 property="name" id="wb-cont">[Topic title]</h1><p>1-2 sentences that describe the topics and top tasks that can be accessed on this page.</p></div>\n' +
                                    '      <div class="col-md-6 hidden-sm hidden-xs">\n' +
                                    '        <img src="https://dummyimage.com/520x200/000000/FFFFFF.png" alt="" class="img-responsive pull-right mrgn-tp-lg">\n' +
                                    '      </div>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '  <section class="gc-most-requested">\n' +
                                    '    <div class="container">\n' +
                                    '      <h2>Most requested</h2>\n' +
                                    '      <ul>\n' +
                                    '        <li><a href="#">[Top task hyperlink with a very long task name that spans over two lines 1]</a></li>\n' +
                                    '        <li><a href="#">[Top task hyperlink 2]</a></li>\n' +
                                    '        <li><a href="#">[Top task hyperlink 3]</a></li>\n' +
                                    '        <li><a href="#">[Top task hyperlink 4]</a></li>\n' +
                                    '        <li><a href="#">[Top task hyperlink 5]</a></li>\n' +
                                    '        <li><a href="#">[Top task hyperlink with a very long task name that spans over two lines 6]</a></li>\n' +
                                    '      </ul>\n' +
                                    '    </div>\n' +
                                    '  </section>\n' +
                                    '  <div class="container">\n' +
                                    '    <section class="gc-srvinfo">\n' +
                                    '      <h2 class="wb-inv">Services and information</h2>\n' +
                                    '      <div class="row wb-eqht-grd">\n' +
                                    '        <div class="col-lg-4 col-md-6">\n' +
                                    '          <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '          <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '        </div>\n' +
                                    '        <div class="col-lg-4 col-md-6">\n' +
                                    '          <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '          <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '        </div>\n' +
                                    '        <div class="col-lg-4 col-md-6">\n' +
                                    '          <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '          <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '        </div>\n' +
                                    '        <div class="col-lg-4 col-md-6">\n' +
                                    '          <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '          <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '        </div>\n' +
                                    '        <div class="col-lg-4 col-md-6">\n' +
                                    '          <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '          <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '        </div>\n' +
                                    '        <div class="col-lg-4 col-md-6">\n' +
                                    '          <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '          <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '        </div>\n' +
                                    '        <div class="col-lg-4 col-md-6">\n' +
                                    '          <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '          <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '        </div>\n' +
                                    '        <div class="col-lg-4 col-md-6">\n' +
                                    '          <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '          <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '        </div>\n' +
                                    '        <div class="col-lg-4 col-md-6">\n' +
                                    '          <h3><a href="#">[Hyperlink text]</a></h3>\n' +
                                    '          <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n' +
                                    '        </div>\n' +
                                    '      </div>\n' +
                                    '    </section>\n' +
                                    '    <div class="row mrgn-tp-xl">\n' +
                                    '      <div class="col-md-8">\n' +
                                    '        <section class="gc-features">\n' +
                                    '          <h2 class="wb-inv">Featured</h2>\n' +
                                    '          <div class="row">\n' +
                                    '            <div class="col-sm-6">\n' +
                                    '              <img src="https://dummyimage.com/360x203/000000/FFFFFF.png" alt="" class="thumbnail">\n' +
                                    '            </div>\n' +
                                    '            <div class="col-sm-6">\n' +
                                    '              <h3><a class="stretched-link" href="#">[Feature hyperlink text]</a></h3>\n' +
                                    '              <p>Brief description of the feature being promoted.</p>\n' +
                                    '            </div>\n' +
                                    '          </div>\n' +
                                    '        </section>\n' +
                                    '      </div>\n' +
                                    '      <div class="col-md-4">\n' +
                                    '        <section class="gc-followus">\n' +
                                    '          <h2>On social media</h2>\n' +
                                    '          <ul>\n' +
                                    '            <li>\n' +
                                    '              <a href="#facebook" class="facebook"><span class="wb-inv">Facebook: </span>FacebookPageName</a>\n' +
                                    '            </li>\n' +
                                    '            <li>\n' +
                                    '              <a href="#" rel="external" class="x-social"><span class="wb-inv">X: </span>@XAccount</a>\n' +
                                    '            </li>\n' +
                                    '            <li>\n' +
                                    '              <a href="#" rel="external" class="youtube"><span class="wb-inv">YouTube: </span>YouTubeName</a>\n' +
                                    '            </li>\n' +
                                    '            <li>\n' +
                                    '              <a href="#" rel="external" class="instagram"><span class="wb-inv">Instagram: </span>InstagramName</a>\n' +
                                    '            </li>\n' +
                                    '            <li>\n' +
                                    '              <a href="#" rel="external" class="linkedin"><span class="wb-inv">LinkedIn: </span>LinkedInName</a>\n' +
                                    '            </li>\n' +
                                    '          </ul>\n' +
                                    '        </section>\n' +
                                    '        <section id="facebook" class="modal-dialog modal-content overlay-def mfp-hide">\n' +
                                    '          <header class="modal-header">\n' +
                                    '            <h2 class="modal-title" id="lbx-title">Facebook</h2>\n' +
                                    '          </header>\n' +
                                    '          <div class="modal-body">\n' +
                                    '            <ul class="list-unstyled lst-spcd">\n' +
                                    '              <li>\n' +
                                    '                <a href="#" rel="external">[First Facebook account title]</a>\n' +
                                    '              </li>\n' +
                                    '              <li>\n' +
                                    '                <a href="#" rel="external">[Second Facebook account title]</a>\n' +
                                    '              </li>\n' +
                                    '            </ul>\n' +
                                    '          </div>\n' +
                                    '          <div class="modal-footer">\n' +
                                    '            <button type="button" class="btn btn-sm btn-primary pull-left popup-modal-dismiss">Close<span class="wb-inv">Close overlay</span></button>\n' +
                                    '          </div>\n' +
                                    '        </section>\n' +
                                    '      </div>\n' +
                                    '    </div>\n' +
                                    '  </div>\n' +
                                    '</div>';
                    break;
                default:
                    // Check if component exists in allComponents
                    const component = allComponents.find(c => c.id === componentType);
                    if (component) {
                        // Check if this is a page component
                        if (component.source === 'page' && component.pageData && component.pageData.content) {
                            // Insert the actual page content for page-based components
                            componentHtml = component.pageData.content;
                            console.log(`Inserted page content for component: ${component.id}`, {
                                componentName: component.name,
                                contentLength: componentHtml.length,
                                hasContent: !!component.pageData.content
                            });
                        } else {
                            // Insert a generic component placeholder with webbot-component class
                            componentHtml = `<div class="webbot-component" data-component-id="${component.id}" data-component-name="${component.name}">
    <h4>${component.name}</h4>
    <p>${component.description || 'Canada.ca component'}</p>
    <small>Component type: ${component.id}</small>
</div>`;
                            console.log(`Inserted generic placeholder for component: ${component.id}`);
                        }
                    } else {
                        console.error('Unknown component type:', componentType);
                        return false;
                    }
            }

            // Insert component at cursor position
            try {
                tinyMceEditor.insertContent(componentHtml);
                console.log(`Inserted ${componentType} component at cursor position`);
                return true;
            } catch (error) {
                console.error('Error inserting component:', error);
                return false;
            }
        }

        /**
         * Insert page content at cursor position by path.
         * Fetches page content via the by-path API and inserts into TinyMCE.
         * @param {string} path - Page path (e.g. /en/contact)
         * @returns {Promise<boolean>} - True if insertion succeeded
         */
        async function insertPath(path) {
            if (!tinyMceEditor) {
                console.error('TinyMCE editor not initialized');
                return false;
            }

            if (!path || typeof path !== 'string') {
                console.error('Invalid path:', path);
                return false;
            }

            // Normalize path
            let normalizedPath = path.trim();
            if (!normalizedPath.startsWith('/')) {
                normalizedPath = '/' + normalizedPath;
            }

            console.log('insertPath called with path:', normalizedPath);

            try {
                // Fetch page content by path
                const apiUrl = `${API_BASE}/by-path?path=${encodeURIComponent(normalizedPath)}`;
                console.log('Fetching page content from:', apiUrl);

                const response = await fetch(apiUrl);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const page = await response.json();
                console.log('Page fetched:', page?.id, page?.title);

                if (!page) {
                    throw new Error('Page not found or returned empty response');
                }

                // Get page content
                let content = page.content || '';
                if (!content) {
                    console.warn('Page has no content');
                    return false;
                }

                // Clean content (remove header/footer)
                content = cleanContent(content, normalizedPath);
                console.log('Content cleaned, length:', content.length);

                // Insert at cursor position
                tinyMceEditor.insertContent(content);
                console.log('Page content inserted successfully at cursor position');
                return true;

            } catch (error) {
                console.error('Error inserting content by path:', error);
                return false;
            }
        }

        // Delete component at cursor position
        function deleteComponent() {
            if (!tinyMceEditor) {
                console.error('TinyMCE editor not initialized');
                return false;
            }

            // Get the current selection
            const selection = tinyMceEditor.selection;
            const node = selection.getNode();

            // Find the nearest webbot-component element
            let componentElement = node;
            while (componentElement && componentElement !== document.body) {
                if (componentElement.classList && componentElement.classList.contains('webbot-component')) {
                    break;
                }
                componentElement = componentElement.parentElement;
            }

            if (!componentElement || componentElement === document.body) {
                // No webbot-component found, try to find by other component-specific classes
                // This is a fallback for components inserted before we added webbot-component class
                const fallbackClasses = ['btn-primary', 'btn-success', 'btn-info', 'btn-warning', 'btn-danger', 'table-striped', 'alert-info', 'alert-danger', 'alert-warning', 'alert-success', 'wb-breadcrumb', 'wb-sec', 'pagedetails', 'form-inline', 'gc-most-requested', 'gc-featured-link', 'gc-features', 'gc-srvinfo'];
                componentElement = node;
                while (componentElement && componentElement !== document.body) {
                    if (componentElement.classList) {
                        for (const cls of fallbackClasses) {
                            if (componentElement.classList.contains(cls)) {
                                break;
                            }
                        }
                    }
                    if (componentElement.classList && Array.from(componentElement.classList).some(c => fallbackClasses.includes(c))) {
                        break;
                    }
                    componentElement = componentElement.parentElement;
                }
            }

            if (componentElement && componentElement !== document.body) {
                // Remove the component element
                componentElement.remove();
                console.log('Deleted component:', componentElement);
                return true;
            } else {
                console.warn('No component found at cursor position');
                // Try to show a user-friendly message
                tinyMceEditor.notificationManager.open({
                    text: 'No WebBot component found at cursor position. Place your cursor inside a component (button, table, alert, etc.) and try again.',
                    type: 'warning',
                    timeout: 3000
                });
                return false;
            }
        }

        // Global variable to store copied component HTML
        window.copiedComponentHTML = null;
        window.copiedComponentElement = null;

        // Copy component at cursor position
        function copyComponent() {
            if (!tinyMceEditor) {
                console.error('TinyMCE editor not initialized');
                return false;
            }

            // Get the current selection
            const selection = tinyMceEditor.selection;
            const node = selection.getNode();

            // Find the nearest div element (direct div) or webbot-component
            let componentElement = node;
            let found = false;
            while (componentElement && componentElement !== document.body) {
                // Check if it's a div (direct div container)
                if (componentElement.tagName && componentElement.tagName.toLowerCase() === 'div') {
                    // We'll use this as the component element
                    found = true;
                    break;
                }
                // Also check for webbot-component class
                if (componentElement.classList && componentElement.classList.contains('webbot-component')) {
                    found = true;
                    break;
                }
                componentElement = componentElement.parentElement;
            }

            if (!found) {
                // Fallback: try to find by other component-specific classes
                const fallbackClasses = ['btn-primary', 'btn-success', 'btn-info', 'btn-warning', 'btn-danger', 'table-striped', 'alert-info', 'alert-danger', 'alert-warning', 'alert-success', 'wb-breadcrumb', 'wb-sec', 'pagedetails', 'form-inline', 'gc-most-requested', 'gc-featured-link', 'gc-features', 'gc-srvinfo'];
                componentElement = node;
                while (componentElement && componentElement !== document.body) {
                    if (componentElement.classList) {
                        // Check if any fallback class exists
                        for (const cls of fallbackClasses) {
                            if (componentElement.classList.contains(cls)) {
                                found = true;
                                break;
                            }
                        }
                    }
                    if (found) break;
                    componentElement = componentElement.parentElement;
                }
            }

            if (componentElement && componentElement !== document.body && found) {
                // Store the component HTML
                window.copiedComponentHTML = componentElement.outerHTML;
                window.copiedComponentElement = componentElement;
                console.log('Copied component:', componentElement);
                return true;
            } else {
                console.warn('No component found at cursor position');
                // Try to show a user-friendly message
                tinyMceEditor.notificationManager.open({
                    text: 'No component found at cursor position. Place your cursor inside a component (button, table, alert, etc.) and try again.',
                    type: 'warning',
                    timeout: 3000
                });
                return false;
            }
        }

        // Paste copied component next to the original component
        function pasteComponent() {
            if (!tinyMceEditor) {
                console.error('TinyMCE editor not initialized');
                return false;
            }

            if (!window.copiedComponentHTML) {
                tinyMceEditor.notificationManager.open({
                    text: 'No component copied yet. Use "copy" command first.',
                    type: 'warning',
                    timeout: 3000
                });
                return false;
            }

            // Try to insert the copied component next to the original if it still exists
            if (window.copiedComponentElement && window.copiedComponentElement.parentNode) {
                // Create a copy of the component
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = window.copiedComponentHTML;
                const clonedComponent = tempDiv.firstElementChild;

                // Insert after the original component
                window.copiedComponentElement.parentNode.insertBefore(clonedComponent, window.copiedComponentElement.nextSibling);
                console.log('Pasted component next to original');
            } else {
                // Otherwise insert at current cursor position
                tinyMceEditor.insertContent(window.copiedComponentHTML);
                console.log('Pasted component at cursor position');
            }
            return true;
        }

        // Append component to end of page content
        function appendComponent(componentType) {
            if (!tinyMceEditor) {
                console.error('TinyMCE editor not initialized');
                return false;
            }

            let componentHtml = '';

            // If componentType is empty or just "append", add empty paragraph
            if (!componentType || componentType === 'append' || componentType.trim() === '') {
                componentHtml = '<p></p>';
            } else {
                // Use getComponentHTML function to get component HTML
                componentHtml = getComponentHTML(componentType);
            }

            // Get current content
            const currentContent = tinyMceEditor.getContent();

            // Append component HTML to the end
            const newContent = currentContent + '\n' + componentHtml;

            // Set new content
            tinyMceEditor.setContent(newContent);

            // Scroll to the end to show the appended component
            const editorBody = tinyMceEditor.getBody();
            editorBody.scrollTop = editorBody.scrollHeight;

            return true;
        }

        // ========== AI ASSISTANT FUNCTIONS ==========

        // Toggle AI assistant panel visibility
        function toggleAIAssistant() {
            const panel = document.getElementById('ai-assistant-panel');
            if (panel) {
                panel.classList.toggle('hidden');
                if (!panel.classList.contains('hidden')) {
                    // Focus on input when panel opens
                    setTimeout(() => {
                        const input = document.getElementById('ai-chat-input');
                        if (input) input.focus();
                    }, 300);
                }
            }
        }

        // Add message to chat
        function addAIMessage(text, sender) {
            const chatMessages = document.getElementById('ai-chat-messages');
            if (!chatMessages) return;

            const messageDiv = document.createElement('div');
            messageDiv.className = `ai-message ${sender}`;
            messageDiv.textContent = text;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        // Show typing indicator
        function showAITypingIndicator() {
            const chatMessages = document.getElementById('ai-chat-messages');
            if (!chatMessages) return;

            const typingDiv = document.createElement('div');
            typingDiv.className = 'ai-typing-indicator';
            typingDiv.id = 'ai-typing-indicator';
            typingDiv.innerHTML = `
                <div class="ai-typing-dot"></div>
                <div class="ai-typing-dot"></div>
                <div class="ai-typing-dot"></div>
            `;
            chatMessages.appendChild(typingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            return typingDiv;
        }

        // Hide typing indicator
        function hideAITypingIndicator() {
            const typingIndicator = document.getElementById('ai-typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }

        // Process AI message (simple rule-based system)
        function processAIMessage(message) {
            const lowerMsg = message.toLowerCase().trim();

            // Show typing indicator
            showAITypingIndicator();

            // Check for slash commands
            if (message.startsWith('/')) {
                // Parse command: /command arg1 arg2
                const parts = message.trim().split(/\s+/);
                const commandName = parts[0].substring(1); // Remove leading slash
                const args = parts.slice(1);

                // Simulate AI processing delay
                setTimeout(() => {
                    hideAITypingIndicator();

                    // Check if command exists in aiAssistantCommands
                    if (window.aiAssistantCommands && window.aiAssistantCommands[commandName]) {
                        const command = window.aiAssistantCommands[commandName];
                        try {
                            const result = command.execute(args);
                            addAIMessage(result || `Executed command: ${commandName}`, 'assistant');
                        } catch (error) {
                            console.error(`Error executing command ${commandName}:`, error);
                            addAIMessage(`Error executing /${commandName}: ${error.message}`, 'assistant');
                        }
                    } else {
                        hideAITypingIndicator();
                        addAIMessage(`I'm not sure what you mean by "${message}". Type "help" to see available commands, or try one of these:\n\n• /template - Insert a Mustache template\n• /html - Quick edit HTML at cursor position\n• /color - Change the color of a component\n• /edit-html - Same as /html\n• insert button - Insert a button component\n• alert danger - Insert a danger alert`, 'assistant');
                    }
                }, 500);
                return; // Exit early for slash commands
            }

            // Simulate AI processing delay for natural language messages
            setTimeout(() => {
                hideAITypingIndicator();

                let response = '';
                let componentType = null;

                // Simple keyword matching
                // Check for help requests first - if message contains "help" or "帮助", only show help
                if (lowerMsg.includes('help')) {
                    // Handle help requests - only show help, don't execute any commands

                    // Simple help system
                    if (lowerMsg === 'help') {
                        // General help
                        response = "I can help you insert or delete components in your page. Just tell me what you want to do:\n• **HTML Edit** (raw code): 'edit html' or '/html'\n• **Component Edit** (WYSIWYG): 'edit component' or '/edit-component'\n• **Buttons**: 'button' (primary), 'button success', 'button info', 'button warning', 'button danger'\n• **Alerts**: 'alert', 'alert danger', 'alert warning', 'alert success', 'alert info' (with or without 'link')\n• **Introduction**: 'introduction', 'introduction full image', 'introduction half image'\n• **Services & Info**: 'services and information' (3 columns, 2 columns, or list)\n• **Feature Links**: 'feature link' (basic, dark, light, or gray background)\n• **Government**: 'government initiatives' (2 columns, stretched links)\n• **Features**: 'features' (3 columns, standard links)\n• **Most Requested**: 'most requested links'\n• **Navigation**: 'breadcrumb', 'sidebar', 'footer', 'search'\n• **Tables**: 'table'\n• **Calendar**: 'calendar' or 'events'\n• **Theme Pages**: 'theme page' or 'jobs theme'\n• **Topic Template**: 'topic template' or 'topic page'\n• **Delete**: 'delete' or 'remove'\n\nType 'help [category]' for more details, e.g. 'help alert', 'help button'.";
                    } else if (lowerMsg.startsWith('help ')) {
                        // Categorized help
                        let topic = lowerMsg;
                        if (topic.startsWith('help ')) {
                            topic = topic.substring(5);
                        } else if (topic.startsWith('help ')) {
                            topic = topic.substring(3);
                        }
                        topic = topic.trim();

                        // Simple category mapping
                        const helpMap = {
                            'button': "**Button Components**\n• 'button' - Insert a primary button (blue)\n• 'button success' - Insert a success button (green)\n• 'button info' - Insert an info button (blue)\n• 'button warning' - Insert a warning button (yellow)\n• 'button danger' - Insert a danger button (red)\n\nExamples: 'insert button', 'button success', 'add danger button'",

                            'alert': "**Alert Components**\n• 'alert' - Insert an info alert\n• 'alert danger' - Insert a danger alert (red)\n• 'alert warning' - Insert a warning alert (yellow)\n• 'alert success' - Insert a success alert (green)\n• 'alert info' - Insert an info alert (blue)\n• 'alert danger link' - Insert danger alert with link\n• 'alert warning link' - Insert warning alert with link\n• 'alert success link' - Insert success alert with link\n• 'alert info link' - Insert info alert with link\n\nExamples: 'alert danger', 'warning alert with link', 'add success alert'",

                            'introduction': "**Introduction Blocks**\n• 'introduction' - Insert basic introduction block\n• 'introduction full image' - Insert introduction with full-width background image\n• 'introduction half image' - Insert introduction with half-width image\n\nExamples: 'introduction', 'add introduction with full image', 'introduction half width'",

                            'services': "**Services and Information Sections**\n• 'services and information' - Insert 3-column services section\n• 'services and information 2 columns' - Insert 2-column services section\n• 'services and information list' - Insert simple list services section\n\nExamples: 'services and information', 'services info 2 columns', 'services list'",

                            'feature': "**Feature Link Components**\n• 'feature link' - Insert feature link with description\n• 'feature link dark' - Insert feature link with dark background\n• 'feature link light' - Insert feature link with light background\n• 'feature link gray' - Insert feature link with gray background\n\nExamples: 'feature link', 'add dark feature link', 'feature link with light background'",

                            'government': "**Government Initiatives**\n• 'government initiatives' - Insert government initiatives section (2 columns, stretched links)\n• 'government features' - Insert government initiatives section\n\nExamples: 'government initiatives', 'add government projects', 'insert government initiatives section'",

                            'features': "**Features Sections**\n• 'features' - Insert standard features section (3 columns, standard links)\n• 'gc-features' - Insert features section using gc-features class\n\nExamples: 'features', 'insert features section', 'add features component'",

                            'most': "**Most Requested Links**\n• 'most requested links' - Insert most requested links section\n\nExamples: 'most requested links', 'top tasks', 'popular links'",

                            'navigation': "**Navigation Components**\n• 'breadcrumb' - Insert breadcrumb navigation\n• 'sidebar' - Insert sidebar navigation\n• 'footer' - Insert footer section\n• 'search' - Insert search box\n\nExamples: 'add breadcrumb', 'insert sidebar', 'search box'",

                            'table': "**Table Component**\n• 'table' - Insert a striped table\n\nExamples: 'insert table', 'add table'",

                            'follow': "**Social Media Follow Us**\n• 'social media' - Insert social media follow us section with Facebook, X (Twitter), YouTube, Instagram, and LinkedIn links\n• 'follow us' - Insert vertical social media links section\n• 'social media horizontal' or 'follow us horizontal' - Insert horizontal (inline) social media links\n\nExamples: 'social media', 'follow us', 'social media horizontal', 'follow us horizontal', 'insert social media links'",

                            'calendar': "**Calendar of Events**\n• 'calendar' or 'events' - Insert a calendar of events component with sample events\n• 'event calendar' - Insert interactive calendar component\n\nExamples: 'calendar', 'events', 'insert event calendar'",

                            'theme': "**Theme Pages**\n• 'theme page' or 'theme template' - Insert a complete Jobs theme page with navigation, most requested links, and services sections\n• 'jobs theme' or 'jobs page' - Insert a structured Jobs page template\n\nExamples: 'theme page', 'theme template', 'jobs theme', 'insert jobs page'",

                            'topic': "**Topic Template**\n• 'topic template' or 'topic page' - Insert a comprehensive topic page template with title, description, most requested links, services grid, featured content, and social media sections\n• 'topic template' or 'topic page' - Insert a complete topic page template\n\nExamples: 'topic template', 'topic page', 'insert topic template'",

                            'delete': "**Delete Component**\n• 'delete' - Delete component at cursor position\n• 'remove' - Remove component at cursor position\n\nExamples: 'delete', 'remove this button', 'delete component'"
                        };

                        // Check if topic is in helpMap
                        if (helpMap[topic]) {
                            response = helpMap[topic];
                        } else {
                            // Try to find matching category
                            let found = false;
                            for (const [category, helpText] of Object.entries(helpMap)) {
                                if (topic.includes(category) || category.includes(topic)) {
                                    response = helpText;
                                    found = true;
                                    break;
                                }
                            }

                            // Also check Chinese mappings
                            const chineseMap = {

                            };

                            // French mappings
                            const frenchMap = {
                                'bouton': 'button',
                                'boutons': 'button',
                                'alerte': 'alert',
                                'alertes': 'alert',
                                'introduction': 'introduction',
                                'services': 'services',
                                'services et information': 'services',
                                'services info': 'services',
                                'lien vedette': 'feature',
                                'liens vedettes': 'feature',
                                'initiatives gouvernementales': 'government',
                                'gouvernement': 'government',
                                'les plus demandés': 'most',
                                'plus demandés': 'most',
                                'navigation': 'navigation',
                                'tableau': 'table',
                                'tableaux': 'table',
                                'médias sociaux': 'follow',
                                'suivez-nous': 'follow',
                                'suivre': 'follow',
                                'calendrier': 'calendar',
                                'événements': 'calendar',
                                'page thématique': 'theme',
                                'thème emplois': 'theme',
                                'modèle de sujet': 'topic',
                                'modèle thématique': 'topic',
                                'supprimer': 'delete',
                                'effacer': 'delete'
                            };

                            if (!found && chineseMap[topic]) {
                                response = helpMap[chineseMap[topic]];
                                found = true;
                            }

                            // Check French mappings
                            if (!found && frenchMap[topic]) {
                                response = helpMap[frenchMap[topic]];
                                found = true;
                            }

                            if (!found) {
                                response = "I can help you with these categories: button, alert, introduction, services, feature, government, most, navigation, table, follow, calendar, theme, topic, delete.\n\nType 'help [category]' for details, e.g. 'help alert' or 'help button'.";
                            }
                        }
                    } else {
                        // Message contains "help" or "帮助" but not in standard format
                        response = "I can help you insert or delete components in your page. Type 'help' to see all options or 'help [category]' for specific help, e.g. 'help alert', 'help button', or 'help follow'.";
                    }

                    // Ensure componentType remains null so no component is inserted
                    componentType = null;
                // Help requests are already handled above
                // This else if block is now redundant
                } else if ((lowerMsg.includes('button') || lowerMsg.includes('btn') || lowerMsg.includes('bouton')) && !lowerMsg.includes('help') && false) {
                    // Handle different button variants
                    if (lowerMsg.includes('success')) {
                        response = "Inserting a success button...";
                        componentType = 'button-success';
                    } else if (lowerMsg.includes('info')) {
                        response = "Inserting an info button...";
                        componentType = 'button-info';
                    } else if (lowerMsg.includes('warning')) {
                        response = "Inserting a warning button...";
                        componentType = 'button-warning';
                    } else if (lowerMsg.includes('danger')) {
                        response = "Inserting a danger button...";
                        componentType = 'button-danger';
                    } else {
                        response = "Inserting a button component...";
                        componentType = 'button';
                    }
                } else if (lowerMsg.includes('table') || lowerMsg.includes('tableau')) {
                    response = "Inserting a table component...";
                    componentType = 'table';
                } else if ((lowerMsg.includes('alert') || lowerMsg.includes('alerte')) && !lowerMsg.includes('help') && false) {
                    // Handle different alert variants
                    if (lowerMsg.includes('danger')) {
                        if (lowerMsg.includes('link')) {
                            response = "Inserting danger alert with link...";
                            componentType = 'alert-danger-link';
                        } else {
                            response = "Inserting danger alert...";
                            componentType = 'alert-danger';
                        }
                    } else if (lowerMsg.includes('warning')) {
                        if (lowerMsg.includes('link')) {
                            response = "Inserting warning alert with link...";
                            componentType = 'alert-warning-link';
                        } else {
                            response = "Inserting warning alert...";
                            componentType = 'alert-warning';
                        }
                    } else if (lowerMsg.includes('success')) {
                        if (lowerMsg.includes('link')) {
                            response = "Inserting success alert with link...";
                            componentType = 'alert-success-link';
                        } else {
                            response = "Inserting success alert...";
                            componentType = 'alert-success';
                        }
                    } else if (lowerMsg.includes('info')) {
                        if (lowerMsg.includes('link')) {
                            response = "Inserting info alert with link...";
                            componentType = 'alert-info-link';
                        } else {
                            response = "Inserting info alert...";
                            componentType = 'alert-info';
                        }
                    } else {
                        // Default alert (info without link)
                        response = "Inserting an alert box...";
                        componentType = 'alert';
                    }
                } else if ((lowerMsg.includes('warning') || lowerMsg.includes('avertissement')) && !lowerMsg.includes('alert')) {
                    // Handle standalone "warning" (without "alert" keyword)
                    response = "Inserting warning alert...";
                    componentType = 'alert-warning';
                } else if (lowerMsg.includes('breadcrumb') || lowerMsg.includes('fil dariane') || lowerMsg.includes('fil d\'ariane')) {
                    response = "Inserting breadcrumb navigation...";
                    componentType = 'breadcrumb';
                } else if (lowerMsg.includes('sidebar') || lowerMsg.includes('menu') || lowerMsg.includes('barre latérale') || lowerMsg.includes('menu latéral')) {
                    response = "Inserting sidebar navigation...";
                    componentType = 'sidebar';
                } else if (lowerMsg.includes('footer') || lowerMsg.includes('pied de page')) {
                    response = "Inserting footer section...";
                    componentType = 'footer';
                } else if (lowerMsg.includes('search') || lowerMsg.includes('find') || lowerMsg.includes('rechercher') || lowerMsg.includes('recherche')) {
                    response = "Inserting search box...";
                    componentType = 'search';
                } else if (lowerMsg.includes('introduction') || lowerMsg.includes('intro') ) {
                    if (lowerMsg.includes('full') || lowerMsg.includes('full-width') || lowerMsg.includes('full image') ) {
                        response = "Inserting introduction block with full-width image...";
                        componentType = 'introduction-full-image';
                    } else if (lowerMsg.includes('half') || lowerMsg.includes('half-width') || lowerMsg.includes('half image') ) {
                        response = "Inserting introduction block with half-width image...";
                        componentType = 'introduction-half-image';
                    } else {
                        response = "Inserting introduction block...";
                        componentType = 'introduction';
                    }
                } else if (lowerMsg.includes('most requested') || lowerMsg.includes('most-requested') || lowerMsg.includes('top tasks')  || false /* removed */ || lowerMsg.includes('les plus demandés') || lowerMsg.includes('plus demandés')) {
                    response = "Inserting most requested links section...";
                    componentType = 'most-requested';
                } else if (lowerMsg.includes('feature link') || lowerMsg.includes('featured link') || lowerMsg.includes('spotlight')  || false /* removed */ || lowerMsg.includes('lien vedette') || lowerMsg.includes('liens vedettes')) {
                    response = "Inserting feature link with description...";
                    componentType = 'feature-link';
                } else if (lowerMsg.includes('government initiatives') || lowerMsg.includes('government features')  || false /* removed */ || lowerMsg.includes('initiatives gouvernementales') || lowerMsg.includes('gouvernement') || lowerMsg.includes('initiatives')) {
                    // 政府倡议组件
                    response = "Inserting government initiatives section...";
                    componentType = 'government-initiatives';
                } else if (lowerMsg.includes('features')  || lowerMsg.includes('fonctionnalités') || lowerMsg.includes('gc-features')) {
                    // 标准Features组件 (A方案 - 独立组件)
                    response = "Inserting features section...";
                    componentType = 'features';
                } else if (lowerMsg.includes('services and information') || lowerMsg.includes('services info') || lowerMsg.includes('gc-srvinfo')   || lowerMsg.includes('services et information') || lowerMsg.includes('services info')) {
                    if (lowerMsg.includes('3 columns')  || lowerMsg.includes('3 column')) {
                        response = "Inserting Services and Information section (3 columns)...";
                        componentType = 'services-info-3col';
                    } else if (lowerMsg.includes('2 columns')  || lowerMsg.includes('2 column')) {
                        response = "Inserting Services and Information section (2 columns)...";
                        componentType = 'services-info-2col';
                    } else if (lowerMsg.includes('list')  || lowerMsg.includes('simple')) {
                        response = "Inserting Services and Information section (list)...";
                        componentType = 'services-info-list';
                    } else {
                        response = "Inserting Services and Information section (3 columns)...";
                        componentType = 'services-info-3col';
                    }
                } else if (lowerMsg.includes('feature link dark') || lowerMsg.includes('dark feature link') || lowerMsg.includes('feature link dark background') ) {
                    response = "Inserting feature link with dark background...";
                    componentType = 'feature-link-dark';
                } else if (lowerMsg.includes('feature link light') || lowerMsg.includes('light feature link') || lowerMsg.includes('feature link light background') ) {
                    response = "Inserting feature link with light background...";
                    componentType = 'feature-link-light';
                } else if (lowerMsg.includes('feature link gray') || lowerMsg.includes('gray feature link') || lowerMsg.includes('feature link gray background')  || lowerMsg.includes('feature link grey')) {
                    response = "Inserting feature link with gray background...";
                    componentType = 'feature-link-gray';
                } else if (lowerMsg.includes('social media') || lowerMsg.includes('follow us')  || lowerMsg.includes('followus') || lowerMsg.includes('social') || lowerMsg.includes('médias sociaux') || lowerMsg.includes('suivez-nous')) {
                    // Check for horizontal version
                    if (lowerMsg.includes('horizontal') ) {
                        response = "Inserting horizontal social media follow us section...";
                        componentType = 'follow-us-horizontal';
                    } else {
                        response = "Inserting social media follow us section...";
                        componentType = 'follow-us';
                    }
                } else if (lowerMsg.includes('calendar') || lowerMsg.includes('events')  || lowerMsg.includes('event calendar') || lowerMsg.includes('calendrier') || lowerMsg.includes('événements')) {
                    response = "Inserting calendar of events component...";
                    componentType = 'calendar-events';
                } else if (lowerMsg.includes('theme page') || lowerMsg.includes('theme template') || lowerMsg.includes('jobs theme') || lowerMsg.includes('jobs page')    || lowerMsg.includes('page thématique') || lowerMsg.includes('thème emplois')) {
                    response = "Inserting Jobs theme page component...";
                    componentType = 'theme-page-jobs';
                } else if (lowerMsg.includes('topic template') || lowerMsg.includes('topic page')  || lowerMsg.includes('topic') || lowerMsg.includes('modèle de sujet') || lowerMsg.includes('modèle thématique')) {
                    response = "Inserting Topic template component...";
                    componentType = 'topic-template';
                } else if (lowerMsg.includes('delete') || lowerMsg.includes('remove')  || lowerMsg.includes('supprimer') || lowerMsg.includes('effacer')) {
                    response = "Deleting component at cursor position...";
                    // Set a flag to indicate delete action
                    componentType = 'delete';
                } else if (lowerMsg.includes('append')) {
                    // Handle append command
                    // Extract component name after "append"
                    let componentName = '';
                    if (lowerMsg.startsWith('append ')) {
                        componentName = lowerMsg.substring(7).trim();
                    } else {
                        // Find "append" in the message and get what follows
                        const appendIndex = lowerMsg.indexOf('append');
                        if (appendIndex !== -1) {
                            componentName = lowerMsg.substring(appendIndex + 6).trim();
                        }
                    }

                    // Remove any extra words like "component", "to end", etc.
                    componentName = componentName.replace(/component|to end|to page|at end|the end|page|content/gi, '').trim();

                    if (componentName === '') {
                        response = "Appending empty paragraph to end of page content...";
                        // Set componentType to special value for empty append
                        componentType = 'append-empty';
                    } else {
                        response = `Appending ${componentName} component to end of page content...`;
                        // Set componentType to append-{componentName}
                        componentType = `append-${componentName}`;
                    }
                } else if (lowerMsg.startsWith('copy') || lowerMsg.startsWith('paste') || lowerMsg.startsWith('past')) {
                    // Handle copy/paste commands
                    if (lowerMsg.startsWith('copy')) {
                        response = "Copying component at cursor position...";
                        componentType = 'copy';
                    } else {
                        response = "Pasting copied component next to original...";
                        componentType = 'paste';
                    }
                } else if (false && (lowerMsg.startsWith('help ') || false || (lowerMsg.includes('help') && lowerMsg !== 'help') || (false && false))) {
                    // Handle categorized help requests (English or Chinese)
                    let helpTopic = lowerMsg;
                    // Remove English "help " prefix
                    if (helpTopic.startsWith('help ')) {
                        helpTopic = helpTopic.substring(5);
                    }
                    // Remove Chinese "帮助 " prefix
                    if (false) {
                        helpTopic = helpTopic.substring(3);
                    }
                    helpTopic = helpTopic.trim();

                    // Define help messages for different categories
                    const helpMessages = {
                        'button': "**Button Components**\n• 'button' - Insert a primary button (blue)\n• 'button success' - Insert a success button (green)\n• 'button info' - Insert an info button (blue)\n• 'button warning' - Insert a warning button (yellow)\n• 'button danger' - Insert a danger button (red)\n\nExamples: 'insert button', 'button success', 'add danger button'",

                        'alert': "**Alert Components**\n• 'alert' - Insert an info alert\n• 'alert danger' - Insert a danger alert (red)\n• 'alert warning' - Insert a warning alert (yellow)\n• 'alert success' - Insert a success alert (green)\n• 'alert info' - Insert an info alert (blue)\n• 'alert danger link' - Insert danger alert with link\n• 'alert warning link' - Insert warning alert with link\n• 'alert success link' - Insert success alert with link\n• 'alert info link' - Insert info alert with link\n\nExamples: 'alert danger', 'warning alert with link', 'add success alert'",

                        'introduction': "**Introduction Blocks**\n• 'introduction' - Insert basic introduction block\n• 'introduction full image' - Insert introduction with full-width background image\n• 'introduction half image' - Insert introduction with half-width image\n\nExamples: 'introduction', 'add introduction with full image', 'introduction half width'",

                        'services': "**Services and Information Sections**\n• 'services and information' - Insert 3-column services section\n• 'services and information 2 columns' - Insert 2-column services section\n• 'services and information list' - Insert simple list services section\n\nExamples: 'services and information', 'services info 2 columns', 'services list'",

                        'feature': "**Feature Link Components**\n• 'feature link' - Insert feature link with description\n• 'feature link dark' - Insert feature link with dark background\n• 'feature link light' - Insert feature link with light background\n• 'feature link gray' - Insert feature link with gray background\n\nExamples: 'feature link', 'add dark feature link', 'feature link with light background'",

                        'government': "**Government Initiatives**\n• 'government initiatives' - Insert government initiatives section (2 columns, stretched links)\n• 'government features' - Insert government initiatives section\n\nExamples: 'government initiatives', 'add government projects', 'insert government initiatives section'",

                        'features': "**Features Sections**\n• 'features' - Insert standard features section (3 columns, standard links)\n• 'gc-features' - Insert features section using gc-features class\n\nExamples: 'features', 'insert features section', 'add features component'",

                        'most': "**Most Requested Links**\n• 'most requested links' - Insert most requested links section\n\nExamples: 'most requested links', 'top tasks', 'popular links'",

                        'navigation': "**Navigation Components**\n• 'breadcrumb' - Insert breadcrumb navigation\n• 'sidebar' - Insert sidebar navigation\n• 'footer' - Insert footer section\n• 'search' - Insert search box\n\nExamples: 'add breadcrumb', 'insert sidebar', 'search box'",

                        'table': "**Table Component**\n• 'table' - Insert a striped table\n\nExamples: 'insert table', 'add table'",

                        'delete': "**Delete Component**\n• 'delete' - Delete component at cursor position\n• 'remove' - Remove component at cursor position\n\nExamples: 'delete', 'remove this button', 'delete component'",

                        'all': "I can help you insert or delete components in your page. Just tell me what you want to do:\n• **Buttons**: 'button' (primary), 'button success', 'button info', 'button warning', 'button danger'\n• **Alerts**: 'alert', 'alert danger', 'alert warning', 'alert success', 'alert info' (with or without 'link')\n• **Introduction**: 'introduction', 'introduction full image', 'introduction half image'\n• **Services & Info**: 'services and information' (3 columns, 2 columns, or list)\n• **Feature Links**: 'feature link' (basic, dark, light, or gray background)\n• **Government**: 'government initiatives'\n• **Most Requested**: 'most requested links'\n• **Navigation**: 'breadcrumb', 'sidebar', 'footer', 'search'\n• **Tables**: 'table'\n• **Calendar**: 'calendar' or 'events'\n• **Theme Pages**: 'theme page' or 'jobs theme'\n• **Topic Template**: 'topic template' or 'topic page'\n• **Delete**: 'delete' or 'remove'\n\nType 'help [category]' for more details, e.g. 'help alert', 'help button'."
                    };

                    // Map aliases to main categories
                    const categoryAliases = {
                        // English aliases
                        'buttons': 'button',
                        'btn': 'button',
                        'alerts': 'alert',
                        'warning': 'alert',
                        'danger': 'alert',
                        'success': 'alert',
                        'info': 'alert',
                        'introductions': 'introduction',
                        'intro': 'introduction',
                        'services and information': 'services',
                        'services info': 'services',
                        'srvinfo': 'services',
                        'feature links': 'feature',
                        'featured': 'feature',
                        'spotlight': 'feature',
                        'government initiatives': 'government',
                        'gov': 'government',
                        'features': 'features',
                        'gc-features': 'features',
                        'most requested': 'most',
                        'most-requested': 'most',
                        'top': 'most',
                        'popular': 'most',
                        'navigation': 'navigation',
                        'nav': 'navigation',
                        'breadcrumbs': 'navigation',
                        'sidebar': 'navigation',
                        'footer': 'navigation',
                        'search': 'navigation',
                        'tables': 'table',
                        'delete': 'delete',
                        'remove': 'delete',
                        'all': 'all',
                        'general': 'all',
                        '': 'all',
                        // Chinese aliases

                    };

                    // Determine which category to show
                    let category = 'all';
                    if (helpTopic) {
                        // Check exact match first
                        if (helpMessages[helpTopic]) {
                            category = helpTopic;
                        } else if (categoryAliases[helpTopic]) {
                            category = categoryAliases[helpTopic];
                        } else {
                            // Fuzzy match: find category that contains the topic
                            for (const [cat, aliases] of Object.entries(categoryAliases)) {
                                if (helpTopic.includes(cat) || cat.includes(helpTopic)) {
                                    category = aliases;
                                    break;
                                }
                            }
                            // Also check category names
                            for (const cat of Object.keys(helpMessages)) {
                                if (helpTopic.includes(cat) || cat.includes(helpTopic)) {
                                    category = cat;
                                    break;
                                }
                            }
                        }
                    }

                    response = helpMessages[category] || helpMessages['all'];

                } else if (false && (lowerMsg === 'help' || lowerMsg.includes('what can you do'))) {
                    // General help without category
                    response = "I can help you insert or delete components in your page. Just tell me what you want to do:\n• **Buttons**: 'button' (primary), 'button success', 'button info', 'button warning', 'button danger'\n• **Alerts**: 'alert', 'alert danger', 'alert warning', 'alert success', 'alert info' (with or without 'link')\n• **Introduction**: 'introduction', 'introduction full image', 'introduction half image'\n• **Services & Info**: 'services and information' (3 columns, 2 columns, or list)\n• **Feature Links**: 'feature link' (basic, dark, light, or gray background)\n• **Government**: 'government initiatives'\n• **Most Requested**: 'most requested links'\n• **Navigation**: 'breadcrumb', 'sidebar', 'footer', 'search'\n• **Tables**: 'table'\n• **Delete**: 'delete' or 'remove'\n\nType 'help [category]' for more details, e.g. 'help alert', 'help button'.";
                } else if (lowerMsg.includes('hello') || lowerMsg.includes('hi') || lowerMsg.includes('hey')) {
                    response = "Hello! I'm your WebBot AI assistant. I can help you insert components into your Canada.ca page. What would you like to add? Try 'insert introduction block', 'most requested links', 'feature link', 'government initiatives', 'social media', 'calendar of events', 'theme page', 'topic template' or 'help' to see all options.";
                } else if (lowerMsg.includes('edit html') || lowerMsg.includes('html edit') || lowerMsg.includes('edit raw') || lowerMsg.includes('编辑 html') || lowerMsg.includes('代码编辑')) {
                    response = "✏️ Opening HTML source editor for the element at cursor position...";
                    setTimeout(() => {
                        if (typeof showCurrentElementHTMLEdit === 'function') {
                            showCurrentElementHTMLEdit('code');
                        }
                    }, 600);
                } else if (lowerMsg.includes('edit component') || lowerMsg.includes('component edit') || lowerMsg.includes('wysiwyg') || lowerMsg.includes('编辑组件') || lowerMsg.includes('可视化') || lowerMsg.includes('组件编辑')) {
                    response = "🎨 Opening WYSIWYG component editor for the element at cursor position...";
                    setTimeout(() => {
                        if (typeof showCurrentElementWYSIWYGEdit === 'function') {
                            showCurrentElementWYSIWYGEdit();
                        } else if (typeof showCurrentElementHTMLEdit === 'function') {
                            showCurrentElementHTMLEdit('wysiwyg');
                        }
                    }, 600);
                } else if (lowerMsg.includes('what') || lowerMsg.includes('detect') || lowerMsg.includes('检测') || lowerMsg.includes('看看') || lowerMsg.includes('检查') || lowerMsg.includes('what is') || lowerMsg.includes('识别')) {
                    // Detect and describe component at cursor
                    if (window.CanadaColorManager) {
                        response = window.CanadaColorManager.describeCurrent();
                    } else {
                        response = "Color/component manager not loaded. Try refreshing the page.";
                    }
                } else if (lowerMsg.includes('make it open') || lowerMsg.includes('打开它') || lowerMsg.includes('展开') || lowerMsg.includes('open details') || lowerMsg.includes('open it') || lowerMsg.includes('make open')) {
                    // "Make it open" - add open="true" to <details>
                    if (window.CanadaColorManager) {
                        var openResult = window.CanadaColorManager.makeOpen();
                        if (openResult.success) {
                            response = '🔓 ' + openResult.display;
                        } else {
                            response = '❌ ' + openResult.error + '\n\nTip: Click on a <details> element first, then say "make it open" or use /open.';
                        }
                    } else {
                        response = 'Component manager not loaded. Try refreshing the page.';
                    }
                } else if (lowerMsg.includes('make it close') || lowerMsg.includes('关') || lowerMsg.includes('收起') || lowerMsg.includes('close details') || lowerMsg.includes('close it') || lowerMsg.includes('make close')) {
                    // "Make it close" - remove open="true" from <details>
                    if (window.CanadaColorManager) {
                        var closeResult = window.CanadaColorManager.makeClose();
                        if (closeResult.success) {
                            response = '🔒 ' + closeResult.display;
                        } else {
                            response = '❌ ' + closeResult.error + '\n\nTip: Click on a <details> element first, then say "make it close" or use /close.';
                        }
                    } else {
                        response = 'Component manager not loaded. Try refreshing the page.';
                    }
                } else if (lowerMsg.includes('change') || lowerMsg.includes('改为') || lowerMsg.includes('改成') || lowerMsg.includes('make it') || lowerMsg.includes('turn it') || lowerMsg.includes('变成')) {
                    // Color change command - natural language
                    const colorKeywords = ['red', 'green', 'blue', 'yellow', 'danger', 'success', 'info', 'warning', '红色', '绿色', '蓝色', '黄色', '红', '绿', '蓝', '黄'];
                    let colorTarget = null;
                    for (const ck of colorKeywords) {
                        if (lowerMsg.includes(ck)) {
                            colorTarget = ck;
                            break;
                        }
                    }
                    if (colorTarget && window.CanadaColorManager) {
                        const comp = window.CanadaColorManager.getCurrentComponent();
                        if (comp) {
                            const result = window.CanadaColorManager.changeColor(comp.element, colorTarget);
                            if (result.success) {
                                response = `🎨 ${result.display}`;
                            } else {
                                response = `❌ ${result.error}`;
                            }
                        } else {
                            response = "Please click on a component first, then say 'change to red' or 'make it blue'.";
                        }
                    } else if (colorTarget) {
                        response = "Color manager not loaded. Try refreshing the page.";
                    } else {
                        // Not a color change, fall through
                        response = "I'm not sure what you mean. I can help you insert components like buttons, tables, alerts, breadcrumbs, sidebars, footers, search boxes, introduction blocks, most requested links, feature links, government initiatives, social media, calendar, theme pages, topic templates, or Services and Information sections.\n\n• To **change color** of a component: click on it, then say 'change to red', 'make it green', etc.\n• To **edit raw HTML** of an element: say 'edit html' or '/html'\n• To **edit a component visually** (WYSIWYG): say 'edit component' or '/edit-component'\n• To insert something, just describe it.\n\nType 'help' to see the full list.";
                    }
                } else {
                    response = "I'm not sure what you mean. I can help you insert components like buttons, tables, alerts, breadcrumbs, sidebars, footers, search boxes, introduction blocks, most requested links, feature links, government initiatives, social media, calendar, theme pages, topic templates, or Services and Information sections.\n\n• To **edit raw HTML** of an element: say 'edit html' or '/html'\n• To **edit a component visually** (WYSIWYG): say 'edit component' or '/edit-component'\n• To insert something, just describe it.\n\nType 'help' to see the full list.";
                }

                // Add AI response
                addAIMessage(response, 'assistant');

                // Insert or delete component if identified
                if (componentType) {
                    setTimeout(async () => {
                        if (componentType === 'delete') {
                            const deleted = deleteComponent();
                            if (deleted) {
                                addAIMessage(`✅ Successfully deleted component at cursor position.`, 'system');
                            } else {
                                addAIMessage(`❌ No WebBot component found at cursor position. Place your cursor inside a component (button, table, alert, etc.) and try again.`, 'system');
                            }
                        } else if (componentType === 'copy') {
                            const copied = copyComponent();
                            if (copied) {
                                addAIMessage(`✅ Successfully copied component at cursor position.`, 'system');
                            } else {
                                addAIMessage(`❌ No component found at cursor position. Place your cursor inside a component (button, table, alert, etc.) and try again.`, 'system');
                            }
                        } else if (componentType === 'paste') {
                            const pasted = pasteComponent();
                            if (pasted) {
                                addAIMessage(`✅ Successfully pasted copied component next to original.`, 'system');
                            } else {
                                addAIMessage(`❌ Failed to paste. Make sure you have copied a component first.`, 'system');
                            }
                        } else if (componentType.startsWith('append-')) {
                            // Handle append commands
                            const appendType = componentType.substring(7); // Remove "append-" prefix
                            let actualComponentType = '';
                            let appendMessage = '';

                            if (appendType === 'empty') {
                                // Append empty paragraph
                                const appended = appendComponent('');
                                if (appended) {
                                    appendMessage = `✅ Successfully appended empty paragraph to end of page content.`;
                                } else {
                                    appendMessage = `❌ Failed to append empty paragraph. Make sure the editor is initialized.`;
                                }
                            } else {
                                // Append specific component
                                actualComponentType = appendType;
                                const appended = appendComponent(actualComponentType);
                                if (appended) {
                                    appendMessage = `✅ Successfully appended ${actualComponentType} component to end of page content.`;
                                } else {
                                    appendMessage = `❌ Failed to append ${actualComponentType} component. Make sure the editor is initialized.`;
                                }
                            }

                            addAIMessage(appendMessage, 'system');
                        } else {
                            // Handle regular insert commands
                            const inserted = await insertComponent(componentType);
                            if (inserted) {
                                addAIMessage(`✅ Successfully inserted ${componentType} component at cursor position.`, 'system');
                            } else {
                                addAIMessage(`❌ Failed to insert ${componentType}. Make sure the editor is initialized.`, 'system');
                            }
                        }
                    }, 500);
                }
            }, 1000 + Math.random() * 1000); // Random delay 1-2 seconds
        }

        // Initialize AI assistant event listeners
        function initializeAIAssistant() {
            const panelCloseBtn = document.getElementById('ai-panel-close');
            const chatSendBtn = document.getElementById('ai-chat-send');
            const chatInput = document.getElementById('ai-chat-input');

            if (panelCloseBtn) {
                panelCloseBtn.addEventListener('click', function() {
                    const panel = document.getElementById('ai-assistant-panel');
                    if (panel) {
                        panel.classList.add('hidden');
                    }
                });
            }

            if (chatSendBtn && chatInput) {
                // Send message on button click
                chatSendBtn.addEventListener('click', function() {
                    const message = chatInput.value.trim();
                    if (message) {
                        addAIMessage(message, 'user');
                        chatInput.value = '';
                        processAIMessage(message);
                    }
                });

                // Send message on Enter key
                chatInput.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        const message = chatInput.value.trim();
                        if (message) {
                            addAIMessage(message, 'user');
                            chatInput.value = '';
                            processAIMessage(message);
                        }
                    }
                });
            }

            console.log('AI Assistant initialized');
        }

        // Initialize AI assistant when DOM is loaded
        document.addEventListener('DOMContentLoaded', function() {
            initializeAIAssistant();
        });

        // ========== END AI ASSISTANT FUNCTIONS ==========

        // ========== FILE MANAGER FUNCTIONS ==========

        /* File Manager HTML structure - COMMENTED OUT: FileManager no longer used per user request
        const fileManagerHTML = `
        <section id="file-manager-modal" class="filebot-modal" style="display: none; max-width: 900px; max-height: 90vh; overflow-y: auto; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 900px; max-width: 90vw; max-height: 90vh; overflow: auto; background-color: white; border: 1px solid #ccc; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); z-index: 9999;">
            <header class="modal-header" style="position: sticky; top: 0; background-color: white; z-index: 1; border-bottom: 1px solid #ddd;">
                <h2 class="modal-title" id="file-manager-title">📁 FileBot File Manager</h2>
                <button type="button" class="close overlay-close" title="Close">×<span>Close</span></button>
            </header>
            <div class="modal-body" style="max-height: calc(90vh - 130px); overflow-y: auto;">
                <div class="row">
                    <div class="col-md-12">
                                        <!-- 顶部:拖放上传区域 -->
                        <div class="panel panel-default" style="margin-bottom: 20px;">
                            <div class="panel-heading">
                                <h3 class="panel-title">📤 Upload to FileBot</h3>
                            </div>
                            <div class="panel-body">
                                <div id="file-upload-area" class="well" style="border: 3px dashed #4CAF50; padding: 30px; text-align: center; cursor: pointer; background-color: #f8fff8;">
                                    <p style="font-size: 18px; margin-bottom: 10px;">
                                        <span class="glyphicon glyphicon-cloud-upload" style="font-size: 48px; color: #4CAF50;"></span>
                                    </p>
                                    <p style="font-size: 18px; font-weight: bold; color: #2E7D32;">Drag & Drop files here</p>
                                    <p style="color: #666; margin-bottom: 15px;">or click to select files (Max: 100MB)</p>
                                    <input type="file" id="file-input" multiple style="display: none;">
                                    <button type="button" class="btn btn-success" id="browse-files-btn">
                                        <span class="glyphicon glyphicon-folder-open"></span> Browse Files
                                    </button>
                                    <div style="margin-top: 15px; font-size: 12px; color: #777;">
                                        <span class="glyphicon glyphicon-info-sign"></span> Files will be uploaded to FileBot storage
                                    </div>
                                </div>
                                <div id="upload-progress" style="display: none; margin-top: 15px;">
                                    <div class="progress">
                                        <div class="progress-bar progress-bar-striped active" role="progressbar" style="width: 0%; background-color: #4CAF50;">
                                            <span class="sr-only">0% Complete</span>
                                        </div>
                                    </div>
                                    <p id="upload-status" style="text-align: center; margin-top: 10px;">Uploading to FileBot...</p>
                                </div>
                            </div>
                        </div>

                        <!-- 中部:筛选控制区域 -->
                        <div class="panel panel-default" style="margin-bottom: 20px;">
                            <div class="panel-heading">
                                <h3 class="panel-title">🔍 Filter & Search</h3>
                            </div>
                            <div class="panel-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="form-group">
                                            <label for="path-input">📁 Path / Folder</label>
                                            <input type="text" class="form-control" id="path-input" placeholder="e.g. /documents/images" value="/">
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="form-group">
                                            <label for="search-filter">🔎 Search</label>
                                            <input type="text" class="form-control" id="search-filter" placeholder="Search by filename, title...">
                                        </div>
                                    </div>
                                </div>
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="form-group">
                                            <label for="file-type-filter">📄 File Type</label>
                                            <select class="form-control" id="file-type-filter">
                                                <option value="all">All Files</option>
                                                <option value="image">Images Only (PNG, JPG, GIF)</option>
                                                <option value="document">Documents (PDF, DOC, XLS)</option>
                                                <option value="archive">Archives (ZIP, RAR)</option>
                                                <option value="other">Other Files</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="form-group">
                                            <label for="sort-by">📊 Sort By</label>
                                            <select class="form-control" id="sort-by">
                                                <option value="name">Name (A-Z)</option>
                                                <option value="date">Date (Newest First)</option>
                                                <option value="size">Size (Largest First)</option>
                                                <option value="type">File Type</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                                <div class="text-right">
                                    <button type="button" class="btn btn-primary" id="apply-filters-btn">
                                        <span class="glyphicon glyphicon-filter"></span> Apply Filters
                                    </button>
                                    <button type="button" class="btn btn-default" id="reset-filters-btn">
                                        <span class="glyphicon glyphicon-refresh"></span> Reset
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- 下部:文件列表 -->
                        <div class="panel panel-default">
                            <div class="panel-heading">
                                <div class="row">
                                    <div class="col-md-8">
                                        <h3 class="panel-title" style="margin-top: 5px;">📁 FileBot Documents <span id="file-count" class="badge">0</span></h3>
                                    </div>
                                    <div class="col-md-4 text-right">
                                        <div class="btn-group">
                                            <button type="button" class="btn btn-xs btn-default" id="refresh-files-btn" title="Refresh list">
                                                <span class="glyphicon glyphicon-refresh"></span>
                                            </button>
                                            <button type="button" class="btn btn-xs btn-default" id="select-all-btn" title="Select all">
                                                <span class="glyphicon glyphicon-check"></span>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="panel-body">
                                <div id="file-list-container">
                                    <div class="alert alert-info" id="loading-files-message">
                                        <span class="glyphicon glyphicon-hourglass"></span>
                                        Loading documents from FileBot...
                                    </div>
                                    <div class="alert alert-warning" id="no-files-message" style="display: none;">
                                        <span class="glyphicon glyphicon-info-sign"></span>
                                        No documents found. Upload your first file to get started.
                                    </div>
                                    <table class="table table-striped table-hover" id="file-list-table" style="display: none;">
                                        <thead>
                                            <tr>
                                                <th width="50px"><input type="checkbox" id="select-all-checkbox"></th>
                                                <th>Name</th>
                                                <th width="120px">Type</th>
                                                <th width="100px">Size</th>
                                                <th width="150px">Date</th>
                                                <th width="100px">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody id="file-list-body">
                                            <!-- Files will be loaded from FileBot API -->
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer" style="position: sticky; bottom: 0; background-color: white; z-index: 1; border-top: 1px solid #ddd;">
                <button type="button" class="btn btn-default overlay-close">Cancel</button>
                <button type="button" class="btn btn-primary" id="insert-selected-file" disabled>
                    <span class="glyphicon glyphicon-link"></span> Insert Selected File
                </button>
            </div>
        </section>
        `;
        */

        // Insert file manager HTML into DOM on page load - COMMENTED OUT: FileManager no longer used
        /*
        function insertFileManagerHTML() {
            // Check if modal already exists
            if (document.getElementById('file-manager-modal')) {
                console.log('File manager modal already exists in DOM');
                return;
            }

            // Create container for file manager modal
            const container = document.createElement('div');
            container.id = 'file-manager-container';
            container.innerHTML = fileManagerHTML;

            // Append to body
            document.body.appendChild(container);
            console.log('File manager HTML inserted into DOM');

            // Initialize file manager after inserting HTML
            setTimeout(() => {
                initializeFileManager();
                // Note: loadFiles() is now called when modal opens (方案C)
                console.log('File manager HTML inserted and initialized');
            }, 100);
        }
        */

        // Ensure file manager modal exists in DOM (lazy loading) - COMMENTED OUT: FileManager no longer used
        /*
        function ensureFileManagerModalExists() {
            const modal = document.getElementById('file-manager-modal');
            if (!modal) {
                console.log('File manager modal not found, inserting HTML...');
                insertFileManagerHTML();
                return true; // Modal was inserted
            }
            return false; // Modal already exists
        }
        */

        // Open file manager modal - COMMENTED OUT: FileManager no longer used
        /*
        function openFileManager() {
            console.log('openFileManager called - opening FileBot picker');

            // Open FileBot picker in a new window or tab
            const pickerUrl = '/static/filebot-picker.html';

            // Check if we want to open in new window or in existing panel
            // For now, open in new window/tab
            window.open(pickerUrl, 'FileBotPicker', 'width=1000,height=700,resizable=yes,scrollbars=yes');

            console.log('Opened FileBot picker at:', pickerUrl);
        }
        */

        // Initialize file manager event handlers - COMMENTED OUT: FileManager no longer used
        function initializeFileManager() { /* Commented out */ return;
            const modal = document.getElementById('file-manager-modal');
            if (!modal) return;

            // Prevent duplicate initialization
            if (window.fileManagerInitialized) {
                console.log('File manager already initialized, skipping');
                return;
            }
            window.fileManagerInitialized = true;
            console.log('Initializing file manager event handlers');

            // Browse files button
            const browseBtn = document.getElementById('browse-files-btn');
            const fileInput = document.getElementById('file-input');
            const uploadArea = document.getElementById('file-upload-area');

            if (browseBtn && fileInput) {
                browseBtn.addEventListener('click', function() {
                    fileInput.click();
                });
            }

            // File input change event
            if (fileInput) {
                fileInput.addEventListener('change', function(e) {
                    if (e.target.files.length > 0) {
                        uploadFiles(e.target.files);
                    }
                });
            }

            // Drag and drop upload
            if (uploadArea) {
                uploadArea.addEventListener('dragover', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    uploadArea.style.borderColor = '#31708f';
                    uploadArea.style.backgroundColor = '#f5f5f5';
                });

                uploadArea.addEventListener('dragleave', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    uploadArea.style.borderColor = '#ccc';
                    uploadArea.style.backgroundColor = '';
                });

                uploadArea.addEventListener('drop', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    uploadArea.style.borderColor = '#ccc';
                    uploadArea.style.backgroundColor = '';

                    if (e.dataTransfer.files.length > 0) {
                        uploadFiles(e.dataTransfer.files);
                    }
                });

                uploadArea.addEventListener('click', function() {
                    fileInput.click();
                });
            }

            // Insert selected file button
            const insertBtn = document.getElementById('insert-selected-file');
            if (insertBtn) {
                insertBtn.addEventListener('click', function() {
                    const selectedFile = document.querySelector('#file-list-body tr.selected');
                    if (selectedFile) {
                        const fileId = selectedFile.dataset.fileId;
                        const fileName = selectedFile.dataset.fileName;
                        const fileType = selectedFile.dataset.fileType;

                        insertFileLink(fileId, fileName, fileType, null);
                        // Close the modal by clicking the close button
                        const closeBtn = document.querySelector('#file-manager-modal .overlay-close');
                        if (closeBtn) closeBtn.click();
                    }
                });
            }

            // Close modal handlers - WET-BOEW handles closing automatically for .overlay-close buttons
            // No need to add additional click handlers

            // Add event listeners for filter controls
            const applyFiltersBtn = document.getElementById('apply-filters-btn');
            const resetFiltersBtn = document.getElementById('reset-filters-btn');
            const refreshFilesBtn = document.getElementById('refresh-files-btn');
            const selectAllBtn = document.getElementById('select-all-btn');
            const selectAllCheckbox = document.getElementById('select-all-checkbox');
            const searchFilter = document.getElementById('search-filter');
            const fileTypeFilter = document.getElementById('file-type-filter');
            const sortBy = document.getElementById('sort-by');

            // Apply filters button
            if (applyFiltersBtn) {
                applyFiltersBtn.addEventListener('click', function() {
                    console.log('Applying filters...');
                    loadFiles();
                });
            }

            // Reset filters button
            if (resetFiltersBtn) {
                resetFiltersBtn.addEventListener('click', function() {
                    console.log('Resetting filters...');
                    if (searchFilter) searchFilter.value = '';
                    if (fileTypeFilter) fileTypeFilter.value = 'all';
                    if (sortBy) sortBy.value = 'name';
                    loadFiles();
                });
            }

            // Refresh files button
            if (refreshFilesBtn) {
                refreshFilesBtn.addEventListener('click', function() {
                    console.log('Refreshing file list...');
                    loadFiles();
                });
            }

            // Select all button
            if (selectAllBtn) {
                selectAllBtn.addEventListener('click', function() {
                    const checkboxes = document.querySelectorAll('.file-select-checkbox');
                    const allChecked = Array.from(checkboxes).every(cb => cb.checked);

                    checkboxes.forEach(cb => {
                        cb.checked = !allChecked;
                    });

                    updateSelectedFilesCount();
                });
            }

            // Select all checkbox
            if (selectAllCheckbox) {
                selectAllCheckbox.addEventListener('change', function() {
                    const checkboxes = document.querySelectorAll('.file-select-checkbox');
                    checkboxes.forEach(cb => {
                        cb.checked = this.checked;
                    });
                    updateSelectedFilesCount();
                });
            }

            // Search filter - auto-apply on Enter key
            if (searchFilter) {
                searchFilter.addEventListener('keyup', function(e) {
                    if (e.key === 'Enter') {
                        loadFiles();
                    }
                });
            }

            // Auto-apply when filter values change (optional)
            if (fileTypeFilter) {
                fileTypeFilter.addEventListener('change', function() {
                    // Optional: auto-apply on change
                    // loadFiles();
                });
            }

            if (sortBy) {
                sortBy.addEventListener('change', function() {
                    // Optional: auto-apply on change
                    // loadFiles();
                });
            }

            // Initial load of files
            // console.log('Initializing FileBot file manager...');
            // loadFiles();
        }

        // FileBot API Configuration - Environment aware
        const FILEBOT_API_BASE = (function() {
            // 1. Priority: Global configuration (can be injected by server template)
            if (window.FILEBOT_API_BASE_CONFIG) {
                console.log('[FileBot] Using window.FILEBOT_API_BASE_CONFIG:', window.FILEBOT_API_BASE_CONFIG);
                return window.FILEBOT_API_BASE_CONFIG;
            }

            // 2. Environment detection
            const hostname = window.location.hostname;
            const protocol = window.location.protocol;
            const port = window.location.port;

            // Check if this is production environment (canada.ca)
            if (hostname.endsWith('canada.ca')) {
                // Production environment - assume same domain strategy for canada.ca
                console.log('[FileBot] Production environment detected:', hostname);

                // Strategy: Use relative path for same-domain access
                // If FileBot API is accessible from the same domain (reverse proxy)
                return '/api/v1'; // Relative path - will use current protocol://hostname
            } else {
                // Development environment (localhost, IP addresses, or other dev domains)
                console.log('[FileBot] Development environment detected:', hostname);
                // Check if we're on WebBot port (8000) or FileBot port (8001)
                if (port === '8000' || port === '') {
                    // WebBot editor - use same hostname for FileBot API to avoid CORS issues
                    // Use the same hostname but port 8001 for FileBot
                    return `${protocol}//${hostname}:8001/api/v1`;
                } else if (port === '8001') {
                    // Direct FileBot access - use current host
                    return `${protocol}//${hostname}:${port}/api/v1`;
                }
                return `${protocol}//${hostname}:8001/api/v1`;
            }

            // Alternative: If FileBot is on a subdomain
            // return 'https://filebot.canada.ca/api/v1';

            // Fallback: default development URL
            // return 'http://localhost:8001/api/v1';
        })();


        console.log('[FileBot] Final API_BASE:', FILEBOT_API_BASE);

        // 方案B:统一URL配置
        const URL_CONFIG = {
            // FileBot API代理路径
            filebot: {
                upload: '/content/upload/',
                documents: '/content/documents/',
                folders: '/content/folders/',
                search: '/content/search/',
                documentById: (id) => `/content/documents/${id}`,
                documentDownload: (id) => `/content/documents/${id}/download`,
                documentByPath: (path) => `/content/dam/${path}`
            },

            // WebBot自身API(保持不变)
            webbot: {
                pages: '/api/v1/pages',
                pagesByPath: (path) => `/api/v1/pages/by-path?path=${encodeURIComponent(path)}`,
                components: '/api/v1/components/templates'
            }
        };

        window.URL_CONFIG = URL_CONFIG;
        console.log('[URL Config] 配置已加载');


        const FILEBOT_JWT_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0ZGFkNmZhMS1kNTIxLTQxN2YtODg3Ny1lZmU5NWZjZjFmMDQiLCJleHAiOjE4MTAwNjQzMDR9.0CI5rjrAcsJUkL5LSrWWBmc2paDNVeOwJxnN4gk9txA';

        // Convert FileBot document to file manager format
        function convertDocumentToFile(doc) {
            try {
                console.log('convertDocumentToFile raw doc:', doc);

                // If doc is null or undefined, return null
                if (!doc) {
                    console.warn('convertDocumentToFile: doc is null or undefined');
                    return null;
                }

                // Determine best filename with extension
                let fileName = 'Unknown';
                let fileExt = '';

            // Prefer original_filename if it has extension
            if (doc.original_filename && doc.original_filename.includes('.')) {
                fileName = doc.original_filename;
                fileExt = fileName.split('.').pop().toLowerCase();
            }
            // Otherwise use stored_filename
            else if (doc.stored_filename) {
                fileName = doc.stored_filename;
                // Check if stored_filename has extension
                if (fileName.includes('.')) {
                    fileExt = fileName.split('.').pop().toLowerCase();
                } else {
                    // If stored_filename has no extension, try to determine from mime_type
                    // Handle both 'image/jpeg' and 'jpg' formats
                    if (doc.mime_type) {
                        let extension = '';

                        // Case 1: mime_type is full MIME type like 'image/jpeg'
                        if (doc.mime_type.startsWith('image/')) {
                            const mimeExt = doc.mime_type.split('/')[1];
                            extension = mimeExt === 'jpeg' ? 'jpg' : mimeExt;
                        }
                        // Case 2: mime_type is just extension like 'jpg'
                        else if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(doc.mime_type.toLowerCase())) {
                            extension = doc.mime_type.toLowerCase() === 'jpeg' ? 'jpg' : doc.mime_type.toLowerCase();
                        }

                        if (extension) {
                            fileExt = extension;
                            fileName = fileName + '.' + fileExt;
                            console.log('Added extension to stored_filename:', { stored_filename: doc.stored_filename, fileName, fileExt });
                        }
                    }
                }
            }
            // Fallback to title
            else if (doc.title) {
                fileName = doc.title;
                if (fileName.includes('.')) {
                    fileExt = fileName.split('.').pop().toLowerCase();
                }
            }

            // Determine file type (MIME type)
            let fileType = 'application/octet-stream';

            // First, use mime_type from API if it's a valid MIME type
            if (doc.mime_type) {
                // Check if mime_type is already a valid MIME type
                if (doc.mime_type.includes('/')) {
                    fileType = doc.mime_type;
                }
                // If mime_type is just an extension like 'jpg', convert to MIME type
                else if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(doc.mime_type.toLowerCase())) {
                    fileType = 'image/' + (doc.mime_type.toLowerCase() === 'jpg' ? 'jpeg' : doc.mime_type.toLowerCase());
                }
            }

            // If still octet-stream, determine from file extension
            if (fileType === 'application/octet-stream' && fileExt) {
                if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(fileExt)) {
                    fileType = 'image/' + (fileExt === 'jpg' ? 'jpeg' : fileExt);
                } else if (fileExt === 'pdf') {
                    fileType = 'application/pdf';
                } else if (['doc', 'docx'].includes(fileExt)) {
                    fileType = 'application/msword';
                } else if (['xls', 'xlsx'].includes(fileExt)) {
                    fileType = 'application/vnd.ms-excel';
                } else if (['zip', 'rar', '7z'].includes(fileExt)) {
                    fileType = 'application/zip';
                }
            }

            // Check if file is image based on mime type or extension
            const isImage = fileType.startsWith('image/') ||
                           ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(fileExt);

            // Use created_at if available, otherwise use current time
            const uploadedAt = doc.created_at || doc.document_metadata?.import_time || new Date().toISOString();

            // Get public URL for the document
            const publicUrl = getPublicUrlFromDocument(doc);

            const result = {
                id: doc.id,
                name: fileName,
                title: doc.title || fileName,
                type: fileType,
                size: doc.file_size || 0,
                uploaded_at: uploadedAt,
                download_url: publicUrl || URL_CONFIG.filebot.documentDownload(doc.id),
                isImage: isImage,
                fileExt: fileExt,
                original_document: doc
            };

            console.log('convertDocumentToFile result:', result);
            return result;
            } catch (error) {
                console.error('Error in convertDocumentToFile:', error, doc);
                // Return null to be filtered out later
                return null;
            }
        }

        // Load documents from FileBot API
        async function loadFiles() {
            console.log('Loading documents from FileBot...');

            // Show loading message
            const loadingMsg = document.getElementById('loading-files-message');
            const noFilesMsg = document.getElementById('no-files-message');
            if (loadingMsg) loadingMsg.style.display = 'block';
            if (noFilesMsg) noFilesMsg.style.display = 'none';

            try {
                // Determine target folder
                const targetFolder = window.currentFileBotFolder;
                let folderId = null;

                // Build API URL with folder filter if target folder exists
                let apiUrl = URL_CONFIG.filebot.documents;
                const params = new URLSearchParams();

                if (targetFolder) {
                    console.log(`Filtering documents by target folder: ${targetFolder}`);
                    try {
                        folderId = await getFolderIdFromPath(targetFolder);
                        if (folderId) {
                            params.append('folder_id', folderId);
                            console.log(`Filtering by folder_id: ${folderId}`);
                        } else {
                            // If folder ID not found, try folder_path parameter
                            params.append('folder_path', targetFolder);
                            console.log(`Filtering by folder_path: ${targetFolder} (folder ID not found)`);
                        }
                    } catch (error) {
                        console.error('Error getting folder ID:', error);
                        // Fallback to folder_path parameter
                        params.append('folder_path', targetFolder);
                        console.log(`Using folder_path fallback: ${targetFolder}`);
                    }
                } else {
                    console.log('No target folder configured, loading all documents');
                }

                if (params.toString()) {
                    apiUrl += '?' + params.toString();
                }

                const response = await fetch(apiUrl, {
                    headers: {
                        'Authorization': `Bearer ${FILEBOT_JWT_TOKEN}`
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const responseData = await response.json();

                // Ensure data is an array
                let data = [];
                if (Array.isArray(responseData)) {
                    data = responseData;
                } else if (responseData && responseData.documents) {
                    // Handle case where API returns {documents: [...]}
                    data = Array.isArray(responseData.documents) ? responseData.documents : [];
                } else if (responseData && responseData.items) {
                    // Handle case where API returns {items: [...]}
                    data = Array.isArray(responseData.items) ? responseData.items : [];
                } else if (responseData && typeof responseData === 'object') {
                    // Single document object
                    data = [responseData];
                }

                console.log(`Loaded ${data.length || 0} documents from FileBot${targetFolder ? ` for folder: ${targetFolder}` : ''}`);

                // Convert documents to file format - handle each document individually
                let files = [];
                if (Array.isArray(data) && data.length > 0) {
                    for (let i = 0; i < data.length; i++) {
                        const doc = data[i];
                        try {
                            const file = convertDocumentToFile(doc);
                            if (file) {
                                files.push(file);
                            }
                        } catch (docError) {
                            console.error(`Error converting document ${i} (ID: ${doc?.id}):`, docError);
                            // Continue processing other documents
                            // Optionally add a placeholder for the failed document
                            files.push({
                                id: doc?.id || `error-${i}`,
                                name: `Error loading document ${doc?.id || i}`,
                                title: `Error loading document`,
                                type: 'application/octet-stream',
                                size: 0,
                                uploaded_at: new Date().toISOString(),
                                download_url: '#',
                                isImage: false,
                                fileExt: '',
                                original_document: null,
                                error: true,
                                errorMessage: docError.message
                            });
                        }
                    }
                    console.log(`Successfully converted ${files.length} out of ${data.length} documents`);
                }

                // Apply UI filters if any
                let filteredFiles = [];
                try {
                    filteredFiles = applyFilters(files);
                } catch (filterError) {
                    console.error('Error applying filters:', filterError);
                    filteredFiles = files; // Fallback to unfiltered files
                }

                try {
                    updateFileList(filteredFiles);
                } catch (updateError) {
                    console.error('Error updating file list:', updateError);
                    // Try to at least clear the UI
                    updateFileList([]);
                }

                // Hide loading message
                if (loadingMsg) loadingMsg.style.display = 'none';

            } catch (error) {
                console.error('Error loading documents from FileBot:', error);
                updateFileList([]);

                // Show error in UI
                if (loadingMsg) {
                    loadingMsg.innerHTML = `
                        <span class="glyphicon glyphicon-exclamation-sign"></span>
                        Error loading documents: ${error.message}
                    `;
                    loadingMsg.className = 'alert alert-danger';
                }
            }
        }

        // Apply filters to files
        function applyFilters(files) {
            // Ensure files is an array
            if (!Array.isArray(files)) {
                console.warn('applyFilters: files is not an array, converting to empty array');
                files = [];
            }

            const searchTerm = document.getElementById('search-filter')?.value.toLowerCase() || '';
            const fileTypeFilter = document.getElementById('file-type-filter')?.value || 'all';
            const sortBy = document.getElementById('sort-by')?.value || 'name';

            let filtered = files;

            // Apply search filter
            if (searchTerm) {
                filtered = filtered.filter(file =>
                    file.name.toLowerCase().includes(searchTerm) ||
                    file.title.toLowerCase().includes(searchTerm)
                );
            }

            // Apply file type filter
            if (fileTypeFilter !== 'all') {
                filtered = filtered.filter(file => {
                    if (fileTypeFilter === 'image') return file.isImage;
                    if (fileTypeFilter === 'document') return file.type.includes('pdf') || file.type.includes('msword') || file.type.includes('excel');
                    if (fileTypeFilter === 'archive') return file.type.includes('zip') || file.type.includes('rar') || file.type.includes('7z');
                    if (fileTypeFilter === 'other') return !file.isImage && !file.type.includes('pdf') && !file.type.includes('msword') && !file.type.includes('excel') && !file.type.includes('zip');
                    return true;
                });
            }

            // Apply sorting
            filtered.sort((a, b) => {
                switch (sortBy) {
                    case 'name':
                        return a.name.localeCompare(b.name);
                    case 'date':
                        return new Date(b.uploaded_at) - new Date(a.uploaded_at);
                    case 'size':
                        return b.size - a.size;
                    case 'type':
                        return a.type.localeCompare(b.type);
                    default:
                        return 0;
                }
            });

            return filtered;
        }

        // Update file list display
        function updateFileList(files) {
            const fileListBody = document.getElementById('file-list-body');
            const noFilesMessage = document.getElementById('no-files-message');
            const fileListTable = document.getElementById('file-list-table');
            const fileCount = document.getElementById('file-count');
            const loadingMsg = document.getElementById('loading-files-message');
            const selectAllCheckbox = document.getElementById('select-all-checkbox');

            if (!fileListBody) return;

            // Hide loading message
            if (loadingMsg) loadingMsg.style.display = 'none';

            // Update file count
            if (fileCount) {
                fileCount.textContent = files.length;
            }

            // Reset select all checkbox
            if (selectAllCheckbox) {
                selectAllCheckbox.checked = false;
            }

            // Show/hide empty state
            if (files.length === 0) {
                if (noFilesMessage) noFilesMessage.style.display = 'block';
                if (fileListTable) fileListTable.style.display = 'none';
                return;
            }

            // Show table
            if (noFilesMessage) noFilesMessage.style.display = 'none';
            if (fileListTable) fileListTable.style.display = 'table';

            // Clear existing rows
            fileListBody.innerHTML = '';

            // Add file rows
            files.forEach((file, index) => {
                console.log('updateFileList processing file:', {
                    id: file.id,
                    name: file.name,
                    hasOriginalDocument: !!file.original_document,
                    originalDocumentKeys: file.original_document ? Object.keys(file.original_document) : []
                });

                const row = document.createElement('tr');
                row.dataset.fileId = file.id;
                row.dataset.fileName = file.name;
                row.dataset.fileType = file.type;
                row.dataset.isImage = file.isImage;
                row.dataset.downloadUrl = file.download_url;
                // Store original document as JSON string for debugging
                if (file.original_document) {
                    try {
                        row.dataset.originalDocument = JSON.stringify(file.original_document);
                    } catch (e) {
                        console.warn('Failed to stringify original_document:', e);
                    }
                }

                // Format file size
                const fileSize = formatFileSize(file.size || 0);

                // Format date
                const uploadDate = new Date(file.uploaded_at || Date.now()).toLocaleDateString('en-CA', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                });

                // Determine file type icon
                const fileIcon = getFileIcon(file.type, file.name);

                // Get file type label
                const fileTypeLabel = getFileTypeLabel(file.type);

                // Determine badge color based on file type
                let badgeClass = 'label-default';
                if (file.isImage) badgeClass = 'label-success';
                else if (fileTypeLabel === 'PDF') badgeClass = 'label-danger';
                else if (['Word', 'Excel', 'PowerPoint'].includes(fileTypeLabel)) badgeClass = 'label-primary';
                else if (fileTypeLabel === 'Archive') badgeClass = 'label-warning';

                row.innerHTML = `
                    <td style="text-align: center; vertical-align: middle;">
                        <input type="checkbox" class="file-select-checkbox" data-file-id="${file.id}">
                    </td>
                    <td style="vertical-align: middle;">
                        <div style="display: flex; align-items: center;">
                            <span class="${fileIcon}" style="font-size: 16px; margin-right: 8px; color: #666;"></span>
                            <div style="flex: 1;">
                                <div style="font-weight: 500; margin-bottom: 2px;">${escapeHtml(file.title || file.name)}</div>
                                <div style="font-size: 11px; color: #888; font-family: monospace;">${escapeHtml(file.name)}</div>
                            </div>
                        </div>
                    </td>
                    <td style="vertical-align: middle;">
                        <span class="label ${badgeClass}" style="font-size: 11px; display: inline-block; padding: 3px 8px;">
                            ${fileTypeLabel}
                        </span>
                    </td>
                    <td style="vertical-align: middle; font-family: monospace; font-size: 12px;">${fileSize}</td>
                    <td style="vertical-align: middle; font-size: 12px;">${uploadDate}</td>
                    <td style="vertical-align: middle; text-align: center;">
                        <div class="btn-group btn-group-xs">
                            <button class="btn btn-info preview-file" data-file-id="${file.id}" title="Preview">
                                <span class="glyphicon glyphicon-eye-open"></span>
                            </button>
                            <button class="btn btn-primary insert-file" data-file-id="${file.id}" title="Insert into editor">
                                <span class="glyphicon glyphicon-link"></span>
                            </button>
                        </div>
                    </td>
                `;

                // Add checkbox change handler
                const checkbox = row.querySelector('.file-select-checkbox');
                if (checkbox) {
                    checkbox.addEventListener('change', function(e) {
                        e.stopPropagation();
                        updateSelectedFilesCount();
                    });
                }

                // Add row click handler (for selection)
                row.addEventListener('click', function(e) {
                    // Don't select if clicking on action buttons or checkbox
                    if (e.target.tagName === 'BUTTON' || e.target.closest('button') ||
                        e.target.tagName === 'INPUT' || e.target.closest('input')) {
                        return;
                    }

                    // Toggle checkbox
                    const checkbox = this.querySelector('.file-select-checkbox');
                    if (checkbox) {
                        checkbox.checked = !checkbox.checked;
                        checkbox.dispatchEvent(new Event('change'));
                    }
                });

                // Add action button handlers
                row.querySelector('.preview-file')?.addEventListener('click', function(e) {
                    e.stopPropagation();
                    previewFile(file.id, file.name, file.download_url);
                });

                row.querySelector('.insert-file')?.addEventListener('click', function(e) {
                    e.stopPropagation();
                    console.log('Insert button clicked for file:', {
                        fileId: file.id,
                        fileName: file.name,
                        fileType: file.type,
                        hasOriginalDocument: !!file.original_document,
                        rowHasOriginalDocument: !!row.dataset.originalDocument
                    });

                    let originalDoc = file.original_document;
                    // Fallback to row dataset if file.original_document is undefined
                    if (!originalDoc && row.dataset.originalDocument) {
                        try {
                            originalDoc = JSON.parse(row.dataset.originalDocument);
                            console.log('Retrieved originalDocument from row.dataset');
                        } catch (e) {
                            console.warn('Failed to parse originalDocument from row.dataset:', e);
                        }
                    }

                    insertFileBotDocument(file.id, file.name, file.type, file.download_url, originalDoc);
                });

                fileListBody.appendChild(row);
            });

            // Initialize selected files count
            updateSelectedFilesCount();
        }

        // Update selected files count
        function updateSelectedFilesCount() {
            const selectedCount = document.querySelectorAll('.file-select-checkbox:checked').length;
            const selectAllCheckbox = document.getElementById('select-all-checkbox');

            // Update select all checkbox state
            if (selectAllCheckbox) {
                const totalCount = document.querySelectorAll('.file-select-checkbox').length;
                selectAllCheckbox.checked = totalCount > 0 && selectedCount === totalCount;
                selectAllCheckbox.indeterminate = selectedCount > 0 && selectedCount < totalCount;
            }

            // Update UI for selected files
            document.querySelectorAll('#file-list-body tr').forEach(row => {
                const checkbox = row.querySelector('.file-select-checkbox');
                if (checkbox && checkbox.checked) {
                    row.style.backgroundColor = '#f0f9ff';
                    row.classList.add('selected');
                } else {
                    row.style.backgroundColor = '';
                    row.classList.remove('selected');
                }
            });
        }

        // Upload files
        // Helper function to publish a document and set its public URL metadata
        async function getUniqueFilename(originalFilename) {
            /**
             * 生成唯一的文件名,避免冲突
             * 规则:
             * 1. 首先尝试原始文件名(如 th.jpg)
             * 2. 如果已存在,尝试 th-1.jpg, th-2.jpg 等
             * 3. 最多尝试20次
             */
            console.log('Generating unique filename for:', originalFilename);

            // 解析文件名和扩展名
            const dotIndex = originalFilename.lastIndexOf('.');
            let name = originalFilename;
            let extension = '';
            if (dotIndex > -1) {
                name = originalFilename.substring(0, dotIndex);
                extension = originalFilename.substring(dotIndex); // 包含点
            }

            // 首先尝试原始文件名
            let candidate = originalFilename;
            let attempt = 0;
            const maxAttempts = 20;

            while (attempt < maxAttempts) {
                console.log('Checking if filename is available:', candidate);

                try {
                    // 通过FileBot API检查文件名是否已存在
                    // 使用by-path端点,如果返回404表示文件名可用
                    const response = await fetch(URL_CONFIG.filebot.documentByPath(candidate), {
                        method: 'GET',
                        headers: {
                            'Authorization': `Bearer ${FILEBOT_JWT_TOKEN}`
                        }
                    });

                    if (response.status === 404) {
                        // 文件名可用!
                        console.log('Filename available:', candidate);
                        return candidate;
                    } else if (response.status === 200) {
                        // 文件名已被占用,尝试下一个
                        console.log('Filename already taken:', candidate);
                        attempt++;
                        if (extension) {
                            candidate = `${name}-${attempt}${extension}`;
                        } else {
                            candidate = `${name}-${attempt}`;
                        }
                    } else {
                        // 其他错误,保守起见认为文件名可用
                        console.warn('Unexpected status checking filename:', response.status, 'Assuming available:', candidate);
                        return candidate;
                    }
                } catch (error) {
                    console.warn('Error checking filename availability:', error, 'Assuming available:', candidate);
                    return candidate;
                }
            }

            // 如果尝试了maxAttempts次仍未找到,返回带时间戳的唯一文件名
            const timestamp = Date.now().toString().slice(-6);
            if (extension) {
                const fallback = `${name}-${timestamp}${extension}`;
                console.log('Max attempts reached, using timestamped filename:', fallback);
                return fallback;
            } else {
                const fallback = `${name}-${timestamp}`;
                console.log('Max attempts reached, using timestamped filename:', fallback);
                return fallback;
            }
        }

        function generateFallbackFilename(originalFilename) {
            console.log('Generating fallback filename for:', originalFilename);
            // 简单回退:原始文件名 + 随机数 + 时间戳
            const dotIndex = originalFilename.lastIndexOf('.');
            let name = originalFilename;
            let extension = '';
            if (dotIndex > -1) {
                name = originalFilename.substring(0, dotIndex);
                extension = originalFilename.substring(dotIndex);
            }
            const randomSuffix = Math.floor(Math.random() * 10000).toString().padStart(4, '0');
            const timestamp = Date.now().toString().slice(-6);
            const fallback = extension ? `${name}-${randomSuffix}-${timestamp}${extension}` : `${name}-${randomSuffix}-${timestamp}`;
            console.log('Fallback filename generated:', fallback);
            return fallback;
        }

        async function publishDocumentAndSetPublicUrl(documentId, storedFilename, originalFilename) {
            console.log('Publishing document and setting public URL:', { documentId, storedFilename, originalFilename });

            try {
                // 确定要使用的文件名
                let filenameToUse;
                if (originalFilename) {
                    try {
                        console.log('Calling getUniqueFilename with:', originalFilename);
                        // 使用原始文件名,生成唯一版本
                        filenameToUse = await getUniqueFilename(originalFilename);
                        console.log('getUniqueFilename returned:', filenameToUse);

                        // 如果getUniqueFilename返回假值或空字符串,使用回退
                        if (!filenameToUse || filenameToUse.trim() === '') {
                            console.warn('getUniqueFilename returned empty value, using fallback');
                            filenameToUse = generateFallbackFilename(originalFilename);
                        }
                    } catch (error) {
                        console.error('Error in getUniqueFilename, using fallback:', error);
                        console.error('Error details:', error.message, error.stack);
                        filenameToUse = generateFallbackFilename(originalFilename);
                    }
                } else {
                    // 向后兼容:使用存储的文件名(UUID)
                    filenameToUse = storedFilename;
                    console.log('Using stored filename (UUID):', filenameToUse);
                }
                console.log('Final filenameToUse:', filenameToUse);

                // 1. Update publish_status to PUBLISHED
                const updateUrl = URL_CONFIG.filebot.documentById(documentId);
                const requestBody = {
                    publish_status: 'PUBLISHED',
                    document_metadata: {
                        url: `/${filenameToUse}`
                    }
                };
                console.log('Publishing document:', {
                    url: updateUrl,
                    documentId: documentId,
                    body: requestBody
                });

                const updateResponse = await fetch(updateUrl, {
                    method: 'PUT',
                    headers: {
                        'Authorization': `Bearer ${FILEBOT_JWT_TOKEN}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestBody)
                });

                if (!updateResponse.ok) {
                    console.error('Publish request failed:', {
                        status: updateResponse.status,
                        statusText: updateResponse.statusText,
                        url: updateUrl
                    });
                    const errorText = await updateResponse.text();
                    console.error('Error response body:', errorText);
                    throw new Error(`HTTP ${updateResponse.status}: ${errorText}`);
                }

                const updatedDoc = await updateResponse.json();
                console.log('Document published successfully:', {
                    id: updatedDoc.id,
                    publish_status: updatedDoc.publish_status,
                    document_metadata: updatedDoc.document_metadata
                });

                return updatedDoc;
            } catch (error) {
                console.error('Error publishing document:', error);
                // Don't throw - we can continue even if publishing fails
                return null;
            }
        }

        /**
         * 从blob URL上传图片到FileBot
         * @param {string} blobUrl - 图片的blob URL
         * @param {string} filename - 建议的文件名
         * @returns {Promise<string>} - 返回图片的公共URL
         */
        async function uploadImageFromBlob(blobUrl, filename) {
            console.log('Uploading image from blob:', { blobUrl, filename });

            try {
                // 1. 从blob URL获取图片数据
                const response = await fetch(blobUrl);
                if (!response.ok) {
                    throw new Error(`Failed to fetch blob: ${response.status} ${response.statusText}`);
                }

                const blob = await response.blob();
                console.log('Fetched blob:', { size: blob.size, type: blob.type });

                // 2. 创建FormData
                const formData = new FormData();
                formData.append('file', blob, filename || 'image.jpg');

                // 3. 上传到FileBot
                // Add folder_path if available
                const folderPath = window.currentFileBotFolder;
                if (folderPath) {
                    console.log('Uploading image to folder path:', folderPath);
                    formData.append('folder_path', folderPath);
                }

                const uploadResponse = await fetch(URL_CONFIG.filebot.upload, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${FILEBOT_JWT_TOKEN}`
                    },
                    body: formData
                });

                if (!uploadResponse.ok) {
                    const errorText = await uploadResponse.text();
                    throw new Error(`FileBot upload failed: ${uploadResponse.status}: ${errorText}`);
                }

                const uploadData = await uploadResponse.json();
                console.log('Image uploaded to FileBot:', uploadData);

                // 4. 自动发布图片
                const finalFilename = filename || 'image.jpg';
                const publishedDoc = await publishDocumentAndSetPublicUrl(
                    uploadData.id,
                    uploadData.stored_filename,
                    finalFilename
                );

                if (!publishedDoc) {
                    console.warn('Image uploaded but publishing failed, using uploaded document');
                    // 即使发布失败,我们仍然可以使用上传的文档
                    // 但需要获取文档的公共URL
                    const publicUrl = getPublicUrlFromDocument(uploadData);
                    return publicUrl;
                }

                // 5. 返回公共URL
                const publicUrl = getPublicUrlFromDocument(publishedDoc);
                console.log('Image public URL:', publicUrl);
                return publicUrl;

            } catch (error) {
                console.error('Error uploading image from blob:', error);
                throw error; // 重新抛出错误,让调用者处理
            }
        }

        /**
         * 处理HTML内容中的图片,上传blob/localhost图片到FileBot
         * @param {string} htmlContent - HTML内容
         * @returns {Promise<string>} - 处理后的HTML内容,图片src已替换为公共URL
         */
        async function processImagesInHtmlContent(htmlContent) {
            console.log('Processing images in HTML content...');

            // 如果内容为空,直接返回
            if (!htmlContent || !htmlContent.includes('<img')) {
                return htmlContent;
            }

            // 创建临时DOM元素来解析HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = htmlContent;

            // 查找所有img标签
            const imgElements = tempDiv.querySelectorAll('img');
            console.log(`Found ${imgElements.length} image(s) in content`);

            // 需要上传的图片列表
            const uploadPromises = [];
            const imageReplacements = [];

            for (let i = 0; i < imgElements.length; i++) {
                const img = imgElements[i];
                const src = img.getAttribute('src');

                // 检查是否需要上传(blob: 或 localhost URL)
                const needsUpload = src && (
                    src.startsWith('blob:') ||
                    src.includes('localhost:') ||
                    src.startsWith('data:image/') // also handle base64 images
                );

                if (!needsUpload) {
                    console.log(`Skipping image ${i}: src="${src}" (not a local/blob image)`);
                    continue;
                }

                console.log(`Processing image ${i}: src="${src}"`);

                // 确定文件名
                let filename = img.getAttribute('title') ||
                               img.getAttribute('alt') ||
                               `image-${Date.now()}-${i}`;

                // 确保文件名有扩展名
                if (!filename.includes('.')) {
                    // 尝试从blob类型推断扩展名
                    const mimeType = img.getAttribute('type') || '';
                    let extension = '.jpg';
                    if (mimeType.includes('png')) extension = '.png';
                    else if (mimeType.includes('gif')) extension = '.gif';
                    else if (mimeType.includes('webp')) extension = '.webp';
                    else if (mimeType.includes('svg')) extension = '.svg';
                    filename += extension;
                }

                // 创建上传任务
                const uploadPromise = uploadImageFromBlob(src, filename)
                    .then(publicUrl => {
                        console.log(`Image ${i} uploaded, public URL: ${publicUrl}`);
                        return { index: i, oldSrc: src, newSrc: publicUrl, img: img };
                    })
                    .catch(error => {
                        console.error(`Failed to upload image ${i}:`, error);
                        // 上传失败,保留原src
                        return { index: i, oldSrc: src, newSrc: src, img: img, error: true };
                    });

                uploadPromises.push(uploadPromise);
                imageReplacements.push({ img, oldSrc: src });
            }

            // 如果没有需要上传的图片,直接返回原内容
            if (uploadPromises.length === 0) {
                console.log('No images need uploading');
                return htmlContent;
            }

            // 等待所有图片上传完成
            console.log(`Waiting for ${uploadPromises.length} image(s) to upload...`);
            const results = await Promise.all(uploadPromises);

            // 替换图片src
            let processedHtml = htmlContent;
            for (const result of results) {
                if (!result.error && result.newSrc !== result.oldSrc) {
                    // 替换src
                    processedHtml = processedHtml.replace(
                        new RegExp(`src=["']${escapeRegExp(result.oldSrc)}["']`, 'g'),
                        `src="${result.newSrc}"`
                    );
                    console.log(`Replaced image src: ${result.oldSrc} -> ${result.newSrc}`);
                }
            }

            // 辅助函数:转义正则表达式特殊字符
            function escapeRegExp(string) {
                return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            }

            console.log('Image processing complete');
            return processedHtml;
        }

        /** Show a floating toast notification for upload status */
        function showUploadToast(message, type) {
            // Remove existing toast if any
            const existing = document.getElementById('upload-toast');
            if (existing) existing.remove();

            const toast = document.createElement('div');
            toast.id = 'upload-toast';
            toast.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 99999;
                padding: 14px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                color: #fff;
                background: ${type === 'success' ? '#28a745' : '#d9534f'};
                box-shadow: 0 4px 12px rgba(0,0,0,0.25);
                animation: fadeInDown 0.3s ease;
                max-width: 400px;
                word-wrap: break-word;
            `;
            toast.textContent = message;
            document.body.appendChild(toast);

            // Auto-dismiss after 4s
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.3s ease';
                setTimeout(() => toast.remove(), 400);
            }, 4000);
        }

        // Add animation keyframes if not already present
        if (!document.getElementById('upload-toast-style')) {
            const style = document.createElement('style');
            style.id = 'upload-toast-style';
            style.textContent = `
                @keyframes fadeInDown {
                    from { opacity: 0; transform: translateY(-20px); }
                    to   { opacity: 1; transform: translateY(0); }
                }
            `;
            document.head.appendChild(style);
        }

        async function uploadFiles(files) {
            const uploadProgress = document.getElementById('upload-progress');
            const progressBar = uploadProgress?.querySelector('.progress-bar');
            const uploadStatus = document.getElementById('upload-status');

            // Sidebar progress elements
            const sidebarUploadProgress = document.getElementById('sidebar-upload-progress');
            const sidebarProgressBar = document.getElementById('sidebar-upload-progress-bar');
            const sidebarUploadStatus = document.getElementById('sidebar-upload-status');

            // Resource sidebar upload info (under upload button)
            const resourceUploadInfo = document.getElementById('resource-upload-info');
            const resourceUploadProgress = document.getElementById('resource-upload-progress-bar');
            const resourceUploadMsg = document.getElementById('resource-upload-msg');

            // Show progress in all locations
            if (uploadProgress) uploadProgress.style.display = 'block';
            if (sidebarUploadProgress) sidebarUploadProgress.style.display = 'block';
            if (resourceUploadInfo) resourceUploadInfo.classList.remove('hidden');

            if (progressBar) {
                progressBar.style.width = '0%';
                progressBar.textContent = '0%';
            }
            if (sidebarProgressBar) {
                sidebarProgressBar.style.width = '0%';
            }
            if (resourceUploadProgress) {
                resourceUploadProgress.style.width = '0%';
            }

            if (uploadStatus) uploadStatus.textContent = 'Preparing upload to FileBot...';
            if (sidebarUploadStatus) sidebarUploadStatus.textContent = 'Preparing upload...';
            if (resourceUploadMsg) resourceUploadMsg.textContent = '⌛ Preparing...';
            if (resourceUploadMsg) resourceUploadMsg.className = 'resource-upload-msg';

            // Use folder path directly - FileBot will handle folder creation if needed
            const folderPath = window.currentFileBotFolder;
            if (folderPath) {
                console.log('Uploading to folder path:', folderPath);
            } else {
                console.log('No target folder configured, uploading to root');
            }

            // Upload each file to FileBot
            for (let index = 0; index < files.length; index++) {
                const file = files[index];
                const formData = new FormData();
                formData.append('file', file);

                // Add metadata (optional)
                formData.append('title', file.name.split('.')[0]); // Use filename without extension as title

                // Add folder_path if available - FileBot will create folder if needed
                // Note: FileBot expects the path to include the app slug as first segment
                // (e.g. '/boarding/canadasite/content/dam/...'), but window.currentFileBotFolder
                // stores the path WITHOUT the app slug (e.g. '/canadasite/content/dam/...')
                if (folderPath) {
                    // Prepend '/boarding' app slug if not already present
                    const uploadPath = folderPath.startsWith('/boarding') ? folderPath : '/boarding' + folderPath;
                    console.log('Uploading to folder path:', uploadPath);
                    formData.append('folder_path', uploadPath);
                }

                if (uploadStatus) {
                    uploadStatus.textContent = `Uploading to FileBot: ${file.name} (${index + 1}/${files.length})`;
                }
                if (sidebarUploadStatus) {
                    sidebarUploadStatus.textContent = `Uploading: ${file.name} (${index + 1}/${files.length})`;
                }

                try {
                    const response = await fetch(URL_CONFIG.filebot.upload, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${FILEBOT_JWT_TOKEN}`
                        },
                        body: formData
                    });

                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(`HTTP ${response.status}: ${errorText}`);
                    }

                    const data = await response.json();
                    console.log('File uploaded to FileBot:', data);

                    // Auto-publish images and set public URL metadata
                    // Check if this is an image file
                    const isImage = file.type.startsWith('image/') || /\.(jpg|jpeg|png|gif|bmp|webp|svg)$/i.test(file.name);
                    if (isImage && data.id && data.stored_filename) {
                        console.log('Auto-publishing image document:', data.id, data.stored_filename);
                        // Publish in background, don't wait for completion
                        publishDocumentAndSetPublicUrl(data.id, data.stored_filename, file.name)
                            .then(publishedDoc => {
                                if (publishedDoc) {
                                    console.log('Image auto-published successfully:', publishedDoc.id);
                                } else {
                                    console.log('Image auto-publish failed or skipped');
                                }
                            })
                            .catch(err => console.error('Background auto-publish error:', err));
                    }

                    // Update progress
                    const progress = Math.round(((index + 1) / files.length) * 100);
                    if (progressBar) {
                        progressBar.style.width = `${progress}%`;
                        progressBar.textContent = `${progress}%`;
                    }
                    if (sidebarProgressBar) {
                        sidebarProgressBar.style.width = `${progress}%`;
                    }

                    if (index === files.length - 1) {
                        // All files uploaded
                        showUploadToast('✅ Upload complete', 'success');

                        if (uploadStatus) {
                            uploadStatus.textContent = 'Upload complete! Files saved to FileBot.';
                            uploadStatus.style.color = '';
                        }
                        if (sidebarUploadStatus) {
                            sidebarUploadStatus.textContent = 'Upload complete! Files saved to FileBot.';
                        }
                        if (resourceUploadMsg) {
                            const count = files.length;
                            resourceUploadMsg.textContent = `✅ ${count} file${count > 1 ? 's' : ''} uploaded successfully`;
                            resourceUploadMsg.className = 'resource-upload-msg success';
                        }

                        // Hide progress after delay
                        setTimeout(() => {
                            if (uploadProgress) uploadProgress.style.display = 'none';
                            if (sidebarUploadProgress) sidebarUploadProgress.style.display = 'none';
                        }, 2000);

                        // Reload the resource sidebar for current mode
                        if (typeof window.refreshResourceSidebar === 'function') {
                            const resourceTypeSelect = document.getElementById('resource-type-select');
                            const pathInput = document.getElementById('resource-path-input');
                            const titleInput = document.getElementById('resource-search-input');
                            const mode = resourceTypeSelect ? resourceTypeSelect.value : 'images';
                            const pathVal = pathInput ? pathInput.value.trim() : '';
                            const titleVal = titleInput ? titleInput.value.trim() : '';
                            window.refreshResourceSidebar(mode, pathVal, titleVal);
                        }
                    }
                } catch (error) {
                    console.error('FileBot upload error:', error);
                    showUploadToast('❌ ' + error.message.substring(0, 120), 'error');
                    if (uploadStatus) {
                        uploadStatus.textContent = `Error: ${file.name} - ${error.message}`;
                        uploadStatus.style.color = '#d9534f';
                    }
                    if (sidebarUploadStatus) {
                        sidebarUploadStatus.textContent = `Error: ${file.name} - ${error.message}`;
                        sidebarUploadStatus.style.color = '#d9534f';
                    }
                    if (resourceUploadMsg) {
                        resourceUploadMsg.textContent = `❌ ${file.name} - ${error.message.substring(0, 80)}`;
                        resourceUploadMsg.className = 'resource-upload-msg error';
                    }

                    // If this is the last file, keep progress bar visible to show error
                    if (index === files.length - 1) {
                        setTimeout(() => {
                            if (uploadProgress) uploadProgress.style.display = 'none';
                            if (sidebarUploadProgress) sidebarUploadProgress.style.display = 'none';
                        }, 5000);
                    }

                    // Break the loop on error
                    break;
                }
            }
        }

        // Insert file link into editor (FileBot version)
        function insertFileLink(fileId, fileName, fileType, originalDocument) {
            // This function is kept for backward compatibility
            // It now delegates to the FileBot document insertion function
            console.log('insertFileLink called, redirecting to insertFileBotDocument');
            const downloadUrl = URL_CONFIG.filebot.documentDownload(fileId);
            insertFileBotDocument(fileId, fileName, fileType, downloadUrl, originalDocument);
        }

        // Preview file from FileBot
        function previewFile(fileId, fileName, downloadUrl) {
            console.log('Previewing file:', fileId, fileName);

            let fileUrl = downloadUrl;

            if (!fileUrl) {
                // Construct proxy URL instead of API URL
                fileUrl = `/content/dam/${fileId}`;
                console.log('Constructed proxy URL for preview:', fileUrl);
            } else if (fileUrl.includes('/api/v1/documents/')) {
                // Convert API URL to proxy URL if possible
                console.log('Converting API URL to proxy URL:', fileUrl);
                // Try to extract stored_filename from download URL pattern
                // Pattern: /api/v1/documents/{id}/download or /api/v1/documents/by-path/{path}
                if (fileUrl.includes('/download')) {
                    // Extract document ID from download URL
                    const match = fileUrl.match(/\/documents\/([^\/]+)\/download/);
                    if (match && match[1]) {
                        fileUrl = `/content/dam/${match[1]}`;
                        console.log('Converted download URL to proxy URL:', fileUrl);
                    }
                } else if (fileUrl.includes('/by-path/')) {
                    // Extract path from by-path URL
                    const match = fileUrl.match(/\/by-path\/(.+)/);
                    if (match && match[1]) {
                        const path = decodeURIComponent(match[1]);
                        fileUrl = `/content/dam/${path}`;
                        console.log('Converted by-path URL to proxy URL:', fileUrl);
                    }
                }
            }

            // Check if it's an image
            const isImage = fileName && /\.(jpg|jpeg|png|gif|bmp|webp|svg)$/i.test(fileName);

            if (isImage) {
                // Use WET-BOEW lightbox for image preview
                if (typeof wb === 'object' && wb.doc && typeof wb.doc.trigger === 'function') {
                    console.log('Using WET-BOEW lightbox to preview image');
                    wb.doc.trigger('open.wb-lbx', [
                        {
                            src: fileUrl,
                            type: 'image',
                            title: escapeHtml(fileName),
                            isModal: true
                        }
                    ]);
                } else {
                    // Fallback: open image in new tab
                    console.log('WET-BOEW not available, opening image in new tab');
                    window.open(fileUrl, '_blank');
                }
            } else {
                // For non-image files, open in new tab
                console.log('Non-image file, opening in new tab');
                window.open(fileUrl, '_blank');
            }
        }



        // Helper functions
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function getFileIcon(fileType, fileName) {
            // Safe handling for undefined/null values
            fileType = fileType || '';
            fileName = fileName || '';

            if (fileType.startsWith('image/')) {
                return 'glyphicon glyphicon-picture';
            } else if (fileType === 'application/pdf') {
                return 'glyphicon glyphicon-file';
            } else if (fileType.includes('word') || fileName.match(/\.docx?$/i)) {
                return 'glyphicon glyphicon-file';
            } else if (fileType.includes('excel') || fileName.match(/\.xlsx?$/i)) {
                return 'glyphicon glyphicon-list-alt';
            } else if (fileType.includes('powerpoint') || fileName.match(/\.pptx?$/i)) {
                return 'glyphicon glyphicon-blackboard';
            } else {
                return 'glyphicon glyphicon-file';
            }
        }

        function getFileTypeLabel(fileType) {
            // Safe handling for undefined/null values
            fileType = fileType || '';

            if (fileType.startsWith('image/')) {
                return 'Image';
            } else if (fileType === 'application/pdf') {
                return 'PDF';
            } else if (fileType.includes('word')) {
                return 'Word';
            } else if (fileType.includes('excel')) {
                return 'Excel';
            } else if (fileType.includes('powerpoint')) {
                return 'PowerPoint';
            } else {
                return 'File';
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Insert FileBot document into editor
        function insertFileBotDocument(documentId, documentName, documentType, downloadUrl, originalDocument) {
            const editor = tinymce.activeEditor;
            if (!editor) {
                console.error('No active TinyMCE editor found');
                return;
            }

            console.log('Inserting FileBot document:', { documentId, documentName, documentType, downloadUrl, originalDocument });

            // If downloadUrl not provided, construct it
            console.log('Before constructing downloadUrl:', { downloadUrl, documentId });
            if (!downloadUrl) {
                downloadUrl = URL_CONFIG.filebot.documentDownload(documentId);
                console.log('Constructed downloadUrl:', downloadUrl);
            }

            // Generate appropriate HTML based on file type
            let html = '';
            const fileName = documentName || 'Document';

            // Check if it's an image by file extension or type
            // Handle various documentType formats: 'image/jpeg', 'jpg', 'jpeg', etc.
            const normalizedDocumentType = documentType ? documentType.toLowerCase() : '';
            const isImage = normalizedDocumentType.startsWith('image/') ||
                           ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(normalizedDocumentType) ||
                           documentName && /\.(jpg|jpeg|png|gif|bmp|webp|svg)$/i.test(documentName);

            console.log('File type analysis:', {
                documentName,
                documentType,
                isImage,
                hasOriginalDocument: !!originalDocument,
                hasDocumentMetadata: originalDocument && !!originalDocument.document_metadata,
                documentMetadata: originalDocument ? originalDocument.document_metadata : null
            });



            if (isImage) {
                // Image file - insert img tag
                // Try to get public URL first
                let imageUrl = getPublicUrlFromDocument(originalDocument);

                if (!imageUrl) {
                    // Fallback: try to construct /content/dam/ URL from available data
                    console.log('No public URL from getPublicUrlFromDocument, trying to construct proxy URL');
                    if (originalDocument && originalDocument.stored_filename) {
                        imageUrl = `/content/dam/${originalDocument.stored_filename}`;
                        console.log('Constructed proxy URL from stored_filename:', imageUrl);
                    } else if (documentId) {
                        imageUrl = `/content/dam/${documentId}`;
                        console.log('Constructed proxy URL from document ID:', imageUrl);
                    } else {
                        // Last resort: use download URL (API endpoint)
                        imageUrl = downloadUrl;
                        console.log('Using download URL as fallback:', imageUrl);
                    }
                } else {
                    console.log('Using public URL for image:', imageUrl);
                }

                html = `<img src="${imageUrl}" alt="${escapeHtml(fileName)}" class="img-responsive">`;
                console.log('Generated image HTML:', html);
            } else {
                // Other file - insert download button (per user request)
                // Try to get proxy URL for document download
                let fileUrl = getPublicUrlFromDocument(originalDocument);

                if (!fileUrl) {
                    // Fallback: construct /content/dam/ URL
                    console.log('No public URL for non-image file, constructing proxy URL');
                    if (originalDocument && originalDocument.stored_filename) {
                        fileUrl = `/content/dam/${originalDocument.stored_filename}`;
                    } else if (documentId) {
                        fileUrl = `/content/dam/${documentId}`;
                    } else {
                        fileUrl = downloadUrl; // Use original download URL as last resort
                    }
                }

                // Add download parameter to suggest browser to download
                if (fileUrl && !fileUrl.includes('?')) {
                    fileUrl += '?download=true';
                }

                html = `<a href="${fileUrl}" class="btn btn-default" target="_blank">
                    <span class="glyphicon glyphicon-download-alt"></span>
                    Download ${escapeHtml(fileName)}
                </a>`;
                console.log('Generated download link HTML:', html);
            }

            // Insert into editor
            editor.insertContent(html);
            console.log('FileBot document inserted successfully');
        }

        // Show FileBot document selector
        function showFileBotDocumentSelector() {
            console.log('Showing FileBot document selector');

            // For now, show a simple alert with instructions
            // In a future version, this could fetch documents from FileBot API
            // and display them in a modal for selection

            alert('FileBot document insertion functionality is being implemented.\n\n' +
                  'Current options:\n' +
                  '1. Use the FileBot panel (left side) to browse documents\n' +
                  '2. Use the "FileBot File Manager" button for file uploads\n' +
                  '3. Component insertion has been deferred (per your request)\n\n' +
                  'For immediate document insertion, you can:\n' +
                  '- Use the file manager (top button) to upload and insert files\n' +
                  '- Or manually add file links in the editor');

            // TODO: Implement proper FileBot document selector modal
            // fetchFileBotDocuments().then(docs => showDocumentSelectionModal(docs));
        }

        // ========== END FILE MANAGER FUNCTIONS ==========

        // ========== PAGES SIDEBAR FUNCTIONS ==========

        let allPagesForSidebar = [];

        // Load pages for sidebar, focusing on second-level pages under /en/(department page path)
        // Get the level of a path (number of segments after removing empty ones)
        function getPathLevel(path) {
            if (!path || path === '/') return 0;
            const cleanPath = path.replace(/^\/+|\/+$/g, '');
            if (!cleanPath) return 0;
            return cleanPath.split('/').length;
        }

        function loadPagesForSidebar(currentPagePath = null) {
            console.log('Loading pages for sidebar, currentPagePath:', currentPagePath);

            const sidebarEl = document.getElementById('filebot-pages-sidebar');
            if (!sidebarEl) {
                console.warn('Pages sidebar element not found');
                return;
            }

            // Show loading message
            sidebarEl.innerHTML = '<li class="filebot-document-item-sidebar"><em>Loading pages...</em></li>';

            // Determine what to load based on current page path level
            let apiUrl;
            let filterLogic = 'all';

            if (currentPagePath) {
                const level = getPathLevel(currentPagePath);
                console.log(`Current page path level: ${level} for path: ${currentPagePath}`);

                if (level === 3) {
                    // Third level page selected (e.g., /en/service-canada)
                    // Load all pages under this department path
                    apiUrl = `/api/v1/pages?path=${encodeURIComponent(currentPagePath)}&limit=1000`;
                    filterLogic = 'third-level-department';
                    console.log(`Loading department pages under: ${currentPagePath}`);
                } else if (level === 2) {
                    // Second level page selected (e.g., /en)
                    // Show no pages at language level (user requirement)
                    console.log('Language level page selected, showing no pages');
                    sidebarEl.innerHTML = '<li class="filebot-document-item-sidebar"><em>No pages available at language level. Select a department page to see pages.</em></li>';
                    allPagesForSidebar = [];
                    return;
                } else if (level === 1 || level === 0) {
                    // Root or first level, show no pages or minimal
                    console.log('Root or first level page, showing no pages');
                    sidebarEl.innerHTML = '<li class="filebot-document-item-sidebar"><em>Select a department page to see pages.</em></li>';
                    allPagesForSidebar = [];
                    return;
                } else {
                    // Level 4+ (subpage within department), load pages under the department
                    // Extract department path (first three segments)
                    const cleanPath = currentPagePath.replace(/^\/+|\/+$/g, '');
                    const pathParts = cleanPath.split('/');
                    if (pathParts.length >= 2) {
                        const departmentPath = '/' + pathParts.slice(0, 2).join('/'); // /en/service-canada
                        apiUrl = `/api/v1/pages?path=${encodeURIComponent(departmentPath)}&limit=1000`;
                        filterLogic = 'department-subpage';
                        console.log(`Loading department pages for subpage: ${departmentPath}`);
                    } else {
                        // Fallback: load all pages
                        apiUrl = '/api/v1/pages/?limit=100';
                        filterLogic = 'fallback-all';
                    }
                }
            } else {
                // No current page selected (initial load)
                // Show no pages initially (user requirement)
                console.log('No page selected, showing no pages initially');
                sidebarEl.innerHTML = '<li class="filebot-document-item-sidebar"><em>Select a department page to see pages.</em></li>';
                allPagesForSidebar = [];
                return;
            }

            // Fetch pages from API
            fetch(apiUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(pages => {
                    console.log(`Loaded ${pages.length} pages from API with filter: ${filterLogic}`);

                    let filteredPages = pages;

                    // Apply additional filtering based on logic
                    if (filterLogic === 'third-level-department' || filterLogic === 'department-subpage') {
                        // For department pages, we already get filtered results from API
                        // Remove the department page itself from the list (if present)
                        filteredPages = pages.filter(page => page.path !== currentPagePath);
                        console.log(`After removing current page, ${filteredPages.length} pages remaining`);
                    }
                    // For other cases, no additional filtering needed

                    // Store filtered pages (remove content field for performance)
                    allPagesForSidebar = filteredPages.map(page => {
                        const { content, ...pageWithoutContent } = page;
                        return pageWithoutContent;
                    });

                    // Render the pages in sidebar
                    renderSidebarPages();
                })
                .catch(error => {
                    console.error('Error loading pages for sidebar:', error);
                    sidebarEl.innerHTML = '<li class="filebot-document-item-sidebar"><em style="color: #d32f2f;">Error loading pages</em></li>';
                });
        }

        // Render pages in the sidebar
        function renderSidebarPages() {
            const sidebarEl = document.getElementById('filebot-pages-sidebar');
            if (!sidebarEl) {
                console.warn('Pages sidebar element not found');
                return;
            }

            if (!allPagesForSidebar || allPagesForSidebar.length === 0) {
                sidebarEl.innerHTML = '<li class="filebot-document-item-sidebar"><em>No pages found</em></li>';
                return;
            }

            // Clear loading message
            sidebarEl.innerHTML = '';

            // Group pages by department (parent or first level under /en/)
            const pagesByDepartment = {};
            allPagesForSidebar.forEach(page => {
                let department = 'General';

                // Try to determine department from path
                if (page.path) {
                    const cleanPath = page.path.replace(/^\/+|\/+$/g, '');
                    const pathParts = cleanPath.split('/');
                    if (pathParts.length >= 2 && pathParts[0] === 'en') {
                        department = pathParts[1]; // First part after /en/
                        // Capitalize first letter
                        department = department.charAt(0).toUpperCase() + department.slice(1);
                    }
                }

                // Fallback to parent title
                if (!department || department === 'General') {
                    if (page.parent_path && page.parent_path !== 'root') {
                        department = `Parent: ${page.parent_path}`;
                    }
                }

                if (!pagesByDepartment[department]) {
                    pagesByDepartment[department] = [];
                }
                pagesByDepartment[department].push(page);
            });

            // Render departments and pages
            Object.keys(pagesByDepartment).sort().forEach(department => {
                const departmentPages = pagesByDepartment[department];

                // Add department header
                const departmentLi = document.createElement('li');
                departmentLi.className = 'filebot-pages-department';
                departmentLi.innerHTML = `<strong>${department}</strong>`;
                sidebarEl.appendChild(departmentLi);

                // Add pages in this department
                departmentPages.forEach(page => {
                    const li = document.createElement('li');
                    li.className = 'filebot-pages-item';
                    li.title = page.description || page.title || 'No description';
                    li.dataset.pageId = page.id;
                    li.dataset.pagePath = page.path || '';
                    li.dataset.pageTitle = page.title || 'Untitled';

                    // Create page name with icon
                    const pageIcon = '📄';
                    const pageName = page.title || page.id || 'Untitled';

                    li.innerHTML = `
                        <div class="filebot-pages-item-content">
                            <span class="filebot-pages-icon">${pageIcon}</span>
                            <span class="filebot-pages-name">${escapeHtml(pageName)}</span>
                            <button class="filebot-pages-insert" title="Insert link to this page">+</button>
                        </div>
                        <div class="filebot-pages-path">${escapeHtml(page.path || '')}</div>
                    `;

                    // Add click event for the insert button
                    const insertBtn = li.querySelector('.filebot-pages-insert');
                    insertBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        insertPageLink(page);
                    });

                    // Also make the whole item clickable (for navigation to edit page)
                    li.addEventListener('click', (e) => {
                        if (e.target !== insertBtn) {
                            // Navigate to edit this page
                            const pagePath = page.path || page.id;
                            if (pagePath) {
                                // Determine current editor page base URL
                                let baseUrl = '/editor.html';
                                if (window.location.pathname.includes('/static/editor.html')) {
                                    baseUrl = '/static/editor.html';
                                }

                                // Use query parameter format: editor.html?path={page path}
                                const editUrl = `${baseUrl}?path=${encodeURIComponent(pagePath)}`;
                                console.log(`Navigating to edit page: ${editUrl}`);
                                window.location.href = editUrl;
                            }
                        }
                    });

                    sidebarEl.appendChild(li);
                });
            });

            console.log(`Rendered ${allPagesForSidebar.length} pages in sidebar`);
        }

        // Insert a page link into the editor
        function insertPageLink(page) {
            const editor = tinymce.activeEditor;
            if (!editor) {
                console.error('No active TinyMCE editor found');
                alert('Please focus the editor first');
                return;
            }

            console.log('Inserting page link:', page);

            // Generate the link HTML
            const pageTitle = page.title || page.id || 'Untitled';
            const pagePath = page.path || `/${page.id}`;
            let pageUrl = pagePath.startsWith('/') ? pagePath : `/${pagePath}`;

            // 修正URL格式:去掉前面的".."和在后面加".html"
            // 1. 如果以".."开头,去掉它
            if (pageUrl.startsWith('../')) {
                pageUrl = pageUrl.substring(3); // remove "../"
            } else if (pageUrl.startsWith('..')) {
                pageUrl = pageUrl.substring(2); // remove ".."
            }

            // 2. 确保以"/"开头(如果还没有)
            if (!pageUrl.startsWith('/')) {
                pageUrl = '/' + pageUrl;
            }

            // 3. 在后面加".html"(如果还没有)
            if (!pageUrl.endsWith('.html') && !pageUrl.endsWith('.HTML')) {
                pageUrl = pageUrl + '.html';
            }

            console.log('Original path:', pagePath, '-> Final URL:', pageUrl);

            // Create link HTML
            const html = `<a href="${escapeHtml(pageUrl)}" class="webbot-page-link">${escapeHtml(pageTitle)}</a>`;

            // Insert into editor
            editor.insertContent(html);

            console.log('Page link inserted successfully');
        }

        // ========== END PAGES SIDEBAR FUNCTIONS ==========

        // WET-BOEW initialization - no-op since WET-BOEW JS is not loaded
        function initializeWETBOEW() {
            // WET-BOEW is not loaded; this function is a no-op placeholder
            // kept for callers that reference it
        }



        // Start initialization when document is ready
        // Wait for both jQuery and WET-BOEW to be ready
        console.log('Second script block executing');
        $(document).ready(function() {
            console.log('jQuery ready, starting WET-BOEW initialization');
            initializeWETBOEW();

            // Initialize metadata modal functionality
            initializeMetadataModal();

        });

        // Initialize metadata modal functionality
        function initializeMetadataModal() {
            console.log('initializeMetadataModal called');

            // Get modal elements
            const metadataModal = document.getElementById('metadata-modal');
            const metadataBtn = document.getElementById('metadata-btn');
            const metadataClose = document.getElementById('metadata-modal-close');
            const metadataCancel = document.getElementById('metadata-cancel');
            const metadataSave = document.getElementById('metadata-save');
            const metadataTabs = document.querySelectorAll('.metadata-tab');

            if (!metadataModal || !metadataBtn) {
                console.warn('Metadata modal elements not found');
                return;
            }

            // Show metadata modal
            metadataBtn.addEventListener('click', function() {
                console.log('Opening metadata modal');
                loadMetadataIntoForm();
                metadataModal.style.display = 'flex';
            });

            // Close modal functions
            const closeModal = function() {
                metadataModal.style.display = 'none';
                console.log('Metadata modal closed');
            };

            metadataClose.addEventListener('click', closeModal);
            metadataCancel.addEventListener('click', closeModal);

            // Close on outside click
            metadataModal.addEventListener('click', function(e) {
                if (e.target === metadataModal) {
                    closeModal();
                }
            });

            // Tab switching
            metadataTabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    const tabId = this.getAttribute('data-tab');
                    console.log('Switching to tab:', tabId);

                    // Update active tab
                    metadataTabs.forEach(t => t.classList.remove('active'));
                    this.classList.add('active');

                    // Show corresponding content
                    document.querySelectorAll('.metadata-tab-panel').forEach(pane => {
                        pane.classList.remove('active');
                    });
                    document.getElementById(`metadata-tab-${tabId}`).classList.add('active');
                });
            });

            // Save metadata
            metadataSave.addEventListener('click', function() {
                console.log('Saving metadata');
                saveMetadataFromForm();
                closeModal();
            });

            // Description character counter
            const descTextarea = document.getElementById('metadata-description');
            const charCount = document.getElementById('desc-char-count');
            if (descTextarea && charCount) {
                descTextarea.addEventListener('input', function() {
                    charCount.textContent = this.value.length;
                    if (this.value.length > 160) {
                        charCount.style.color = '#dc3545'; // Red
                    } else if (this.value.length > 140) {
                        charCount.style.color = '#ffc107'; // Yellow
                    } else {
                        charCount.style.color = '#28a745'; // Green
                    }
                });
            }

            /* === FUTURE: Multi-language support ===
            // Alternate language UI will be re-enabled when multi-language support is implemented
            const addLangBtn = document.getElementById('add-language-btn');
            ...
            */

            // Export metadata as HTML
            const exportBtn = document.getElementById('export-metadata-btn');
            if (exportBtn) {
                exportBtn.addEventListener('click', function() {
                    const metadata = metadataManager.getMetadata();
                    const html = metadataManager.exportAsHtml(metadata);
                    const rawTextarea = document.getElementById('metadata-raw');
                    if (rawTextarea) {
                        rawTextarea.value = `<!-- Generated metadata HTML -->\n${html}`;
                        alert('Metadata HTML exported. Copy from Raw HTML tab if needed.');
                    }
                });
            }

            // Validate metadata
            const validateBtn = document.getElementById('metadata-save');
            if (validateBtn) {
                validateBtn.addEventListener('click', function() {
                    const metadata = metadataManager.getMetadata();
                    const validation = metadataManager.validate(metadata);

                    if (validation.isValid) {
                        alert('✅ All metadata is valid!');
                    } else {
                        alert('⚠️ Metadata validation issues:\n\n' + validation.errors.join('\n'));
                    }
                });
            }

            console.log('Metadata modal initialized');
        }

        // Load current metadata into form
        function loadMetadataIntoForm() {
            console.log('loadMetadataIntoForm called');
            const metadata = metadataManager.getMetadata();

            // Basic metadata
            const titleInput = document.getElementById('metadata-title');
            const descInput = document.getElementById('metadata-description');
            const keywordsInput = document.getElementById('metadata-keywords');
            const authorInput = document.getElementById('metadata-author');

            if (titleInput) titleInput.value = metadata.title || currentPageData?.title || '';
            if (descInput) {
                descInput.value = metadata.description || '';
                // Trigger character counter update
                const event = new Event('input');
                descInput.dispatchEvent(event);
            }
            if (keywordsInput) keywordsInput.value = metadata.keywords || '';
            if (authorInput) authorInput.value = metadata.author || 'Government of Canada';

            // Subjects and Audience - auto-populate from sidebar child page titles if field is empty
            const subjectsInput = document.getElementById('metadata-subjects');
            const audienceInput = document.getElementById('metadata-audience');

            if (allPagesForSidebar && allPagesForSidebar.length > 0) {
                const allTitles = allPagesForSidebar
                    .map(p => (p.navigation_title || p.title || '').trim())
                    .filter(t => t.length > 0)
                    .join('; ');
                if (subjectsInput && !subjectsInput.value.trim()) {
                    subjectsInput.value = allTitles;
                }
                if (audienceInput && !audienceInput.value.trim()) {
                    audienceInput.value = allTitles;
                }
            } else {
                if (subjectsInput) subjectsInput.value = metadata.subjects || '';
                if (audienceInput) audienceInput.value = metadata.audience || '';
            }

            // SEO metadata
            const canonicalInput = document.getElementById('metadata-canonical');
            const robotsSelect = document.getElementById('metadata-robots');
            const viewportInput = document.getElementById('metadata-viewport');
            const htmlLangInput = document.getElementById('metadata-html-lang');

            if (canonicalInput) canonicalInput.value = metadata.canonicalUrl || '';
            if (robotsSelect) robotsSelect.value = metadata.robots || 'index, follow';
            if (viewportInput) viewportInput.value = metadata.viewport || 'width=device-width, initial-scale=1.0';
            if (htmlLangInput) htmlLangInput.value = metadata.htmlLang || currentPageData?.language || 'en';

            // Hide in navigation
            const hideNavCheckbox = document.getElementById('metadata-hide-nav');
            if (hideNavCheckbox) hideNavCheckbox.checked = currentPageData?.hide_in_navigation === true;

            // Navigation title
            const navTitleInput = document.getElementById('metadata-nav-title');
            if (navTitleInput) navTitleInput.value = currentPageData?.navigation_title || '';

            // Custom HTML (free text field for author)
            const customHtmlInput = document.getElementById('metadata-custom-html');
            if (customHtmlInput) customHtmlInput.value = metadata.custom_html || '';

            // Search engine settings
            const searchUrlInput = document.getElementById('metadata-search-url');
            if (searchUrlInput) searchUrlInput.value = metadata.search_url || '';
            const searchLabelInput = document.getElementById('metadata-search-label');
            if (searchLabelInput) searchLabelInput.value = metadata.search_label || '';
            const searchIndexSelect = document.getElementById('metadata-search-index');
            if (searchIndexSelect) searchIndexSelect.value = metadata.search_index || 'default';

            // Social metadata
            const ogTitleInput = document.getElementById('og-title');
            const ogDescInput = document.getElementById('og-description');
            const ogImageInput = document.getElementById('og-image');
            const ogUrlInput = document.getElementById('og-url');
            const twitterCardSelect = document.getElementById('twitter-card');
            const twitterTitleInput = document.getElementById('twitter-title');
            const twitterDescInput = document.getElementById('twitter-description');

            if (ogTitleInput) ogTitleInput.value = metadata.openGraph?.title || metadata.title || currentPageData?.title || '';
            if (ogDescInput) ogDescInput.value = metadata.openGraph?.description || metadata.description || '';
            if (ogImageInput) ogImageInput.value = metadata.openGraph?.image || '';
            if (ogUrlInput) ogUrlInput.value = metadata.openGraph?.url || '';
            if (twitterCardSelect) twitterCardSelect.value = metadata.twitterCard?.card || 'summary';
            if (twitterTitleInput) twitterTitleInput.value = metadata.twitterCard?.title || metadata.title || currentPageData?.title || '';
            if (twitterDescInput) twitterDescInput.value = metadata.twitterCard?.description || metadata.description || '';

            // Other language path
            const otherLangInput = document.getElementById('other-language-path');
            if (otherLangInput) otherLangInput.value = currentPageData?.other_language_path || '';

            // Populate Raw HTML tab with current editor content
            const rawTextarea = document.getElementById('metadata-raw');
            const editorEl = document.getElementById('editor-content');
            if (rawTextarea && editorEl) {
                rawTextarea.value = editorEl.value;
            }

            console.log('Metadata loaded into form');
        }

        // Save metadata from form to currentPageData
        function saveMetadataFromForm() {
            console.log('saveMetadataFromForm called');
            if (!currentPageData) {
                console.error('currentPageData not available');
                return;
            }

            // Get form values
            const titleInput = document.getElementById('metadata-title');
            const descInput = document.getElementById('metadata-description');
            const keywordsInput = document.getElementById('metadata-keywords');
            const authorInput = document.getElementById('metadata-author');
            const canonicalInput = document.getElementById('metadata-canonical');
            const robotsSelect = document.getElementById('metadata-robots');
            const viewportInput = document.getElementById('metadata-viewport');
            const htmlLangInput = document.getElementById('metadata-html-lang');
            const ogTitleInput = document.getElementById('og-title');
            const ogDescInput = document.getElementById('og-description');
            const ogImageInput = document.getElementById('og-image');
            const ogUrlInput = document.getElementById('og-url');
            const twitterCardSelect = document.getElementById('twitter-card');
            const twitterTitleInput = document.getElementById('twitter-title');
            const twitterDescInput = document.getElementById('twitter-description');

            // Update metadata object
            if (!currentPageData.metadata) {
                currentPageData.metadata = {};
            }

            // Update basic metadata
            if (titleInput && titleInput.value.trim()) {
                metadataManager.updateField('title', titleInput.value.trim());
            }
            if (descInput) {
                metadataManager.updateField('description', descInput.value.trim());
            }
            if (keywordsInput) {
                metadataManager.updateField('keywords', keywordsInput.value.trim());
            }
            if (authorInput) {
                metadataManager.updateField('author', authorInput.value.trim());
            }
            if (canonicalInput) {
                metadataManager.updateField('canonicalUrl', canonicalInput.value.trim());
            }
            if (robotsSelect) {
                metadataManager.updateField('robots', robotsSelect.value);
            }
            if (viewportInput) {
                metadataManager.updateField('viewport', viewportInput.value.trim());
            }
            if (htmlLangInput) {
                metadataManager.updateField('htmlLang', htmlLangInput.value.trim());
            }

            // Other language path
            const otherLangInput = document.getElementById('other-language-path');
            if (otherLangInput) {
                currentPageData.other_language_path = otherLangInput.value.trim() || null;
            }

            // Hide in navigation
            const hideNavCheckbox = document.getElementById('metadata-hide-nav');
            if (hideNavCheckbox) {
                currentPageData.hide_in_navigation = hideNavCheckbox.checked ? true : false;
            }

            // Navigation title
            const navTitleInput = document.getElementById('metadata-nav-title');
            if (navTitleInput) {
                currentPageData.navigation_title = navTitleInput.value.trim() || null;
            }

            // Custom HTML (free text field for author)
            const customHtmlInput = document.getElementById('metadata-custom-html');
            if (customHtmlInput) {
                metadataManager.updateField('custom_html', customHtmlInput.value);
            }

            // Search engine settings
            const searchUrlInput = document.getElementById('metadata-search-url');
            if (searchUrlInput) {
                metadataManager.updateField('search_url', searchUrlInput.value.trim() || '');
            }
            const searchLabelInput = document.getElementById('metadata-search-label');
            if (searchLabelInput) {
                metadataManager.updateField('search_label', searchLabelInput.value.trim() || '');
            }
            const searchIndexSelect = document.getElementById('metadata-search-index');
            if (searchIndexSelect) {
                metadataManager.updateField('search_index', searchIndexSelect.value || 'default');
            }

            // Subjects and Audience (text inputs, tag names from page metadata)
            const subjectsInput = document.getElementById('metadata-subjects');
            if (subjectsInput && subjectsInput.value.trim()) {
                metadataManager.updateField('subjects', subjectsInput.value.trim());
            }
            const audienceInput = document.getElementById('metadata-audience');
            if (audienceInput && audienceInput.value.trim()) {
                metadataManager.updateField('audience', audienceInput.value.trim());
            }

            // Update social metadata
            const openGraph = {};
            if (ogTitleInput && ogTitleInput.value.trim()) {
                openGraph.title = ogTitleInput.value.trim();
            }
            if (ogDescInput && ogDescInput.value.trim()) {
                openGraph.description = ogDescInput.value.trim();
            }
            if (ogImageInput && ogImageInput.value.trim()) {
                openGraph.image = ogImageInput.value.trim();
            }
            if (ogUrlInput && ogUrlInput.value.trim()) {
                openGraph.url = ogUrlInput.value.trim();
            }
            if (Object.keys(openGraph).length > 0) {
                if (!currentPageData.metadata.openGraph) {
                    currentPageData.metadata.openGraph = {};
                }
                Object.assign(currentPageData.metadata.openGraph, openGraph);
            }

            const twitterCard = {};
            if (twitterCardSelect) {
                twitterCard.card = twitterCardSelect.value;
            }
            if (twitterTitleInput && twitterTitleInput.value.trim()) {
                twitterCard.title = twitterTitleInput.value.trim();
            }
            if (twitterDescInput && twitterDescInput.value.trim()) {
                twitterCard.description = twitterDescInput.value.trim();
            }
            if (Object.keys(twitterCard).length > 0) {
                if (!currentPageData.metadata.twitterCard) {
                    currentPageData.metadata.twitterCard = {};
                }
                Object.assign(currentPageData.metadata.twitterCard, twitterCard);
            }

            console.log('Metadata saved:', currentPageData.metadata);

            // Update page title in the UI if it was changed
            if (titleInput && titleInput.value.trim() && currentPageData.title !== titleInput.value.trim()) {
                currentPageData.title = titleInput.value.trim();
                updatePageTitleDisplay();
            }

            // Show success message
            showSuccess('Metadata saved successfully! It will be included when you save the page.');
        }

        // Helper function to update page title display
        function updatePageTitleDisplay() {
            const titleDisplay = document.querySelector('#page-title-display, .page-title-display');
            if (titleDisplay && currentPageData && currentPageData.title) {
                titleDisplay.textContent = currentPageData.title;
            }
        }

        // Helper function to show success message
        function showSuccess(message) {
            // You can integrate with your existing notification system
            alert(message); // Simple alert for now
        }

        // ===========================================================================
        // Mustache.js Template Integration
        // ===========================================================================

        // Global template registry for Canada.ca components
        const templateRegistry = {
            // Canada.ca header template
            'canada-ca-header': {
                name: 'Canada.ca Header',
                template: `<header>
    <div id="wb-bnr" class="container">
        <div class="row">
            <section id="wb-lng" class="col-xs-3 col-sm-12 pull-right text-right">
                <h2 class="wb-inv">{{languageSwitchLabel}}</h2>
                <ul class="list-inline mrgn-bttm-0">
                    {{#languages}}
                    <li><a lang="{{code}}" hreflang="{{code}}" href="{{url}}">{{name}}</a></li>
                    {{/languages}}
                </ul>
            </section>
            <div class="brand col-xs-9 col-sm-5 col-md-4">
                <a href="{{homeUrl}}">
                    <img src="{{logoUrl}}" alt="{{siteName}}" />
                    <span class="wb-inv">{{siteName}} - <span lang="en">{{englishSlogan}}</span><span lang="fr">{{frenchSlogan}}</span></span>
                </a>
            </div>
        </div>
    </div>
</header>`,
                variables: {
                    languageSwitchLabel: 'Language selection',
                    languages: [
                        { code: 'en', name: 'English', url: '/en/index.html' },
                        { code: 'fr', name: 'Français', url: '/fr/index.html' }
                    ],
                    homeUrl: '/index.html',
                    logoUrl: '/GCWeb/assets/sig-blk-en.svg',
                    siteName: 'Canada.ca',
                    englishSlogan: 'The official website of the Government of Canada',
                    frenchSlogan: 'Le site officiel du gouvernement du Canada'
                }
            },

            // Canada.ca footer template
            'canada-ca-footer': {
                name: 'Canada.ca Footer',
                template: `<footer id="wb-info">
    <div class="container">
        <nav class="row">
            <h2 class="wb-inv">{{aboutGovernmentLabel}}</h2>
            <section class="col-sm-4">
                <h3>{{contactLabel}}</h3>
                <ul class="list-unstyled">
                    {{#contactLinks}}
                    <li><a href="{{url}}">{{text}}</a></li>
                    {{/contactLinks}}
                </ul>
            </section>
            <section class="col-sm-4">
                <h3>{{departmentsLabel}}</h3>
                <ul class="list-unstyled">
                    {{#departmentLinks}}
                    <li><a href="{{url}}">{{name}}</a></li>
                    {{/departmentLinks}}
                </ul>
            </section>
            <section class="col-sm-4">
                <h3>{{socialMediaLabel}}</h3>
                <ul class="list-unstyled">
                    {{#socialLinks}}
                    <li><a href="{{url}}">{{platform}}</a></li>
                    {{/socialLinks}}
                </ul>
            </section>
        </nav>
        <div class="row">
            <div class="col-xs-12">
                <p class="text-center">{{copyrightText}}</p>
            </div>
        </div>
    </div>
</footer>`,
                variables: {
                    aboutGovernmentLabel: 'About government',
                    contactLabel: 'Contact us',
                    contactLinks: [
                        { text: 'All contacts', url: '/en/contact.html' },
                        { text: 'Departments and agencies', url: '/en/government/dept.html' },
                        { text: 'Public service and military', url: '/en/services/publicservice.html' }
                    ],
                    departmentsLabel: 'Departments and agencies',
                    departmentLinks: [
                        { name: 'Health Canada', url: '/en/health-canada.html' },
                        { name: 'Service Canada', url: '/en/service-canada.html' },
                        { name: 'Canada Revenue Agency', url: '/en/revenue-agency.html' }
                    ],
                    socialMediaLabel: 'Social media',
                    socialLinks: [
                        { platform: 'Twitter', url: 'https://twitter.com/Canada' },
                        { platform: 'Facebook', url: 'https://www.facebook.com/Canada' },
                        { platform: 'YouTube', url: 'https://www.youtube.com/user/Canada' }
                    ],
                    copyrightText: '© Her Majesty the Queen in Right of Canada, as represented by the Minister of ...'
                }
            },

            // Canada.ca content page template
            'canada-ca-content-page': {
                name: 'Canada.ca Content Page',
                template: `<main property="mainContentOfPage" class="container">
    <h1 property="name" id="wb-cont">{{pageTitle}}</h1>
    <p class="lead">{{pageDescription}}</p>

    {{#sections}}
    <section>
        <h2>{{title}}</h2>
        <p>{{content}}</p>
        {{#items}}
        <ul>
            {{#.}}
            <li>{{.}}</li>
            {{/.}}
        </ul>
        {{/items}}
    </section>
    {{/sections}}

    <div class="row">
        <div class="col-md-8">
            <h2>{{relatedInformationLabel}}</h2>
            <ul>
                {{#relatedLinks}}
                <li><a href="{{url}}">{{text}}</a></li>
                {{/relatedLinks}}
            </ul>
        </div>
        <div class="col-md-4">
            <div class="well">
                <h3>{{contactBoxLabel}}</h3>
                <p>{{contactInstructions}}</p>
                <p><strong>{{phoneLabel}}:</strong> {{phoneNumber}}</p>
                <p><strong>{{emailLabel}}:</strong> <a href="mailto:{{emailAddress}}">{{emailAddress}}</a></p>
            </div>
        </div>
    </div>
</main>`,
                variables: {
                    pageTitle: 'Page Title',
                    pageDescription: 'This is a sample content page for Canada.ca',
                    sections: [
                        {
                            title: 'Section 1',
                            content: 'This is the first section of the page.',
                            items: ['Item 1', 'Item 2', 'Item 3']
                        },
                        {
                            title: 'Section 2',
                            content: 'This is the second section of the page.',
                            items: ['Point A', 'Point B', 'Point C']
                        }
                    ],
                    relatedInformationLabel: 'Related information',
                    relatedLinks: [
                        { text: 'Related link 1', url: '/en/link1.html' },
                        { text: 'Related link 2', url: '/en/link2.html' },
                        { text: 'Related link 3', url: '/en/link3.html' }
                    ],
                    contactBoxLabel: 'Contact us',
                    contactInstructions: 'For more information about this page:',
                    phoneLabel: 'Telephone',
                    phoneNumber: '1-800-555-5555',
                    emailLabel: 'Email',
                    emailAddress: 'info@canada.ca'
                }
            },

            // Canada.ca navigation menu
            'canada-ca-navigation': {
                name: 'Canada.ca Navigation Menu',
                template: `<nav id="wb-sm" class="wb-menu visible-md visible-lg" data-trgt="mb-pnl" title="{{menuTitle}}">
    <div class="container">
        <h2 class="wb-inv">{{menuTitle}}</h2>
        <ul class="list-inline menu">
            {{#menuItems}}
            <li{{#active}} class="active"{{/active}}>
                <a href="{{url}}">{{text}}</a>
                {{#children}}
                <ul class="sm list-unstyled">
                    {{#children}}
                    <li><a href="{{url}}">{{text}}</a></li>
                    {{/children}}
                </ul>
                {{/children}}
            </li>
            {{/menuItems}}
        </ul>
    </div>
</nav>`,
                variables: {
                    menuTitle: 'Site menu',
                    menuItems: [
                        {
                            text: 'Home',
                            url: '/en/index.html',
                            active: true
                        },
                        {
                            text: 'Services',
                            url: '/en/services.html',
                            children: [
                                { text: 'Apply for a passport', url: '/en/services/passports.html' },
                                { text: 'Employment Insurance', url: '/en/services/ei.html' },
                                { text: 'Taxes', url: '/en/services/taxes.html' }
                            ]
                        },
                        {
                            text: 'Departments',
                            url: '/en/government/dept.html',
                            children: [
                                { text: 'Health Canada', url: '/en/health-canada.html' },
                                { text: 'Environment Canada', url: '/en/environment-canada.html' },
                                { text: 'Transport Canada', url: '/en/transport-canada.html' }
                            ]
                        }
                    ]
                }
            },

            // Custom template (generic)
            'customer-template': {
                name: 'Custom Template',
                template: `<div class="custom-info" style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin: 20px 0; background-color: #f9f9f9;">
    <h2 style="color: #2c3e50; margin-top: 0;">{{section_title}}</h2>

    <div style="display: flex; flex-wrap: wrap; gap: 20px;">
        <div style="flex: 1; min-width: 250px;">
            <h3 style="color: #3498db; font-size: 16px; margin-bottom: 10px;">Personal Details</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold; width: 120px;">Name:</td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{{customer_name}}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">Email:</td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><a href="mailto:{{customer_email}}">{{customer_email}}</a></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">Phone:</td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><a href="tel:{{customer_phone}}">{{customer_phone}}</a></td>
                </tr>
            </table>
        </div>

        <div style="flex: 1; min-width: 250px;">
            <h3 style="color: #3498db; font-size: 16px; margin-bottom: 10px;">Company Information</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold; width: 120px;">Company:</td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{{customer_company}}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">Position:</td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{{customer_position}}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">Address:</td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{{customer_address}}</td>
                </tr>
            </table>
        </div>
    </div>

    <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd;">
        <h3 style="color: #3498db; font-size: 16px; margin-bottom: 10px;">Service Request</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold; width: 120px;">Service Type:</td>
                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{{service_type}}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">Request Date:</td>
                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{{request_date}}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">Priority:</td>
                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">
                    <span style="display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold; background-color: {{priority_color}}; color: white;">
                        {{priority}}
                    </span>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">Status:</td>
                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">
                    <span style="display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold; background-color: {{status_color}}; color: white;">
                        {{status}}
                    </span>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">Notes:</td>
                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{{notes}}</td>
            </tr>
        </table>
    </div>

    {{#additional_info}}
    <div style="margin-top: 20px; padding: 15px; background-color: #e8f4fd; border-radius: 6px; border-left: 4px solid #3498db;">
        <h4 style="margin-top: 0; color: #2c3e50;">Additional Information</h4>
        <p style="margin-bottom: 0;">{{additional_info}}</p>
    </div>
    {{/additional_info}}
</div>`,
                variables: {
                    section_title: 'Custom Information',
                    customer_name: 'John Doe',
                    customer_email: 'john.doe@example.com',
                    customer_phone: '+1 (555) 123-4567',
                    customer_company: 'Acme Corporation',
                    customer_position: 'Project Manager',
                    customer_address: '123 Business Street, Toronto, ON M5H 2N2',
                    service_type: 'Web Development',
                    request_date: '2026-04-18',
                    priority: 'Medium',
                    priority_color: '#f39c12',
                    status: 'In Progress',
                    status_color: '#3498db',
                    notes: 'Initial requirements gathering completed. Awaiting design approval.',
                    additional_info: ''
                }
            },

            // Simple generic template
            'simple-template': {
                name: 'Simple Template',
                template: `<div style="border: 1px solid #ddd; border-radius: 6px; padding: 20px; margin: 20px 0; background-color: #f8f9fa;">
    <h2 style="color: #333; margin-top: 0; border-bottom: 2px solid #007bff; padding-bottom: 10px;">{{title}}</h2>

    <div style="color: #666; font-size: 14px; margin-bottom: 15px;">
        <strong>Author:</strong> {{author}} | <strong>Date:</strong> {{date}}
    </div>

    <div style="line-height: 1.6;">
        {{content}}
    </div>

    {{#has_tags}}
    <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee;">
        <strong>Tags:</strong>
        {{#tags}}
        <span style="display: inline-block; background-color: #e9ecef; color: #495057; padding: 4px 10px; border-radius: 12px; margin-right: 5px; margin-bottom: 5px; font-size: 12px;">{{.}}</span>
        {{/tags}}
    </div>
    {{/has_tags}}
</div>`,
                variables: {
                    title: 'Sample Title',
                    author: 'Author Name',
                    date: '2026-04-18',
                    content: 'This is sample content. You can edit this text to add your own content.',
                    tags: ['sample', 'template', 'example'],
                    has_tags: true
                }
            }
        };

        // Expose template registry globally
        window.templateRegistry = templateRegistry;

        // Render a Mustache template with data
        function renderMustacheTemplate(templateId, customData = {}) {
            if (!window.Mustache) {
                console.error('Mustache.js not loaded');
                return '<div class="alert alert-danger">Mustache.js template engine not loaded</div>';
            }

            // Use window.templateRegistry first, fallback to templateRegistry
            const registry = window.templateRegistry || templateRegistry;
            const templateInfo = registry[templateId];
            if (!templateInfo) {
                console.error(`Template not found: ${templateId}`);
                return `<div class="alert alert-danger">Template "${templateId}" not found</div>`;
            }

            try {
                // Merge default variables with custom data
                const data = { ...templateInfo.variables, ...customData };

                // Render the template
                const rendered = Mustache.render(templateInfo.template, data);

                console.log(`Rendered template: ${templateId}`, { data, rendered });
                return rendered;
            } catch (error) {
                console.error(`Error rendering template ${templateId}:`, error);
                return `<div class="alert alert-danger">Error rendering template: ${error.message}</div>`;
            }
        }

        // Helper function to escape HTML for data attributes
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Insert a Mustache template into the editor with edit capabilities
        function insertMustacheTemplate(templateId, customData = {}) {
            const rendered = renderMustacheTemplate(templateId, customData);

            if (window.tinymce && window.tinymce.activeEditor) {
                // Generate unique ID for this template instance
                const instanceId = 'template-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);

                // Create wrapper with metadata (menu will be added dynamically)
                const wrapperHtml = `
                    <div class="webbot-component webbot-mustache-template"
                         data-template-id="${templateId}"
                         data-template-instance="${instanceId}"
                         data-template-vars="${escapeHtml(JSON.stringify(customData))}"
                         style="position: relative; border: 1px dashed #ccc; margin: 10px 0; padding: 10px;">

                        <!-- Template content -->
                        ${rendered}

                        <!-- Template info badge -->
                        <div style="font-size: 11px; color: #666; text-align: right; margin-top: 5px; padding-top: 5px; border-top: 1px dashed #eee;">
                            🥕 ${(window.templateRegistry || templateRegistry)[templateId]?.name || templateId}
                        </div>
                    </div>
                `;

                // Insert into TinyMCE editor
                window.tinymce.activeEditor.insertContent(wrapperHtml);
                console.log(`Inserted template ${templateId} with instance ID: ${instanceId}`, customData);

                // Add hover effect for edit button (via CSS)
                addTemplateEditStyles();

                // Wait for DOM to be updated, then attach menu system dynamically
                setTimeout(() => {
                    try {
                        // Find the newly inserted template wrapper in TinyMCE editor
                        const editor = window.tinymce.activeEditor;
                        const wrapper = editor.dom.select(`[data-template-instance="${instanceId}"]`)[0];

                        if (wrapper) {
                            // Attach menu system dynamically
                            attachComponentMenu(wrapper, instanceId);
                            console.log('Menu system dynamically attached to template:', instanceId);
                        } else {
                            console.warn('Could not find template wrapper in editor DOM:', instanceId);
                        }
                    } catch (error) {
                        console.error('Failed to attach menu system:', error);
                    }
                }, 50);

                // Trigger WET-BOEW initialization for newly inserted components
                setTimeout(() => {
                    if (typeof initializeWETBOEW === 'function') {
                        console.log('Re-initializing WET-BOEW for new content');
                        initializeWETBOEW();
                    }
                }, 100);
            } else {
                console.error('TinyMCE editor not available');
                alert('Please focus the editor before inserting a template');
            }
        }

        // Insert a custom Mustache template (with template string, not from registry)
        function insertCustomMustacheTemplate(templateString, templateName = 'Custom Template', customData = {}, templateId = 'custom-template') {
            if (!window.Mustache) {
                console.error('Mustache.js not loaded');
                alert('Mustache.js template engine not loaded');
                return;
            }

            let rendered;
            try {
                // Render the template with data
                rendered = Mustache.render(templateString, customData);
                console.log('Rendered custom template:', { templateString, customData, rendered });
            } catch (error) {
                console.error('Error rendering custom template:', error);
                alert('Error rendering template: ' + error.message);
                return;
            }

            if (window.tinymce && window.tinymce.activeEditor) {
                // Generate unique ID for this template instance
                const instanceId = 'custom-template-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);

                // Create wrapper with metadata and edit capabilities
                const wrapperHtml = `
                    <div class="webbot-component webbot-mustache-template"
                         data-template-id="${escapeHtml(templateId)}"
                         data-template-custom="true"
                         data-template-instance="${instanceId}"
                         data-template-content="${escapeHtml(templateString)}"
                         data-template-vars="${escapeHtml(JSON.stringify(customData))}"
                         style="position: relative; border: 1px dashed #28a745; margin: 10px 0; padding: 10px;">

                        <!-- Template content -->
                        ${rendered}

                        <!-- Template info badge -->
                        <div style="font-size: 11px; color: #666; text-align: right; margin-top: 5px; padding-top: 5px; border-top: 1px dashed #eee;">
                            🥕 ${escapeHtml(templateName)} (custom)
                        </div>
                    </div>
                `;

                // Insert into TinyMCE editor
                window.tinymce.activeEditor.insertContent(wrapperHtml);
                console.log(`Inserted custom template "${templateName}" with instance ID: ${instanceId}`, customData);

                // Add hover effect for edit button (via CSS)
                addTemplateEditStyles();

                // Wait for DOM to be updated, then attach menu system dynamically
                setTimeout(() => {
                    try {
                        // Find the newly inserted template wrapper in TinyMCE editor
                        const editor = window.tinymce.activeEditor;
                        const wrapper = editor.dom.select(`[data-template-instance="${instanceId}"]`)[0];

                        if (wrapper) {
                            // Attach menu system dynamically
                            attachComponentMenu(wrapper, instanceId);
                            console.log('Menu system dynamically attached to custom template:', instanceId);
                        } else {
                            console.warn('Could not find custom template wrapper in editor DOM:', instanceId);
                        }
                    } catch (error) {
                        console.error('Failed to attach menu system to custom template:', error);
                    }
                }, 50);

                // Trigger WET-BOEW initialization for newly inserted components
                setTimeout(() => {
                    if (typeof initializeWETBOEW === 'function') {
                        console.log('Re-initializing WET-BOEW for new content');
                        initializeWETBOEW();
                    }
                }, 100);
            } else {
                console.error('TinyMCE editor not available');
                alert('Please focus the editor before inserting a template');
            }
        }

        // Edit a custom Mustache template instance
        function editCustomMustacheTemplateInstance(instanceId) {
            console.log('Editing custom template instance:', instanceId);

            // Find the template wrapper in the document
            const wrapper = document.querySelector(`[data-template-instance="${instanceId}"]`);
            if (!wrapper) {
                console.error('Custom template instance not found:', instanceId);
                alert('Template not found in document. It may have been removed.');
                return;
            }

            // Extract template metadata
            const templateId = wrapper.getAttribute('data-template-id');
            const templateContent = wrapper.getAttribute('data-template-content');
            const varsJson = wrapper.getAttribute('data-template-vars');
            let currentData = {};

            try {
                currentData = JSON.parse(varsJson || '{}');
            } catch (error) {
                console.error('Failed to parse template variables:', error);
                currentData = {};
            }

            // Show the custom template editor
            showCustomTemplateEditor(instanceId, templateContent, currentData);
        }

        // Make function available globally for inline onclick handlers
        window.editCustomMustacheTemplateInstance = editCustomMustacheTemplateInstance;

        // Show custom template editor modal for editing both template and data
        function showCustomTemplateEditor(instanceId, templateContent = '', currentData = {}) {
            // Parse current data for form display
            const dataJson = JSON.stringify(currentData, null, 2);

            const modalHtml = `
                <div id="custom-template-editor-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000; display: flex; align-items: center; justify-content: center;">
                    <div style="background: white; border-radius: 8px; width: 90%; max-width: 800px; max-height: 90vh; overflow-y: auto; padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <h2 style="margin: 0;">✏️ Edit Custom Template</h2>
                            <button id="close-custom-template-editor" style="background: none; border: none; font-size: 24px; cursor: pointer;">×</button>
                        </div>

                        <p>Edit your custom Mustache template and data. Use <code>{{variable}}</code> syntax in the template.</p>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
                            <!-- Left column: Template editor -->
                            <div>
                                <h4 style="margin: 0 0 10px 0;">Template Content</h4>
                                <textarea id="custom-template-content"
                                          style="width: 100%; min-height: 300px; font-family: monospace; border: 1px solid #ddd; padding: 10px; border-radius: 4px;"
                                          placeholder="Enter Mustache template with {{variables}}">${escapeHtml(templateContent)}</textarea>
                                <div style="margin-top: 10px; font-size: 12px; color: #666;">
                                    <strong>Template tips:</strong>
                                    <ul style="margin: 5px 0; padding-left: 20px;">
                                        <li>Use <code>{{variable}}</code> to insert data values</li>
                                        <li>Use <code>{{#section}}...{{/section}}</code> for loops</li>
                                        <li>Use <code>{{^inverted}}...{{/inverted}}</code> for inverted sections</li>
                                        <li>Use <code>{{& html}}</code> for unescaped HTML</li>
                                    </ul>
                                </div>
                            </div>

                            <!-- Right column: Data editor -->
                            <div>
                                <h4 style="margin: 0 0 10px 0;">Template Data (JSON)</h4>
                                <textarea id="custom-template-data"
                                          style="width: 100%; min-height: 300px; font-family: monospace; border: 1px solid #ddd; padding: 10px; border-radius: 4px;"
                                          placeholder='{"variable": "value", "list": ["item1", "item2"]}'>${escapeHtml(dataJson)}</textarea>
                                <div style="margin-top: 10px; font-size: 12px; color: #666;">
                                    <strong>Data tips:</strong>
                                    <ul style="margin: 5px 0; padding-left: 20px;">
                                        <li>Must be valid JSON format</li>
                                        <li>Objects: <code>{"key": "value"}</code></li>
                                        <li>Arrays: <code>["item1", "item2"]</code></li>
                                        <li>Nested: <code>{"user": {"name": "John"}}</code></li>
                                    </ul>
                                </div>

                                <!-- API/URL data loading -->
                                <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 4px; border: 1px solid #ddd;">
                                    <h5 style="margin: 0 0 10px 0;">🌐 Load Data from API/URL</h5>
                                    <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                                        <input type="text" id="api-url-input"
                                               style="flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px;"
                                               placeholder="https://api.example.com/data">
                                        <button id="fetch-api-data" class="btn btn-primary" style="background: #007bff; border-color: #007bff; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer;">
                                            Fetch
                                        </button>
                                    </div>
                                    <div style="display: flex; gap: 10px;">
                                        <button id="test-api-connection" class="btn btn-secondary" style="background: #6c757d; border-color: #6c757d; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer;">
                                            Test Connection
                                        </button>
                                        <button id="preview-template" class="btn btn-info" style="background: #17a2b8; border-color: #17a2b8; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer;">
                                            Preview
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd;">
                            <button id="cancel-custom-template-edit" class="btn btn-secondary">Cancel</button>
                            <button id="save-custom-template-edit" class="btn btn-success" style="background: #28a745; border-color: #28a745;">Save Changes</button>
                        </div>
                    </div>
                </div>
            `;

            // Remove any existing custom template editor modal
            const existingModal = document.getElementById('custom-template-editor-modal');
            if (existingModal) existingModal.remove();

            // Add modal to document
            document.body.insertAdjacentHTML('beforeend', modalHtml);

            // Setup event handlers
            document.getElementById('close-custom-template-editor').addEventListener('click', closeCustomTemplateEditor);
            document.getElementById('cancel-custom-template-edit').addEventListener('click', closeCustomTemplateEditor);

            // Fetch API data button
            document.getElementById('fetch-api-data').addEventListener('click', () => {
                fetchAPIData(instanceId);
            });

            // Test API connection button
            document.getElementById('test-api-connection').addEventListener('click', () => {
                testAPIConnection();
            });

            // Preview template button
            document.getElementById('preview-template').addEventListener('click', () => {
                previewTemplate(instanceId);
            });

            // Save changes button
            document.getElementById('save-custom-template-edit').addEventListener('click', () => {
                saveCustomTemplateChanges(instanceId);
            });
        }

        // Fetch data from API/URL
        async function fetchAPIData(instanceId) {
            const urlInput = document.getElementById('api-url-input');
            const url = urlInput.value.trim();

            if (!url) {
                alert('Please enter a URL');
                return;
            }

            // Show loading state
            const fetchBtn = document.getElementById('fetch-api-data');
            const originalText = fetchBtn.textContent;
            fetchBtn.textContent = 'Fetching...';
            fetchBtn.disabled = true;

            try {
                console.log(`Fetching data from: ${url}`);
                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                console.log('Fetched API data:', data);

                // Update the data textarea with fetched JSON
                const dataTextarea = document.getElementById('custom-template-data');
                dataTextarea.value = JSON.stringify(data, null, 2);

                // Also save the URL for future use
                const urlInfo = `// Data fetched from: ${url}\n// Timestamp: ${new Date().toISOString()}\n`;
                dataTextarea.value = urlInfo + dataTextarea.value;

                alert(`✅ Successfully fetched ${Object.keys(data).length} data items from API`);
            } catch (error) {
                console.error('Error fetching API data:', error);
                alert(`❌ Failed to fetch data: ${error.message}\n\nCommon issues:\n1. CORS policy (try JSONPlaceholder for testing)\n2. Invalid URL\n3. API requires authentication`);
            } finally {
                // Restore button state
                fetchBtn.textContent = originalText;
                fetchBtn.disabled = false;
            }
        }

        // Test API connection
        async function testAPIConnection() {
            const urlInput = document.getElementById('api-url-input');
            const url = urlInput.value.trim();

            if (!url) {
                alert('Please enter a URL to test');
                return;
            }

            const testBtn = document.getElementById('test-api-connection');
            const originalText = testBtn.textContent;
            testBtn.textContent = 'Testing...';
            testBtn.disabled = true;

            try {
                console.log(`Testing API connection: ${url}`);
                const response = await fetch(url, {
                    method: 'HEAD',
                    mode: 'cors',
                    headers: {
                        'Accept': 'application/json'
                    }
                });

                const corsAllowed = response.headers.get('access-control-allow-origin') !== null;
                const contentType = response.headers.get('content-type') || 'unknown';

                const message = `✅ Connection successful!\n\n` +
                               `Status: ${response.status} ${response.statusText}\n` +
                               `CORS: ${corsAllowed ? '✅ Allowed' : '⚠️ May be blocked'}\n` +
                               `Content-Type: ${contentType}\n` +
                               `URL: ${url}`;

                alert(message);
                console.log('API test result:', { status: response.status, corsAllowed, contentType });
            } catch (error) {
                console.error('API connection test failed:', error);
                alert(`❌ Connection failed: ${error.message}\n\nTry these test APIs:\n• https://jsonplaceholder.typicode.com/posts/1\n• https://api.github.com/users/octocat\n• https://httpbin.org/get`);
            } finally {
                testBtn.textContent = originalText;
                testBtn.disabled = false;
            }
        }

        // Preview template with current data
        function previewTemplate(instanceId) {
            const templateContent = document.getElementById('custom-template-content').value;
            const dataText = document.getElementById('custom-template-data').value;

            if (!templateContent.trim()) {
                alert('Please enter a template to preview');
                return;
            }

            let data = {};
            if (dataText.trim()) {
                try {
                    // Remove URL comment lines if present
                    const cleanDataText = dataText.replace(/^\/\/.*$/mg, '').trim();
                    data = JSON.parse(cleanDataText);
                } catch (e) {
                    alert('Invalid JSON data: ' + e.message + '\n\nPlease check your JSON syntax.');
                    return;
                }
            }

            try {
                const rendered = Mustache.render(templateContent, data);

                // Show preview in a modal
                const previewHtml = `
                    <div id="template-preview-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10001; display: flex; align-items: center; justify-content: center;">
                        <div style="background: white; border-radius: 8px; width: 90%; max-width: 800px; max-height: 80vh; overflow-y: auto; padding: 20px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                                <h3 style="margin: 0;">👁️ Template Preview</h3>
                                <button id="close-preview" style="background: none; border: none; font-size: 24px; cursor: pointer;">×</button>
                            </div>

                            <div style="border: 1px solid #ddd; border-radius: 4px; padding: 20px; background: #f9f9f9; margin-bottom: 20px;">
                                ${rendered}
                            </div>

                            <div style="display: flex; justify-content: flex-end;">
                                <button id="close-preview-btn" class="btn btn-primary">Close Preview</button>
                            </div>
                        </div>
                    </div>
                `;

                // Remove any existing preview modal
                const existingPreview = document.getElementById('template-preview-modal');
                if (existingPreview) existingPreview.remove();

                // Add preview modal
                document.body.insertAdjacentHTML('beforeend', previewHtml);

                // Setup close handlers
                document.getElementById('close-preview').addEventListener('click', () => {
                    document.getElementById('template-preview-modal').remove();
                });
                document.getElementById('close-preview-btn').addEventListener('click', () => {
                    document.getElementById('template-preview-modal').remove();
                });

                console.log('Template preview generated');
            } catch (error) {
                console.error('Error previewing template:', error);
                alert('Error rendering preview: ' + error.message);
            }
        }

        // Save custom template changes
        function saveCustomTemplateChanges(instanceId) {
            const templateContent = document.getElementById('custom-template-content').value.trim();
            const dataText = document.getElementById('custom-template-data').value;

            if (!templateContent) {
                alert('Template content cannot be empty');
                return;
            }

            let data = {};
            if (dataText.trim()) {
                try {
                    // Remove URL comment lines if present
                    const cleanDataText = dataText.replace(/^\/\/.*$/mg, '').trim();
                    data = JSON.parse(cleanDataText);
                } catch (e) {
                    alert('Invalid JSON data: ' + e.message + '\n\nPlease check your JSON syntax.');
                    return;
                }
            }

            console.log('Saving custom template changes:', { instanceId, templateContent, data });

            // Update the template instance in the editor
            updateCustomMustacheTemplateInstance(instanceId, templateContent, data);

            // Close the editor
            closeCustomTemplateEditor();
        }

        // Update a custom template instance with new template and data
        function updateCustomMustacheTemplateInstance(instanceId, newTemplateContent, newData) {
            console.log('Updating custom template instance:', instanceId, newTemplateContent, newData);

            // Find the template wrapper
            const wrapper = document.querySelector(`[data-template-instance="${instanceId}"]`);
            if (!wrapper) {
                console.error('Custom template instance not found for update:', instanceId);
                return;
            }

            const templateId = wrapper.getAttribute('data-template-id');
            const isCustom = wrapper.getAttribute('data-template-custom') === 'true';

            if (!isCustom) {
                console.error('Cannot update non-custom template with custom editor:', instanceId);
                alert('This template is not a custom template. Use the standard template editor instead.');
                return;
            }

            // Re-render the template with new content and data
            let rendered;
            try {
                rendered = Mustache.render(newTemplateContent, newData);
            } catch (error) {
                console.error('Error rendering updated template:', error);
                alert('Error rendering template: ' + error.message);
                return;
            }

            // Create new wrapper HTML (keeping the same instance ID)
            const newWrapperHtml = `
                <div class="webbot-mustache-template"
                     data-template-id="${escapeHtml(templateId)}"
                     data-template-custom="true"
                     data-template-instance="${instanceId}"
                     data-template-content="${escapeHtml(newTemplateContent)}"
                     data-template-vars="${escapeHtml(JSON.stringify(newData))}"
                     style="position: relative; border: 1px dashed #28a745; margin: 10px 0; padding: 10px;">

                    <!-- Edit button -->
                    <div class="template-edit-button"
                         style="position: absolute; top: -10px; right: -10px; background: #28a745; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 12px; z-index: 100; opacity: 0; transition: opacity 0.2s;"
                         onclick="window.editCustomMustacheTemplateInstance('${instanceId}')"
                         title="Edit custom template">
                        ✏️
                    </div>

                    <!-- Template content -->
                    ${rendered}

                    <!-- Template info badge -->
                    <div style="font-size: 11px; color: #666; text-align: right; margin-top: 5px; padding-top: 5px; border-top: 1px dashed #eee;">
                        🥕 Custom Template (edited)
                    </div>
                </div>
            `;

            // Replace the wrapper in TinyMCE editor
            if (window.tinymce && window.tinymce.activeEditor) {
                const editor = window.tinymce.activeEditor;
                const wrapperNode = editor.dom.select(`[data-template-instance="${instanceId}"]`)[0];

                if (wrapperNode) {
                    // Create a temporary container for the new HTML
                    const tempDiv = editor.dom.create('div', {}, newWrapperHtml);

                    // Replace the old wrapper with new content
                    wrapperNode.parentNode.replaceChild(tempDiv, wrapperNode);

                    console.log('Custom template instance updated:', instanceId);

                    // Re-initialize WET-BOEW
                    setTimeout(() => {
                        if (typeof initializeWETBOEW === 'function') {
                            initializeWETBOEW();
                        }
                    }, 100);
                } else {
                    console.error('Custom template instance not found in TinyMCE DOM');
                }
            } else {
                console.error('TinyMCE editor not available for update');
            }
        }

        // Close custom template editor modal
        function closeCustomTemplateEditor() {
            const modal = document.getElementById('custom-template-editor-modal');
            if (modal) modal.remove();
        }

        // Add CSS styles for template editing
        function addTemplateEditStyles() {
            // Add to main document
            if (!document.getElementById('template-edit-styles')) {
                const style = document.createElement('style');
                style.id = 'template-edit-styles';
                style.textContent = `
                    /* Component hover effects */
                    .webbot-component:hover,
                    .webbot-mustache-template:hover {
                        border-color: #4e54c8 !important;
                        box-shadow: 0 0 0 3px rgba(78, 84, 200, 0.2) !important;
                        background-color: rgba(78, 84, 200, 0.02);
                        transition: all 0.3s ease;
                    }

                    /* Menu button styles */
                    .webbot-component .component-menu-btn,
                    .webbot-mustache-template .component-menu-btn {
                        position: absolute;
                        top: 5px;
                        right: 5px;
                        background: white;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        width: 24px;
                        height: 24px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        cursor: pointer;
                        font-size: 16px;
                        opacity: 0;
                        transition: opacity 0.2s, background-color 0.2s;
                        z-index: 100;
                    }

                    .webbot-component:hover .component-menu-btn,
                    .webbot-mustache-template:hover .component-menu-btn {
                        opacity: 1;
                    }

                    .webbot-component .component-menu-btn:hover,
                    .webbot-mustache-template .component-menu-btn:hover {
                        background: #f0f0f0;
                        border-color: #bbb;
                    }

                    /* Dropdown menu inside components (legacy) */
                    .webbot-component .component-dropdown,
                    .webbot-mustache-template .component-dropdown {
                        display: none;
                        position: absolute;
                        top: 30px;
                        right: 5px;
                        background: white;
                        border: 1px solid #ddd;
                        border-radius: 6px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                        min-width: 140px;
                        z-index: 1000;
                        padding: 5px 0;
                    }

                    /* Global dropdown menu (for body-attached menus) */
                    .component-dropdown {
                        display: none;
                        position: fixed; /* Use fixed for body positioning */
                        background: white;
                        border: 1px solid #ddd;
                        border-radius: 6px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                        min-width: 140px;
                        z-index: 9999; /* Very high z-index to be above everything */
                        padding: 5px 0;
                    }

                    .webbot-component .component-dropdown.show,
                    .webbot-mustache-template .component-dropdown.show,
                    .component-dropdown.show {
                        display: block;
                    }

                    /* Menu items */
                    .webbot-component .menu-item,
                    .webbot-mustache-template .menu-item {
                        display: block;
                        width: 100%;
                        padding: 8px 12px;
                        background: none;
                        border: none;
                        text-align: left;
                        cursor: pointer;
                        font-size: 13px;
                        color: #333;
                        transition: background-color 0.2s;
                    }

                    .webbot-component .menu-item:hover,
                    .webbot-mustache-template .menu-item:hover {
                        background-color: #f5f5f5;
                    }

                    /* Delete button special styling */
                    .webbot-component .menu-item[data-action="delete"],
                    .webbot-mustache-template .menu-item[data-action="delete"] {
                        color: #dc3545;
                    }

                    .webbot-component .menu-item[data-action="delete"]:hover,
                    .webbot-mustache-template .menu-item[data-action="delete"]:hover {
                        background-color: #f8d7da;
                    }

                    /* Keep existing edit button styles for backward compatibility */
                    .webbot-mustache-template:hover .template-edit-button {
                        opacity: 1 !important;
                    }
                    .webbot-mustache-template .template-edit-button:hover {
                        background: #5a32a3 !important;
                        transform: scale(1.1);
                    }
                `;
                document.head.appendChild(style);
                console.log('Template edit styles added to main document');
            }

            // Also add to TinyMCE editor if available
            if (window.tinymce && window.tinymce.activeEditor) {
                try {
                    const editor = window.tinymce.activeEditor;
                    // Check if style already exists in editor
                    const editorDoc = editor.getDoc();
                    if (editorDoc && !editorDoc.getElementById('template-edit-styles')) {
                        const editorStyle = editorDoc.createElement('style');
                        editorStyle.id = 'template-edit-styles';
                        editorStyle.textContent = `
                            /* Component hover effects for editor */
                            .webbot-component:hover,
                            .webbot-mustache-template:hover {
                                border-color: #4e54c8 !important;
                                box-shadow: 0 0 0 3px rgba(78, 84, 200, 0.2) !important;
                                background-color: rgba(78, 84, 200, 0.02);
                                transition: all 0.3s ease;
                            }

                            /* Menu button styles for editor */
                            .webbot-component .component-menu-btn,
                            .webbot-mustache-template .component-menu-btn {
                                position: absolute;
                                top: 5px;
                                right: 5px;
                                background: white;
                                border: 1px solid #ddd;
                                border-radius: 4px;
                                width: 24px;
                                height: 24px;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                cursor: pointer;
                                font-size: 16px;
                                opacity: 0;
                                transition: opacity 0.2s, background-color 0.2s;
                                z-index: 100;
                            }

                            .webbot-component:hover .component-menu-btn,
                            .webbot-mustache-template:hover .component-menu-btn {
                                opacity: 1;
                            }

                            .webbot-component .component-menu-btn:hover,
                            .webbot-mustache-template .component-menu-btn:hover {
                                background: #f0f0f0;
                                border-color: #bbb;
                            }

                            /* Dropdown menu for editor */
                            .webbot-component .component-dropdown,
                            .webbot-mustache-template .component-dropdown {
                                display: none;
                                position: absolute;
                                top: 30px;
                                right: 5px;
                                background: white;
                                border: 1px solid #ddd;
                                border-radius: 6px;
                                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                                min-width: 140px;
                                z-index: 1000;
                                padding: 5px 0;
                            }

                            .webbot-component .component-dropdown.show,
                            .webbot-mustache-template .component-dropdown.show {
                                display: block;
                            }

                            /* Menu items for editor */
                            .webbot-component .menu-item,
                            .webbot-mustache-template .menu-item {
                                display: block;
                                width: 100%;
                                padding: 8px 12px;
                                background: none;
                                border: none;
                                text-align: left;
                                cursor: pointer;
                                font-size: 13px;
                                color: #333;
                                transition: background-color 0.2s;
                            }

                            .webbot-component .menu-item:hover,
                            .webbot-mustache-template .menu-item:hover {
                                background-color: #f5f5f5;
                            }

                            /* Delete button special styling for editor */
                            .webbot-component .menu-item[data-action="delete"],
                            .webbot-mustache-template .menu-item[data-action="delete"] {
                                color: #dc3545;
                            }

                            .webbot-component .menu-item[data-action="delete"]:hover,
                            .webbot-mustache-template .menu-item[data-action="delete"]:hover {
                                background-color: #f8d7da;
                            }
                        `;
                        editorDoc.head.appendChild(editorStyle);
                        console.log('Template edit styles added to TinyMCE editor');
                    }
                } catch (error) {
                    console.error('Failed to add styles to TinyMCE editor:', error);
                }
            }
        }

        // ===========================================================================
        // Component Menu System
        // ===========================================================================

        // Global clipboard for component copy/paste
        window.webbotClipboard = {
            componentData: null,
            componentType: null, // 'mustache-template' or 'custom-template'
            copiedAt: null
        };

        // Dynamically add menu system to a component
        function attachComponentMenu(wrapper, instanceId) {
            if (!wrapper || !instanceId) {
                console.error('Invalid parameters for attachComponentMenu');
                return;
            }

            // Check if menu already exists
            if (wrapper.querySelector('.component-menu-btn')) {
                console.log('Menu already attached to component:', instanceId);
                return;
            }

            // Check if this is a template that should not be editable by customers
            // Only the custom template (customer-template) should show edit icon
            const templateId = wrapper.getAttribute('data-template-id');
            if (templateId && templateId !== 'customer-template') {
                console.log('Skipping menu for non-custom template:', templateId);
                return;
            }

            // Create menu button
            const menuBtn = document.createElement('div');
            menuBtn.className = 'component-menu-btn';
            menuBtn.title = 'Component menu';
            menuBtn.textContent = '⋮';

            // Create dropdown menu - append to body instead of wrapper
            const dropdown = document.createElement('div');
            dropdown.className = 'component-dropdown';
            dropdown.id = `menu-${instanceId}`;
            dropdown.style.display = 'none'; // Initially hidden
            dropdown.setAttribute('data-component-instance', instanceId);

            // Menu items configuration
            const menuItems = [
                { label: '✏️ Edit', action: 'edit' },
                { label: '📋 Copy', action: 'copy' },
                { label: '📄 Paste Here', action: 'paste' },
                { label: '🗑️ Delete', action: 'delete' }
            ];

            // Create menu items
            menuItems.forEach(item => {
                const button = document.createElement('button');
                button.className = 'menu-item';
                button.setAttribute('data-action', item.action);
                button.textContent = item.label;

                // Add click event listener
                button.addEventListener('click', (event) => {
                    event.stopPropagation();
                    // Close menu before action
                    dropdown.classList.remove('show');
                    window.handleComponentAction(event, instanceId, item.action, wrapper);
                });

                dropdown.appendChild(button);
            });

            // Add click event to menu button
            menuBtn.addEventListener('click', (event) => {
                event.stopPropagation();

                // Get menu button position for dropdown placement
                const rect = menuBtn.getBoundingClientRect();

                // Check if dropdown is in parent document
                const dropdownInParent = dropdown.parentNode &&
                                       dropdown.parentNode.ownerDocument !== document;

                let topPos, leftPos;

                if (dropdownInParent && window.parent && window.parent !== window) {
                    // Dropdown is in parent document, need to convert coordinates
                    // Get iframe position in parent window
                    const iframe = window.frameElement;
                    if (iframe) {
                        const iframeRect = iframe.getBoundingClientRect();
                        // Convert from iframe-relative to parent-relative coordinates
                        topPos = iframeRect.top + rect.bottom;
                        leftPos = iframeRect.left + rect.right - 140;
                        console.log('📍 Converting coordinates for parent document:', {
                            iframeTop: iframeRect.top,
                            iframeLeft: iframeRect.left,
                            rectBottom: rect.bottom,
                            rectRight: rect.right,
                            finalTop: topPos,
                            finalLeft: leftPos
                        });
                    } else {
                        // Fallback: use current coordinates (may not be accurate)
                        topPos = rect.bottom;
                        leftPos = rect.right - 140;
                    }
                } else {
                    // Dropdown is in same document, use viewport coordinates
                    topPos = rect.bottom;
                    leftPos = rect.right - 140;
                }

                // Apply positions
                dropdown.style.top = `${topPos}px`;
                dropdown.style.left = `${leftPos}px`;

                // Ensure dropdown is visible and on top
                dropdown.style.zIndex = '99999';

                window.toggleComponentMenu(event, instanceId, dropdown);
            });

            // Add hover events for showing/hiding menu button
            let hideTimeout;
            wrapper.addEventListener('mouseenter', () => {
                clearTimeout(hideTimeout);
            });

            wrapper.addEventListener('mouseleave', () => {
                hideTimeout = setTimeout(() => {
                    // Also hide dropdown if open
                    dropdown.classList.remove('show');
                }, 300); // Small delay to allow moving to menu
            });

            // Keep menu button visible when hovering over it or dropdown
            menuBtn.addEventListener('mouseenter', () => {
                clearTimeout(hideTimeout);
            });

            dropdown.addEventListener('mouseenter', () => {
                clearTimeout(hideTimeout);
            });

            dropdown.addEventListener('mouseleave', () => {
                hideTimeout = setTimeout(() => {
                    dropdown.classList.remove('show');
                }, 300);
            });

            // Determine the correct document for appending dropdown
            // If we're in an iframe (like TinyMCE), append to parent document for proper positioning
            let targetDocument = document;
            let targetBody = document.body;

            try {
                // Check if we're in an iframe with a parent window
                if (window.parent && window.parent !== window && window.parent.document) {
                    // Check if we should use parent document (for TinyMCE iframes)
                    const isInEditor = wrapper.closest('iframe') ||
                                      (typeof tinymce !== 'undefined' && tinymce.activeEditor);

                    if (isInEditor) {
                        targetDocument = window.parent.document;
                        targetBody = window.parent.document.body;
                        console.log('📦 Using parent document for dropdown placement');
                    }
                }
            } catch (error) {
                console.warn('Cannot access parent document, using current document:', error);
            }

            // Append menu button to wrapper, dropdown to appropriate body
            wrapper.appendChild(menuBtn);
            targetBody.appendChild(dropdown);

            console.log('Menu system attached to component:', instanceId);
        }

        // Initialize menus for existing components on page load
        function initializeComponentMenus() {
            console.log('Initializing component menus...');

            // Find all component elements
            const components = document.querySelectorAll('.webbot-component, .webbot-mustache-template');
            console.log(`Found ${components.length} components to initialize`);

            components.forEach(wrapper => {
                // Get instance ID from data attribute
                const instanceId = wrapper.getAttribute('data-template-instance');

                if (instanceId) {
                    // Check if menu already exists
                    if (!wrapper.querySelector('.component-menu-btn')) {
                        attachComponentMenu(wrapper, instanceId);
                    }
                } else {
                    console.warn('Component missing data-template-instance attribute:', wrapper);
                }
            });

            // Also check inside TinyMCE editor if available
            if (window.tinymce) {
                const checkEditor = () => {
                    try {
                        const editor = window.tinymce.activeEditor;
                        if (!editor || !editor.dom || !editor.initialized) {
                            // Editor not ready yet, retry
                            setTimeout(checkEditor, 500);
                            return;
                        }
                        const editorComponents = editor.dom.select('.webbot-component, .webbot-mustache-template');
                        console.log(`Found ${editorComponents.length} components in editor to initialize`);

                        editorComponents.forEach(wrapper => {
                            const instanceId = wrapper.getAttribute('data-template-instance');
                            if (instanceId && !wrapper.querySelector('.component-menu-btn')) {
                                attachComponentMenu(wrapper, instanceId);
                            }
                        });
                    } catch (error) {
                        console.error('Failed to initialize menus in editor:', error);
                    }
                };
                // Initial call
                checkEditor();
            }

            console.log('Component menu initialization complete');
        }

        // Make functions globally available
        window.attachComponentMenu = attachComponentMenu;
        window.initializeComponentMenus = initializeComponentMenus;

        // Toggle component menu visibility
        function toggleComponentMenu(event, instanceId, dropdown = null) {
            event.stopPropagation(); // Prevent event bubbling

            // Get the dropdown element if not provided
            if (!dropdown) {
                dropdown = document.getElementById(`menu-${instanceId}`);
            }

            if (!dropdown) {
                console.error('Dropdown not found for instance:', instanceId);
                return;
            }

            // Close all other open menus
            document.querySelectorAll('.component-dropdown.show').forEach(menu => {
                if (menu.id !== `menu-${instanceId}`) {
                    menu.classList.remove('show');
                }
            });

            // Toggle the clicked menu
            dropdown.classList.toggle('show');

            // Close menu when clicking outside (only if menu exists)
            if (dropdown) {
                const closeMenuHandler = (e) => {
                    // Check if dropdown still exists
                    if (!dropdown || !dropdown.contains(e.target) && e.target.className !== 'component-menu-btn') {
                        if (dropdown) dropdown.classList.remove('show');
                        document.removeEventListener('click', closeMenuHandler);
                    }
                };

                // Add event listener to close menu on outside click
                setTimeout(() => {
                    document.addEventListener('click', closeMenuHandler);
                }, 10);
            }
        }

        // Handle component menu actions
        function handleComponentAction(event, instanceId, action, wrapper = null) {
            event.stopPropagation();

            // Close the menu
            const menu = document.getElementById(`menu-${instanceId}`);
            if (menu) {
                menu.classList.remove('show');
            }

            // Find the component wrapper if not provided
            if (!wrapper) {
                wrapper = document.querySelector(`[data-template-instance="${instanceId}"]`);

                // If not found in main document, try TinyMCE editor
                if (!wrapper && window.tinymce && window.tinymce.activeEditor) {
                    try {
                        const editor = window.tinymce.activeEditor;
                        wrapper = editor.dom.select(`[data-template-instance="${instanceId}"]`)[0];
                    } catch (error) {
                        console.error('Error finding component in editor:', error);
                    }
                }

                if (!wrapper) {
                    console.error('Component not found:', instanceId);
                    alert('Component not found in document. It may have been removed.');
                    return;
                }
            }

            // Execute the requested action
            switch (action) {
                case 'edit':
                    // Check if it's a custom template
                    const isCustom = wrapper.getAttribute('data-template-custom') === 'true';
                    if (isCustom) {
                        if (typeof window.editCustomMustacheTemplateInstance === 'function') {
                            window.editCustomMustacheTemplateInstance(instanceId);
                        } else {
                            alert('Custom template editor not available');
                        }
                    } else {
                        if (typeof window.editMustacheTemplateInstance === 'function') {
                            window.editMustacheTemplateInstance(instanceId);
                        } else {
                            alert('Template editor not available');
                        }
                    }
                    break;

                case 'copy':
                    copyComponent(wrapper);
                    break;

                case 'paste':
                    pasteComponent(wrapper);
                    break;

                case 'delete':
                    deleteComponent(wrapper);
                    break;

                default:
                    console.error('Unknown action:', action);
            }
        }

        // Copy component to clipboard
        function copyComponent(wrapper) {
            try {
                // Extract all relevant data from the component
                const componentData = {
                    templateId: wrapper.getAttribute('data-template-id'),
                    instanceId: wrapper.getAttribute('data-template-instance'),
                    isCustom: wrapper.getAttribute('data-template-custom') === 'true',
                    templateContent: wrapper.getAttribute('data-template-content'),
                    templateVars: wrapper.getAttribute('data-template-vars'),
                    // Store the HTML structure for re-insertion
                    html: wrapper.outerHTML
                };

                // Update global clipboard
                window.webbotClipboard.componentData = componentData;
                window.webbotClipboard.componentType = componentData.isCustom ? 'custom-template' : 'mustache-template';
                window.webbotClipboard.copiedAt = new Date().toISOString();

                console.log('Component copied to clipboard:', componentData);
                alert('✅ Component copied to clipboard! You can now paste it elsewhere.');

            } catch (error) {
                console.error('Failed to copy component:', error);
                alert('Failed to copy component: ' + error.message);
            }
        }

        // Paste component after the selected component
        function pasteComponent(referenceWrapper) {
            try {
                if (!window.webbotClipboard.componentData) {
                    alert('No component in clipboard. Copy a component first.');
                    return;
                }

                const componentData = window.webbotClipboard.componentData;

                // Create a new instance ID for the pasted component
                const newInstanceId = componentData.isCustom
                    ? 'custom-template-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9)
                    : 'template-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);

                // Update the HTML with new instance ID
                let newHtml = componentData.html
                    .replace(`data-template-instance="${componentData.instanceId}"`, `data-template-instance="${newInstanceId}"`)
                    .replace(`id="menu-${componentData.instanceId}"`, `id="menu-${newInstanceId}"`)
                    .replace(/onclick=\"window\.toggleComponentMenu\(event, '${componentData.instanceId}'\)\"/g,
                             `onclick="window.toggleComponentMenu(event, '${newInstanceId}')"`)
                    .replace(/onclick=\"window\.handleComponentAction\(event, '${componentData.instanceId}',/g,
                             `onclick="window.handleComponentAction(event, '${newInstanceId}',`);

                // If pasting in TinyMCE editor
                if (window.tinymce && window.tinymce.activeEditor) {
                    // Insert after the reference component
                    const editor = window.tinymce.activeEditor;
                    const referenceNode = editor.dom.select(`[data-template-instance="${referenceWrapper.getAttribute('data-template-instance')}"]`)[0];

                    if (referenceNode && referenceNode.parentNode) {
                        // Create a temporary container
                        const tempDiv = editor.dom.create('div', {}, newHtml);

                        // Insert after the reference node
                        referenceNode.parentNode.insertBefore(tempDiv, referenceNode.nextSibling);

                        console.log('Component pasted with new instance ID:', newInstanceId);
                        alert('✅ Component pasted successfully!');

                        // Re-initialize WET-BOEW
                        setTimeout(() => {
                            if (typeof initializeWETBOEW === 'function') {
                                initializeWETBOEW();
                            }
                        }, 100);
                    } else {
                        // Fallback: insert at cursor position
                        editor.insertContent(newHtml);
                        console.log('Component pasted at cursor position:', newInstanceId);
                        alert('✅ Component pasted at cursor position!');
                    }
                } else {
                    console.error('TinyMCE editor not available for paste');
                    alert('Editor not available for paste operation');
                }

            } catch (error) {
                console.error('Failed to paste component:', error);
                alert('Failed to paste component: ' + error.message);
            }
        }

        // Delete component with confirmation
        function deleteComponent(wrapper) {
            if (!confirm('Are you sure you want to delete this component?')) {
                return;
            }

            try {
                // Get instance ID before removal for logging
                const instanceId = wrapper.getAttribute('data-template-instance');

                // Remove from DOM
                if (wrapper.parentNode) {
                    wrapper.parentNode.removeChild(wrapper);
                    console.log('Component deleted:', instanceId);
                    alert('✅ Component deleted successfully!');

                    // Also remove the associated dropdown menu from body
                    const dropdown = document.getElementById(`menu-${instanceId}`);
                    if (dropdown && dropdown.parentNode) {
                        dropdown.parentNode.removeChild(dropdown);
                        console.log('Dropdown menu removed:', dropdown.id);
                    }
                } else {
                    console.error('Component has no parent node');
                    alert('Failed to delete component: No parent node');
                }

            } catch (error) {
                console.error('Failed to delete component:', error);
                alert('Failed to delete component: ' + error.message);
            }
        }

        // Make functions available globally for inline onclick handlers
        window.toggleComponentMenu = toggleComponentMenu;
        window.handleComponentAction = handleComponentAction;
        window.copyComponent = copyComponent;
        window.pasteComponent = pasteComponent;
        window.deleteComponent = deleteComponent;

        // ===========================================================================
        // End Component Menu System
        // ===========================================================================

        // Edit a Mustache template instance
        function editMustacheTemplateInstance(instanceId) {
            console.log('Editing template instance:', instanceId);

            // Find the template wrapper in the document
            const wrapper = document.querySelector(`[data-template-instance="${instanceId}"]`);
            if (!wrapper) {
                console.error('Template instance not found:', instanceId);
                alert('Template not found in document. It may have been removed.');
                return;
            }

            // Extract template metadata
            const templateId = wrapper.getAttribute('data-template-id');
            const varsJson = wrapper.getAttribute('data-template-vars');
            let currentData = {};

            try {
                currentData = JSON.parse(varsJson || '{}');
            } catch (error) {
                console.error('Failed to parse template variables:', error);
                currentData = {};
            }

            // Show the template editor
            showTemplateEditor(templateId, instanceId, currentData);
        }

        // Make function available globally for inline onclick handlers
        window.editMustacheTemplateInstance = editMustacheTemplateInstance;

        // Show template editor modal for editing variables
        function showTemplateEditor(templateId, instanceId, currentData = {}) {
            // Use window.templateRegistry first, fallback to templateRegistry
            const registry = window.templateRegistry || templateRegistry;
            const templateInfo = registry[templateId];
            if (!templateInfo) {
                console.error('Template not found:', templateId);
                alert(`Template "${templateId}" not found in registry`);
                return;
            }

            // Create modal HTML with form fields for each variable
            const variables = templateInfo.variables || {};
            const formFields = Object.entries(variables).map(([key, defaultValue]) => {
                const currentValue = currentData[key] !== undefined ? currentData[key] : defaultValue;
                const valueStr = typeof currentValue === 'object' ? JSON.stringify(currentValue, null, 2) : currentValue;

                return `
                    <div class="form-group" style="margin-bottom: 15px;">
                        <label for="template-var-${key}" style="display: block; margin-bottom: 5px; font-weight: bold;">
                            ${key}
                            <span style="font-weight: normal; color: #666; font-size: 12px;">
                                (default: ${typeof defaultValue === 'object' ? JSON.stringify(defaultValue) : defaultValue})
                            </span>
                        </label>
                        ${typeof defaultValue === 'object' ?
                            `<textarea id="template-var-${key}"
                                      class="form-control"
                                      style="width: 100%; min-height: 100px; font-family: monospace;"
                                      placeholder="Enter JSON for ${key}">${valueStr}</textarea>` :
                            `<input type="text"
                                   id="template-var-${key}"
                                   class="form-control"
                                   style="width: 100%;"
                                   value="${escapeHtml(String(valueStr))}">`
                        }
                    </div>
                `;
            }).join('');

            const modalHtml = `
                <div id="template-editor-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000; display: flex; align-items: center; justify-content: center;">
                    <div style="background: white; border-radius: 8px; width: 90%; max-width: 600px; max-height: 80vh; overflow-y: auto; padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <h2 style="margin: 0;">✏️ Edit Template: ${templateInfo.name}</h2>
                            <button id="close-template-editor" style="background: none; border: none; font-size: 24px; cursor: pointer;">×</button>
                        </div>

                        <p>Edit the template variables below. Changes will update the template in the editor.</p>

                        <div id="template-editor-form" style="margin: 20px 0;">
                            ${formFields || '<p>This template has no editable variables.</p>'}
                        </div>

                        <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd;">
                            <button id="cancel-template-edit" class="btn btn-secondary">Cancel</button>
                            <button id="save-template-edit" class="btn btn-primary" style="background: #6f42c1; border-color: #6f42c1;">Save Changes</button>
                        </div>
                    </div>
                </div>
            `;

            // Remove any existing template editor modal
            const existingModal = document.getElementById('template-editor-modal');
            if (existingModal) existingModal.remove();

            // Add modal to document
            document.body.insertAdjacentHTML('beforeend', modalHtml);

            // Setup event handlers
            document.getElementById('close-template-editor').addEventListener('click', closeTemplateEditor);
            document.getElementById('cancel-template-edit').addEventListener('click', closeTemplateEditor);
            document.getElementById('save-template-edit').addEventListener('click', () => {
                saveTemplateChanges(templateId, instanceId);
            });
        }

        // Save template changes from editor
        function saveTemplateChanges(templateId, instanceId) {
            // Use window.templateRegistry first, fallback to templateRegistry
            const registry = window.templateRegistry || templateRegistry;
            const templateInfo = registry[templateId];
            if (!templateInfo) return;

            const variables = templateInfo.variables || {};
            const newData = {};

            // Collect values from form fields
            Object.keys(variables).forEach(key => {
                const input = document.getElementById(`template-var-${key}`);
                if (!input) return;

                const defaultValue = variables[key];
                const value = input.value.trim();

                if (typeof defaultValue === 'object') {
                    // Parse JSON for object values
                    try {
                        newData[key] = value ? JSON.parse(value) : defaultValue;
                    } catch (error) {
                        console.error(`Failed to parse JSON for ${key}:`, error);
                        alert(`Invalid JSON for ${key}. Please check your syntax.`);
                        throw error; // Stop saving
                    }
                } else {
                    // Convert string values to appropriate type
                    if (typeof defaultValue === 'number') {
                        newData[key] = value ? Number(value) : defaultValue;
                    } else if (typeof defaultValue === 'boolean') {
                        newData[key] = value ? value.toLowerCase() === 'true' : defaultValue;
                    } else {
                        newData[key] = value || defaultValue;
                    }
                }
            });

            console.log('Saving template changes:', { templateId, instanceId, newData });

            // Update the template instance
            updateMustacheTemplateInstance(instanceId, newData);

            // Close the editor
            closeTemplateEditor();
        }

        // Update a template instance with new data
        function updateMustacheTemplateInstance(instanceId, newData) {
            console.log('Updating template instance:', instanceId, newData);

            // Find the template wrapper
            const wrapper = document.querySelector(`[data-template-instance="${instanceId}"]`);
            if (!wrapper) {
                console.error('Template instance not found for update:', instanceId);
                return;
            }

            const templateId = wrapper.getAttribute('data-template-id');

            // Re-render the template with new data
            const rendered = renderMustacheTemplate(templateId, newData);

            // Create new wrapper HTML (keeping the same instance ID)
            const newWrapperHtml = `
                <div class="webbot-mustache-template"
                     data-template-id="${templateId}"
                     data-template-instance="${instanceId}"
                     data-template-vars="${escapeHtml(JSON.stringify(newData))}"
                     style="position: relative; border: 1px dashed #ccc; margin: 10px 0; padding: 10px;">

                    <!-- Edit button -->
                    <div class="template-edit-button"
                         style="position: absolute; top: -10px; right: -10px; background: #6f42c1; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 12px; z-index: 100; opacity: 0; transition: opacity 0.2s;"
                         onclick="window.editMustacheTemplateInstance('${instanceId}')"
                         title="Edit template">
                        ✏️
                    </div>

                    <!-- Template content -->
                    ${rendered}

                    <!-- Template info badge -->
                    <div style="font-size: 11px; color: #666; text-align: right; margin-top: 5px; padding-top: 5px; border-top: 1px dashed #eee;">
                        🥕 ${(window.templateRegistry || templateRegistry)[templateId]?.name || templateId} (edited)
                    </div>
                </div>
            `;

            // Replace the wrapper in TinyMCE editor
            if (window.tinymce && window.tinymce.activeEditor) {
                const editor = window.tinymce.activeEditor;
                const wrapperNode = editor.dom.select(`[data-template-instance="${instanceId}"]`)[0];

                if (wrapperNode) {
                    // Create a temporary container for the new HTML
                    const tempDiv = editor.dom.create('div', {}, newWrapperHtml);

                    // Replace the old wrapper with new content
                    wrapperNode.parentNode.replaceChild(tempDiv, wrapperNode);

                    console.log('Template instance updated:', instanceId);

                    // Re-initialize WET-BOEW
                    setTimeout(() => {
                        if (typeof initializeWETBOEW === 'function') {
                            initializeWETBOEW();
                        }
                    }, 100);
                } else {
                    console.error('Template instance not found in TinyMCE DOM');
                }
            } else {
                console.error('TinyMCE editor not available for update');
            }
        }

        // Close template editor modal
        function closeTemplateEditor() {
            const modal = document.getElementById('template-editor-modal');
            if (modal) {
                modal.remove();
                console.log('Template editor modal closed');
            } else {
                console.warn('Template editor modal not found');
            }
        }

        // Make function available globally
        window.addTemplateButtonToUI = addTemplateButtonToUI;

        // Initialize template button with retry logic
        function initializeTemplateButtonWhenReady() {
            // Initialize retry counter if not exists
            if (typeof initializeTemplateButtonWhenReady.retryCount === 'undefined') {
                initializeTemplateButtonWhenReady.retryCount = 0;
            }

            // Check max retries (8 attempts = ~4 seconds)
            if (initializeTemplateButtonWhenReady.retryCount >= 8) {
                console.error('❌ Failed to initialize template button after 8 retries');
                console.error('Possible causes:');
                console.error('1. Component button not found (ID: insert-component-btn)');
                console.error('2. Mustache.js failed to load');
                console.error('3. DOM structure changed');
                console.error('Check console for detailed error messages');
                return;
            }

            console.log('initializeTemplateButtonWhenReady called (attempt ' + (initializeTemplateButtonWhenReady.retryCount + 1) + '/8)');

            if (addTemplateButtonToUI()) {
                console.log('✅ Mustache.js template system initialized');
            } else {
                // Retry every 500ms until successful
                console.log('Template button not ready yet, retrying in 500ms...');
                initializeTemplateButtonWhenReady.retryCount++;
                setTimeout(initializeTemplateButtonWhenReady, 500);
            }
        }

        // ===========================================================================
        // Quick Edit HTML - AI & Command-driven inline HTML editing
        // ===========================================================================

        /**
         * Find the closest meaningful container element at cursor position.
         * Walks up from the current selection to find:
         *   1. webbot-component-wrapper / data-template-instance (component)
         *   2. webbot-component / data-html-content (inline component)
         *   3. section, article, nav, footer, main, aside with classes
         *   4. div with gc- class (Canada.ca pattern)
         *   5. div with any class (generic block)
         *   6. editor body as fallback
         */
        function findTargetElement() {
            const editor = tinyMceEditor || window.tinyMceEditor;
            if (!editor) return null;

            const node = editor.selection.getNode();
            const body = editor.getBody();

            let target = node;
            while (target && target !== body) {
                const tag = (target.tagName || '').toLowerCase();
                const cls = (target.className || '').trim();

                // 1. Component wrapper (has menu, edit, delete)
                if (target.classList && (target.classList.contains('webbot-component-wrapper') ||
                    target.hasAttribute('data-template-instance') ||
                    target.hasAttribute('data-component-id'))) {
                    return target;
                }

                // 2. Inline component marker
                if (target.classList && target.classList.contains('webbot-component') ||
                    target.hasAttribute && target.hasAttribute('data-html-content')) {
                    return target;
                }

                // 3. Semantic HTML5 containers with classes
                if (/^(section|article|nav|footer|header|main|aside|figure)$/.test(tag) && cls) {
                    return target;
                }

                // 4. Canada.ca gc- prefixed containers
                if (tag === 'div' && cls && /\bgc-/.test(cls)) {
                    return target;
                }

                // 5. Any block-level element with a class or id
                if (/^(div|p|table|ul|ol|blockquote|form)$/.test(tag) && (cls || target.id)) {
                    return target;
                }

                target = target.parentNode;
            }

            // Fallback: return the element right after body's first text wrapper
            return body;
        }

        /**
         * Get a short human-readable locator string for the target element
         */
        function getElementLocator(el) {
            if (!el) return '';
            const tag = (el.tagName || '').toLowerCase();
            const id = el.id ? '#' + el.id : '';
            const cls = (el.className || '').trim();
            const classStr = cls ? '.' + cls.replace(/\s+/g, '.') : '';
            // Truncate if too long
            const loc = tag + id + classStr;
            return loc.length > 60 ? loc.substring(0, 57) + '...' : loc;
        }

        /**
         * Store the element being edited and the TinyMCE WYSIWYG editor instance
         */
        let _editingHTMLTarget = null;
        let _wysiwygEditor = null;
        let _editMode = 'code'; // 'code' or 'wysiwyg'

        /**
         * Open Quick Edit modal - "edit HTML" triggers code mode, "edit component" triggers WYSIWYG
         */
        function showCurrentElementHTMLEdit(mode) {
            if (mode === undefined || mode === null) mode = 'code';
            const editor = tinyMceEditor || window.tinyMceEditor;
            if (!editor) {
                alert('Editor not initialized');
                return;
            }

            const target = findTargetElement();
            if (!target) {
                alert('Could not find a target element at cursor position.');
                return;
            }

            if (target === editor.getBody()) {
                const selContent = editor.selection.getContent();
                if (selContent) {
                    editor.selection.setContent('<div class="quick-edit-block">' + selContent + '</div>');
                    const node = editor.selection.getNode();
                    const wrapper = node.classList && node.classList.contains('quick-edit-block') ? node :
                        node.closest ? node.closest('.quick-edit-block') : node;
                    if (wrapper) {
                        showHTMLEditModal(wrapper, mode);
                        return;
                    }
                }
                alert('Place your cursor inside or select the HTML content you want to edit.');
                return;
            }

            showHTMLEditModal(target, mode);
        }

        /** Shorthand for WYSIWYG mode (component editing) */
        function showCurrentElementWYSIWYGEdit() {
            showCurrentElementHTMLEdit('wysiwyg');
        }

        /**
         * Show the HTML edit modal - code mode = dark textarea, wysiwyg mode = TinyMCE (no Canada theme)
         */
        function showHTMLEditModal(targetElement, mode) {
            const modal = document.getElementById('html-edit-modal');
            const textarea = document.getElementById('html-edit-textarea');
            const wysiwygContainer = document.getElementById('html-edit-wysiwyg');
            const location = document.getElementById('html-edit-location');
            const status = document.getElementById('html-edit-status');
            const title = document.getElementById('html-edit-mode-title');
            const badge = document.getElementById('html-edit-mode-badge');
            const label = document.getElementById('html-edit-mode-label');

            if (!modal || !textarea || !wysiwygContainer) {
                console.error('HTML edit modal not found in DOM');
                return;
            }

            mode = mode || 'code';
            _editMode = mode;
            _editingHTMLTarget = targetElement;

            // Destroy any previous WYSIWYG instance
            if (_wysiwygEditor) {
                try { _wysiwygEditor.remove(); } catch(e) {}
                _wysiwygEditor = null;
            }
            wysiwygContainer.innerHTML = '';

            const html = (targetElement.outerHTML || targetElement.innerHTML || '').trim();
            const loc = getElementLocator(targetElement);
            location.textContent = loc;
            location.title = loc;
            if (status) { status.textContent = ''; status.className = 'html-edit-status'; }

            // Configure UI for mode
            if (mode === 'wysiwyg') {
                title.innerHTML = '<span>🎨</span> Component Editor';
                badge.textContent = 'WYSIWYG';
                badge.className = 'html-edit-mode-badge mode-wysiwyg';
                if (label) label.innerHTML = 'Edit visually (flat layout, no Canada.ca theme). Use <strong>Code</strong> button in toolbar for raw HTML.';
                textarea.style.display = 'none';
                wysiwygContainer.style.display = 'block';
            } else {
                title.innerHTML = '<span>✏️</span> HTML Editor';
                badge.textContent = 'CODE';
                badge.className = 'html-edit-mode-badge mode-code';
                if (label) label.textContent = 'Edit raw HTML. Ctrl+Enter to save, Esc to close.';
                wysiwygContainer.style.display = 'none';
                textarea.style.display = 'block';
                textarea.value = html
                    .replace(/>\s*</g, '>\n<')
                    .replace(/<\/(div|section|article|nav|footer|header|main|aside|table|tr|td|th|ul|ol|li|p|figure|form|blockquote)>/g, (m) => m + '\n')
                    .replace(/<\/(h[1-6]|span|a|strong|em|br \/?)>/g, (m) => m + '\n')
                    .replace(/(\n\s*)+/g, '\n')
                    .trim();
            }

            // Show modal
            modal.classList.add('show');
            modal.style.display = 'flex';
            document.body.classList.add('html-edit-modal-open');

            if (mode === 'code') {
                setTimeout(() => { textarea.focus(); textarea.select(); }, 100);
            } else {
                // Initialize TinyMCE with NO Canada.ca CSS
                void wysiwygContainer.offsetHeight; // force layout
                const editorDiv = document.createElement('div');
                editorDiv.id = 'wysiwyg-editor-inline';
                editorDiv.innerHTML = html;
                wysiwygContainer.appendChild(editorDiv);
                void wysiwygContainer.offsetHeight;

                // Force TinyMCE floating elements above modal backdrop
                if (!document.getElementById('tox-zindex-fix')) {
                    var s = document.createElement('style');
                    s.id = 'tox-zindex-fix';
                    s.textContent = '.html-edit-modal-open .tox-dialog-wrap,' +
                        '.html-edit-modal-open .tox-menu,' +
                        '.html-edit-modal-open .tox-pop,' +
                        '.html-edit-modal-open .tox-pop__dialog,' +
                        '.html-edit-modal-open .tox-notifications-container{z-index:2147483647!important}' +
                        '.html-edit-modal-open #wysiwyg-editor-container .tox-tinymce{display:none!important}';                    document.head.appendChild(s);
                }

                tinymce.init({
                    selector: '#wysiwyg-editor-inline',
                    height: 450,
                    menubar: 'edit view insert format table help',
                    base_url: '/gcweb/external/tinymce/tinymce/js/tinymce/',
                    zIndex: 100000,
                    contextmenu: 'link image table',
                    plugins: [
                        'advlist', 'autolink', 'lists', 'link', 'image', 'charmap', 'preview',
                        'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
                        'insertdatetime', 'media', 'table', 'help', 'wordcount'
                    ],
                    toolbar: 'undo redo | styleselect | bold italic underline | ' +
                             'alignleft aligncenter alignright alignjustify | ' +
                             'bullist numlist outdent indent | link image table | ' +
                             'blockquote | code fullscreen | help',
                    content_style: 'body { font-family: Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.5; color: #333; padding: 16px; margin: 0; background: #fff; } ' +
                        'p { margin: 0 0 1em; } ' +
                        'h1, h2, h3, h4, h5, h6 { margin: 1em 0 0.5em; font-weight: 600; } ' +
                        'ul, ol { margin: 0 0 1em 2em; } ' +
                        'table { border-collapse: collapse; width: 100%; margin: 1em 0; } ' +
                        'td, th { border: 1px solid #ccc; padding: 8px; } ' +
                        'th { background: #f5f5f5; font-weight: 600; } ' +
                        'img { max-width: 100%; height: auto; } ' +
                        'blockquote { border-left: 3px solid #ddd; padding-left: 16px; margin-left: 0; color: #666; } ' +
                        'a { color: #1a73e8; } ' +
                        '* { box-sizing: border-box; }',
                    content_css: [],
                    extended_valid_elements: '*[*]',
                    cleanup: false,
                    valid_elements: '*[*]',
                    allow_html_in_named_anchor: true,
                    image_advtab: true,
                    image_dimensions: true,
                    image_title: true,
                    image_caption: true,
                    object_resizing: 'img',
                    setup: function(editor) {
                        _wysiwygEditor = editor;
                        editor.addShortcut('ctrl+enter', 'Save', function() { saveHTMLEdit(); });
                        editor.addShortcut('meta+enter', 'Save', function() { saveHTMLEdit(); });
                        editor.on('init', function() {
                            setTimeout(function() { editor.focus(); }, 200);
                        });
                        // MutationObserver: catch TinyMCE dialog elements and force z-index
                        if (!window._toxZobserver) {
                            window._toxZobserver = new MutationObserver(function(muts) {
                                muts.forEach(function(m) {
                                    m.addedNodes.forEach(function(n) {
                                        if (n.nodeType === 1) {
                                            if (n.matches && n.matches('.tox-dialog-wrap,.tox-menu,.tox-pop,.tox-pop__dialog,.tox-notifications-container')) {
                                                n.style.setProperty('z-index', '2147483647', 'important');
                                            }
                                            if (n.querySelectorAll) {
                                                n.querySelectorAll('.tox-dialog-wrap,.tox-menu,.tox-pop,.tox-pop__dialog,.tox-notifications-container').forEach(function(el) {
                                                    el.style.setProperty('z-index', '2147483647', 'important');
                                                });
                                            }
                                        }
                                    });
                                });
                            });
                            window._toxZobserver.observe(document.body, { childList: true, subtree: true });
                        }
                    }
                });
            }

            console.log(`✏️ ${mode === 'wysiwyg' ? 'WYSIWYG' : 'Code'} editor opened for element:`, loc);
        }

        /**
         * Save the edited HTML back to the main editor (works for both code and wysiwyg modes)
         */
        function saveHTMLEdit() {
            const editor = tinyMceEditor || window.tinyMceEditor;
            const status = document.getElementById('html-edit-status');

            if (!editor || !_editingHTMLTarget) {
                console.error('Cannot save: missing editor or target');
                return;
            }

            let newHTML;
            if (_editMode === 'wysiwyg') {
                if (!_wysiwygEditor) {
                    console.error('WYSIWYG editor instance not found');
                    return;
                }
                newHTML = _wysiwygEditor.getContent().trim();
            } else {
                const textarea = document.getElementById('html-edit-textarea');
                if (!textarea) {
                    console.error('Textarea not found');
                    return;
                }
                newHTML = textarea.value.trim();
            }

            if (!newHTML) {
                if (status) {
                    status.textContent = '⚠️ HTML content cannot be empty';
                    status.className = 'html-edit-status error';
                }
                return;
            }

            try {
                const target = _editingHTMLTarget;
                const tempDiv = editor.getDoc().createElement('div');
                tempDiv.innerHTML = newHTML;

                if (tempDiv.children.length === 1) {
                    const newEl = tempDiv.children[0];
                    target.parentNode.replaceChild(newEl, target);
                } else if (tempDiv.children.length > 1) {
                    const fragment = editor.getDoc().createDocumentFragment();
                    while (tempDiv.firstChild) {
                        fragment.appendChild(tempDiv.firstChild);
                    }
                    target.parentNode.replaceChild(fragment, target);
                } else {
                    target.innerHTML = newHTML;
                }

                editor.undoManager.add();
                editor.fire('Change');

                if (status) {
                    status.textContent = '✅ Updated successfully!';
                    status.className = 'html-edit-status success';
                }

                console.log(`✅ ${_editMode === 'wysiwyg' ? 'WYSIWYG' : 'Code'} edit saved successfully`);
                setTimeout(() => { closeHTMLEditModal(); }, 600);

            } catch (error) {
                console.error('Failed to save HTML edit:', error);
                if (status) {
                    status.textContent = '❌ Error: ' + error.message;
                    status.className = 'html-edit-status error';
                }
            }
        }

        /**
         * Close the modal and destroy any editor instance
         */
        function closeHTMLEditModal() {
            if (_wysiwygEditor) {
                try { _wysiwygEditor.remove(); } catch(e) {}
                _wysiwygEditor = null;
            }
            const container = document.getElementById('html-edit-wysiwyg');
            if (container) { container.innerHTML = ''; }

            const modal = document.getElementById('html-edit-modal');
            if (modal) {
                modal.classList.remove('show');
                modal.style.display = 'none';
            document.body.classList.remove('html-edit-modal-open');
            }
            _editingHTMLTarget = null;
            _editMode = 'code';
        }

        // Bind modal event handlers
        document.addEventListener('DOMContentLoaded', function() {
            const modal = document.getElementById('html-edit-modal');
            if (!modal) return;

            document.getElementById('html-edit-modal-close')?.addEventListener('click', closeHTMLEditModal);
            document.getElementById('html-edit-cancel')?.addEventListener('click', closeHTMLEditModal);
            document.getElementById('html-edit-save')?.addEventListener('click', saveHTMLEdit);

            document.addEventListener('keydown', function(e) {
                const modalEl = document.getElementById('html-edit-modal');
                if (e.key === 'Escape' && modalEl && modalEl.classList.contains('show')) {
                    // Don't close if WYSIWYG code panel is open (TinyMCE handles its own Escape)
                    if (_editMode === 'code') {
                        e.preventDefault();
                        closeHTMLEditModal();
                    }
                }
            });

            // Close on backdrop click
            modal.addEventListener('click', function(e) {
                if (e.target === modal) closeHTMLEditModal();
            });
        });

        // Globals
        window.showCurrentElementHTMLEdit = showCurrentElementHTMLEdit;
        window.showCurrentElementWYSIWYGEdit = showCurrentElementWYSIWYGEdit;
        window.closeHTMLEditModal = closeHTMLEditModal;

        // ===========================================================================
        // End Quick Edit HTML
        // ===========================================================================

        // Initialize template system when document is ready
        $(document).ready(function() {
            // Wait a bit for everything to load, then start retry logic
            setTimeout(() => {
                console.log('Starting template button initialization...');
                initializeTemplateButtonWhenReady();
            }, 1000);
        });

        // Add template command to AI assistant
        if (window.aiAssistantCommands) {
            window.aiAssistantCommands.template = {
                name: 'template',
                description: 'Insert a Mustache template',
                usage: '/template [template-id]',
                execute: function(args) {
                    if (args.length === 0) {
                        // No template ID specified, show selector
                        showTemplateSelector();
                        return 'Opening template selector...';
                    } else {
                        const templateId = args[0];
                        insertMustacheTemplate(templateId);
                        return `Inserted template: ${templateId}`;
                    }
                }
            };
            console.log('Template command added to AI assistant');

            // Add HTML quick edit command (code mode)
            window.aiAssistantCommands.html = {
                name: 'html',
                description: 'Edit HTML source code at cursor position',
                usage: '/html',
                execute: function(args) {
                    if (typeof showCurrentElementHTMLEdit === 'function') {
                        showCurrentElementHTMLEdit('code');
                        return 'Opened raw HTML editor for the element at cursor position.';
                    } else {
                        return 'Error: HTML edit function not available.';
                    }
                }
            };
            window.aiAssistantCommands["edit-html"] = {
                name: 'edit-html',
                description: 'Edit HTML source code at cursor position',
                usage: '/edit-html',
                execute: function(args) {
                    return window.aiAssistantCommands.html.execute(args);
                }
            };

            // Add component edit command (WYSIWYG mode)
            window.aiAssistantCommands["edit-component"] = {
                name: 'edit-component',
                description: 'Edit component visually with WYSIWYG editor (flat layout, no Canada theme)',
                usage: '/edit-component',
                execute: function(args) {
                    if (typeof showCurrentElementWYSIWYGEdit === 'function') {
                        showCurrentElementWYSIWYGEdit();
                        return 'Opened WYSIWYG component editor for the element at cursor position.';
                    } else {
                        return 'Error: Component edit function not available.';
                    }
                }
            };
            window.aiAssistantCommands["component"] = {
                name: 'component',
                description: 'Edit component visually with WYSIWYG editor',
                usage: '/component',
                execute: function(args) {
                    return window.aiAssistantCommands["edit-component"].execute(args);
                }
            };
            // Add color change command
            window.aiAssistantCommands.color = {
                name: 'color',
                description: 'Change the color of a component at cursor position',
                usage: '/color [red|green|blue|yellow]',
                execute: function(args) {
                    if (!window.CanadaColorManager) {
                        return 'Error: Color manager not loaded. Please refresh the page.';
                    }

                    if (args.length === 0) {
                        // Describe current component and available colors
                        const desc = window.CanadaColorManager.describeCurrent();
                        return desc;
                    }

                    const colorName = args.join(' ');
                    const comp = window.CanadaColorManager.getCurrentComponent();
                    if (!comp) {
                        return 'Please place your cursor on a component first (click on a button, alert, etc.), then try again.';
                    }

                    const result = window.CanadaColorManager.changeColor(comp.element, colorName);
                    if (result.success) {
                        return result.display;
                    } else {
                        return result.error || `Cannot change to "${colorName}". ${result.available ? 'Available colors: ' + result.available.join(', ') : ''}`;
                    }
                }
            };
            console.log('🎨 Color command added to AI assistant');

            // Add open/details command
            window.aiAssistantCommands.open = {
                name: 'open',
                description: 'Make a <details> element open by adding open="true"',
                usage: '/open',
                execute: function(args) {
                    if (!window.CanadaColorManager) {
                        return 'Error: Color/component manager not loaded. Please refresh the page.';
                    }
                    var result = window.CanadaColorManager.makeOpen();
                    if (result.success) {
                        return result.display;
                    } else {
                        return result.error || 'Could not open the details element.';
                    }
                }
            };
            console.log('🔓 /open command added to AI assistant');

            // Add close/details command
            window.aiAssistantCommands.close = {
                name: 'close',
                description: 'Close a <details> element by removing open="true"',
                usage: '/close',
                execute: function(args) {
                    if (!window.CanadaColorManager) {
                        return 'Error: Color/component manager not loaded. Please refresh the page.';
                    }
                    var result = window.CanadaColorManager.makeClose();
                    if (result.success) {
                        return result.display;
                    } else {
                        return result.error || 'Could not close the details element.';
                    }
                }
            };
            console.log('🔒 /close command added to AI assistant');
        }

        // ============================================================
        // Resource Sidebar Module - Images, Documents, Components, etc.
        // ============================================================

        (function initResourceSidebar() {
            const resourceTypeSelect = document.getElementById('resource-type-select');
            const pathInput = document.getElementById('resource-path-input');
            const searchInput = document.getElementById('resource-search-input');
            const searchBtn = document.getElementById('resource-search-btn');
            const resultsEl = document.getElementById('resource-results');

            if (!resourceTypeSelect || !resultsEl) return;

            // Get current page path for default search
            function getCurrentPathPrefix() {
                // Priority 1: Already resolved file_path from getEffectiveFilePath
                if (window.currentFileBotFolder) {
                    return window.currentFileBotFolder;
                }
                // Priority 2: currentPageData (from API)
                if (currentPageData) {
                    if (currentPageData.metadata && currentPageData.metadata.file_path) return currentPageData.metadata.file_path;
                    if (currentPageData.file_path) return currentPageData.file_path;
                }
                // Priority 3: the left path label element
                const pathDisplay = document.getElementById('file-path-display');
                if (pathDisplay && pathDisplay.textContent && pathDisplay.textContent !== 'No page selected') {
                    return pathDisplay.textContent.trim();
                }
                return '';
            }

            // Set default path from current page
            function updateDefaultPath() {
                var path = getCurrentPathPrefix();
                if (path) {
                    pathInput.value = path;
                }
            }

            // Trigger search
            function doSearch() {
                var type = resourceTypeSelect.value;
                var pathVal = pathInput.value.trim();
                var titleVal = searchInput.value.trim();

                resultsEl.innerHTML = '<div class="resource-loading">⏳ Searching...</div>';

                switch (type) {
                    case 'images':
                        searchImages(pathVal, titleVal);
                        break;
                    case 'documents':
                        searchDocuments(pathVal, titleVal);
                        break;
                    case 'components':
                        searchComponents(pathVal, titleVal);
                        break;
                    case 'templates':
                        searchTemplates(pathVal, titleVal);
                        break;
                    case 'pages':
                        searchPages(pathVal, titleVal);
                        break;
                }
            }

            // -------- Images --------
            async function searchImages(pathVal, titleVal) {
                try {
                    var url = '/api/v1/search/documents?limit=200&mime_type=image%';
                    if (pathVal) {
                        // DB paths need /boarding prefix (e.g. /boarding/canadasite/content/dam/...)
                        // metadata.file_path is stored as /canadasite/content/dam/canada
                        var cleanPath = pathVal;
                        if (cleanPath.indexOf('/') !== 0) {
                            cleanPath = '/' + cleanPath;
                        }
                        if (cleanPath.indexOf('/boarding') !== 0) {
                            // Prepend /boarding for DB path matching
                            if (cleanPath.indexOf('/canadasite') === 0) {
                                cleanPath = '/boarding' + cleanPath;
                            } else {
                                cleanPath = '/boarding/canadasite' + cleanPath;
                            }
                        }
                        url += '&path=' + encodeURIComponent(cleanPath);
                    }
                    if (titleVal) {
                        url += '&title=' + encodeURIComponent(titleVal);
                    }

                    var resp = await fetch(url);
                    if (!resp.ok) throw new Error('HTTP ' + resp.status);
                    var data = await resp.json();
                    renderImageResults(data.documents || []);
                } catch (e) {
                    resultsEl.innerHTML = '<div class="resource-error">❌ Error: ' + e.message + '</div>';
                }
            }

            function renderImageResults(docs) {
                if (!docs || docs.length === 0) {
                    resultsEl.innerHTML = '<div class="resource-empty">🔍 No images found.</div>';
                    return;
                }

                // Filter to only image-like mime types (extra safety)
                docs = docs.filter(function(d) {
                    var mt = (d.mime_type || '').toLowerCase();
                    return mt.indexOf('image') >= 0;
                });

                if (docs.length === 0) {
                    resultsEl.innerHTML = '<div class="resource-empty">🔍 No images found.</div>';
                    return;
                }

                // Helper: convert storage_path to DAM proxy URL
                function pathToDamUrl(storagePath) {
                    // storage_path: 'boarding/canadasite/content/dam/canada/...'
                    // DAM proxy URL: '/content/dam/canada/...'
                    // Strip 'boarding/canadasite' or just 'boarding/' prefix
                    if (!storagePath) return '';
                    // Find 'canada/' or 'content/dam/canada/' in path
                    var idx = storagePath.indexOf('canada/');
                    if (idx >= 0) {
                        return '/content/dam/' + storagePath.substring(idx);
                    }
                    // Fallback: strip leading boarding/canadasite/
                    return '/content/dam/' + storagePath.replace(/^boarding\/?/, '').replace(/^canadasite\/?/, '');
                }

                let html = '<div class="image-grid">';
                docs.forEach(function(doc) {
                    var storagePath = doc.storage_path || doc.path || '';
                    var damUrl = pathToDamUrl(storagePath);
                    var filename = doc.original_filename || doc.title || 'image';
                    var fileSize = doc.file_size;
                    html += '<div class="image-card" data-url="' + damUrl + '" data-filename="' + filename + '">';
                    html += '<div class="image-card-thumb">';
                    html += '<img src="' + damUrl + '" alt="' + filename + '" loading="lazy">';
                    html += '</div>';
                    html += '<div class="image-card-info">';
                    html += '<span class="image-card-name" title="' + filename + '">' + filename + '</span>';
                    html += '<span class="image-card-size">' + formatFileSize(fileSize) + '</span>';
                    html += '</div>';
                    html += '<button class="image-insert-btn" title="Insert into editor">➕</button>';
                    html += '</div>';
                });
                html += '</div>';

                resultsEl.innerHTML = html;

                // Bind click events for insert buttons
                resultsEl.querySelectorAll('.image-insert-btn').forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        var card = btn.closest('.image-card');
                        var url = card.dataset.url;
                        var filename = card.dataset.filename;
                        insertImageToEditor(url, filename);
                    });
                });

                // Click full card = insert
                resultsEl.querySelectorAll('.image-card').forEach(function(card) {
                    card.addEventListener('click', function() {
                        var url = card.dataset.url;
                        var filename = card.dataset.filename;
                        insertImageToEditor(url, filename);
                    });
                });
            }

            function insertImageToEditor(url, filename) {
                var editor = window.tinyMceEditor;
                if (editor) {
                    editor.insertContent('<img src="' + url + '" alt="' + filename + '">');
                    // Show brief flash feedback
                    var btn = resultsEl.querySelector('.image-card[data-url="' + url + '"] .image-insert-btn');
                    if (btn) {
                        btn.textContent = '✅';
                        btn.classList.add('inserted');
                        setTimeout(function() {
                            if (btn) {
                                btn.textContent = '➕';
                                btn.classList.remove('inserted');
                            }
                        }, 1500);
                    }
                } else {
                    alert('Editor not initialized. Please wait and try again.');
                }
            }

            // -------- Documents (PDF, Word, Excel, etc.) --------
            async function searchDocuments(pathVal, titleVal) {
                try {
                    // Filter common document types: PDF, Word, Excel, PowerPoint, text
                    var mimeFilter = 'application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation,text/plain';
                    var url = '/api/v1/search/documents?limit=200&mime_type=' + encodeURIComponent(mimeFilter);
                    if (pathVal) {
                        var cleanPath = pathVal;
                        if (cleanPath.indexOf('/') !== 0) {
                            cleanPath = '/' + cleanPath;
                        }
                        if (cleanPath.indexOf('/boarding') !== 0) {
                            if (cleanPath.indexOf('/canadasite') === 0) {
                                cleanPath = '/boarding' + cleanPath;
                            } else {
                                cleanPath = '/boarding/canadasite' + cleanPath;
                            }
                        }
                        url += '&path=' + encodeURIComponent(cleanPath);
                    }
                    if (titleVal) {
                        url += '&title=' + encodeURIComponent(titleVal);
                    }

                    var resp = await fetch(url);
                    if (!resp.ok) throw new Error('HTTP ' + resp.status);
                    var data = await resp.json();
                    renderDocumentResults(data.documents || []);
                } catch (e) {
                    resultsEl.innerHTML = '<div class="resource-error">❌ Error: ' + e.message + '</div>';
                }
            }

            function renderDocumentResults(docs) {
                if (!docs || docs.length === 0) {
                    resultsEl.innerHTML = '<div class="resource-empty">📄 No documents found. Try a different path or title.</div>';
                    return;
                }

                // Filter to only document-like mime types
                var docMimes = ['pdf','msword','openxmlformats','ms-excel','ms-powerpoint','spreadsheetml','presentationml','text/plain','application/octet-stream'];
                docs = docs.filter(function(d) {
                    var mt = (d.mime_type || '').toLowerCase();
                    return docMimes.some(function(m) { return mt.indexOf(m) >= 0; });
                });

                if (docs.length === 0) {
                    resultsEl.innerHTML = '<div class="resource-empty">📄 No documents found. Try a different path or title.</div>';
                    return;
                }

                function pathToDamUrl(storagePath) {
                    if (!storagePath) return '';
                    var idx = storagePath.indexOf('canada/');
                    if (idx >= 0) {
                        return '/content/dam/' + storagePath.substring(idx);
                    }
                    return '/content/dam/' + storagePath.replace(/^boarding\/?/, '').replace(/^canadasite\/?/, '');
                }

                function getFileIcon(mimeType) {
                    var mt = (mimeType || '').toLowerCase();
                    if (mt.indexOf('pdf') >= 0) return '📕';
                    if (mt.indexOf('word') >= 0 || mt.indexOf('document') >= 0) return '📘';
                    if (mt.indexOf('excel') >= 0 || mt.indexOf('spreadsheet') >= 0) return '📗';
                    if (mt.indexOf('powerpoint') >= 0 || mt.indexOf('presentation') >= 0) return '📙';
                    return '📄';
                }

                var html = '<div class="doc-list">';
                docs.forEach(function(doc) {
                    var storagePath = doc.storage_path || doc.path || '';
                    var damUrl = pathToDamUrl(storagePath);
                    var filename = doc.original_filename || doc.title || 'document';
                    var fileSize = doc.file_size;
                    var icon = getFileIcon(doc.mime_type);

                    html += '<div class="doc-card" data-url="' + damUrl + '" data-filename="' + filename + '">';
                    html += '<div class="doc-card-icon">' + icon + '</div>';
                    html += '<div class="doc-card-info">';
                    html += '<span class="doc-card-name" title="' + filename + '">' + filename + '</span>';
                    html += '<span class="doc-card-size">' + formatFileSize(fileSize) + '</span>';
                    html += '</div>';
                    html += '<button class="doc-insert-btn" title="Insert document link into editor">🔗</button>';
                    html += '</div>';
                });
                html += '</div>';

                resultsEl.innerHTML = html;

                // Bind insert buttons
                resultsEl.querySelectorAll('.doc-insert-btn').forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        var card = btn.closest('.doc-card');
                        var url = card.dataset.url;
                        var filename = card.dataset.filename;
                        insertDocumentLink(url, filename);
                    });
                });

                // Click full card = insert
                resultsEl.querySelectorAll('.doc-card').forEach(function(card) {
                    card.addEventListener('click', function() {
                        var url = card.dataset.url;
                        var filename = card.dataset.filename;
                        insertDocumentLink(url, filename);
                    });
                });
            }

            function insertDocumentLink(url, filename) {
                var editor = window.tinyMceEditor;
                if (editor) {
                    editor.insertContent('<a href="' + url + '" target="_blank">' + filename + '</a>');
                    // Flash feedback
                    var btn = resultsEl.querySelector('.doc-card[data-url="' + url + '"] .doc-insert-btn');
                    if (btn) {
                        btn.textContent = '✅';
                        setTimeout(function() {
                            if (btn) btn.textContent = '🔗';
                        }, 1500);
                    }
                } else {
                    alert('Editor not initialized. Please wait and try again.');
                }
            }

            // -------- Components (pages under /canadasite/{lang}/components) --------
            async function searchComponents(pathVal, titleVal) {
                try {
                    var compPath = getComponentsPath();
                    if (!compPath) {
                        resultsEl.innerHTML = '<div class="resource-empty">Could not determine components path.</div>';
                        return;
                    }

                    // Override path input to show the system-determined path
                    pathInput.value = compPath;

                    var url = '/api/v1/pages/by-path/' + encodeURIComponent(compPath) + '/children';
                    if (titleVal) {
                        url += '?title=' + encodeURIComponent(titleVal);
                    }

                    var resp = await fetch(url);
                    if (!resp.ok) throw new Error('HTTP ' + resp.status);
                    var data = await resp.json();
                    renderComponentResults(data, compPath);
                } catch (e) {
                    resultsEl.innerHTML = '<div class="resource-error">❌ Error: ' + e.message + '</div>';
                }
            }

            function getComponentsPath() {
                // Derive from current page path: /canadasite/{lang}/... → /canadasite/{lang}/components
                if (currentPageData && currentPageData.path) {
                    var parts = currentPageData.path.split('/').filter(Boolean);
                    if (parts.length >= 2) {
                        return '/' + parts[0] + '/' + parts[1] + '/components';
                    }
                }
                // Fallback to English
                return '/canadasite/en/components';
            }

            function renderComponentResults(data, basePath) {
                if (!data || data.length === 0) {
                    resultsEl.innerHTML = '<div class="resource-empty">🧩 No components found under ' + basePath + '</div>';
                    return;
                }

                var html = '<div class="resource-info">🧩 ' + basePath + '</div>';
                html += '<div class="page-list">';

                var childrenMap = (typeof componentChildrenMap !== 'undefined') ? componentChildrenMap : {};

                data.forEach(function(page) {
                    var title = page.title || page.name || '(untitled)';
                    var pagePath = page.path || '';
                    var children = childrenMap[pagePath];
                    var hasChildren = children && children.length > 0;

                    if (hasChildren) {
                        // Parent component: render as expandable group (NOT insertable)
                        html += '<div class="comp-group" data-path="' + pagePath + '">';
                        html += '<div class="comp-group-header" title="Click to expand/collapse">';
                        html += '<span class="comp-group-arrow">▶</span>';
                        html += '<span class="comp-group-icon">📁</span>';
                        html += '<span class="comp-group-title">' + title + '</span>';
                        html += '</div>';
                        html += '<div class="comp-group-children" style="display:none">';

                        children.forEach(function(child) {
                            var childTitle = child.title || child.path.split('/').pop() || '(untitled)';
                            var childPath = child.path || '';
                            html += '<div class="comp-card" data-path="' + childPath + '">';
                            html += '<div class="comp-card-icon">🧩</div>';
                            html += '<div class="comp-card-info">';
                            html += '<div class="comp-card-title" title="' + childTitle + '">' + childTitle + '</div>';
                            html += '<div class="comp-card-path">' + childPath + '</div>';
                            html += '</div>';
                            html += '<button class="comp-insert-btn" title="Insert component content into editor">➕</button>';
                            html += '</div>';
                        });

                        html += '</div>'; // comp-group-children
                        html += '</div>'; // comp-group
                    } else {
                        // Leaf component: render as normal insertable card
                        html += '<div class="comp-card" data-path="' + pagePath + '">';
                        html += '<div class="comp-card-icon">🧩</div>';
                        html += '<div class="comp-card-info">';
                        html += '<div class="comp-card-title" title="' + title + '">' + title + '</div>';
                        html += '<div class="comp-card-path">' + pagePath + '</div>';
                        html += '</div>';
                        html += '<button class="comp-insert-btn" title="Insert component content into editor">➕</button>';
                        html += '</div>';
                    }
                });

                html += '</div>';
                resultsEl.innerHTML = html;

                // Bind expand/collapse for group headers
                resultsEl.querySelectorAll('.comp-group-header').forEach(function(header) {
                    header.addEventListener('click', function(e) {
                        e.stopPropagation();
                        var group = header.closest('.comp-group');
                        var childrenEl = group.querySelector('.comp-group-children');
                        var arrow = header.querySelector('.comp-group-arrow');
                        if (childrenEl.style.display === 'none') {
                            childrenEl.style.display = 'block';
                            arrow.textContent = '▼';
                        } else {
                            childrenEl.style.display = 'none';
                            arrow.textContent = '▶';
                        }
                    });
                });

                // Bind insert buttons (only on leaf comp-cards, not group headers)
                resultsEl.querySelectorAll('.comp-insert-btn').forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        var card = btn.closest('.comp-card');
                        var path = card.dataset.path;
                        insertComponentContent(path, card);
                    });
                });

                // Click full card = insert (only on leaf comp-cards, not group headers)
                resultsEl.querySelectorAll('.comp-card').forEach(function(card) {
                    card.addEventListener('click', function() {
                        var path = card.dataset.path;
                        insertComponentContent(path, card);
                    });
                });
            }

            async function insertComponentContent(pagePath, cardEl) {
                try {
                    // Flash loading state
                    if (cardEl) {
                        var btn = cardEl.querySelector('.comp-insert-btn');
                        if (btn) btn.textContent = '⏳';
                    }

                    var resp = await fetch('/api/v1/pages/by-path/' + encodeURIComponent(pagePath));
                    if (!resp.ok) throw new Error('HTTP ' + resp.status);
                    var page = await resp.json();

                    var content = page.content || '';
                    if (!content) {
                        if (cardEl) {
                            var btn = cardEl.querySelector('.comp-insert-btn');
                            if (btn) btn.textContent = '❌';
                        }
                        return;
                    }

                    var editor = window.tinyMceEditor;
                    if (editor) {
                        editor.insertContent(content);
                        // Flash success
                        if (cardEl) {
                            var btn = cardEl.querySelector('.comp-insert-btn');
                            if (btn) {
                                btn.textContent = '✅';
                                setTimeout(function() {
                                    if (btn) btn.textContent = '➕';
                                }, 1500);
                            }
                        }
                    } else {
                        alert('Editor not initialized.');
                    }
                } catch (e) {
                    console.error('Insert component failed:', e);
                    if (cardEl) {
                        var btn = cardEl.querySelector('.comp-insert-btn');
                        if (btn) btn.textContent = '❌';
                    }
                }
            }

            // -------- Templates (pages under /canadasite/{lang}/templates) --------
            async function searchTemplates(pathVal, titleVal) {
                try {
                    var templPath = getTemplatesPath();
                    if (!templPath) {
                        resultsEl.innerHTML = '<div class="resource-empty">Could not determine templates path.</div>';
                        return;
                    }

                    // Override path input to show system-determined path
                    pathInput.value = templPath;

                    var url = '/api/v1/pages/by-path/' + encodeURIComponent(templPath) + '/children';
                    if (titleVal) {
                        url += '?title=' + encodeURIComponent(titleVal);
                    }

                    var resp = await fetch(url);
                    if (!resp.ok) throw new Error('HTTP ' + resp.status);
                    var data = await resp.json();
                    renderTemplateResults(data, templPath);
                } catch (e) {
                    resultsEl.innerHTML = '<div class="resource-error">❌ Error: ' + e.message + '</div>';
                }
            }

            function getTemplatesPath() {
                // Derive from current page path: /canadasite/{lang}/... → /canadasite/{lang}/templates
                if (currentPageData && currentPageData.path) {
                    var parts = currentPageData.path.split('/').filter(Boolean);
                    if (parts.length >= 2) {
                        return '/' + parts[0] + '/' + parts[1] + '/templates';
                    }
                }
                return '/canadasite/en/templates';
            }

            function renderTemplateResults(data, basePath) {
                if (!data || data.length === 0) {
                    resultsEl.innerHTML = '<div class="resource-empty">📋 No templates found under ' + basePath + '</div>';
                    return;
                }

                var html = '<div class="resource-info">📋 ' + basePath + '</div>';
                html += '<div class="page-list">';
                data.forEach(function(page) {
                    var title = page.title || page.name || '(untitled)';
                    var pagePath = page.path || '';
                    html += '<div class="templ-card" data-path="' + pagePath + '">';
                    html += '<div class="templ-card-icon">📋</div>';
                    html += '<div class="templ-card-info">';
                    html += '<div class="templ-card-title" title="' + title + '">' + title + '</div>';
                    html += '<div class="templ-card-path">' + pagePath + '</div>';
                    html += '</div>';
                    html += '<button class="templ-insert-btn" title="Insert template content into editor">➕</button>';
                    html += '</div>';
                });
                html += '</div>';

                resultsEl.innerHTML = html;

                resultsEl.querySelectorAll('.templ-insert-btn').forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        var card = btn.closest('.templ-card');
                        var path = card.dataset.path;
                        insertTemplateContent(path, card);
                    });
                });

                resultsEl.querySelectorAll('.templ-card').forEach(function(card) {
                    card.addEventListener('click', function() {
                        var path = card.dataset.path;
                        insertTemplateContent(path, card);
                    });
                });
            }

            async function insertTemplateContent(pagePath, cardEl) {
                try {
                    if (cardEl) {
                        var btn = cardEl.querySelector('.templ-insert-btn');
                        if (btn) btn.textContent = '⏳';
                    }

                    var resp = await fetch('/api/v1/pages/by-path/' + encodeURIComponent(pagePath));
                    if (!resp.ok) throw new Error('HTTP ' + resp.status);
                    var page = await resp.json();

                    var content = page.content || '';
                    if (!content) {
                        if (cardEl) {
                            var btn = cardEl.querySelector('.templ-insert-btn');
                            if (btn) btn.textContent = '❌';
                        }
                        return;
                    }

                    var editor = window.tinyMceEditor;
                    if (editor) {
                        editor.insertContent(content);
                        if (cardEl) {
                            var btn = cardEl.querySelector('.templ-insert-btn');
                            if (btn) {
                                btn.textContent = '✅';
                                setTimeout(function() {
                                    if (btn) btn.textContent = '➕';
                                }, 1500);
                            }
                        }
                    } else {
                        alert('Editor not initialized.');
                    }
                } catch (e) {
                    console.error('Insert template failed:', e);
                    if (cardEl) {
                        var btn = cardEl.querySelector('.templ-insert-btn');
                        if (btn) btn.textContent = '❌';
                    }
                }
            }

            // -------- Pages (department-level) --------
            async function searchPages(pathVal, titleVal) {
                try {
                    // Extract department-level path (3rd level)
                    // e.g. /canadasite/en/employment-social-development/... → /canadasite/en/employment-social-development
                    var deptPath = getDepartmentLevelPath(pathVal);
                    if (!deptPath) {
                        resultsEl.innerHTML = '<div class="resource-empty">Select a page first to see department pages.</div>';
                        return;
                    }

                    var url = '/api/v1/pages/by-path/' + encodeURIComponent(deptPath) + '/children';
                    if (titleVal) {
                        url += '?title=' + encodeURIComponent(titleVal);
                    }

                    var resp = await fetch(url);
                    if (!resp.ok) throw new Error('HTTP ' + resp.status);
                    var data = await resp.json();
                    renderPageResults(data, deptPath);
                } catch (e) {
                    resultsEl.innerHTML = '<div class="resource-error">❌ Error: ' + e.message + '</div>';
                }
            }

            function getDepartmentLevelPath(fullPath) {
                // Extract 3rd level from path: /canadasite/en/department/...
                // Splits by '/', takes first 3 non-empty segments
                if (!fullPath) return '';
                var parts = fullPath.split('/').filter(Boolean);
                if (parts.length < 3) return '';
                return '/' + parts.slice(0, 3).join('/');
            }

            function renderPageResults(data, deptPath) {
                if (!data || data.length === 0) {
                    resultsEl.innerHTML = '<div class="resource-empty">📑 No pages found under ' + deptPath + '</div>';
                    return;
                }

                function addHtmlExt(p) { return p ? p + '.html' : p; }

                var html = '<div class="resource-info">📁 ' + deptPath + '</div>';
                html += '<div class="page-list">';
                data.forEach(function(page) {
                    var title = page.title || page.name || '(untitled)';
                    var pagePath = page.path || '';
                    var pagePathHtml = addHtmlExt(pagePath);
                    html += '<div class="page-card" data-path="' + pagePathHtml + '">';
                    html += '<div class="page-card-icon">📄</div>';
                    html += '<div class="page-card-info">';
                    html += '<div class="page-card-title" title="' + title + '">' + title + '</div>';
                    html += '<div class="page-card-path">' + pagePathHtml + '</div>';
                    html += '</div>';
                    html += '<button class="page-insert-btn" title="Insert page link into editor">🔗</button>';
                    html += '</div>';
                });
                html += '</div>';

                resultsEl.innerHTML = html;

                // Bind insert buttons
                resultsEl.querySelectorAll('.page-insert-btn').forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        var card = btn.closest('.page-card');
                        var path = card.dataset.path;
                        var title = card.querySelector('.page-card-title').textContent;
                        insertPageLink(path, title);
                    });
                });

                resultsEl.querySelectorAll('.page-card').forEach(function(card) {
                    card.addEventListener('click', function() {
                        var path = card.dataset.path;
                        var title = card.querySelector('.page-card-title').textContent;
                        insertPageLink(path, title);
                    });
                });
            }

            function insertPageLink(path, title) {
                var editor = window.tinyMceEditor;
                if (editor) {
                    editor.insertContent('<a href="' + path + '">' + title + '</a>');
                } else {
                    alert('Editor not initialized.');
                }
            }

            // Utility: format file size
            function formatFileSize(bytes) {
                if (!bytes) return '';
                const n = parseInt(bytes);
                if (n < 1024) return n + ' B';
                if (n < 1048576) return (n / 1024).toFixed(1) + ' KB';
                return (n / 1048576).toFixed(1) + ' MB';
            }

            // -------- Events --------
            resourceTypeSelect.addEventListener('change', function() {
                // Update path based on mode
                var type = resourceTypeSelect.value;
                if (type === 'components' || type === 'templates') {
                    // System-determined path - override input
                    if (type === 'components') {
                        pathInput.value = getComponentsPath();
                    } else if (type === 'templates') {
                        pathInput.value = getTemplatesPath();
                    }
                } else if (type === 'images' || type === 'documents') {
                    // DAM-based path
                    updateDefaultPath();
                } else if (type === 'pages') {
                    // Use CMS page path (not DAM path) to derive department level
                    if (currentPageData && currentPageData.path) {
                        pathInput.value = currentPageData.path;
                    } else {
                        updateDefaultPath();
                    }
                }

                // Clear title filter and search
                searchInput.value = '';
                doSearch();
            });

            searchBtn.addEventListener('click', doSearch);
            searchInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') doSearch();
            });

            // Auto-search on sidebar open (when filebot-toggle-btn is clicked)
            const toggleBtn = document.getElementById('filebot-toggle-btn');
            if (toggleBtn) {
                toggleBtn.addEventListener('click', function() {
                    setTimeout(function() {
                        updateDefaultPath();
                        setTimeout(doSearch, 50);
                    }, 200);
                });
            }

            // If sidebar is already visible on load, auto-search
            var rs = document.getElementById('resource-sidebar');
            if (rs && !rs.classList.contains('hidden')) {
                setTimeout(doSearch, 100);
            }

            // -------- Upload button (Images mode) --------
            var uploadBtn = document.getElementById('resource-upload-btn');
            var uploadInput = document.getElementById('resource-upload-input');

            if (uploadBtn && uploadInput) {
                uploadBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    uploadInput.click();
                });

                uploadInput.addEventListener('change', function(e) {
                    if (e.target.files.length > 0) {
                        uploadFiles(e.target.files);
                    }
                });

                // Show/hide upload button based on mode
                resourceTypeSelect.addEventListener('change', function() {
                    uploadBtn.style.display = (resourceTypeSelect.value === 'images') ? '' : 'none';
                });

                // Initial state
                uploadBtn.style.display = (resourceTypeSelect.value === 'images') ? '' : 'none';
            }

            // Initial setup
            updateDefaultPath();
            console.log('🔧 Resource sidebar module initialized');

            // Expose a global refresh function for uploadFiles() to call after upload
            window.refreshResourceSidebar = function(mode, pathVal, titleVal) {
                switch (mode) {
                    case 'images':
                        searchImages(pathVal, titleVal);
                        break;
                    case 'documents':
                        searchDocuments(pathVal, titleVal);
                        break;
                    case 'components':
                        searchComponents(pathVal, titleVal);
                        break;
                    case 'templates':
                        searchTemplates(pathVal, titleVal);
                        break;
                    case 'pages':
                        searchPages(pathVal, titleVal);
                        break;
                }
            };
        })();
