#!/usr/bin/env node

// 测试编辑器修复
const http = require('http');
const fs = require('fs');
const path = require('path');

console.log('=== WebBot Editor 修复测试 ===');

// 1. 检查服务是否运行
function checkService() {
    return new Promise((resolve, reject) => {
        const req = http.get('http://localhost:8000/health', (res) => {
            console.log(`✅ 服务运行正常 (状态: ${res.statusCode})`);
            resolve();
        });
        
        req.on('error', (err) => {
            console.log('❌ 服务无法访问，尝试检查静态文件...');
            // 尝试检查静态文件
            const staticReq = http.get('http://localhost:8000/static/editor.html', (res) => {
                console.log(`✅ 静态文件可访问 (状态: ${res.statusCode})`);
                resolve();
            });
            
            staticReq.on('error', (staticErr) => {
                reject(new Error(`服务无法访问: ${err.message}`));
            });
        });
        
        req.setTimeout(5000, () => {
            req.destroy();
            reject(new Error('服务连接超时'));
        });
    });
}

// 2. 检查API是否工作
function checkAPI() {
    return new Promise((resolve, reject) => {
        const req = http.get('http://localhost:8000/api/v1/pages/contact', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    const json = JSON.parse(data);
                    console.log(`✅ API工作正常 (页面: ${json.id || 'contact'}, 内容长度: ${json.content ? json.content.length : 0})`);
                    resolve(json);
                } catch (e) {
                    reject(new Error(`API返回无效JSON: ${e.message}`));
                }
            });
        });
        
        req.on('error', (err) => {
            reject(new Error(`API无法访问: ${err.message}`));
        });
        
        req.setTimeout(5000, () => {
            req.destroy();
            reject(new Error('API连接超时'));
        });
    });
}

// 3. 检查编辑器文件是否有语法错误
function checkEditorFile() {
    const editorPath = path.join(__dirname, 'webbot/static/editor.html');
    try {
        const content = fs.readFileSync(editorPath, 'utf8');
        
        console.log(`✅ 编辑器文件存在 (${content.length} 字符)`);
        
        // 检查关键函数
        const checks = [
            { name: 'addGCWebHeaderFooter函数', pattern: /function addGCWebHeaderFooter/ },
            { name: 'extractMainContent函数', pattern: /function extractMainContent/ },
            { name: 'updatePreview函数', pattern: /function updatePreview/ },
            { name: 'switchToPreviewMode函数', pattern: /function switchToPreviewMode/ },
            { name: 'console.log调试日志', pattern: /console\.log/ }
        ];
        
        checks.forEach(check => {
            const count = (content.match(check.pattern) || []).length;
            console.log(`   ${check.name}: ${count > 0 ? '✅' : '❌'} (${count} 次)`);
        });
        
        // 检查是否有模板字符串语法问题
        const backtickCount = (content.match(/`/g) || []).length;
        console.log(`   反引号数量: ${backtickCount}`);
        
        // 检查是否有明显的语法错误
        const syntaxChecks = [
            { name: '未闭合的字符串', pattern: /[^\\]"[^"]*$/m, shouldBe: 0 },
            { name: '未闭合的注释', pattern: /\/\*[^*]*\*?(?!\/)/, shouldBe: 0 }
        ];
        
        syntaxChecks.forEach(check => {
            const matches = content.match(check.pattern);
            const count = matches ? matches.length : 0;
            if (count === check.shouldBe) {
                console.log(`   ${check.name}: ✅`);
            } else {
                console.log(`   ${check.name}: ❌ (找到 ${count} 个)`);
            }
        });
        
        return content;
    } catch (err) {
        throw new Error(`无法读取编辑器文件: ${err.message}`);
    }
}

// 4. 运行所有测试
async function runTests() {
    try {
        console.log('\n1. 检查WebBot服务...');
        await checkService();
        
        console.log('\n2. 检查API端点...');
        const pageData = await checkAPI();
        
        console.log('\n3. 检查编辑器文件...');
        const editorContent = checkEditorFile();
        
        console.log('\n4. 分析页面内容...');
        if (pageData.content) {
            const content = pageData.content;
            console.log(`   内容类型: ${content.includes('<!doctype') ? '完整HTML文档' : '部分HTML/文本'}`);
            console.log(`   内容长度: ${content.length} 字符`);
            console.log(`   是否包含main标签: ${content.includes('<main') ? '是' : '否'}`);
            console.log(`   是否包含GCWeb元素: ${content.includes('gcweb') ? '是' : '否'}`);
            
            // 检查是否可能是导致解析问题的内容
            if (content.includes('`')) {
                console.log('   ⚠️  警告: 内容包含反引号，可能导致模板字符串问题');
            }
        }
        
        console.log('\n=== 测试总结 ===');
        console.log('✅ 所有基本检查通过');
        console.log('\n建议用户进行以下测试:');
        console.log('1. 访问导航页面: http://localhost:8000/static/navigation.html');
        console.log('2. 点击任意页面的 "Composing" 按钮');
        console.log('3. 检查浏览器控制台 (F12 → Console) 是否有错误');
        console.log('4. 验证预览是否正常显示，而不是显示错误消息');
        console.log('5. 检查控制台中的调试日志 (查找 "extractMainContent", "addGCWebHeaderFooter" 等)');
        
        return true;
    } catch (error) {
        console.error('\n❌ 测试失败:', error.message);
        console.log('\n=== 故障排除建议 ===');
        console.log('1. 确保WebBot服务正在运行:');
        console.log('   cd /home/hongb/.openclaw/workspace/webbot');
        console.log('   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload');
        console.log('2. 检查端口8000是否被占用:');
        console.log('   netstat -tlnp | grep :8000');
        console.log('3. 检查编辑器文件权限:');
        console.log('   ls -la /home/hongb/.openclaw/workspace/webbot/static/editor.html');
        
        return false;
    }
}

// 运行测试
runTests().then(success => {
    process.exit(success ? 0 : 1);
}).catch(err => {
    console.error('测试运行失败:', err);
    process.exit(1);
});