// Component Parameters Modal System for WebBot Editor

class ComponentParamsModal {
    constructor() {
        this.modal = null;
        this.currentComponent = null;
        this.resolvePromise = null;
        this.rejectPromise = null;
        this.init();
    }

    init() {
        // Create modal HTML
        const modalHtml = `
            <div id="component-params-modal" class="components-modal" style="display: none;">
                <div class="components-modal-content" style="width: 600px; height: auto; max-height: 80vh;">
                    <div class="components-modal-header">
                        <h3>Configure Component</h3>
                        <button class="components-modal-close" id="params-modal-close">×</button>
                    </div>
                    <div class="components-modal-body" style="padding: 20px; overflow-y: auto;">
                        <form id="component-params-form">
                            <div id="params-fields-container">
                                <!-- Dynamic fields will be inserted here -->
                            </div>
                            <div style="margin-top: 20px; display: flex; justify-content: flex-end; gap: 10px;">
                                <button type="button" id="params-cancel-btn" class="btn btn-default">Cancel</button>
                                <button type="submit" id="params-submit-btn" class="btn btn-primary">Insert Component</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;

        // Add to body if not already present
        if (!document.getElementById('component-params-modal')) {
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }

        this.modal = document.getElementById('component-params-modal');
        this.setupEventListeners();
    }

    setupEventListeners() {
        const closeBtn = document.getElementById('params-modal-close');
        const cancelBtn = document.getElementById('params-cancel-btn');
        const form = document.getElementById('component-params-form');

        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.hide());
        }
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitForm();
            });
        }

        // Close modal when clicking outside
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });

        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.classList.contains('show')) {
                this.hide();
            }
        });
    }

    show(component, currentParams = null) {
        this.currentComponent = component;
        this.currentParams = currentParams;
        this.renderForm(component, currentParams);
        this.modal.style.display = 'flex';
        this.modal.classList.add('show');

        // Return a promise that resolves with the parameters
        return new Promise((resolve, reject) => {
            this.resolvePromise = resolve;
            this.rejectPromise = reject;
        });
    }

    hide() {
        this.modal.style.display = 'none';
        this.modal.classList.remove('show');
        if (this.rejectPromise) {
            this.rejectPromise(new Error('User cancelled'));
        }
        this.clear();
    }

    clear() {
        this.currentComponent = null;
        this.resolvePromise = null;
        this.rejectPromise = null;
        const container = document.getElementById('params-fields-container');
        if (container) container.innerHTML = '';
    }

    renderForm(component, currentParams = null) {
        const container = document.getElementById('params-fields-container');
        if (!container) return;

        let html = '';
        
        if (!component.properties || Object.keys(component.properties).length === 0) {
            html = '<p>This component has no configurable properties.</p>';
        } else {
            for (const [propName, propDef] of Object.entries(component.properties)) {
                html += this.renderField(propName, propDef, currentParams);
            }
        }

        container.innerHTML = html;
        
        // Initialize JSON validation buttons
        this.initJSONValidation();
    }
    
    initJSONValidation() {
        const validationButtons = document.querySelectorAll('.json-validate-btn');
        validationButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = btn.getAttribute('data-target');
                const textarea = document.getElementById(targetId);
                const resultSpan = btn.nextElementSibling;
                
                if (!textarea || !resultSpan) return;
                
                try {
                    JSON.parse(textarea.value);
                    resultSpan.textContent = '✅ Valid JSON format';
                    resultSpan.style.color = 'green';
                } catch (err) {
                    resultSpan.textContent = `❌ JSON error: ${err.message}`;
                    resultSpan.style.color = 'red';
                }
            });
        });
    }

    renderField(propName, propDef, currentParams = null) {
        const label = propDef.label || propName;
        const required = propDef.required ? 'required' : '';
        
        // Determine the value to use: current param value, then default, then empty
        let fieldValue = '';
        if (currentParams && propName in currentParams) {
            fieldValue = currentParams[propName];
        } else if (propDef.default !== undefined) {
            fieldValue = propDef.default;
        }
        
        let fieldHtml = '';

        switch (propDef.type) {
            case 'string':
                fieldHtml = `
                    <div class="form-group">
                        <label for="param-${propName}">${label}</label>
                        <input type="text" 
                               id="param-${propName}" 
                               name="${propName}" 
                               class="form-control" 
                               value="${this.escapeHtml(fieldValue)}" 
                               ${required}>
                        ${propDef.description ? `<small class="form-text text-muted">${propDef.description}</small>` : ''}
                    </div>
                `;
                break;
            
            case 'text':
                const textRows = propDef.rows || 6;
                fieldHtml = `
                    <div class="form-group">
                        <label for="param-${propName}">${label}</label>
                        <textarea id="param-${propName}" 
                                  name="${propName}" 
                                  class="form-control" 
                                  rows="${textRows}" 
                                  ${required}>${this.escapeHtml(fieldValue)}</textarea>
                        ${propDef.description ? `<small class="form-text text-muted">${propDef.description}</small>` : ''}
                    </div>
                `;
                break;
            
            case 'json':
                const jsonRows = propDef.rows || 8;
                fieldHtml = `
                    <div class="form-group">
                        <label for="param-${propName}">${label}</label>
                        <textarea id="param-${propName}" 
                                  name="${propName}" 
                                  class="form-control" 
                                  rows="${jsonRows}" 
                                  ${required}>${this.escapeHtml(fieldValue)}</textarea>
                        ${propDef.description ? `<small class="form-text text-muted">${propDef.description}</small>` : ''}
                        <div class="mt-1">
                            <button type="button" class="btn btn-sm btn-outline-secondary json-validate-btn" data-target="param-${propName}">
                                Validate JSON
                            </button>
                            <span class="json-validation-result ml-2"></span>
                        </div>
                    </div>
                `;
                break;
            
            case 'select':
                const options = propDef.options || [];
                let optionsHtml = '';
                for (const option of options) {
                    const selected = option === fieldValue ? 'selected' : '';
                    optionsHtml += `<option value="${option}" ${selected}>${option}</option>`;
                }
                fieldHtml = `
                    <div class="form-group">
                        <label for="param-${propName}">${label}</label>
                        <select id="param-${propName}" name="${propName}" class="form-control" ${required}>
                            ${optionsHtml}
                        </select>
                        ${propDef.description ? `<small class="form-text text-muted">${propDef.description}</small>` : ''}
                    </div>
                `;
                break;
            
            case 'boolean':
                const checked = fieldValue ? 'checked' : '';
                fieldHtml = `
                    <div class="form-check">
                        <input type="checkbox" 
                               id="param-${propName}" 
                               name="${propName}" 
                               class="form-check-input" 
                               ${checked}>
                        <label class="form-check-label" for="param-${propName}">${label}</label>
                        ${propDef.description ? `<small class="form-text text-muted">${propDef.description}</small>` : ''}
                    </div>
                `;
                break;
            
            case 'color':
                fieldHtml = `
                    <div class="form-group">
                        <label for="param-${propName}">${label}</label>
                        <input type="color" 
                               id="param-${propName}" 
                               name="${propName}" 
                               class="form-control" 
                               value="${fieldValue}" 
                               ${required}>
                        ${propDef.description ? `<small class="form-text text-muted">${propDef.description}</small>` : ''}
                    </div>
                `;
                break;
            
            default:
                fieldHtml = `
                    <div class="form-group">
                        <label for="param-${propName}">${label}</label>
                        <input type="text" 
                               id="param-${propName}" 
                               name="${propName}" 
                               class="form-control" 
                               value="${this.escapeHtml(fieldValue)}" 
                               ${required}>
                        ${propDef.description ? `<small class="form-text text-muted">${propDef.description}</small>` : ''}
                    </div>
                `;
        }

        return fieldHtml;
    }

    escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    submitForm() {
        const form = document.getElementById('component-params-form');
        if (!form) return;

        const formData = new FormData(form);
        const params = {};

        for (const [key, value] of formData.entries()) {
            // Handle checkbox boolean
            const input = form.querySelector(`[name="${key}"]`);
            if (input && input.type === 'checkbox') {
                params[key] = input.checked;
            } else {
                params[key] = value;
            }
        }

        if (this.resolvePromise) {
            this.resolvePromise(params);
        }

        this.hide();
    }
}

// Component Template Manager
class ComponentTemplateManager {
    constructor() {
        this.templates = {};
        this.modal = new ComponentParamsModal();
    }

    async fetchTemplate(componentId) {
        // Check cache
        if (this.templates[componentId]) {
            return this.templates[componentId];
        }

        try {
            const response = await fetch(`/api/v1/components/templates/${componentId}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const template = await response.json();
            this.templates[componentId] = template;
            return template;
        } catch (error) {
            console.error(`Failed to fetch component template ${componentId}:`, error);
            
            // Fallback for mustache-renderer if API fails
            if (componentId === 'mustache-renderer') {
                console.log('Using fallback template for mustache-renderer');
                const fallbackTemplate = {
                    id: 'mustache-renderer',
                    name: 'mustache-renderer',
                    display_name: 'Mustache Template Renderer',
                    category: 'custom',
                    description: 'Render Mustache templates with variable substitution, conditionals, and loops',
                    html_template: '<div class="mustache-renderer-container" data-template="{{template_text}}" data-json="{{json_data}}" data-escape-html="{{escape_html}}"><div class="mustache-placeholder"><p><em>Mustache Template Renderer — content renders on page load</em></p></div></div>',
                    css_template: '.mustache-renderer-container { border: 1px solid #ddd; border-radius: 4px; padding: 15px; margin: 10px 0; background-color: #f9f9f9; } .mustache-placeholder { color: #666; font-style: italic; padding: 10px; background-color: #f0f0f0; border-radius: 3px; }',
                    js_template: '// Mustache Renderer — client logic',
                    properties: {
                        template_text: {
                            name: 'template_text',
                            type: 'text',
                            label: 'Mustache Template',
                            default: '<h1>{{title}}</h1>\n<p>{{content}}</p>\n{{#if show_more}}\n<div class="more-content">{{more_text}}</div>\n{{/if}}',
                            required: true,
                            description: 'Mustache template using {{variable}} syntax',
                            multiline: true,
                            rows: 8
                        },
                        json_data: {
                            name: 'json_data',
                            type: 'json',
                            label: 'JSON Data',
                            default: '{"title": "Sample Title", "content": "Sample content", "show_more": true, "more_text": "More content..."}',
                            required: true,
                            description: 'JSON object providing template variables',
                            multiline: true,
                            rows: 8
                        },
                        escape_html: {
                            name: 'escape_html',
                            type: 'boolean',
                            label: 'HTML Escape',
                            default: true,
                            description: 'Automatically escape HTML characters to prevent XSS attacks'
                        }
                    },
                    dependencies_json: '[]',
                    wet_boew_version: '',
                    wet_boew_compliant: false,
                    accessibility_checked: false,
                    tags_json: '["template", "mustache", "dynamic", "json"]',
                    author: 'WebBot System',
                    version: '1.0.0',
                    status: 'published'
                };
                this.templates[componentId] = fallbackTemplate;
                return fallbackTemplate;
            }
            
            // Fallback for mustache-api-renderer if API fails
            if (componentId === 'mustache-api-renderer') {
                console.log('Using fallback template for mustache-api-renderer');
                const fallbackTemplate = {
                    id: 'mustache-api-renderer',
                    name: 'mustache-api-renderer',
                    display_name: 'Mustache API Renderer',
                    category: 'custom',
                    description: 'Fetch data from an API path and render a Mustache template',
                    html_template: '<div class="mustache-api-renderer-container" data-api-path="{{api_path}}" data-template="{{template_text}}" data-escape-html="{{escape_html}}"><div class="mustache-api-placeholder"><p><em>Mustache API Renderer — fetches from {{api_path}} and renders template</em></p></div></div>',
                    css_template: '.mustache-api-renderer-container { border: 1px solid #4a86e8; border-radius: 4px; padding: 15px; margin: 10px 0; background-color: #e8f4ff; } .mustache-api-placeholder { color: #4a86e8; font-style: italic; padding: 10px; background-color: #f0f8ff; border-radius: 3px; }',
                    js_template: '// Mustache API Renderer — client logic',
                    properties: {
                        api_path: {
                            name: 'api_path',
                            type: 'string',
                            label: 'API Path',
                            default: '/api/v1/pages/en/data',
                            required: true,
                            description: 'API path to fetch JSON data, e.g. /api/v1/pages/en/contact'
                        },
                        template_text: {
                            name: 'template_text',
                            type: 'text',
                            label: 'Mustache Template',
                            default: '<h1>{{title}}</h1>\n<p>{{content}}</p>\n{{#if show_more}}\n<div class="more-content">{{more_text}}</div>\n{{/if}}',
                            required: true,
                            description: 'Mustache template using {{variable}} syntax',
                            multiline: true,
                            rows: 8
                        },
                        escape_html: {
                            name: 'escape_html',
                            type: 'boolean',
                            label: 'HTML Escape',
                            default: true,
                            description: 'Automatically escape HTML characters to prevent XSS attacks'
                        }
                    },
                    dependencies_json: '[]',
                    wet_boew_version: '',
                    wet_boew_compliant: false,
                    accessibility_checked: false,
                    tags_json: '["template", "mustache", "api", "dynamic", "json"]',
                    author: 'WebBot System',
                    version: '1.0.0',
                    status: 'published'
                };
                this.templates[componentId] = fallbackTemplate;
                return fallbackTemplate;
            }
            
            return null;
        }
    }

    async renderTemplate(template, params) {
        // Simple template rendering using string replacement
        let html = template.html_template;
        
        // Replace {{variable}} and {{{variable}}} (triple braces for unescaped)
        for (const [key, value] of Object.entries(params)) {
            const regexEscaped = new RegExp(`{{${key}}}`, 'g');
            const regexUnescaped = new RegExp(`{{{${key}}}}`, 'g');
            
            html = html.replace(regexUnescaped, value);
            html = html.replace(regexEscaped, this.escapeHtml(value));
        }

        // Remove any remaining template tags
        html = html.replace(/\{\{[^}]*\}\}/g, '');
        html = html.replace(/\{\{\{[^}]*\}\}\}/g, '');

        return html;
    }

    escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async renderMustacheTemplate(params) {
        try {
            const { template_text, json_data, escape_html } = params;
            
            // Validate JSON
            let parsedJson;
            try {
                parsedJson = JSON.parse(json_data);
            } catch (err) {
                throw new Error(`JSON parse error: ${err.message}`);
            }
            
            // Call backend rendering API
            const formData = new FormData();
            formData.append('template', template_text);
            formData.append('json_data', json_data);
            formData.append('escape_html', escape_html);
            
            const response = await fetch('/api/v1/components/render-mustache', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Mustache render failed');
            }
            
            // Wrap in webbot-component div
            return `<div class="webbot-component mustache-rendered">${result.html}</div>`;
            
        } catch (error) {
            console.error('Mustache render error:', error);
            return `<div class="alert alert-danger">Mustache render error: ${error.message}</div>`;
        }
    }

    async renderMustacheApiTemplate(params) {
        try {
            const { api_path, template_text, escape_html } = params;
            
            // Validate API path
            if (!api_path || !api_path.startsWith('/')) {
                throw new Error('API path must be a valid path starting with /');
            }
            
            // Fetch data from API
            console.log(`Fetching data from API path: ${api_path}`);
            const apiResponse = await fetch(api_path);
            
            if (!apiResponse.ok) {
                throw new Error(`API request failed: HTTP ${apiResponse.status} - ${apiResponse.statusText}`);
            }
            
            let jsonData;
            try {
                jsonData = await apiResponse.json();
            } catch (err) {
                throw new Error(`API did not return valid JSON: ${err.message}`);
            }
            
            // Convert JSON object to string for the mustache renderer
            const jsonString = JSON.stringify(jsonData);
            
            // Call backend rendering API
            const formData = new FormData();
            formData.append('template', template_text);
            formData.append('json_data', jsonString);
            formData.append('escape_html', escape_html);
            
            const renderResponse = await fetch('/api/v1/components/render-mustache', {
                method: 'POST',
                body: formData
            });
            
            const result = await renderResponse.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Mustache render failed');
            }
            
            // Wrap in webbot-component div with additional data attributes
            return `<div class="webbot-component mustache-api-rendered" data-api-path="${this.escapeHtml(api_path)}">${result.html}</div>`;
            
        } catch (error) {
            console.error('Mustache API render error:', error);
            return `<div class="alert alert-danger">Mustache API render error: ${error.message}</div>`;
        }
    }

    async insertComponentWithParams(componentId) {
        try {
            // Fetch template
            const template = await this.fetchTemplate(componentId);
            if (!template) {
                console.error(`Component template ${componentId} not found`);
                return false;
            }

            // Check if component has properties
            if (!template.properties || Object.keys(template.properties).length === 0) {
                // No properties, render with defaults
                const defaultParams = {};
                for (const [propName, propDef] of Object.entries(template.properties || {})) {
                    defaultParams[propName] = propDef.default;
                }
                const html = await this.renderTemplate(template, defaultParams);
                const success = await this.insertIntoEditor(html, componentId, defaultParams);
                return success;
            }

            // Show modal for parameters
            const currentParams = window._editingCurrentParams || null;
            const params = await this.modal.show(template, currentParams);
            
            // Merge with defaults
            const finalParams = {};
            for (const [propName, propDef] of Object.entries(template.properties)) {
                if (params[propName] !== undefined) {
                    finalParams[propName] = params[propName];
                } else {
                    finalParams[propName] = propDef.default;
                }
            }

            // Special handling for Mustache renderers
            let html;
            if (componentId === 'mustache-renderer') {
                html = await this.renderMustacheTemplate(finalParams);
            } else if (componentId === 'mustache-api-renderer') {
                html = await this.renderMustacheApiTemplate(finalParams);
            } else {
                // Render template using standard method
                html = await this.renderTemplate(template, finalParams);
            }
            const success = await this.insertIntoEditor(html, componentId, finalParams);
            return success;

        } catch (error) {
            if (error.message !== 'User cancelled') {
                console.error('Error inserting component:', error);
                showWetAlert(`Failed to insert component: ${error.message}`);
            }
            return false;
        }
    }

    async waitForEditor(maxRetries = 10, interval = 200) {
        // Wait for TinyMCE editor to become available
        for (let i = 0; i < maxRetries; i++) {
            let editor = null;
            
            // Method 1: tinymce.activeEditor (standard API)
            if (typeof tinymce !== 'undefined' && tinymce.activeEditor) {
                editor = tinymce.activeEditor;
                console.log(`📝 Attempt ${i+1}/${maxRetries}: Using tinymce.activeEditor`);
            }
            // Method 2: window.tinyMceEditor (legacy global variable)
            else if (window.tinyMceEditor) {
                editor = window.tinyMceEditor;
                console.log(`📝 Attempt ${i+1}/${maxRetries}: Using window.tinyMceEditor`);
            }
            // Method 3: Try to get by selector
            else if (typeof tinymce !== 'undefined') {
                const editors = tinymce.editors;
                if (editors && editors.length > 0) {
                    editor = editors[0];
                    console.log(`📝 Attempt ${i+1}/${maxRetries}: Using first tinymce editor from editors array`);
                }
            }
            
            if (editor) {
                return editor;
            }
            
            // Wait before retrying
            if (i < maxRetries - 1) {
                console.log(`⏳ Editor not available yet, waiting ${interval}ms...`);
                await new Promise(resolve => setTimeout(resolve, interval));
            }
        }
        
        // If we get here, editor is still not available
        console.error('❌ TinyMCE editor not available after maximum retries. Available methods:');
        console.error('  - tinymce:', typeof tinymce);
        console.error('  - tinyMCE:', typeof tinyMCE);
        console.error('  - window.tinyMceEditor:', window.tinyMceEditor);
        console.error('  - tinymce.editors:', typeof tinymce !== 'undefined' ? tinymce.editors : 'tinymce not defined');
        
        // Show user-friendly error message
        showWetAlert('The editor is not ready yet. Please try clicking in the editor area first, then insert the component.');
        throw new Error('TinyMCE editor not available');
    }

    async insertIntoEditor(html, componentId = null, params = null) {
        try {
            // Check if we're in edit mode
            let isEditMode = false;
            let oldWrapperId = null;
            
            if (window._editingWrapperId && componentId === window._editingComponentId) {
                isEditMode = true;
                oldWrapperId = window._editingWrapperId;
                console.log(`🔄 EDIT MODE: Replacing component ${oldWrapperId} with new version`);
                
                // Clear the global variables
                window._editingWrapperId = null;
                window._editingComponentId = null;
                window._editingCurrentParams = null;
            }
            
            // Wait for editor to become available
            const editor = await this.waitForEditor();
            
            // Add webbot-component class if not present
            if (!html.includes('webbot-component')) {
                console.log('🔧 Adding webbot-component class to component HTML');
                
                // Improved regex to properly add class to first HTML tag
                // Match the first HTML tag and its attributes
                html = html.replace(/<(\w+)([^>]*)>/, (match, tagName, attributes) => {
                    console.log(`🔧 Processing tag: <${tagName}${attributes}>`);
                    
                    // Check if the tag already has a class attribute
                    const classMatch = attributes.match(/class\s*=\s*["']([^"']*)["']/);
                    
                    if (classMatch) {
                        // Tag has class attribute, append webbot-component to existing classes
                        const existingClasses = classMatch[1];
                        const newClasses = existingClasses + ' webbot-component';
                        const newAttributes = attributes.replace(
                            /class\s*=\s*["'][^"']*["']/,
                            `class="${newClasses}"`
                        );
                        console.log(`🔧 Added webbot-component to existing classes: ${newClasses}`);
                        return `<${tagName}${newAttributes}>`;
                    } else {
                        // Tag doesn't have class attribute, add one
                        console.log(`🔧 Adding new class="webbot-component" attribute`);
                        return `<${tagName}${attributes} class="webbot-component">`;
                    }
                });
            } else {
                console.log('🔧 Component already has webbot-component class');
            }

            console.log('✅ Inserting component into editor:', html.substring(0, 150) + '...');
            console.log('🔍 Final HTML starts with:', html.substring(0, 200));
            
            // If in edit mode, remove the old component first
            if (isEditMode && oldWrapperId) {
                try {
                    console.log(`🗑️ Removing old component wrapper: ${oldWrapperId}`);
                    // Try to find and remove the old component from editor
                    const oldElement = editor.dom.select('#' + oldWrapperId)[0];
                    if (oldElement) {
                        editor.dom.remove(oldElement);
                        console.log(`✅ Removed old component: ${oldWrapperId}`);
                    } else {
                        console.warn(`⚠️ Old component not found in editor: ${oldWrapperId}`);
                    }
                } catch (err) {
                    console.error(`❌ Failed to remove old component: ${err.message}`);
                }
            }
            
            // Add edit icon for components that have parameters
            console.log(`🔍 Debug: componentId=${componentId}, params=`, params, 'params type:', typeof params);
            console.log(`🔍 Debug: params is truthy?`, !!params);
            console.log(`🔍 Debug: componentId is truthy?`, !!componentId);
            
            // Always wrap components that come from parameter dialog system
            // Check if this is a component that should have edit capability
            const componentsWithDialog = window.componentsWithDialog || [
                'wet-carousel', 'wet-tabs', 'wet-ajax-table-final', 
                'wet-feature-columns', 'wet-embed-html', 'api-data-card', 
                'mustache-renderer', 'mustache-api-renderer'
            ];
            
            const shouldHaveEdit = componentId && componentsWithDialog.includes(componentId);
            console.log(`🔍 Debug: Should have edit button?`, shouldHaveEdit, `(componentId: ${componentId})`);
            
            if (shouldHaveEdit) {
                // Wrap component with edit icon
                const wrapperId = 'webbot-component-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
                const safeParams = params || {};
                const wrappedHtml = `
<div class="webbot-component-wrapper" id="${this.escapeHtml(wrapperId)}" data-webbot-component="${this.escapeHtml(componentId)}" data-webbot-params='${this.escapeHtml(JSON.stringify(safeParams))}' style="position: relative; display: inline-block; min-height: 40px; min-width: 40px; border: 1px dashed #ccc; margin: 5px; padding: 5px;">
    ${html}
    <button class="webbot-edit-btn" 
            style="position: absolute; top: 2px; right: 2px; background: #007bff; color: white; border: none; border-radius: 50%; width: 24px; height: 24px; font-size: 12px; cursor: pointer; z-index: 1000;"
            onclick="(function(){try{if(top.editWebBotComponent){top.editWebBotComponent('${this.escapeHtml(wrapperId)}');}else if(parent.editWebBotComponent){parent.editWebBotComponent('${this.escapeHtml(wrapperId)}');}else if(window.editWebBotComponent){window.editWebBotComponent('${this.escapeHtml(wrapperId)}');}else{showWetAlert('Edit function not available. Please refresh the page.');}}catch(e){console.error('Error calling edit function:',e);showWetAlert('Error editing component: '+e.message);}})()"
            title="Edit component parameters">
        ✎
    </button>
</div>
                `;
                console.log(`🛠️ Wrapped component with edit button (wrapper: ${wrapperId})`);
                editor.insertContent(wrappedHtml);
            } else {
                // Insert without edit button
                console.log(`⚠️ Component inserted WITHOUT edit button (componentId: ${componentId})`);
                editor.insertContent(html);
            }
            
            console.log('✅ Component inserted successfully');
            return true;
        } catch (error) {
            console.error('❌ Failed to insert component into editor:', error.message);
            console.error('❌ Error stack:', error.stack);
            return false;
        }
    }
}

