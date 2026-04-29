// WebBot组件插入功能终极修复脚本
// 在浏览器控制台(F12)中运行此脚本以修复组件插入问题

(function() {
    console.log('🚀 开始修复WebBot组件插入功能...');
    
    // 1. 检测当前环境
    console.log('🔍 环境检测:');
    console.log('- tinymce:', typeof tinymce);
    console.log('- tinymce.activeEditor:', typeof tinymce !== 'undefined' ? tinymce.activeEditor : '未定义');
    console.log('- window.tinyMceEditor:', window.tinyMceEditor);
    console.log('- ComponentTemplateManager:', typeof ComponentTemplateManager);
    
    // 2. 修复编辑器获取函数
    function createWaitForEditorFunction() {
        return async function(maxRetries = 10, interval = 200) {
            console.log('🔄 waitForEditor: 开始查找编辑器实例...');
            
            for (let i = 0; i < maxRetries; i++) {
                let editor = null;
                
                // 方法1: tinymce.activeEditor (标准API)
                if (typeof tinymce !== 'undefined' && tinymce.activeEditor) {
                    editor = tinymce.activeEditor;
                    console.log(`📝 尝试${i+1}/${maxRetries}: 使用tinymce.activeEditor`);
                }
                // 方法2: window.tinyMceEditor (旧全局变量)
                else if (window.tinyMceEditor) {
                    editor = window.tinyMceEditor;
                    console.log(`📝 尝试${i+1}/${maxRetries}: 使用window.tinyMceEditor`);
                }
                // 方法3: 尝试通过选择器获取
                else if (typeof tinymce !== 'undefined' && tinymce.editors && tinymce.editors.length > 0) {
                    editor = tinymce.editors[0];
                    console.log(`📝 尝试${i+1}/${maxRetries}: 使用tinymce.editors[0]`);
                }
                // 方法4: 通过ID获取
                else if (typeof tinymce !== 'undefined') {
                    const editorElement = document.getElementById('wysiwyg-editor-container');
                    if (editorElement) {
                        editor = tinymce.get(editorElement.id);
                        console.log(`📝 尝试${i+1}/${maxRetries}: 通过ID获取编辑器`);
                    }
                }
                
                if (editor) {
                    console.log(`✅ 成功找到编辑器实例`);
                    return editor;
                }
                
                // 等待后重试
                if (i < maxRetries - 1) {
                    console.log(`⏳ 编辑器尚未就绪，等待${interval}ms后重试...`);
                    await new Promise(resolve => setTimeout(resolve, interval));
                }
            }
            
            // 所有重试都失败
            console.error('❌ 无法找到TinyMCE编辑器实例');
            console.error('可能的原因:');
            console.error('1. 编辑器尚未完全加载');
            console.error('2. 编辑器失去焦点');
            console.error('3. TinyMCE初始化失败');
            
            // 用户友好的错误提示
            const userConfirmed = confirm(
                '无法找到编辑器。\n\n' +
                '请按以下步骤操作:\n' +
                '1. 点击编辑器区域激活编辑器\n' +
                '2. 然后重新插入组件\n\n' +
                '点击"确定"继续，或"取消"放弃。'
            );
            
            if (userConfirmed) {
                // 让用户手动激活编辑器
                alert('请点击编辑器区域，然后重试插入组件。');
            }
            
            throw new Error('TinyMCE编辑器未就绪');
        };
    }
    
    // 3. 修复插入函数
    function createInsertIntoEditorFunction() {
        return async function(html) {
            try {
                console.log('🔄 insertIntoEditor: 开始插入组件...');
                
                // 等待编辑器就绪
                const editor = await this.waitForEditor();
                
                // 添加webbot-component类
                if (!html.includes('webbot-component')) {
                    html = html.replace(/<(\w+)([^>]*)>/, '<$1$2 class="webbot-component">');
                }
                
                console.log('✅ 正在插入组件到编辑器:', html.substring(0, 100) + '...');
                
                // 插入内容
                editor.insertContent(html);
                
                // 可选: 滚动到插入位置
                editor.selection.scrollIntoView();
                
                console.log('🎉 组件插入成功!');
                return true;
            } catch (error) {
                console.error('❌ 组件插入失败:', error.message);
                
                // 提供备选方案
                const useFallback = confirm(
                    `组件插入失败: ${error.message}\n\n` +
                    '是否尝试使用备选方法插入?'
                );
                
                if (useFallback) {
                    try {
                        // 备选方案: 直接操作DOM
                        const editorElement = document.getElementById('wysiwyg-editor-container');
                        if (editorElement) {
                            editorElement.innerHTML += html;
                            console.log('🔄 使用DOM备选方法插入成功');
                            return true;
                        }
                    } catch (fallbackError) {
                        console.error('❌ 备选方法也失败:', fallbackError);
                    }
                }
                
                return false;
            }
        };
    }
    
    // 4. 修复插入组件带参数函数
    function createInsertComponentWithParamsFunction() {
        return async function(componentId) {
            try {
                console.log(`🚀 insertComponentWithParams: 开始插入组件 ${componentId}`);
                
                // 获取组件模板
                const response = await fetch(`/api/v1/components/templates/${componentId}`);
                if (!response.ok) {
                    throw new Error(`获取组件模板失败: HTTP ${response.status}`);
                }
                
                const template = await response.json();
                console.log(`📋 获取到模板: ${template.display_name || componentId}`);
                
                // 显示参数对话框
                if (this.modal && typeof this.modal.show === 'function') {
                    const params = await this.modal.show(template);
                    
                    // 渲染模板
                    let html = template.html_template || '<div>组件HTML</div>';
                    for (const [key, value] of Object.entries(params || {})) {
                        const regex = new RegExp(`{{${key}}}`, 'g');
                        html = html.replace(regex, value);
                    }
                    
                    // 插入到编辑器
                    return await this.insertIntoEditor(html);
                } else {
                    console.warn('⚠️ 参数对话框不可用，使用默认参数');
                    
                    // 使用默认参数
                    let html = template.html_template || '<div>组件HTML</div>';
                    return await this.insertIntoEditor(html);
                }
            } catch (error) {
                console.error(`❌ 插入组件 ${componentId} 失败:`, error);
                alert(`插入组件失败: ${error.message}`);
                return false;
            }
        };
    }
    
    // 5. 应用修复
    function applyFixes() {
        console.log('🔧 应用修复...');
        
        // 检查ComponentTemplateManager是否存在
        if (typeof ComponentTemplateManager === 'undefined') {
            console.error('❌ ComponentTemplateManager未定义，无法修复');
            return false;
        }
        
        // 备份原始函数
        const originalInsertIntoEditor = ComponentTemplateManager.prototype.insertIntoEditor;
        
        // 应用修复
        ComponentTemplateManager.prototype.waitForEditor = createWaitForEditorFunction();
        ComponentTemplateManager.prototype.insertIntoEditor = createInsertIntoEditorFunction();
        ComponentTemplateManager.prototype.insertComponentWithParams = createInsertComponentWithParamsFunction();
        
        console.log('✅ 修复已应用');
        console.log('- waitForEditor:', typeof ComponentTemplateManager.prototype.waitForEditor);
        console.log('- insertIntoEditor:', typeof ComponentTemplateManager.prototype.insertIntoEditor);
        console.log('- insertComponentWithParams:', typeof ComponentTemplateManager.prototype.insertComponentWithParams);
        
        return true;
    }
    
    // 6. 修复全局insertComponent函数
    function fixGlobalInsertComponent() {
        console.log('🔧 修复全局insertComponent函数...');
        
        // 定义需要参数对话框的组件
        const componentsWithDialog = [
            'wet-carousel',
            'wet-tabs', 
            'wet-ajax-table-final',
            'wet-feature-columns',
            'wet-embed-html',
            'api-data-card',
            'mustache-renderer'
        ];
        
        // 备份原始函数
        const originalInsertComponent = window.insertComponent || function(componentId) {
            console.warn(`⚠️ 直接插入组件 ${componentId} (无参数对话框)`);
            // 简单实现
            const html = `<div class="webbot-component">${componentId} 组件</div>`;
            const editor = tinymce.activeEditor;
            if (editor) {
                editor.insertContent(html);
                return true;
            }
            return false;
        };
        
        // 创建ComponentTemplateManager实例
        const manager = new ComponentTemplateManager();
        
        // 覆盖全局函数
        window.insertComponent = function(componentId) {
            console.log(`🔘 insertComponent被调用: ${componentId}`);
            
            if (componentsWithDialog.includes(componentId)) {
                console.log(`🚀 显示参数对话框: ${componentId}`);
                return manager.insertComponentWithParams(componentId);
            } else {
                console.log(`⚡ 直接插入: ${componentId}`);
                return originalInsertComponent.call(this, componentId);
            }
        };
        
        // 暴露组件列表用于调试
        window.componentsWithDialog = componentsWithDialog;
        
        console.log('✅ 全局insertComponent函数已修复');
        console.log(`📋 需要参数对话框的组件: ${componentsWithDialog.join(', ')}`);
        
        return true;
    }
    
    // 7. 激活编辑器（如果可能）
    function activateEditor() {
        if (typeof tinymce !== 'undefined' && tinymce.activeEditor) {
            tinymce.activeEditor.focus();
            console.log('🎯 编辑器已激活并获得焦点');
            return true;
        } else if (typeof tinymce !== 'undefined' && tinymce.editors && tinymce.editors.length > 0) {
            tinymce.editors[0].focus();
            console.log('🎯 第一个编辑器已激活');
            return true;
        }
        
        console.log('⚠️ 无法自动激活编辑器，请手动点击编辑器区域');
        return false;
    }
    
    // 8. 主修复流程
    console.log('🔧 开始执行修复流程...');
    
    // 步骤1: 应用ComponentTemplateManager修复
    const step1 = applyFixes();
    
    // 步骤2: 修复全局insertComponent函数
    const step2 = fixGlobalInsertComponent();
    
    // 步骤3: 激活编辑器
    const step3 = activateEditor();
    
    // 步骤4: 测试修复
    console.log('\n📊 修复结果汇总:');
    console.log(`✅ 步骤1 - 修复ComponentTemplateManager: ${step1 ? '成功' : '失败'}`);
    console.log(`✅ 步骤2 - 修复全局insertComponent: ${step2 ? '成功' : '失败'}`);
    console.log(`✅ 步骤3 - 激活编辑器: ${step3 ? '成功' : '部分成功'}`);
    
    if (step1 && step2) {
        console.log('\n🎉 修复完成! 现在可以测试组件插入功能。');
        console.log('\n👉 测试步骤:');
        console.log('1. 点击组件面板中的 "Carousel Component (WET-BOEW)"');
        console.log('2. 应该看到参数配置对话框');
        console.log('3. 填写参数后点击 "Insert Component"');
        console.log('4. 组件应该插入到编辑器');
        
        // 提供测试函数
        window.testComponentInsertion = async function(componentId = 'wet-carousel') {
            console.log(`🧪 测试组件插入: ${componentId}`);
            const result = await window.insertComponent(componentId);
            console.log(`测试结果: ${result ? '✅ 成功' : '❌ 失败'}`);
            return result;
        };
        
        console.log('\n💡 提示: 运行 testComponentInsertion() 测试组件插入');
    } else {
        console.log('\n⚠️ 修复部分完成，可能需要手动干预。');
    }
    
    console.log('\n🔧 修复脚本执行完毕。');
})();