// WebBot组件插入功能简化修复脚本
// 复制此代码到浏览器控制台(F12)并运行

console.log('🔧 开始修复组件插入功能...');

// 1. 修复waitForEditor函数
if (typeof ComponentTemplateManager !== 'undefined') {
    ComponentTemplateManager.prototype.waitForEditor = async function(maxRetries=10, interval=200) {
        for (let i=0; i<maxRetries; i++) {
            if (tinymce && tinymce.activeEditor) {
                console.log('✅ 找到tinymce.activeEditor');
                return tinymce.activeEditor;
            }
            if (window.tinyMceEditor) {
                console.log('✅ 找到window.tinyMceEditor');
                return window.tinyMceEditor;
            }
            if (tinymce && tinymce.editors && tinymce.editors.length>0) {
                console.log('✅ 找到tinymce.editors[0]');
                return tinymce.editors[0];
            }
            if (i < maxRetries-1) {
                await new Promise(r => setTimeout(r, interval));
            }
        }
        alert('请先点击编辑器区域激活编辑器！');
        throw new Error('编辑器未就绪');
    };
    
    // 2. 修复insertIntoEditor函数
    const originalInsert = ComponentTemplateManager.prototype.insertIntoEditor;
    ComponentTemplateManager.prototype.insertIntoEditor = async function(html) {
        try {
            const editor = await this.waitForEditor();
            if (!html.includes('webbot-component')) {
                html = html.replace(/<(\w+)([^>]*)>/, '<$1$2 class="webbot-component">');
            }
            console.log('✅ 插入组件:', html.substring(0,50)+'...');
            editor.insertContent(html);
            return true;
        } catch(e) {
            console.error('❌ 插入失败:', e.message);
            return false;
        }
    };
    
    console.log('✅ ComponentTemplateManager修复完成');
}

// 3. 确保编辑器激活
if (tinymce && tinymce.activeEditor) {
    tinymce.activeEditor.focus();
    console.log('🎯 编辑器已激活');
} else {
    console.log('⚠️ 请点击编辑器区域激活编辑器');
}

// 4. 测试函数
window.testFix = async function() {
    console.log('🧪 测试修复...');
    if (typeof ComponentTemplateManager === 'undefined') {
        console.error('❌ ComponentTemplateManager未定义');
        return false;
    }
    
    const manager = new ComponentTemplateManager();
    const testHTML = '<div>测试组件</div>';
    const result = await manager.insertIntoEditor(testHTML);
    console.log(`测试结果: ${result ? '✅ 成功' : '❌ 失败'}`);
    return result;
};

console.log('🔧 修复完成！');
console.log('👉 运行 testFix() 测试修复效果');
console.log('👉 现在可以测试组件插入功能了');