// Initialize and attach to global scope
window.ComponentTemplateManager = ComponentTemplateManager;

// Override the default insertComponent function for selected components
(function() {
    const originalInsertComponent = window.insertComponent;
    const manager = new ComponentTemplateManager();

    // Components that require parameter dialog (showcase examples)
    const componentsWithDialog = [
        'wet-carousel',           // Carousel - 17 params, most complex
        'wet-tabs',               // Tabs - 9 params
        'wet-ajax-table-final',   // AJAX Table - needs data source config
        'wet-feature-columns',    // Feature Columns - multi-image config
        'wet-embed-html',         // HTML Embed - needs HTML code config
        'api-data-card',          // API Data Card - fetches JSON from API
        'mustache-renderer',      // Mustache Renderer - template + JSON rendering
        'mustache-api-renderer'  // Mustache API Renderer - fetch API data + render template
    ];

    window.insertComponent = function(componentId) {
        // Check if this component should show parameter dialog
        if (componentsWithDialog.includes(componentId)) {
            console.log(`🚀 Showing parameter dialog for: ${componentId}`);
            return manager.insertComponentWithParams(componentId);
        } else {
            // For other components, insert directly without dialog
            console.log(`⚡ Direct insert for: ${componentId}`);
            return originalInsertComponent.call(this, componentId);
        }
    };

    // Also expose the list for debugging/UI
    window.componentsWithDialog = componentsWithDialog;

    console.log('📋 Component parameters system initialized');
    console.log(`🔧 Dialog components: ${componentsWithDialog.join(', ')}`);
    console.log('💡 Most components insert directly; only complex ones show dialog.');
    
    // Add global edit function for WebBot components
    window.editWebBotComponent = async function(wrapperId) {
        console.log(`🔄 Edit component clicked for wrapper: ${wrapperId}`);
        
        try {
            // Find the wrapper element - try multiple methods
            let wrapper = null;
            
            // Method 1: Try to get from TinyMCE editor iframe
            if (typeof tinymce !== 'undefined' && tinymce.activeEditor) {
                const editor = tinymce.activeEditor;
                const iframeDoc = editor.getDoc();
                if (iframeDoc) {
                    wrapper = iframeDoc.getElementById(wrapperId);
                    console.log(`🔍 Attempted to find wrapper in TinyMCE iframe: ${wrapper ? 'found' : 'not found'}`);
                }
            }
            
            // Method 2: Try parent window (if called from iframe)
            if (!wrapper && window.parent && window.parent !== window) {
                wrapper = window.parent.document.getElementById(wrapperId);
                console.log(`🔍 Attempted to find wrapper in parent window: ${wrapper ? 'found' : 'not found'}`);
            }
            
            // Method 3: Try current document
            if (!wrapper) {
                wrapper = document.getElementById(wrapperId);
                console.log(`🔍 Attempted to find wrapper in current document: ${wrapper ? 'found' : 'not found'}`);
            }
            
            if (!wrapper) {
                console.error(`Wrapper element not found: ${wrapperId}`);
                console.error('Available methods:');
                console.error('  - tinymce:', typeof tinymce);
                console.error('  - tinymce.activeEditor:', typeof tinymce !== 'undefined' ? tinymce.activeEditor : 'N/A');
                console.error('  - window.parent:', window.parent !== window ? 'available' : 'same window');
                showWetAlert('Cannot edit component: element not found in DOM. Try refreshing the page.');
                return;
            }
            
            // Get component data from data attributes
            const componentId = wrapper.getAttribute('data-webbot-component');
            const paramsJson = wrapper.getAttribute('data-webbot-params');
            let currentParams = {};
            
            if (paramsJson) {
                try {
                    currentParams = JSON.parse(paramsJson);
                } catch (e) {
                    console.warn('Could not parse component params from data attribute:', e);
                }
            }
            
            console.log(`📝 Editing component: ${componentId}`, currentParams);
            
            // Store the wrapper ID so we can replace it later
            window._editingWrapperId = wrapperId;
            window._editingComponentId = componentId;
            window._editingCurrentParams = currentParams;
            
            // Trigger the parameter dialog
            if (window.insertComponent) {
                window.insertComponent(componentId);
            } else {
                console.error('insertComponent function not found');
                showWetAlert('Cannot edit component: insertComponent function not available');
            }
        } catch (error) {
            console.error('Error editing component:', error);
            showWetAlert(`Error editing component: ${error.message}`);
        }
    };
})();